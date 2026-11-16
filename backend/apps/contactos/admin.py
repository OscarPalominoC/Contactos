from django.contrib import admin

from apps.contactos.models import Contacto


@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("nip", "nombre", "celular", "estado", "mes_nac", "dia_nac", "fecha_registro")
    list_filter = ("estado", "mes_nac")
    search_fields = ("nip", "nombre")
    date_hierarchy = "fecha_registro"
    readonly_fields = ("creado_en", "actualizado_en", "creado_por", "actualizado_por", "fecha_registro", "usuario")
    list_per_page = 50
    show_full_result_count = False
