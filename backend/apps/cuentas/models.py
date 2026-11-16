"""Usuario personalizado, ingresos e historial de claves."""

from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import Group, PermissionsMixin
from django.db import models

ROLES = [
    ("administrador", "Administrador"),
    ("ingeniero", "Ingeniero"),
    ("tecnico", "Técnico"),
    ("usuario", "Usuario"),
]


class GestorUsuarios(BaseUserManager["Usuario"]):
    def create_user(self, nip: str, nombre: str, password: str | None = None, **extra: Any) -> "Usuario":
        if not nip:
            raise ValueError("El nip es obligatorio.")
        usuario = self.model(nip=nip, nombre=nombre, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        usuario.sincronizar_grupo()
        return usuario

    def create_superuser(self, nip: str, nombre: str, password: str | None = None, **extra: Any) -> "Usuario":
        extra.update(is_staff=True, is_superuser=True, rol="administrador")
        return self.create_user(nip, nombre, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Cuenta del sistema. Sucesor de la tabla legada `usuario` (sin migrar la clave)."""

    nip = models.CharField("usuario (nip)", max_length=20, primary_key=True)
    nombre = models.CharField(max_length=255)
    rol = models.CharField(max_length=20, choices=ROLES, default="usuario")
    is_active = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField("acceso al admin", default=False)
    debe_cambiar_clave = models.BooleanField(default=True)
    clave_cambiada_en = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    objects = GestorUsuarios()

    USERNAME_FIELD = "nip"
    REQUIRED_FIELDS = ["nombre"]

    class Meta:
        db_table = "cuentas_usuario"
        ordering = ["nombre"]
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self) -> str:
        return f"{self.nombre} ({self.nip})"

    def sincronizar_grupo(self) -> None:
        """Deja al usuario únicamente en el grupo de su rol y ajusta is_staff."""
        grupo, _ = Group.objects.get_or_create(name=self.rol)
        self.groups.set([grupo])
        es_admin = self.rol == "administrador"
        if self.is_staff != es_admin and not self.is_superuser:
            self.is_staff = es_admin
            self.save(update_fields=["is_staff"])


class ClaveAnterior(models.Model):
    """Hash de claves anteriores para impedir su reutilización."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="claves_anteriores")
    hash_clave = models.CharField(max_length=255)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cuentas_clave_anterior"
        ordering = ["-creado_en"]


class Ingreso(models.Model):
    """Registro de ingresos al sistema. Sucesor de `entrada_sistema`."""

    fecha = models.DateTimeField(db_index=True)
    nip_usuario = models.CharField(max_length=45, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    exitoso = models.BooleanField(default=True)
    origen = models.CharField(max_length=20, default="api", help_text="api, admin o legado")

    class Meta:
        db_table = "cuentas_ingreso"
        ordering = ["-fecha"]
        verbose_name = "ingreso"
        verbose_name_plural = "ingresos"

    def __str__(self) -> str:
        return f"{self.nip_usuario} {self.fecha:%Y-%m-%d %H:%M}"
