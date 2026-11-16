"""Servicios para la gestión y ejecución de copias de seguridad de la base de datos."""

import json
import logging
import os
import re
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone

from apps.comun.analisis_dump import analizar_dump

logger = logging.getLogger(__name__)

RUTA_DEFAULT_RESPALDOS = settings.BASE_DIR.parent / "respaldos"
ARCHIVO_CONFIG_RESPALDO = RUTA_DEFAULT_RESPALDOS / "config_respaldo.json"
ARCHIVO_ESTADO_RESPALDO = settings.BASE_DIR.parent / "logs" / "respaldo_estado.json"
SEGUNDOS_SIN_SENAL = 900  # sin escrituras de estado en 15 min, la operación se da por abortada


def es_cliente_servidor_local(request: HttpRequest) -> bool:
    """Verifica si la petición HTTP proviene de la propia máquina servidora."""
    # 1. Comprobación por Host de destino local (localhost, 127.0.0.1 o ::1)
    try:
        host = request.get_host().split(":")[0].strip().lower()
        if host in ("localhost", "127.0.0.1", "::1"):
            return True
    except Exception:
        pass

    # 2. Comprobación por IP de origen (directa o reenviada por proxy inverso)
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        ip = x_forwarded.split(",")[0].strip()
    else:
        ip = request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR", "").strip()

    if ip in ("127.0.0.1", "::1", "localhost", "testclient"):
        return True

    # 3. IPs de interfaces de red locales
    try:
        ips_locales = {
            ip_info[4][0]
            for ip_info in socket.getaddrinfo(socket.gethostname(), None)
            if ip_info[4]
        }
        if ip in ips_locales:
            return True
    except Exception:
        pass

    return False


def formatear_tamano(bytes_totales: int) -> str:
    """Convierte un tamaño en bytes a representación legible (KB, MB, GB)."""
    if bytes_totales < 1024:
        return f"{bytes_totales} B"
    if bytes_totales < 1024 * 1024:
        return f"{bytes_totales / 1024:.1f} KB"
    if bytes_totales < 1024 * 1024 * 1024:
        return f"{bytes_totales / (1024 * 1024):.1f} MB"
    return f"{bytes_totales / (1024 * 1024 * 1024):.2f} GB"


def generar_nombre_archivo_respaldo(
    destino: Path, nombre_bd: str = "check_contactos", fecha: datetime | None = None
) -> Path:
    """Genera la ruta del archivo con nomenclatura estricta <nombre_bd>-DD-MM-YYYY.sql y sufijo si colisiona."""
    fecha_ref = fecha or datetime.now()
    fecha_str = fecha_ref.strftime("%d-%m-%Y")
    nombre_base = f"{nombre_bd}-{fecha_str}.sql"
    archivo = destino / nombre_base

    if not archivo.exists():
        return archivo

    consecutivo = 1
    while True:
        nombre_consecutivo = f"{nombre_bd}-{fecha_str}_{consecutivo:02d}.sql"
        candidato = destino / nombre_consecutivo
        if not candidato.exists():
            return candidato
        consecutivo += 1


def es_ruta_absoluta(ruta_str: str) -> bool:
    """Verifica si una ruta es absoluta tanto en formato Windows como POSIX."""
    limpio = (ruta_str or "").strip()
    if not limpio:
        return False
    # Formato Windows con unidad (ej. C:\..., F:/...)
    if re.match(r"^[a-zA-Z]:[\\/]", limpio):
        return True
    # Rutas UNC Windows (ej. \\servidor\compartido)
    if limpio.startswith(("\\\\", "//")):
        return True
    # Rutas POSIX absolutas (ej. /app/respaldos)
    if limpio.startswith("/"):
        return True
    try:
        return PureWindowsPath(limpio).is_absolute() or PurePosixPath(limpio).is_absolute()
    except Exception:
        return False


def mapear_ruta_windows_a_posix(ruta_str: str) -> str:
    """Traduce una ruta Windows (ej: F:\\Prueba) a su ruta equivalente en el contenedor Linux (/mnt/f/Prueba)."""
    limpio = (ruta_str or "").strip()
    match_drive = re.match(r"^([a-zA-Z]):[\\/](.*)$", limpio)
    if not match_drive:
        return limpio
    letra = match_drive.group(1).lower()
    resto = match_drive.group(2).replace("\\", "/").strip("/")
    return f"/mnt/{letra}/{resto}" if resto else f"/mnt/{letra}"


