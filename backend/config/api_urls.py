"""Rutas de la API v1."""

from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.comun.views_respaldo import (
    VistaConfigurarRutaRespaldo,
    VistaEjecutarRespaldo,
    VistaEsServidor,
    VistaEstadoRespaldo,
    VistaValidarRutaRespaldo,
)
from apps.contactos.views import ContactoViewSet
from apps.cuentas.views import UsuarioViewSet
from apps.llamadas.views import LlamadaCumpleanosViewSet, LlamadaRtmViewSet, LlamadaSoatViewSet
from apps.revisiones.views import RevisionViewSet, SoatViewSet, TableroView
from apps.vehiculos.views import LineaViewSet, MarcaViewSet, MotoViewSet

router = SimpleRouter(trailing_slash=False)
router.register("contactos", ContactoViewSet, basename="contactos")
router.register("motos", MotoViewSet, basename="motos")
router.register("marcas", MarcaViewSet, basename="marcas")
router.register("lineas", LineaViewSet, basename="lineas")
router.register("revisiones", RevisionViewSet, basename="revisiones")
router.register("soats", SoatViewSet, basename="soats")
router.register("llamadas-cumpleanos", LlamadaCumpleanosViewSet, basename="llamadas-cumpleanos")
router.register("llamadas-rtm", LlamadaRtmViewSet, basename="llamadas-rtm")
router.register("llamadas-soat", LlamadaSoatViewSet, basename="llamadas-soat")
router.register("usuarios", UsuarioViewSet, basename="usuarios")

urlpatterns = [
    path("auth/", include("apps.cuentas.urls")),
    path("tablero", TableroView.as_view(), name="tablero"),
    path("respaldos/es-servidor", VistaEsServidor.as_view(), name="respaldos-es-servidor"),
    path("respaldos/estado", VistaEstadoRespaldo.as_view(), name="respaldos-estado"),
    path("respaldos/validar-ruta", VistaValidarRutaRespaldo.as_view(), name="respaldos-validar-ruta"),
    path("respaldos/configurar-ruta", VistaConfigurarRutaRespaldo.as_view(), name="respaldos-configurar-ruta"),
    path("respaldos/ejecutar", VistaEjecutarRespaldo.as_view(), name="respaldos-ejecutar"),
    *router.urls,
]
