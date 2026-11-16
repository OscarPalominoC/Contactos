"""Enrutador principal."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.cuentas.views import jwks

admin.site.site_header = "Check Contactos — Administración"
admin.site.site_title = "Check Contactos"
admin.site.index_title = "Gestión"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path(".well-known/jwks.json", jwks, name="jwks"),
    path("api/v1/", include("config.api_urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("redoc", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