def resolver_ruta_sistema(ruta_str: str) -> Path:
    """
    Resuelve una ruta (Windows o POSIX) al objeto Path local del sistema.
    Si estamos en Linux (e.g. contenedor Docker) y se recibe una ruta con letra de unidad Windows
    (por ejemplo: 'F:\\Prueba' o 'F:\\Check\\respaldos'), se mapea al punto de montaje correspondiente
    (/mnt/f/Prueba o /app/respaldos si está dentro de la raíz del proyecto).
    """
    limpio = (ruta_str or "").strip()
    if not limpio:
        return Path()

    # Si estamos en Windows nativo
    if os.name == "nt":
        return Path(limpio)

    # Si estamos en Linux / POSIX (e.g. dentro del contenedor Docker)
    posix_str = mapear_ruta_windows_a_posix(limpio)
    ruta = Path(posix_str)

    # Si apunta a F:\Check\... pero /mnt/f aún no está montado, mapear a /app/...
    match_drive = re.match(r"^([a-zA-Z]):[\\/](.*)$", limpio)
    if match_drive:
        letra = match_drive.group(1).lower()
        resto = match_drive.group(2).replace("\\", "/").strip("/")
        if letra == "f" and (resto.lower().startswith("check/") or resto.lower() == "check"):
            ruta_mnt_f = Path("/mnt/f")
            if not ruta_mnt_f.exists():
                sub_resto = re.sub(r"^check/?", "", resto, flags=re.IGNORECASE).strip("/")
                return Path("/app") / sub_resto if sub_resto else Path("/app")

    return ruta


def obtener_ruta_configurada_display() -> str:
    """Obtiene la ruta configurada en su formato legible para el cliente."""
    if ARCHIVO_CONFIG_RESPALDO.exists():
        try:
            datos = json.loads(ARCHIVO_CONFIG_RESPALDO.read_text(encoding="utf-8"))
            ruta_str = datos.get("ruta")
            if ruta_str:
                return ruta_str
        except Exception:
            pass
    return str(RUTA_DEFAULT_RESPALDOS)


def obtener_ruta_respaldo() -> Path:
    """Obtiene la ruta configurada para respaldos o la predeterminada."""
    if ARCHIVO_CONFIG_RESPALDO.exists():
        try:
            datos = json.loads(ARCHIVO_CONFIG_RESPALDO.read_text(encoding="utf-8"))
            ruta_str = datos.get("ruta")
            if ruta_str:
                ruta = resolver_ruta_sistema(ruta_str)
                if not ruta.exists():
                    try:
                        ruta.mkdir(parents=True, exist_ok=True)
                    except Exception:
                        pass
                if ruta.exists() and ruta.is_dir():
                    return ruta
        except Exception as exc:
            logger.warning("No se pudo leer la configuración de respaldo: %s", exc)

    RUTA_DEFAULT_RESPALDOS.mkdir(parents=True, exist_ok=True)
    return RUTA_DEFAULT_RESPALDOS


def validar_ruta_servidor(
    ruta_str: str, crear_si_no_existe: bool = True
) -> tuple[bool, str, Path | None]:
    """Valida que una ruta exista en el disco del servidor, sea directorio y tenga permisos de escritura."""
    limpio = (ruta_str or "").strip()
    if not limpio:
        return False, "La ruta no puede estar vacía.", None

    if not es_ruta_absoluta(limpio):
        return False, "La ruta debe ser absoluta (por ejemplo: F:\\Check\\respaldos).", None

    try:
        ruta = resolver_ruta_sistema(limpio)

        if not ruta.exists():
            if crear_si_no_existe:
                try:
                    ruta.mkdir(parents=True, exist_ok=True)
                except Exception as exc:
                    return False, f"La carpeta '{limpio}' no existe y no pudo ser creada en el servidor: {exc}", None
            else:
                return False, f"La carpeta '{limpio}' no existe en el disco del servidor.", None

        if not ruta.is_dir():
            return False, f"La ruta '{limpio}' no corresponde a una carpeta.", None

        # Prueba de escritura en el servidor
        archivo_prueba = ruta / f".test_permiso_{uuid4().hex[:8]}.tmp"
        try:
            archivo_prueba.write_text("permiso_ok", encoding="utf-8")
            archivo_prueba.unlink(missing_ok=True)
        except Exception as exc:
            return False, f"La carpeta '{limpio}' no tiene permisos de escritura: {exc}", None

        return True, "Ruta válida y con permisos de escritura confirmados.", ruta
    except Exception as exc:
        return False, f"Ruta inválida: {exc}", None


