"""Crea o actualiza el superadministrador definido en variables de entorno o argumentos."""

from typing import Any
from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction
from apps.cuentas.models import Usuario


class Command(BaseCommand):
    help = "Crea o actualiza el superadministrador a partir de las variables de entorno."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--nip", type=str, default=None, help="NIP / Email del superadmin")
        parser.add_argument("--password", type=str, default=None, help="Contraseña del superadmin")
        parser.add_argument("--nombre", type=str, default=None, help="Nombre del superadmin")

    @transaction.atomic
    def handle(self, *args: Any, **opciones: Any) -> None:
        nip = opciones.get("nip") or getattr(settings, "SUPERADMIN_NIP", None) or "admin@admin.com"
        nombre = opciones.get("nombre") or getattr(settings, "SUPERADMIN_NOMBRE", None) or "Super Administrador"
        password = opciones.get("password") or getattr(settings, "SUPERADMIN_PASSWORD", None)

        if not password:
            self.stdout.write(
                self.style.WARNING("SUPERADMIN_PASSWORD no está definida. Se omite la creación del superadmin.")
            )
            return

        usuario, creado = Usuario.objects.get_or_create(
            nip=nip,
            defaults={
                "nombre": nombre,
                "rol": "administrador",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "debe_cambiar_clave": False,
            },
        )
        usuario.nombre = nombre
        usuario.rol = "administrador"
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.is_active = True
        usuario.debe_cambiar_clave = False
        usuario.set_password(password)
        usuario.save()
        usuario.sincronizar_grupo()

        accion = "creado" if creado else "actualizado"
        self.stdout.write(
            self.style.SUCCESS(f"Superadministrador {usuario.nip} ({usuario.nombre}) {accion} exitosamente.")
        )

