"""Compuerta previa a restaurar: analiza un volcado SQL leyendo bytes, sin ejecutar ni decodificar sus INSERT."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from django.conf import settings

from apps.comun import normalizacion as n
from apps.comun.legado import _parsear_valores

TipoDump = Literal["mysql_legado", "postgres_check", "desconocido"]

COLUMNAS_USUARIO = ["nip", "nombre", "clave", "tipo"]
_LINEAS_ENCABEZADO = 30
_PREFIJO_INSERT = b"INSERT INTO `"
_PREFIJO_CREATE = b"CREATE TABLE `"
_PREFIJO_COLUMNA = b"  `"
_INSERT_USUARIO = b"INSERT INTO `usuario` VALUES "
_UNRESTRICT = rb"\unrestrict"
_ERROR_POSTGRES = "No es un respaldo completo de Check Contactos."
_AVISO_CLAVE_PUBLICA = (
    "La clave temporal inicial es la clave pública por defecto; "
    "defina una propia en backend/.env antes de importar usuarios."
)
_ERROR_DESCONOCIDO = (
    "Formato no reconocido: solo se aceptan respaldos de Check Contactos o volcados MySQL del sistema anterior."
)


@dataclass
class TablaDump:
    nombre: str
    columnas: list[str]
    filas_aprox: int  # tuplas en los INSERT: "),(" + 1 por línea INSERT


@dataclass
class InformeDump:
    tipo: TipoDump
    completo: bool
    tablas: dict[str, TablaDump] = field(default_factory=dict)
    errores: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    usuarios: int = 0
    usuarios_admin: int = 0

    @property
    def valido(self) -> bool:
        return not self.errores


def _contar_usuarios(linea: bytes) -> tuple[int, int] | None:
    """Cuenta filas y administradores de un INSERT de `usuario`; la columna 2 (`clave`) nunca se conserva.

    Devuelve None si la línea está malformada o sus filas no tienen las 4 columnas esperadas.
    """
    texto = linea.decode("latin-1")
    total = admin = 0
    try:
        for fila in _parsear_valores(texto, len(_INSERT_USUARIO)):
            if len(fila) != len(COLUMNAS_USUARIO):
                return None
            total += 1
            if n.texto(fila[3]).lower() == "administrador":  # misma normalización que importar_usuarios
                admin += 1
    except (ValueError, IndexError):
        return None
    return total, admin


def _es_linea_significativa(linea: bytes) -> bool:
    r"""Descarta el adorno final de pg_dump: líneas vacías, `--` y el `\unrestrict <clave>` de pg_dump 17.6+."""
    limpia = linea.strip()
    return limpia not in (b"", b"--") and not limpia.startswith(_UNRESTRICT)


def _nombre_tabla(linea: bytes) -> str | None:
    """Nombre entre las primeras comillas invertidas de la línea; None si falta la de cierre."""
    partes = linea.split(b"`", 2)
    return partes[1].decode("latin-1") if len(partes) == 3 else None


def analizar_dump(ruta: Path) -> InformeDump:
    """Clasifica el volcado y valida su estructura; no modifica nada."""
    from apps.comun.management.commands.importar_legado import TABLAS  # noqa: PLC0415  (evita importación circular)

    tablas: dict[str, TablaDump] = {}
    actual: TablaDump | None = None
    en_create = False
    cabecera: list[bytes] = []
    ultima_linea = b""
    completo = False
    tiene_contacto_pg = tiene_usuario_pg = False
    usuarios = admin = malformadas = 0
    usuario_ilegible = False

    with ruta.open("rb") as archivo:
        for numero, linea in enumerate(archivo):
            if numero < _LINEAS_ENCABEZADO:
                cabecera.append(linea)
            if _es_linea_significativa(linea):
                ultima_linea = linea
            if en_create:
                if linea.startswith(_PREFIJO_COLUMNA) and actual is not None:
                    actual.columnas.append(linea.split(b"`")[1].decode("latin-1"))
                elif linea.startswith(b")"):
                    en_create = False
            elif linea.startswith(_PREFIJO_CREATE):
                nombre = _nombre_tabla(linea)
                if nombre is None:
                    malformadas += 1
                    continue
                actual = tablas[nombre] = TablaDump(nombre, [], 0)
                en_create = True
            elif linea.startswith(_PREFIJO_INSERT):
                nombre = _nombre_tabla(linea)
                if nombre is None:
                    malformadas += 1
                    continue
                tabla = tablas.get(nombre)
                if tabla is not None:
                    tabla.filas_aprox += linea.count(b"),(") + 1
                if linea.startswith(_INSERT_USUARIO):
                    conteo = _contar_usuarios(linea)
                    if conteo is None:
                        usuario_ilegible = True
                    else:
                        usuarios += conteo[0]
                        admin += conteo[1]
            elif linea.startswith(b"-- Dump completed"):
                completo = True
            elif linea.startswith(b"CREATE TABLE public.contactos_contacto"):
                tiene_contacto_pg = True
            elif linea.startswith(b"CREATE TABLE public.cuentas_usuario"):
                tiene_usuario_pg = True

    if any(b"MySQL dump" in linea or b"MariaDB" in linea for linea in cabecera):
        informe = InformeDump("mysql_legado", completo, tablas, usuarios=usuarios, usuarios_admin=admin)
        _validar_mysql(informe, TABLAS)
        if malformadas:
            informe.errores.append(f"El volcado tiene {malformadas} líneas SQL malformadas.")
        if usuario_ilegible and not any("`usuario`" in e for e in informe.errores):
            informe.errores.append("No se pudieron leer las filas de la tabla `usuario`.")
        return informe

    if any(linea.strip() == b"-- PostgreSQL database dump" for linea in cabecera):
        terminado = ultima_linea.strip() == b"-- PostgreSQL database dump complete"
        informe = InformeDump("postgres_check", terminado)
        if not (terminado and tiene_contacto_pg and tiene_usuario_pg):
            informe.errores.append(_ERROR_POSTGRES)
        return informe

    return InformeDump("desconocido", False, errores=[_ERROR_DESCONOCIDO])


def _validar_mysql(informe: InformeDump, requeridas: list) -> None:  # type: ignore[type-arg]
    """Agrega errores y advertencias de un volcado MySQL del sistema anterior."""
    if not informe.completo:
        informe.errores.append("El archivo está incompleto: falta la marca final del volcado.")
    conocidas = {t.legada for t in requeridas} | {"usuario"}
    for tabla in requeridas:
        encontrada = informe.tablas.get(tabla.legada)
        if encontrada is None:
            informe.errores.append(f"Falta la tabla `{tabla.legada}` en el volcado.")
        elif len(encontrada.columnas) != tabla.columnas:
            informe.errores.append(
                f"La tabla `{tabla.legada}` tiene {len(encontrada.columnas)} columnas; se esperaban {tabla.columnas}."
            )
        elif encontrada.filas_aprox == 0:
            informe.advertencias.append(
                f"La tabla `{tabla.legada}` está vacía: sus datos actuales se reemplazarán por nada."
            )
    usuario = informe.tablas.get("usuario")
    if usuario is not None and usuario.columnas != COLUMNAS_USUARIO:
        informe.errores.append("La tabla `usuario` no tiene las columnas esperadas (nip, nombre, clave, tipo).")
    sobrantes = sum(1 for nombre in informe.tablas if nombre not in conocidas)
    if sobrantes:
        informe.advertencias.append(f"{sobrantes} tablas del sistema anterior no se importan.")
    if informe.usuarios_admin:
        informe.advertencias.append(
            f"{informe.usuarios_admin} cuentas con rol administrador se crearán inactivas; actívelas desde Usuarios."
        )
    clave = (settings.CLAVE_TEMPORAL_INICIAL or "").strip()
    if informe.usuarios and clave == settings.CLAVE_TEMPORAL_PUBLICA:
        informe.advertencias.append(_AVISO_CLAVE_PUBLICA)
