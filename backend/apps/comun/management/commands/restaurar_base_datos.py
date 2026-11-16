"""Comando de gestión de Django para restaurar la base de datos PostgreSQL desde un archivo SQL."""

import logging
import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.comun.analisis_dump import analizar_dump
from apps.comun.management.commands.importar_legado import escribir_informe, importar_dump
from apps.comun.servicios_respaldo import (
    buscar_psql,
    es_ruta_absoluta,
    escribir_estado_ejecucion,
    leer_estado_ejecucion,
    obtener_ruta_respaldo,
    resolver_ruta_sistema,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Restaura la base de datos PostgreSQL en el servidor desde un archivo SQL ejecutado con psql o importar_legado."
    )

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--origen",
            type=str,
            required=True,
            help="Ruta absoluta al archivo .sql que se cargará a la base de datos.",
        )

        parser.add_argument(
            "--sin-usuarios",
            action="store_true",
            help="No importar las cuentas del legado (solo aplica a volcados MySQL).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        estado: dict[str, Any] = {"ejecutando": True, "accion": "restaurar", "iniciado_en": timezone.now().isoformat()}
        try:
            self._restaurar(estado, options)
        except Exception as exc:
            escribir_estado_ejecucion(
                {
                    **estado,
                    "ejecutando": False,
                    "exitoso": False,
                    "error": str(exc),
                    "finalizado_en": timezone.now().isoformat(),
                }
            )
            raise

    def _restaurar(self, estado: dict[str, Any], options: dict[str, Any]) -> None:
        origen_str = (options.get("origen") or "").strip()
        if not origen_str:
            raise CommandError("Debe suministrar la ruta del archivo SQL (--origen).")
        if not es_ruta_absoluta(origen_str):
            raise CommandError(f"La ruta '{origen_str}' debe ser absoluta (ej: F:\\Prueba\respaldo.sql).")
        archivo = resolver_ruta_sistema(origen_str)
        if not archivo.exists() or not archivo.is_file():
            raise CommandError(f"El archivo de respaldo '{origen_str}' no existe o no es un archivo válido.")
        if not archivo.name.lower().endswith(".sql"):
            raise CommandError(f"El archivo '{archivo.name}' debe tener extensión .sql.")

        def publicar(**cambios: Any) -> None:
            estado.update(cambios)
            escribir_estado_ejecucion(estado)

        estado["archivo_origen"] = str(archivo)
        publicar(etapa="analizando")
        self.stdout.write(f"Iniciando restauración de base de datos desde: {archivo}")
        informe_dump = analizar_dump(archivo)
        if not informe_dump.valido:
            raise CommandError("; ".join(informe_dump.errores) or "El archivo SQL no es válido.")

        publicar(etapa="respaldo_previo")
        try:
            call_command("respaldar_base_datos", destino=str(obtener_ruta_respaldo()))
        except Exception as exc:
            raise CommandError("No se pudo crear el respaldo previo; la base de datos no se modificó.") from exc
        # respaldar_base_datos deja `ejecutando: False`: se reescribe para que la restauración siga activa.
        publicar(respaldo_previo=leer_estado_ejecucion().get("archivo"), ejecutando=True)

        if informe_dump.tipo == "mysql_legado":
            self._importar_legado(archivo, bool(options.get("sin_usuarios")), publicar)
            mensaje = f"Base de datos importada y restaurada con éxito desde el dump legado: {archivo.name}"
        else:
            self._ejecutar_psql(archivo, publicar)
            mensaje = f"Base de datos restaurada con éxito desde: {archivo.name}"

        publicar(
            ejecutando=False,
            etapa="finalizado",
            exitoso=True,
            archivo=archivo.name,
            finalizado_en=timezone.now().isoformat(),
            mensaje=mensaje,
        )
        self.stdout.write(self.style.SUCCESS(mensaje))

    def _importar_legado(self, archivo: Path, sin_usuarios: bool, publicar: Callable[..., None]) -> None:
        inicio = time.monotonic()
        publicar(etapa="importando", tabla_actual="", avance=0, total=10)

        def avance(tabla: str, indice: int, total: int) -> None:
            publicar(etapa="importando", tabla_actual=tabla, avance=indice, total=total)

        resultados, faltantes = importar_dump(archivo, importar_usuarios=not sin_usuarios, al_avanzar=avance)
        informe = escribir_informe(resultados, faltantes, time.monotonic() - inicio)
        self.stdout.write(f"Informe de importación: {informe}")

    def _ejecutar_psql(self, archivo: Path, publicar: Callable[..., None]) -> None:
        publicar(etapa="importando")
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
            "-v",
            "ON_ERROR_STOP=1",
            "--single-transaction",
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

        resultado = subprocess.run(comando, env=env_copia, capture_output=True, text=True, check=False)  # noqa: S603
        if resultado.returncode != 0:
            err_msg = resultado.stderr.strip() or f"Código de salida: {resultado.returncode}"
            self.stderr.write(self.style.ERROR(f"Error en psql: {err_msg}"))
            raise CommandError(f"Fallo al ejecutar psql: {err_msg}")
