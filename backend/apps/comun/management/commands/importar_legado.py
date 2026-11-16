"""Importa las 10 tablas de datos (más `usuario`) del dump legado de MySQL a PostgreSQL.

Uso: python manage.py importar_legado ../CONTACTOS_recuperado_2026-11-07.sql

- Lee el dump en streaming, extrae valores de los INSERT (nunca ejecuta SQL del dump).
- Valida el volcado antes de tocar nada y lo importa todo en una sola transacción: si falla, no cambia nada.
- La columna legada `usuario.clave` NUNCA se lee: las cuentas se crean con `crear_cuentas_temporales`.
- Las filas inválidas van a `comun_importacion_rechazo`; ninguna se descarta en silencio.
"""

import logging
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection, models, transaction
from django.utils import timezone

from apps.comun import normalizacion as n
from apps.comun.legado import Valor, filas_de_tabla
from apps.comun.models import ImportacionRechazo
from apps.contactos.models import Contacto
from apps.cuentas.models import ROLES, Ingreso, Usuario
from apps.llamadas.models import LlamadaCumpleanos, LlamadaRtm, LlamadaSoat
from apps.revisiones.models import Revision, Soat
from apps.vehiculos.models import Linea, Marca, Moto

if TYPE_CHECKING:
    from apps.comun.analisis_dump import InformeDump

logger = logging.getLogger(__name__)
LOTE = 5000


AlAvanzar = Callable[[str, int, int], None]


class FilaInvalidaError(Exception):
    """La fila no se puede convertir; se registra como rechazo."""


@dataclass
class Resultado:
    tabla: str
    origen: int = 0
    insertadas: int = 0
    rechazadas: int = 0
    duplicadas: int = 0
    omitidas: int = 0
    normalizadas: dict[str, int] = field(default_factory=dict)

    def contar(self, motivo: str) -> None:
        self.normalizadas[motivo] = self.normalizadas.get(motivo, 0) + 1


# --- Conversores fila legada → instancia ---------------------------------------------------


def conv_marca(f: list[Valor], r: Resultado) -> Marca:
    codigo = n.texto(f[0])
    if not codigo:
        raise FilaInvalidaError("código vacío")
    return Marca(codigo=codigo, nombre=n.texto(f[1]) or codigo)


def conv_linea(f: list[Valor], r: Resultado) -> Linea:
    linea = n.texto(f[0])
    if not linea:
        raise FilaInvalidaError("línea vacía")
    return Linea(linea=linea, marca_id=n.texto(f[1]))


def conv_contacto(f: list[Valor], r: Resultado) -> Contacto:
    nip = n.mayusculas_sin_espacios(f[0])
    if not nip:
        raise FilaInvalidaError("documento vacío")
    if n.texto(f[5]) and n.mes(f[5]) is None:
        r.contar("mes de nacimiento no reconocido → vacío")
    if f[9] not in ("habilitado", "inhabilitado"):
        r.contar("estado vacío → habilitado")
    return Contacto(
        nip=nip,
        nombre=n.texto(f[1]).upper(),
        telefono="" if n.texto(f[2]) in ("0", "") else n.texto(f[2]),
        celular="" if n.texto(f[3]) in ("0", "") else n.texto(f[3]),
        dia_nac=n.dia(f[4]),
        mes_nac=n.mes(f[5]),
        direccion="" if n.texto(f[6]).upper() == "ND" else n.texto(f[6]),
        correo="" if n.texto(f[7]).upper() == "ND" else n.texto(f[7]).lower(),
        usuario=n.texto(f[8]),
        estado=n.estado_contacto(f[9]),
        fecha_registro=n.fecha_hora(f[10]),
        cumple_confir=n.entero(f[11]) == 1,
    )


