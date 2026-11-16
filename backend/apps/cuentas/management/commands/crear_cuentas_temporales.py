"""Crea las cuentas a partir de scripts/credenciales_temporales.json y borra el archivo.

Uso: python manage.py crear_cuentas_temporales ../scripts/credenciales_temporales.json

Las contraseñas temporales se guardan solo como hash Argon2id, con `debe_cambiar_clave=True`.
La columna `clave` del legado nunca se usa.
"""

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.cuentas.models import ROLES, Usuario

ROLES_VALIDOS = {clave for clave, _ in ROLES}


class Command(BaseCommand):
    help = "Crea o reinicia las cuentas con claves temporales y elimina el archivo JSON."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("archivo", type=Path)
        parser.add_argument("--conservar-archivo", action="store_true", help="No borrar el JSON (solo pruebas).")

    @transaction.atomic
    def handle(self, *args: Any, **opciones: Any) -> None:
        archivo: Path = opciones["archivo"]
        if not archivo.is_file():
            raise CommandError(f"No existe {archivo}.")
        cuentas = json.loads(archivo.read_text(encoding="utf-8"))
        for cuenta in cuentas:
            rol = cuenta["tipo"] if cuenta["tipo"] in ROLES_VALIDOS else "usuario"
            usuario, creado = Usuario.objects.get_or_create(
                nip=cuenta["nip"], defaults={"nombre": cuenta["nombre"], "rol": rol}
            )
            usuario.nombre = cuenta["nombre"]
            usuario.rol = rol
            clave = cuenta.get("clave_temporal") or getattr(settings, "CLAVE_TEMPORAL_INICIAL", "CheckLTDA!")
            usuario.set_password(clave)
            usuario.debe_cambiar_clave = True
            usuario.is_active = True
            usuario.save()
            usuario.sincronizar_grupo()
            self.stdout.write(f"{'creada' if creado else 'reiniciada'}: {usuario.nip} ({rol})")
        if not opciones["conservar_archivo"]:
            archivo.unlink()
            self.stdout.write(self.style.WARNING(f"Archivo {archivo.name} eliminado."))
        self.stdout.write(self.style.SUCCESS(f"{len(cuentas)} cuentas listas con cambio de clave obligatorio."))
