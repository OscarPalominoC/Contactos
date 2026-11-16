"""Comando de gestión de Django para realizar la copia de seguridad de la base de datos por consola."""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.comun.servicios_respaldo import (
    escribir_estado_ejecucion,
    formatear_tamano,
    generar_nombre_archivo_respaldo,
    obtener_ruta_respaldo,
    validar_ruta_servidor,
)

logger = logging.getLogger(__name__)

RUTAS_PG_DUMP = [
    Path(r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"),
    Path(r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe"),
    Path(r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"),
]
RESPALDOS_CONSERVADOS = 14


def buscar_pg_dump() -> str:
    """Localiza el binario ejecutable de pg_dump en el sistema."""
    for ruta in RUTAS_PG_DUMP:
        if ruta.exists():
            return str(ruta)
    hallado = shutil.which("pg_dump")
    if hallado:
        return hallado
    raise CommandError("No se encontró el ejecutable 'pg_dump' en el servidor.")


def _depurar_antiguos(destino: Path, conservar: Path | None) -> None:
    """Conserva los `RESPALDOS_CONSERVADOS` .sql más recientes; `conservar` nunca se borra."""
    protegido = conservar.resolve() if conservar else None
    archivos = sorted(destino.glob("*.sql"), key=lambda a: a.stat().st_mtime, reverse=True)
    for sobrante in archivos[RESPALDOS_CONSERVADOS:]:
        if protegido is not None and sobrante.resolve() == protegido:
            continue
        try:
            sobrante.unlink(missing_ok=True)
            logger.info("Depurado respaldo antiguo: %s", sobrante.name)
        except Exception as exc:
            logger.warning("No se pudo eliminar respaldo antiguo %s: %s", sobrante, exc)


def generar_respaldo(destino: Path, *, conservar: Path | None = None, escribir_estado: bool = True) -> Path:
    """Ejecuta pg_dump hacia `destino`, depura los antiguos y devuelve el archivo creado.

    Con `escribir_estado=False` no toca el archivo de estado: lo usa la restauración, que es dueña del estado
    mientras crea su respaldo previo. `conservar` protege de la depuración el archivo que se va a restaurar.
    """

    def estado(datos: dict[str, Any]) -> None:
        if escribir_estado:
            escribir_estado_ejecucion(datos)

    destino.mkdir(parents=True, exist_ok=True)
    estado({"ejecutando": True, "iniciado_en": timezone.now().isoformat(), "ruta_destino": str(destino)})

    db_config = settings.DATABASES["default"]
    host = db_config.get("HOST") or "localhost"
    port = str(db_config.get("PORT") or "5433")
    dbname = db_config.get("NAME") or "check_contactos"
    user = db_config.get("USER") or "check_super"
    password = db_config.get("PASSWORD") or ""

    # Si existe pg_superuser.txt, usar el superusuario como en respaldar.ps1
    secreto_super = settings.BASE_DIR.parent / ".secrets" / "pg_superuser.txt"
    if secreto_super.exists():
        try:
            pass_super = secreto_super.read_text(encoding="utf-8").strip()
            if pass_super:
                user = "check_super"
                password = pass_super
        except Exception as exc:
            logger.warning("No se pudo leer secreto de superusuario: %s", exc)

    try:
        ejecutable = buscar_pg_dump()
        archivo_salida = generar_nombre_archivo_respaldo(destino, dbname)
        comando = [
            ejecutable,
            "-h",
            host,
            "-p",
            port,
            "-U",
            user,
            "--clean",
            "--if-exists",
            "-f",
            str(archivo_salida),
            dbname,
        ]
        env_copia = os.environ.copy()
        if password:
            env_copia["PGPASSWORD"] = password

        resultado = subprocess.run(comando, env=env_copia, capture_output=True, text=True, check=False)  # noqa: S603
        if resultado.returncode != 0:
            err_msg = resultado.stderr.strip() or f"Código de salida: {resultado.returncode}"
            raise CommandError(f"Error generando respaldo: {err_msg}")

        tamano = archivo_salida.stat().st_size if archivo_salida.exists() else 0
        tamano_fmt = formatear_tamano(tamano)
        _depurar_antiguos(destino, conservar)
    except Exception as exc:
        estado(
            {
                "ejecutando": False,
                "exitoso": False,
                "error": str(exc),
                "finalizado_en": timezone.now().isoformat(),
            }
        )
        raise

    estado(
        {
            "ejecutando": False,
            "exitoso": True,
            "archivo": archivo_salida.name,
            "tamano_bytes": tamano,
            "tamano_formateado": tamano_fmt,
            "finalizado_en": timezone.now().isoformat(),
            "mensaje": f"Respaldo generado con éxito: {archivo_salida.name} ({tamano_fmt})",
        }
    )
    return archivo_salida


class Command(BaseCommand):
    help = "Ejecuta el respaldo de la base de datos PostgreSQL en el servidor usando pg_dump en formato comprimido."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--destino",
            type=str,
            default=None,
            help="Ruta absoluta de la carpeta en el servidor donde se guardará el respaldo.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        destino_arg = options.get("destino")
        if destino_arg:
            valida, mensaje, ruta = validar_ruta_servidor(destino_arg)
            if not valida or not ruta:
                escribir_estado_ejecucion(
                    {
                        "ejecutando": False,
                        "exitoso": False,
                        "error": f"Ruta inválida: {mensaje}",
                        "finalizado_en": timezone.now().isoformat(),
                    }
                )
                raise CommandError(f"Ruta de destino inválida: {mensaje}")
            destino = ruta
        else:
            destino = obtener_ruta_respaldo()

        self.stdout.write(f"Iniciando respaldo de base de datos en: {destino}")
        try:
            archivo = generar_respaldo(destino)
        except CommandError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            raise
        self.stdout.write(self.style.SUCCESS(f"Respaldo creado con éxito: {archivo}"))