def conv_moto(f: list[Valor], r: Resultado) -> Moto:
    placa = n.placa(f[0])
    if not placa:
        raise FilaInvalidaError("placa vacía")
    fechas = [n.fecha(f[i]) for i in (5, 6, 9, 10)]
    for indice, valor in zip((5, 6, 9, 10), fechas, strict=True):
        if valor is None and n.texto(f[indice]) not in ("", "0000-00-00"):
            r.contar("fecha de moto no reconocida → vacía")
    return Moto(
        placa=placa,
        marca=n.texto(f[1]).upper(),
        modelo=n.texto(f[2])[:4],
        linea=n.texto(f[3]),
        nro_soat="" if n.texto(f[4]) == "0" else n.texto(f[4]),
        fecha_venc_soat=fechas[0],
        fecha_venc_rtmg=fechas[1],
        contacto_id=n.mayusculas_sin_espacios(f[7]),
        nro_certificado="" if n.texto(f[8]) == "0" else n.texto(f[8]),
        fecha_rtmg=fechas[2],
        fecha_soat=fechas[3],
    )


def conv_revision(f: list[Valor], r: Resultado) -> Revision:
    certificado = n.texto(f[1]).upper()
    if not certificado:
        raise FilaInvalidaError("certificado vacío")
    if f[11] is None:
        r.contar("estado vacío → VENCIDO")
    return Revision(
        soat=n.texto(f[0]),
        certificado=certificado,
        fecha_soat=n.fecha(f[2]),
        fecha_venc_soat=n.fecha(f[3]),
        fecha_certificado=n.fecha(f[4]),
        fecha_venc_certificado=n.fecha(f[5]),
        moto_id=n.placa(f[6]),
        nro_autodeclaracion_runt=n.texto(f[7]),
        nro_solicitud_runt=n.texto(f[8]),
        nro_certificado_runt=n.texto(f[9]),
        fecha_registro_runt=n.fecha(f[10]),
        estado=n.estado_documento(f[11]),
        fecha_registro=n.fecha_hora(f[12]),
        usuario=n.texto(f[13]),
    )


def conv_soat(f: list[Valor], r: Resultado) -> Soat:
    numero = n.texto(f[0]).upper()
    if not numero:
        raise FilaInvalidaError("póliza vacía")
    placa = n.placa(f[3])
    return Soat(
        soat=numero,
        fecha_soat=n.fecha(f[1]),
        fecha_venc_soat=n.fecha(f[2]),
        moto_id=placa or None,
        estado=n.estado_documento(f[4]),
        usuario=n.texto(f[5]),
        fecha_registro=n.fecha_hora(f[6]),
    )


def conv_llamada_cumple(f: list[Valor], r: Resultado) -> LlamadaCumpleanos:
    fecha = n.fecha_hora(f[1])
    if fecha is None:
        raise FilaInvalidaError("fecha inválida")
    estado = n.estado_llamada(f[2])
    if n.texto(f[2]).lower() == "no realizada":
        r.contar("estado 'no realizada' → no_realizada")
    if estado == "sin_estado":
        r.contar("estado vacío → sin_estado")
    num, marcas = n.intentos_llamada(f[7])
    return LlamadaCumpleanos(
        id=n.entero(f[0]),
        fecha=fecha,
        estado=estado,
        observacion="" if n.texto(f[3]).lower() == "nd" else n.texto_multilinea(f[3]),
        contacto_id=n.mayusculas_sin_espacios(f[4]),
        motivo_llamada="cumpleanos",
        usuario=n.texto(f[6]),
        num_llamadas=num or 1,
        intentos=marcas,
    )


def _conv_llamada_placa(modelo: type[models.Model], indice_num: int, indice_marcas: int) -> Callable[..., Any]:
    def convertir(f: list[Valor], r: Resultado) -> Any:
        identificador = n.texto(f[0]).upper()
        fecha = n.fecha(f[1])
        if not identificador or fecha is None:
            raise FilaInvalidaError("id o fecha inválidos")
        motivo = n.texto(f[5]).lower()
        return modelo(
            id=identificador,
            fecha=fecha,
            estado=n.estado_llamada(f[2]),
            observacion=n.texto_multilinea(f[3]),
            moto_id=n.placa(f[4]),
            motivo_llamada=motivo if motivo in ("rtmyg", "soat") else "rtmyg",
            usuario=n.texto(f[6]),
            num_llamadas=n.entero(f[indice_num], 1) or 1,
            intentos=n.texto(f[indice_marcas]),
        )

    return convertir


def conv_ingreso(f: list[Valor], r: Resultado) -> Ingreso:
    fecha = n.fecha_entrada_sistema(f[1])
    if fecha is None:
        raise FilaInvalidaError("fecha de ingreso no reconocida")
    return Ingreso(id=n.entero(f[0]), fecha=fecha, nip_usuario=n.texto(f[2])[:45], exitoso=True, origen="legado")