def guardar_ruta_respaldo(nueva_ruta: Path | str) -> str:
    """Guarda la nueva ruta de respaldo en el archivo de configuración."""
    RUTA_DEFAULT_RESPALDOS.mkdir(parents=True, exist_ok=True)
    ruta_str = str(nueva_ruta)
    contenido = {
        "ruta": ruta_str,
        "actualizado_en": timezone.now().isoformat(),
    }
    ARCHIVO_CONFIG_RESPALDO.write_text(json.dumps(contenido, indent=2), encoding="utf-8")
    return ruta_str


def obtener_info_ultimo_respaldo(ruta: Path) -> dict[str, Any] | None:
    """Busca el archivo de respaldo más reciente en la carpeta indicada."""
    if not ruta.exists() or not ruta.is_dir():
        return None
    archivos = list(ruta.glob("*.sql"))
    if not archivos:
        return None
    mas_reciente = max(archivos, key=lambda a: a.stat().st_mtime)
    stat = mas_reciente.stat()
    fecha_creacion = datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone())
    return {
        "archivo": mas_reciente.name,
        "tamano_bytes": stat.st_size,
        "tamano_formateado": formatear_tamano(stat.st_size),
        "creado_en": fecha_creacion.isoformat(),
    }


def leer_estado_ejecucion() -> dict[str, Any]:
    """Lee el estado actual de ejecución desde el archivo de estado."""
    if ARCHIVO_ESTADO_RESPALDO.exists():
        try:
            datos = json.loads(ARCHIVO_ESTADO_RESPALDO.read_text(encoding="utf-8"))
            if datos.get("ejecutando"):
                # Si lleva más de 15 minutos sin publicar avance, el proceso se considera abortado.
                ultima_senal = datos.get("actualizado_en") or datos.get("iniciado_en")
                if ultima_senal:
                    delta = timezone.now() - datetime.fromisoformat(ultima_senal)
                    if delta.total_seconds() > SEGUNDOS_SIN_SENAL:
                        datos["ejecutando"] = False
                        datos["error"] = "Tiempo máximo de ejecución excedido (proceso abortado)."
                        escribir_estado_ejecucion(datos)
            return datos
        except Exception as exc:
            logger.warning("Error leyendo estado de respaldo: %s", exc)
    return {"ejecutando": False}


def escribir_estado_ejecucion(datos: dict[str, Any]) -> None:
    """Actualiza el archivo de estado de ejecución; cada escritura sella `actualizado_en` (señal de vida)."""
    ARCHIVO_ESTADO_RESPALDO.parent.mkdir(parents=True, exist_ok=True)
    sellado = {**datos, "actualizado_en": timezone.now().isoformat()}
    ARCHIVO_ESTADO_RESPALDO.write_text(json.dumps(sellado, indent=2), encoding="utf-8")


def _progreso_de_estado(estado: dict[str, Any]) -> dict[str, Any] | None:
    """Extrae el avance de una restauración del archivo de estado, o None si no hay etapa registrada."""
    if not estado.get("etapa"):
        return None
    return {
        "etapa": estado["etapa"],
        "tabla_actual": estado.get("tabla_actual"),
        "avance": estado.get("avance"),
        "total": estado.get("total"),
    }


def obtener_estado_respaldo(request: HttpRequest | None = None) -> dict[str, Any]:
    """Compila el estado consolidado de la funcionalidad de respaldos."""
    ruta = obtener_ruta_respaldo()
    ultimo = obtener_info_ultimo_respaldo(ruta)
    total = len(list(ruta.glob("*.sql"))) if ruta.exists() else 0
    estado_ejecucion = leer_estado_ejecucion()
    es_local = es_cliente_servidor_local(request) if request else True

    return {
        "es_servidor_local": es_local,
        "ruta_configurada": obtener_ruta_configurada_display(),
        "ejecutando": bool(estado_ejecucion.get("ejecutando", False)),
        "ultimo_respaldo": ultimo,
        "total_respaldos": total,
        "ultimo_resultado": estado_ejecucion.get("mensaje") or estado_ejecucion.get("error"),
        "progreso": _progreso_de_estado(estado_ejecucion),
    }


