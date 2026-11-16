"""Vistas de llamadas."""

from typing import Any

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.comun.vistas import BaseViewSet, auditar
from apps.llamadas.filtros import FiltroLlamadasCumpleanos, FiltroLlamadasRtm, FiltroLlamadasSoat
from apps.llamadas.models import LlamadaCumpleanos, LlamadaRtm, LlamadaSoat
from apps.llamadas.por_llamar import RTM, SOAT, Canal, PorLlamarSerializer, por_llamar, rango
from apps.llamadas.serializers import (
    IntentoSerializer,
    LlamadaCumpleanosEscrituraSerializer,
    LlamadaCumpleanosSerializer,
    LlamadaRtmEscrituraSerializer,
    LlamadaRtmSerializer,
    LlamadaSoatEscrituraSerializer,
    LlamadaSoatSerializer,
    agregar_intento,
)


class IntentoMixin:
    """POST {id}/intentos: suma un intento (num_llamadas + 1), actualiza estado y agrega la observación."""

    @extend_schema(summary="Registrar un intento de llamada", request=IntentoSerializer)
    @action(detail=True, methods=["post"])
    def intentos(self, request: Request, **kwargs: Any) -> Response:
        guardada: Response | None = self._respuesta_guardada()  # type: ignore[attr-defined]
        if guardada is not None:
            return guardada
        llamada = self.get_object()  # type: ignore[attr-defined]
        datos = IntentoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        nueva = datos.validated_data["observacion"].strip()
        llamada.estado = datos.validated_data["estado"]
        llamada.observacion = f"{llamada.observacion}\n{nueva}".strip() if nueva else llamada.observacion
        llamada.num_llamadas += 1
        llamada.intentos = agregar_intento(llamada.intentos)
        llamada.usuario = getattr(request.user, "nombre", "")
        llamada.actualizado_en = timezone.now()
        llamada.actualizado_por = llamada.usuario
        llamada.save()
        auditar(request, "actualizar", llamada, {"intento": llamada.num_llamadas, "estado": llamada.estado})
        cuerpo: Any = self.get_serializer(llamada).data  # type: ignore[attr-defined]
        return Response(cuerpo)


@extend_schema(tags=["Llamadas"])
class LlamadaCumpleanosViewSet(IntentoMixin, BaseViewSet):
    queryset = LlamadaCumpleanos.objects.all()
    serializer_class = LlamadaCumpleanosSerializer
    serializer_escritura = LlamadaCumpleanosEscrituraSerializer
    filterset_class = FiltroLlamadasCumpleanos
    campos_orden = ("fecha", "estado", "num_llamadas")

    def get_queryset(self) -> Any:
        # prefetch y no select_related: el INNER JOIN ocultaría llamadas de contactos que ya no existen.
        return super().get_queryset().prefetch_related("contacto").order_by("-fecha", "-id")


class PorLlamarMixin:
    """GET por-llamar: vencimientos del rango que aún no tienen llamada realizada (ver apps.llamadas.por_llamar)."""

    canal: Canal

    @extend_schema(summary="Llamadas por hacer (desde los vencimientos)", responses=PorLlamarSerializer(many=True))
    @action(detail=False, methods=["get"], url_path="por-llamar")
    def pendientes_por_llamar(self, request: Request, **kwargs: Any) -> Response:
        desde, hasta = rango(request.query_params)
        pagina = self.paginate_queryset(por_llamar(self.canal, desde, hasta))  # type: ignore[attr-defined]
        respuesta: Response = self.get_paginated_response(  # type: ignore[attr-defined]
            PorLlamarSerializer(pagina, many=True).data
        )
        return respuesta


@extend_schema(tags=["Llamadas"])
class LlamadaRtmViewSet(PorLlamarMixin, IntentoMixin, BaseViewSet):
    canal = RTM
    queryset = LlamadaRtm.objects.all()
    serializer_class = LlamadaRtmSerializer
    serializer_escritura = LlamadaRtmEscrituraSerializer
    filterset_class = FiltroLlamadasRtm
    lookup_value_regex = "[^/]+"
    campos_orden = ("fecha", "estado", "num_llamadas")

    def get_queryset(self) -> Any:
        return super().get_queryset().order_by("-fecha", "id")


@extend_schema(tags=["Llamadas"])
class LlamadaSoatViewSet(PorLlamarMixin, IntentoMixin, BaseViewSet):
    canal = SOAT
    queryset = LlamadaSoat.objects.all()
    serializer_class = LlamadaSoatSerializer
    serializer_escritura = LlamadaSoatEscrituraSerializer
    filterset_class = FiltroLlamadasSoat
    lookup_value_regex = "[^/]+"
    campos_orden = ("fecha", "estado", "num_llamadas")

    def get_queryset(self) -> Any:
        return super().get_queryset().order_by("-fecha", "id")
