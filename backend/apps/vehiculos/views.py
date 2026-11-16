"""Vistas de vehículos."""

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import mixins
from rest_framework.request import Request
from rest_framework.response import Response

from apps.comun.vistas import BaseViewSet, auditar
from apps.vehiculos.filtros import FiltroLineas, FiltroMarcas, FiltroMotos
from apps.vehiculos.models import Linea, Marca, Moto
from apps.vehiculos.serializers import (
    LineaEscrituraSerializer,
    LineaSerializer,
    MarcaEscrituraSerializer,
    MarcaSerializer,
    MotoDetalleSerializer,
    MotoEscrituraSerializer,
    MotoSerializer,
)


@extend_schema(tags=["Motos"])
class MotoViewSet(BaseViewSet):
    queryset = Moto.objects.all()
    serializer_class = MotoSerializer
    serializer_escritura = MotoEscrituraSerializer
    filterset_class = FiltroMotos
    lookup_field = "placa"
    campos_orden = ("placa", "marca", "modelo", "fecha_venc_rtmg", "fecha_venc_soat")

    def get_queryset(self) -> Any:
        return super().get_queryset().prefetch_related("contacto").order_by("placa")

    def get_serializer_class(self) -> Any:
        if self.action == "retrieve":
            return MotoDetalleSerializer
        return super().get_serializer_class()


class CatalogoViewSet(mixins.DestroyModelMixin, BaseViewSet):
    """Catálogos: único recurso que admite DELETE (con confirmación en la interfaz)."""

    def perform_destroy(self, instance: Any) -> None:
        auditar(self.request, "eliminar", instance)
        instance.delete()

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().destroy(request, *args, **kwargs)


@extend_schema(tags=["Catálogos"])
class MarcaViewSet(CatalogoViewSet):
    queryset = Marca.objects.all().order_by("nombre")
    serializer_class = MarcaSerializer
    serializer_escritura = MarcaEscrituraSerializer
    filterset_class = FiltroMarcas
    lookup_value_regex = "[^/]+"
    campos_orden = ("nombre", "codigo")

    def perform_destroy(self, instance: Marca) -> None:
        from apps.comun.excepciones import Conflicto

        if instance.lineas.exists() or Moto.objects.filter(marca=instance.nombre).exists():
            raise Conflicto("La marca tiene líneas o motos asociadas; no se puede eliminar.")
        super().perform_destroy(instance)


@extend_schema(tags=["Catálogos"])
class LineaViewSet(CatalogoViewSet):
    queryset = Linea.objects.select_related("marca").order_by("linea")
    serializer_class = LineaSerializer
    serializer_escritura = LineaEscrituraSerializer
    filterset_class = FiltroLineas
    lookup_value_regex = "[^/]+"
    campos_orden = ("linea",)

    def perform_destroy(self, instance: Linea) -> None:
        from apps.comun.excepciones import Conflicto

        if Moto.objects.filter(linea=instance.linea).exists():
            raise Conflicto("La línea tiene motos asociadas; no se puede eliminar.")
        super().perform_destroy(instance)
