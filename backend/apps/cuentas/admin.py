from typing import Any

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.cuentas.models import Ingreso, Usuario
from apps.cuentas.servicios import reiniciar_clave


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):  # type: ignore[type-arg]
    ordering = ("nombre",)
    list_display = ("nip", "nombre", "rol", "is_active", "debe_cambiar_clave", "last_login")
    list_filter = ("rol", "is_active", "debe_cambiar_clave")
    search_fields = ("nip", "nombre")
    readonly_fields = ("last_login", "fecha_creacion", "clave_cambiada_en", "password")
    fieldsets = (
        (None, {"fields": ("nip", "nombre", "rol", "password")}),
        ("Estado", {"fields": ("is_active", "is_staff", "debe_cambiar_clave", "clave_cambiada_en")}),
        ("Permisos", {"fields": ("is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "fecha_creacion")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("nip", "nombre", "rol", "password1", "password2")}),)
    filter_horizontal = ("groups", "user_permissions")
    actions = ["accion_reiniciar_clave"]

    def save_model(self, request: HttpRequest, obj: Usuario, form: Any, change: bool) -> None:
        super().save_model(request, obj, form, change)
        obj.sincronizar_grupo()

    @admin.action(description="Reiniciar clave temporal (se muestra una sola vez)")
    def accion_reiniciar_clave(self, request: HttpRequest, queryset: QuerySet[Usuario]) -> None:
        for usuario in queryset:
            temporal = reiniciar_clave(usuario)
            self.message_user(
                request,
                f"{usuario.nip}: nueva clave temporal {temporal} — entréguela en persona; no se volverá a mostrar.",
                messages.WARNING,
            )


@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("fecha", "nip_usuario", "ip", "exitoso", "origen")
    list_filter = ("exitoso", "origen")
    search_fields = ("nip_usuario",)
    date_hierarchy = "fecha"
    list_per_page = 50
    show_full_result_count = False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False
