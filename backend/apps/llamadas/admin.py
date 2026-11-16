from django.contrib import admin

from apps.llamadas.models import LlamadaCumpleanos, LlamadaRtm, LlamadaSoat


class LlamadaAdminBase(admin.ModelAdmin):  # type: ignore[type-arg]
    list_filter = ("estado",)
    date_hierarchy = "fecha"
    readonly_fields = ("creado_en", "actualizado_en", "creado_por", "actualizado_por", "intentos")
    list_per_page = 50
    show_full_result_count = False


@admin.register(LlamadaCumpleanos)
class LlamadaCumpleanosAdmin(LlamadaAdminBase):
    list_display = ("id", "fecha", "contacto_id", "estado", "usuario", "num_llamadas")
    search_fields = ("contacto__nip",)
    raw_id_fields = ("contacto",)


@admin.register(LlamadaRtm)
class LlamadaRtmAdmin(LlamadaAdminBase):
    list_display = ("id", "fecha", "moto_id", "estado", "usuario", "num_llamadas")
    search_fields = ("id", "moto__placa")
    raw_id_fields = ("moto",)


@admin.register(LlamadaSoat)
class LlamadaSoatAdmin(LlamadaAdminBase):
    list_display = ("id", "fecha", "moto_id", "estado", "motivo_llamada", "usuario", "num_llamadas")
    search_fields = ("id", "moto__placa")
    raw_id_fields = ("moto",)
