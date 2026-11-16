from django.contrib import admin

from apps.comun.models import ImportacionRechazo, RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("fecha", "usuario", "accion", "modelo", "objeto_id")
    list_filter = ("accion", "modelo")
    search_fields = ("usuario", "objeto_id", "request_id")
    date_hierarchy = "fecha"
    list_per_page = 50
    show_full_result_count = False

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False

    def has_delete_permission(self, request: object, obj: object = None) -> bool:
        return False


@admin.register(ImportacionRechazo)
class ImportacionRechazoAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("tabla", "motivo", "creado_en")
    list_filter = ("tabla",)
    list_per_page = 50

    def has_add_permission(self, request: object) -> bool:
        return False

    def has_change_permission(self, request: object, obj: object = None) -> bool:
        return False