@dataclass
class Tabla:
    legada: str
    modelo: type[models.Model]
    convertir: Callable[[list[Valor], Resultado], models.Model]
    columnas: int


TABLAS = [
    Tabla("marca", Marca, conv_marca, 2),
    Tabla("linea", Linea, conv_linea, 2),
    Tabla("contacto", Contacto, conv_contacto, 12),
    Tabla("moto", Moto, conv_moto, 11),
    Tabla("revision", Revision, conv_revision, 14),
    Tabla("soat1", Soat, conv_soat, 7),
    Tabla("bitacora_llamadas", LlamadaCumpleanos, conv_llamada_cumple, 8),
    Tabla("bitacora_llamadas_rtmyg", LlamadaRtm, _conv_llamada_placa(LlamadaRtm, 7, 8), 9),
    Tabla("bitacora_llamadas_soat", LlamadaSoat, _conv_llamada_placa(LlamadaSoat, 8, 7), 9),
    Tabla("entrada_sistema", Ingreso, conv_ingreso, 3),
]


def ajustar_longitudes(instancia: models.Model, resultado: Resultado) -> None:
    """Recorta los textos que exceden `max_length`; si es la clave primaria, la fila se rechaza."""
    for campo in instancia._meta.fields:
        if not isinstance(campo, models.CharField) or not campo.max_length:
            continue
        valor = getattr(instancia, campo.attname)
        if not isinstance(valor, str) or len(valor) <= campo.max_length:
            continue
        if campo.primary_key:
            raise FilaInvalidaError(f"{campo.name} excede {campo.max_length} caracteres")
        setattr(instancia, campo.attname, valor[: campo.max_length])
        resultado.contar(f"{campo.name} recortado a {campo.max_length} caracteres")


def _lotes(iterable: Iterator[models.Model], tamano: int) -> Iterator[list[models.Model]]:
    lote: list[models.Model] = []
    for elemento in iterable:
        lote.append(elemento)
        if len(lote) >= tamano:
            yield lote
            lote = []
    if lote:
        yield lote


@contextmanager
def _datos_legibles(tabla: str) -> Iterator[None]:
    """Convierte un error del autómata de `legado.py` en un mensaje sin valores de las filas (NIP, placas)."""
    try:
        yield
    except (ValueError, IndexError) as exc:
        logger.error("Datos ilegibles en la tabla legada %s (%s)", tabla, type(exc).__name__)
        raise CommandError(
            f"El volcado tiene datos ilegibles en la tabla `{tabla}`; no se modificó la base de datos."
        ) from exc


def importar_tabla(ruta: Path, tabla: Tabla) -> Resultado:
    """Carga una tabla (savepoint dentro de `importar_dump`). Las PK repetidas se registran como rechazo."""
    resultado = Resultado(tabla.legada)
    vistas: set[Any] = set()
    rechazos: list[ImportacionRechazo] = []

    def instancias() -> Iterator[models.Model]:
        for fila in filas_de_tabla(ruta, tabla.legada):
            resultado.origen += 1
            try:
                if len(fila) != tabla.columnas:
                    raise FilaInvalidaError(f"se esperaban {tabla.columnas} columnas y llegaron {len(fila)}")
                instancia = tabla.convertir(fila, resultado)
                ajustar_longitudes(instancia, resultado)
            except FilaInvalidaError as exc:
                rechazos.append(ImportacionRechazo(tabla=tabla.legada, fila_origen=repr(fila)[:2000], motivo=str(exc)))
                resultado.rechazadas += 1
                continue
            clave = instancia.pk
            if clave in vistas:
                rechazos.append(
                    ImportacionRechazo(
                        tabla=tabla.legada, fila_origen=repr(fila)[:2000], motivo="clave repetida en el legado"
                    )
                )
                resultado.duplicadas += 1
                continue
            vistas.add(clave)
            yield instancia

    with transaction.atomic():
        tabla.modelo._default_manager.all()._raw_delete(tabla.modelo._default_manager.db)  # type: ignore[attr-defined]
        ImportacionRechazo.objects.filter(tabla=tabla.legada).delete()
        with _datos_legibles(tabla.legada):
            for lote in _lotes(instancias(), LOTE):
                tabla.modelo._default_manager.bulk_create(lote, batch_size=LOTE)
                resultado.insertadas += len(lote)
        ImportacionRechazo.objects.bulk_create(rechazos, batch_size=LOTE)
        _ajustar_secuencia(tabla.modelo)
    return resultado


