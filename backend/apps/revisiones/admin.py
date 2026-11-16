from django.contrib import admin

from apps.revisiones.models import Revision, Soat


@admin.register(Revision)
class RevisionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("certificado", "moto_id", "fecha_certificado", "fecha_venc_certificado", "estado", "usuario")
    list_filter = ("estado",)
    search_fields = ("certificado", "moto__placa", "nro_certificado_runt")
    date_hierarchy = "fecha_certificado"
    raw_id_fields = ("moto",)
    readonly_fields = ("creado_en", "actualizado_en", "creado_por", "actualizado_por", "fecha_registro")
    list_per_page = 50
    show_full_result_count = False


@admin.register(Soat)
class SoatAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("soat", "moto_id", "fecha_soat", "fecha_venc_soat", "estado", "usuario")
    list_filter = ("estado",)
    search_fields = ("soat", "moto__placa")
    date_hierarchy = "fecha_soat"
    raw_id_fields = ("moto",)
    readonly_fields = ("creado_en", "actualizado_en", "creado_por", "actualizado_por", "fecha_registro")
    list_per_page = 50
    show_full_result_count = False
