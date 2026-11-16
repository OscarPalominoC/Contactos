from django.contrib import admin

from apps.vehiculos.models import Linea, Marca, Moto


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("codigo", "nombre")
    search_fields = ("codigo", "nombre")
    list_per_page = 50


@admin.register(Linea)
class LineaAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("linea", "marca")
    search_fields = ("linea",)
    raw_id_fields = ("marca",)
    list_per_page = 50
    show_full_result_count = False


@admin.register(Moto)
class MotoAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("placa", "marca", "linea", "modelo", "contacto_id", "fecha_venc_rtmg", "fecha_venc_soat")
    search_fields = ("placa", "contacto__nip")
    list_filter = ("marca",)
    raw_id_fields = ("contacto",)
    readonly_fields = ("creado_en", "actualizado_en", "creado_por", "actualizado_por")
    list_per_page = 50
    show_full_result_count = False