def importar_usuarios(ruta: Path) -> Resultado:
    """Crea las cuentas nuevas con `CLAVE_TEMPORAL_INICIAL` y cambio obligatorio (corre dentro de `importar_dump`).

    Solo se leen nip (0), nombre (1) y tipo (3): la columna 2 (`clave`) nunca se toca.
    Las cuentas que ya existen no se modifican y cuentan como omitidas.
    Las cuentas con rol administrador se crean inactivas (un administrador actual debe activarlas), y si la
    clave temporal es la pública por defecto no se crea ninguna: cualquiera la conoce.
    """
    resultado = Resultado("usuario")
    clave_inicial = (settings.CLAVE_TEMPORAL_INICIAL or "").strip()
    if clave_inicial == settings.CLAVE_TEMPORAL_PUBLICA:
        clave_inicial = ""
        motivo_sin_clave = "CLAVE_TEMPORAL_INICIAL es la clave pública por defecto: usuarios no importados"
    else:
        motivo_sin_clave = "CLAVE_TEMPORAL_INICIAL no configurada: usuarios no importados"
    roles = {codigo for codigo, _ in ROLES}
    ImportacionRechazo.objects.filter(tabla="usuario").delete()
    existentes = set(Usuario.objects.values_list("nip", flat=True))
    vistos: set[str] = set()
    rechazos: list[ImportacionRechazo] = []
    sin_clave_avisado = False

    def rechazar(fila: list[Valor], motivo: str, *, duplicada: bool = False) -> None:
        # Nunca se copia la fila completa: contendría la clave legada.
        origen = repr([fila[0], fila[1], fila[3]] if len(fila) == 4 else [])[:2000]
        rechazos.append(ImportacionRechazo(tabla="usuario", fila_origen=origen, motivo=motivo))
        if duplicada:
            resultado.duplicadas += 1
        else:
            resultado.rechazadas += 1

    with _datos_legibles("usuario"):
        filas = list(filas_de_tabla(ruta, "usuario"))  # pocas filas: se leen de una vez
    for fila in filas:
        resultado.origen += 1
        if len(fila) != 4:
            rechazar(fila, f"se esperaban 4 columnas y llegaron {len(fila)}")
            continue
        nip = n.mayusculas_sin_espacios(fila[0])
        if not nip:
            rechazar(fila, "nip vacío")
            continue
        if len(nip) > 20:
            rechazar(fila, "nip excede 20 caracteres")
            continue
        if nip in vistos:
            rechazar(fila, "clave repetida en el legado", duplicada=True)
            continue
        vistos.add(nip)
        if nip in existentes:
            resultado.omitidas += 1
            continue
        if not clave_inicial:
            resultado.omitidas += 1
            if not sin_clave_avisado:
                resultado.contar(motivo_sin_clave)
                sin_clave_avisado = True
            continue
        tipo = n.texto(fila[3])
        rol = tipo.lower()
        if rol not in roles:
            resultado.contar(f"tipo '{tipo}' → usuario")
            rol = "usuario"
        nombre = n.texto(fila[1]).upper()
        if len(nombre) > 255:
            nombre = nombre[:255]
            resultado.contar("nombre recortado a 255 caracteres")
        es_admin = rol == "administrador"
        if es_admin:
            resultado.contar("administrador legado creado inactivo")
        cuenta = Usuario(nip=nip, nombre=nombre, rol=rol, debe_cambiar_clave=True, is_active=not es_admin)
        cuenta.set_password(clave_inicial)
        cuenta.save()
        cuenta.sincronizar_grupo()
        resultado.insertadas += 1
    ImportacionRechazo.objects.bulk_create(rechazos, batch_size=LOTE)
    return resultado


# El parámetro `importar_usuarios` de `importar_dump` oculta la función; se usa este alias.
_importar_cuentas = importar_usuarios