def ejecutar_respaldo_consola(ruta_destino: Path | None = None) -> dict[str, Any]:
    """Lanza el respaldo de la base de datos como un subproceso desacoplado de consola."""
    estado = leer_estado_ejecucion()
    if estado.get("ejecutando"):
        from apps.comun.excepciones import Conflicto

        raise Conflicto("Ya hay una copia de seguridad en ejecución en el servidor.")

    destino = (ruta_destino or obtener_ruta_respaldo()).resolve()
    valida, mensaje, ruta_valida = validar_ruta_servidor(str(destino))
    if not valida or not ruta_valida:
        from apps.comun.excepciones import DatosInvalidos

        raise DatosInvalidos(f"Ruta de destino no válida: {mensaje}")

    ahora = timezone.now()
    nuevo_estado = {
        "ejecutando": True,
        "iniciado_en": ahora.isoformat(),
        "ruta_destino": str(ruta_valida),
    }
    escribir_estado_ejecucion(nuevo_estado)

    # Comando de consola Django: manage.py respaldar_base_datos --destino <ruta>
    manage_py = settings.BASE_DIR / "manage.py"
    comando = [
        sys.executable,
        str(manage_py),
        "respaldar_base_datos",
        "--destino",
        str(ruta_valida),
    ]

    log_consola = settings.BASE_DIR.parent / "logs" / "respaldo_consola.log"
    log_consola.parent.mkdir(parents=True, exist_ok=True)

    flags = 0
    if sys.platform == "win32":
        # Ejecución desacoplada en consola independiente en Windows
        flags = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    with open(log_consola, "a", encoding="utf-8") as archivo_log:
        archivo_log.write(f"\n--- Inicio de respaldo por consola: {ahora.isoformat()} ---\n")
        subprocess.Popen(
            comando,
            cwd=str(settings.BASE_DIR),
            stdout=archivo_log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )

    logger.info("Respaldo por consola lanzado con éxito hacia: %s", ruta_valida)
    return {
        "mensaje": "Copia de seguridad iniciada por consola en el servidor.",
        "ruta_destino": str(ruta_valida),
        "iniciado_en": ahora.isoformat(),
    }


CARPETAS_IGNORADAS = {
    "$recycle.bin",
    "system volume information",
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".idea",
    ".vscode",
    "pagefile.sys",
    "swapfile.sys",
    "dumpstack.log.tmp",
}

RUTAS_PSQL = [
    Path(r"C:\Program Files\PostgreSQL\18\bin\psql.exe"),
    Path(r"C:\Program Files\PostgreSQL\17\bin\psql.exe"),
    Path(r"C:\Program Files\PostgreSQL\16\bin\psql.exe"),
    Path("/usr/bin/psql"),
    Path("/usr/local/bin/psql"),
]


def buscar_psql() -> str:
    """Localiza el binario ejecutable de psql en el servidor."""
    for ruta in RUTAS_PSQL:
        if ruta.exists():
            return str(ruta)
    import shutil

    hallado = shutil.which("psql")
    if hallado:
        return hallado
    raise FileNotFoundError("No se encontró el ejecutable 'psql' en el servidor.")


def mapear_posix_a_ruta_windows(ruta: Path | str) -> str:
    """Traduce una ruta interna Linux (/mnt/f/Prueba) o POSIX a representación de Windows (F:\\Prueba)."""
    s = str(ruta).replace("\\", "/")
    m = re.match(r"^/mnt/([a-zA-Z])(?:/(.*))?$", s)
    if m:
        letra = m.group(1).upper()
        resto = (m.group(2) or "").strip("/").replace("/", "\\")
        return f"{letra}:\\{resto}" if resto else f"{letra}:\\"
    if s.startswith("/app"):
        resto = s[4:].strip("/").replace("/", "\\")
        return f"F:\\Check\\{resto}" if resto else "F:\\Check"
    m_win = re.match(r"^([a-zA-Z]):[\\/](.*)$", s)
    if m_win:
        letra = m_win.group(1).upper()
        resto = m_win.group(2).replace("/", "\\")
        return f"{letra}:\\{resto}" if resto else f"{letra}:\\"
    return str(ruta)


