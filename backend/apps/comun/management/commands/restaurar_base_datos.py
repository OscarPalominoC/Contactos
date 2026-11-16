"""Comando de gestión de Django para restaurar la base de datos PostgreSQL desde un archivo SQL."""

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
    buscar_psql,
    es_ruta_absoluta,
    escribir_estado_ejecucion,
    resolver_ruta_sistema,
)

logger = logging.getLogger(__name__)


def es_dump_mysql(archivo: Path) -> bool:
    """Verifica si el archivo SQL corresponde a un dump legado de MySQL."""
    try:
        with open(archivo, "r", encoding="utf-8", errors="ignore") as f:
            primeras_lineas = "".join(f.readline() for _ in range(30)).lower()
            return "mysql dump" in primeras_lineas or "mariadb" in primeras_lineas
    except Exception:
        return False


class Command(BaseCommand):
    help = "Restaura la base de datos PostgreSQL en el servidor desde un archivo SQL ejecutado con psql o importar_legado."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--origen",
            type=str,
            required=True,
            help="Ruta absoluta al archivo .sql que se cargará a la base de datos.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        origen_str = options.get("origen", "").strip()
        if not origen_str:
            raise CommandError("Debe suministrar la ruta del archivo SQL (--origen).")

        if not es_ruta_absoluta(origen_str):
            raise CommandError(f"La ruta '{origen_str}' debe ser absoluta (ej: F:\\Prueba\\respaldo.sql).")

        archivo = resolver_ruta_sistema(origen_str)
        if not archivo.exists() or not archivo.is_file():
            escribir_estado_ejecucion(
                {
                    "ejecutando": False,
                    "exitoso": False,
                    "error": f"El archivo de respaldo '{origen_str}' no existe.",
                    "finalizado_en": timezone.now().isoformat(),
                }
            )
            raise CommandError(f"El archivo de respaldo '{origen_str}' no existe o no es un archivo válido.")

        if not archivo.name.lower().endswith(".sql"):
            raise CommandError(f"El archivo '{archivo.name}' debe tener extensión .sql.")

        inicio = timezone.now()
        escribir_estado_ejecucion(
            {
                "ejecutando": True,
                "accion": "restaurar",
                "iniciado_en": inicio.isoformat(),
                "archivo_origen": str(archivo),
            }
        )

        self.stdout.write(f"Iniciando restauración de base de datos desde: {archivo}")

        if es_dump_mysql(archivo):
            self.stdout.write(
                self.style.WARNING(
                    f"Detectado archivo SQL de dump legado MySQL: {archivo.name}. "
                    "Ejecutando importación estructurada hacia PostgreSQL con importar_legado..."
                )
            )
            from django.core.management import call_command

            call_command("importar_legado", str(archivo))

            fin = timezone.now()
            mensaje_exito = f"Base de datos importada y restaurada con éxito desde el dump legado: {archivo.name}"
            escribir_estado_ejecucion(
                {
                    "ejecutando": False,
                    "accion": "restaurar",
                    "exitoso": True,
                    "archivo": archivo.name,
                    "finalizado_en": fin.isoformat(),
                    "mensaje": mensaje_exito,
                }
            )
            self.stdout.write(self.style.SUCCESS(mensaje_exito))
            return

        db_config = settings.DATABASES["default"]
        host = db_config.get("HOST") or "localhost"
        port = str(db_config.get("PORT") or "5433")
        dbname = db_config.get("NAME") or "check_contactos"
        user = db_config.get("USER") or "check_app"
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

        ejecutable = buscar_psql()

        comando = [
            ejecutable,
            "-h",
            host,
            "-p",
            port,
            "-U",
            user,
            "-d",
            dbname,
            "-f",
            str(archivo),
        ]

        env_copia = os.environ.copy()
        if password:
            env_copia["PGPASSWORD"] = password

        try:
            resultado = subprocess.run(
                comando,
                env=env_copia,
                capture_output=True,
                text=True,
                check=False,
            )

            if resultado.returncode != 0:
                err_msg = resultado.stderr.strip() or f"Código de salida: {resultado.returncode}"
                escribir_estado_ejecucion(
                    {
                        "ejecutando": False,
                        "accion": "restaurar",
                        "exitoso": False,
                        "error": f"Fallo al ejecutar psql: {err_msg}",
                        "finalizado_en": timezone.now().isoformat(),
                    }
                )
                self.stderr.write(self.style.ERROR(f"Error en psql: {err_msg}"))
                raise CommandError(f"Error restaurando respaldo: {err_msg}")

            fin = timezone.now()
            mensaje_exito = f"Base de datos restaurada con éxito desde: {archivo.name}"
            escribir_estado_ejecucion(
                {
                    "ejecutando": False,
                    "accion": "restaurar",
                    "exitoso": True,
                    "archivo": archivo.name,
                    "finalizado_en": fin.isoformat(),
                    "mensaje": mensaje_exito,
                }
            )

            self.stdout.write(self.style.SUCCESS(mensaje_exito))

        except Exception as exc:
            if not isinstance(exc, CommandError):
                escribir_estado_ejecucion(
                    {
                        "ejecutando": False,
                        "accion": "restaurar",
                        "exitoso": False,
                        "error": str(exc),
                        "finalizado_en": timezone.now().isoformat(),
                    }
                )
            raise