def _ajustar_secuencia(modelo: type[models.Model]) -> None:
    """Tras insertar ids explícitos, la secuencia autoincremental continúa desde el máximo (utilidad de Django)."""
    from django.core.management.color import no_style

    with connection.cursor() as cursor:
        for sentencia in connection.ops.sequence_reset_sql(no_style(), [modelo]):
            cursor.execute(sentencia)


def huerfanos() -> dict[str, int]:
    """Relaciones lógicas sin registro destino (no se eliminan; se informan)."""
    placas = Moto.objects.values("placa")
    return {
        "motos sin contacto": Moto.objects.exclude(contacto_id__in=Contacto.objects.values("nip")).count(),
        "revisiones con placa sin moto": Revision.objects.exclude(moto_id__in=placas).count(),
        "SOAT con placa sin moto": Soat.objects.exclude(moto_id__in=placas).exclude(moto_id__isnull=True).count(),
        "llamadas de cumpleaños sin contacto": LlamadaCumpleanos.objects.exclude(
            contacto_id__in=Contacto.objects.values("nip")
        ).count(),
        "llamadas RTM con placa sin moto": LlamadaRtm.objects.exclude(moto_id__in=placas).count(),
        "llamadas SOAT con placa sin moto": LlamadaSoat.objects.exclude(moto_id__in=placas).count(),
        "líneas con marca inexistente": Linea.objects.exclude(marca_id__in=Marca.objects.values("codigo")).count(),
    }


def _cuadra(r: Resultado) -> bool:
    return r.insertadas + r.rechazadas + r.duplicadas + r.omitidas == r.origen


def importar_dump(
    ruta: Path,
    *,
    elegidas: set[str] | None = None,
    importar_usuarios: bool = True,
    al_avanzar: AlAvanzar | None = None,
    analisis: "InformeDump | None" = None,
    destino_informe: Path | None = None,
) -> tuple[list[Resultado], dict[str, int]]:
    """Valida el volcado y lo importa en una sola transacción. Devuelve (resultados por tabla, huérfanos).

    `analisis` evita recorrer otra vez el archivo si quien llama ya lo analizó. Si alguna tabla no cuadra, antes
    de deshacer todo se escribe el informe (en `destino_informe` o el predeterminado) marcado como revertido.
    """
    from django.apps import apps as registro

    from apps.comun.analisis_dump import analizar_dump
    from apps.comun.saneamiento import sanear_datos_legados

    informe_dump = analisis if analisis is not None else analizar_dump(ruta)
    if not informe_dump.valido or informe_dump.tipo != "mysql_legado":
        raise CommandError("; ".join(informe_dump.errores) or "El archivo no es un volcado MySQL del legado.")
    tablas = [t for t in TABLAS if elegidas is None or t.legada in elegidas]
    resultados: list[Resultado] = []
    inicio = time.monotonic()
    actual = ""
    try:
        with transaction.atomic():
            for tabla in reversed(tablas):
                tabla.modelo._default_manager.all()._raw_delete(tabla.modelo._default_manager.db)  # type: ignore[attr-defined]
            for indice, tabla in enumerate(tablas, start=1):
                actual = tabla.legada
                resultados.append(importar_tabla(ruta, tabla))
                if al_avanzar:
                    al_avanzar(tabla.legada, indice, len(tablas))
            if importar_usuarios:
                actual = "usuario"
                resultados.append(_importar_cuentas(ruta))
            actual = ""
            sanear_datos_legados(registro)
            faltantes = huerfanos()
            malas = [r.tabla for r in resultados if not _cuadra(r)]
            if malas:
                escribir_informe(resultados, faltantes, time.monotonic() - inicio, destino_informe, revertida=True)
                raise CommandError(f"Hay tablas que no cuadran ({', '.join(malas)}); no se importó nada.")
    except CommandError:
        raise
    except Exception as exc:  # fallo de BD u otro imprevisto: la transacción ya se revirtió
        # Sin str(exc) ni traza: podrían contener valores de las filas (NIP, placas).
        logger.error("Falló la importación del legado en la tabla %r (%s)", actual, type(exc).__name__)
        raise CommandError(
            f"No se pudo importar el volcado ({type(exc).__name__}); no se modificó la base de datos."
        ) from exc
    return resultados, faltantes