def obtener_unidades_disponibles() -> list[str]:
    """Retorna las unidades de disco o puntos de montaje principales disponibles en el servidor."""
    unidades: list[str] = []
    if os.name == "nt":
        for letra in ["C", "D", "E", "F", "Z"]:
            if Path(f"{letra}:/").exists():
                unidades.append(f"{letra}:\\")
    else:
        for letra in ["c", "d", "e", "f", "z"]:
            if Path(f"/mnt/{letra}").exists():
                unidades.append(f"{letra.upper()}:\\")
        if not unidades:
            unidades.append("/")
    return sorted(unidades)


def explorar_directorio_servidor(ruta_str: str | None = None) -> dict[str, Any]:
    """
    Explora una carpeta del servidor listando subcarpetas y archivos .sql disponibles.
    Si ruta_str no se suministra, inicia en la carpeta configurada de respaldos.
    """
    if ruta_str:
        limpio = ruta_str.strip()
        if not es_ruta_absoluta(limpio):
            from apps.comun.excepciones import DatosInvalidos

            raise DatosInvalidos(f"La ruta '{limpio}' debe ser absoluta (ej: F:\\Prueba).")
        ruta_sistema = resolver_ruta_sistema(limpio)
    else:
        ruta_sistema = obtener_ruta_respaldo()
        limpio = obtener_ruta_configurada_display()

    if not ruta_sistema.exists():
        from apps.comun.excepciones import DatosInvalidos

        raise DatosInvalidos(f"La carpeta '{limpio or str(ruta_sistema)}' no existe en el disco del servidor.")

    if not ruta_sistema.is_dir():
        from apps.comun.excepciones import DatosInvalidos

        raise DatosInvalidos(f"La ruta '{limpio or str(ruta_sistema)}' no corresponde a una carpeta.")

    carpetas: list[str] = []
    archivos_sql: list[dict[str, Any]] = []

    try:
        for entrada in ruta_sistema.iterdir():
            nombre_lower = entrada.name.lower()
            if nombre_lower in CARPETAS_IGNORADAS or entrada.name.startswith("."):
                continue
            if entrada.is_dir():
                carpetas.append(entrada.name)
            elif entrada.is_file() and nombre_lower.endswith(".sql"):
                stat = entrada.stat()
                mtime_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone())
                ruta_display = mapear_posix_a_ruta_windows(entrada)
                archivos_sql.append(
                    {
                        "nombre": entrada.name,
                        "ruta_completa": ruta_display,
                        "tamano_bytes": stat.st_size,
                        "tamano_formateado": formatear_tamano(stat.st_size),
                        "modificado_en": mtime_dt.isoformat(),
                    }
                )
    except PermissionError as exc:
        from apps.comun.excepciones import DatosInvalidos

        raise DatosInvalidos(f"Permiso denegado al acceder a '{limpio}': {exc}")

    carpetas.sort(key=str.lower)
    archivos_sql.sort(key=lambda a: a["nombre"].lower())

    ruta_actual_display = mapear_posix_a_ruta_windows(ruta_sistema)
    ruta_padre_display: str | None = None
    padre = ruta_sistema.parent
    if padre and padre != ruta_sistema and str(padre) not in ("/", "/mnt", "\\", "."):
        ruta_padre_display = mapear_posix_a_ruta_windows(padre)

    return {
        "ruta_actual": ruta_actual_display,
        "ruta_padre": ruta_padre_display,
        "carpetas": carpetas,
        "archivos_sql": archivos_sql,
        "unidades_disponibles": obtener_unidades_disponibles(),
    }


def _validar_ruta_sql(ruta_str: str) -> Path:
    """Valida que la ruta sea absoluta y apunte a un archivo .sql existente del servidor; devuelve su Path."""
    from apps.comun.excepciones import DatosInvalidos

    limpio = (ruta_str or "").strip()
    if not limpio:
        raise DatosInvalidos("Debe especificar la ruta del archivo .sql a restaurar.")
    if not es_ruta_absoluta(limpio):
        raise DatosInvalidos(f"La ruta '{limpio}' debe ser absoluta (ej: F:\\Prueba\\respaldo.sql).")
    ruta = resolver_ruta_sistema(limpio)
    if not ruta.exists():
        raise DatosInvalidos(f"El archivo '{limpio}' no existe en el disco del servidor.")
    if not ruta.is_file():
        raise DatosInvalidos(f"La ruta '{limpio}' no corresponde a un archivo.")
    if not ruta.name.lower().endswith(".sql"):
        raise DatosInvalidos("El archivo a restaurar debe tener extensión .sql")
    return ruta


