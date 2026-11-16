"""Permisos: cambio de clave obligatorio, permisos de modelo y solo administrador."""

from typing import Any

from rest_framework.permissions import BasePermission, DjangoModelPermissions
from rest_framework.request import Request

from apps.comun.excepciones import CambioClaveRequerido


class CambioClaveCompletado(BasePermission):
    """Mientras `debe_cambiar_clave` sea True, toda la API responde 403 cambio-clave-requerido."""

    def has_permission(self, request: Request, view: Any) -> bool:
        usuario = request.user
        if usuario is None or not getattr(usuario, "is_authenticated", False):
            return False
        if getattr(view, "permite_clave_temporal", False):
            return True
        if getattr(usuario, "debe_cambiar_clave", False):
            raise CambioClaveRequerido()
        return True


class PermisosDeModelo(DjangoModelPermissions):
    """Exige también el permiso `view` para GET (por defecto DRF no lo exige)."""

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def has_permission(self, request: Request, view: Any) -> bool:
        if getattr(view, "sin_permiso_modelo", False):
            return True
        return super().has_permission(request, view)


class SoloAdministrador(BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        usuario = request.user
        return bool(usuario and getattr(usuario, "rol", "") == "administrador" and usuario.is_active)