_AVISO_REVERTIDA = [
    "**IMPORTACIÓN REVERTIDA: hay tablas que no cuadran.** La base de datos quedó como estaba y tampoco se",
    "guardaron los rechazos de esta corrida; los conteos de abajo sirven para ubicar la tabla con problemas.",
    "",
]


def informe(resultados: list[Resultado], faltantes: dict[str, int], segundos: float, *, revertida: bool = False) -> str:
    """Informe en Markdown, sin datos personales."""
    ahora = timezone.localtime()
    lineas = [
        "---",
        "persona: oscar",
        "ia: Claude Code (Claude Opus 5.5)",
        f"actualizado: {ahora:%Y-%m-%d %H:%M}",
        "zona_horaria: America/Bogota",
        "---",
        f"# Informe de importación del legado — {ahora:%Y-%m-%d %H:%M}",
        "",
        *(_AVISO_REVERTIDA if revertida else []),
        f"Duración: {segundos:.0f} s. Regla de cuadre: insertadas + rechazadas + duplicadas + omitidas = filas de origen.",
        "",
        "| Tabla legada | Origen | Insertadas | Rechazadas | Duplicadas | Omitidas | ¿Cuadra? |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in resultados:
        cuadra = _cuadra(r)
        marca = "Sí" if cuadra else "NO"
        lineas.append(
            f"| {r.tabla} | {r.origen} | {r.insertadas} | {r.rechazadas} | {r.duplicadas} | {r.omitidas} | {marca} |"
        )
    lineas += ["", "## Normalizaciones", ""]
    for r in resultados:
        for motivo, cantidad in sorted(r.normalizadas.items()):
            lineas.append(f"- {r.tabla}: {motivo} ({cantidad})")
    lineas += [
        "",
        "## Huérfanos (se conservan; decisión pendiente con la empresa)",
        "",
        *[f"- {nombre}: {cantidad}" for nombre, cantidad in faltantes.items()],
        "",
        "Las filas rechazadas y duplicadas están en Django Admin → Común → Rechazos de importación.",
        "",
    ]
    return "\n".join(lineas)


def escribir_informe(
    resultados: list[Resultado],
    faltantes: dict[str, int],
    segundos: float,
    destino: Path | None = None,
    *,
    revertida: bool = False,
) -> Path:
    """Escribe el informe Markdown (por defecto en `logs/importacion-*.md`) y devuelve su ruta."""
    destino = destino or Path(__file__).resolve().parents[5] / "logs" / (
        f"importacion-{timezone.localtime():%Y-%m-%d-%H%M}.md"
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(informe(resultados, faltantes, segundos, revertida=revertida), encoding="utf-8")
    return destino


class Command(BaseCommand):
    help = "Importa el dump legado de MySQL (10 tablas de datos y usuarios) a PostgreSQL."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("dump", type=Path, help="Ruta al archivo .sql del legado.")
        parser.add_argument("--tablas", nargs="*", help="Importar solo estas tablas legadas.")
        parser.add_argument("--sin-usuarios", action="store_true", help="No importar las cuentas del legado.")
        parser.add_argument("--informe", type=Path, default=None, help="Ruta del informe Markdown.")

    def handle(self, *args: Any, **opciones: Any) -> None:
        ruta: Path = opciones["dump"]
        if not ruta.is_file():
            raise CommandError(f"No existe el archivo {ruta}.")
        elegidas = set(opciones["tablas"]) if opciones["tablas"] else None
        inicio = time.monotonic()

        def avance(tabla: str, indice: int, total: int) -> None:
            self.stdout.write(f"[{indice}/{total}] {tabla}")

        resultados, faltantes = importar_dump(
            ruta,
            elegidas=elegidas,
            importar_usuarios=not opciones["sin_usuarios"],
            al_avanzar=avance,
            destino_informe=opciones["informe"],
        )
        for r in resultados:
            self.stdout.write(
                f"{r.tabla:26} origen={r.origen:>7} insertadas={r.insertadas:>7} "
                f"rechazadas={r.rechazadas:>4} duplicadas={r.duplicadas:>4} omitidas={r.omitidas:>4}"
            )
        destino = escribir_informe(resultados, faltantes, time.monotonic() - inicio, opciones["informe"])
        self.stdout.write(self.style.SUCCESS(f"Informe: {destino}"))