def analizar_respaldo_servidor(ruta_archivo_str: str) -> dict[str, Any]:
    """Analiza (sin modificar nada) un volcado ubicado en el servidor y devuelve el informe serializable."""
    from apps.comun.management.commands.importar_legado import TABLAS

    informe = analizar_dump(_validar_ruta_sql(ruta_archivo_str))
    return {
        "tipo": informe.tipo,
        "valido": informe.valido,
        "completo": informe.completo,
        "errores": informe.errores,
        "advertencias": informe.advertencias,
        "usuarios": informe.usuarios,
        "usuarios_admin": informe.usuarios_admin,
        "tablas_importables": [
            {"nombre": t.legada, "filas_aprox": informe.tablas[t.legada].filas_aprox}
            for t in TABLAS
            if t.legada in informe.tablas
        ],
    }


def guardar_archivo_respaldo_subido(archivo: Any) -> dict[str, Any]:
    """Guarda un archivo de respaldo .sql subido en la carpeta configurada del servidor."""
    nombre = getattr(archivo, "name", "")
    if not nombre.lower().endswith(".sql"):
        from apps.comun.excepciones import DatosInvalidos

        raise DatosInvalidos("El archivo debe tener extensión .sql")

    destino_dir = obtener_ruta_respaldo()
    destino_dir.mkdir(parents=True, exist_ok=True)
    nombre_seguro = re.sub(r"[^\w\s\-\.]", "_", Path(nombre).name)
    ruta_destino = destino_dir / nombre_seguro
    base = Path(nombre_seguro)
    consecutivo = 0
    while True:
        try:
            # Modo "xb": falla si existe, así nunca se sobrescribe un respaldo previo.
            with open(ruta_destino, "xb") as f_dest:
                for chunk in archivo.chunks():
                    f_dest.write(chunk)
            break
        except FileExistsError:
            consecutivo += 1
            nombre_seguro = f"{base.stem}-{consecutivo}{base.suffix}"
            ruta_destino = destino_dir / nombre_seguro

    stat = ruta_destino.stat()
    return {
        "mensaje": "Archivo de respaldo subido exitosamente al servidor.",
        "archivo": nombre_seguro,
        "ruta_completa": mapear_posix_a_ruta_windows(ruta_destino),
        "tamano_formateado": formatear_tamano(stat.st_size),
    }


def ejecutar_restauracion_consola(ruta_archivo_str: str, importar_usuarios: bool = True) -> dict[str, Any]:
    """Lanza la restauración de la base de datos como subproceso de consola en el servidor."""
    estado = leer_estado_ejecucion()
    if estado.get("ejecutando"):
        from apps.comun.excepciones import Conflicto

        raise Conflicto("Ya hay una operación de base de datos en ejecución en el servidor.")

    ruta_archivo = _validar_ruta_sql(ruta_archivo_str)
    informe = analizar_dump(ruta_archivo)
    if not informe.valido:
        from apps.comun.excepciones import DatosInvalidos

        raise DatosInvalidos(" ".join(informe.errores))

    ahora = timezone.now()
    nuevo_estado = {
        "ejecutando": True,
        "accion": "restaurar",
        "iniciado_en": ahora.isoformat(),
        "archivo_origen": str(ruta_archivo),
    }
    escribir_estado_ejecucion(nuevo_estado)

    manage_py = settings.BASE_DIR / "manage.py"
    comando = [
        sys.executable,
        str(manage_py),
        "restaurar_base_datos",
        "--origen",
        str(ruta_archivo),
    ]
    if not importar_usuarios:
        comando.append("--sin-usuarios")

    log_consola = settings.BASE_DIR.parent / "logs" / "restauracion_consola.log"
    log_consola.parent.mkdir(parents=True, exist_ok=True)

    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    with open(log_consola, "a", encoding="utf-8") as archivo_log:
        archivo_log.write(f"\n--- Inicio de restauración por consola: {ahora.isoformat()} ---\n")
        subprocess.Popen(
            comando,
            cwd=str(settings.BASE_DIR),
            stdout=archivo_log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )

    logger.info("Restauración por consola lanzada hacia: %s", ruta_archivo)
    return {
        "mensaje": "Restauración de la base de datos iniciada por consola en el servidor.",
        "archivo": ruta_archivo.name,
        "iniciado_en": ahora.isoformat(),
    }

