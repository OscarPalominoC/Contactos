"""Vistas de revisiones RTM, SOAT y tablero."""

from datetime import timedelta
from typing import Any

from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.vistas import BaseViewSet, auditar
from apps.cuentas.permisos import CambioClaveCompletado
from apps.revisiones.filtros import FiltroRevisiones, FiltroSoats
from apps.revisiones.models import Revision, Soat
from apps.revisiones.serializers import (
    RevisionEscrituraSerializer,
    RevisionSerializer,
    SoatEscrituraSerializer,
    SoatSerializer,
)

DIAS_VENCIMIENTO_PROXIMO = 30


class AnulableMixin:
    """Anulación en lugar de borrado físico."""

    @extend_schema(summary="Anular", request=None)
    @action(detail=True, methods=["post"])
    def anular(self, request: Request, **kwargs: Any) -> Response:
        guardada: Response | None = self._respuesta_guardada()  # type: ignore[attr-defined]
        if guardada is not None:
            return guardada
        instancia = self.get_object()  # type: ignore[attr-defined]
        if instancia.estado == "ANULADO":
            from apps.comun.excepciones import Conflicto

            raise Conflicto("El registro ya está anulado.")
        instancia.estado = "ANULADO"
        instancia.actualizado_en = timezone.now()
        instancia.actualizado_por = getattr(request.user, "nombre", "")
        instancia.save(update_fields=["estado", "actualizado_en", "actualizado_por"])
        auditar(request, "anular", instancia)
        cuerpo: Any = self.get_serializer(instancia).data  # type: ignore[attr-defined]
        return Response(cuerpo)


@extend_schema(tags=["Revisiones RTM"])
class RevisionViewSet(AnulableMixin, BaseViewSet):
    queryset = Revision.objects.all()
    serializer_class = RevisionSerializer
    serializer_escritura = RevisionEscrituraSerializer
    filterset_class = FiltroRevisiones
    lookup_field = "certificado"
    lookup_value_regex = "[^/]+"
    campos_orden = ("fecha_certificado", "fecha_venc_certificado", "certificado", "fecha_registro")

    def get_queryset(self) -> Any:
        return super().get_queryset().prefetch_related("moto__contacto").order_by("-fecha_certificado", "certificado")


@extend_schema(tags=["SOAT"])
class SoatViewSet(AnulableMixin, BaseViewSet):
    queryset = Soat.objects.all()
    serializer_class = SoatSerializer
    serializer_escritura = SoatEscrituraSerializer
    filterset_class = FiltroSoats
    lookup_field = "soat"
    lookup_value_regex = "[^/]+"
    campos_orden = ("fecha_soat", "fecha_venc_soat", "soat", "fecha_registro")

    def get_queryset(self) -> Any:
        return super().get_queryset().prefetch_related("moto__contacto").order_by("-fecha_soat", "soat")


class TableroView(APIView):
    """Indicadores del día: vencimientos próximos, llamadas, cumpleaños y contactos nuevos."""

    permission_classes = [CambioClaveCompletado]
    sin_permiso_modelo = True

    @extend_schema(
        summary="Indicadores del tablero",
        tags=["Tablero"],
        responses={
            200: inline_serializer(
                name="Tablero",
                fields={
                    "rtm_por_vencer": serializers.IntegerField(),
                    "soat_por_vencer": serializers.IntegerField(),
                    "llamadas_hoy": serializers.DictField(child=serializers.IntegerField()),
                    "cumpleanos_hoy": serializers.IntegerField(),
                    "contactos_nuevos_mes": serializers.IntegerField(),
                    "dias_horizonte": serializers.IntegerField(),
                },
            )
        },
    )
    def get(self, request: Request) -> Response:
        from apps.contactos.models import Contacto
        from apps.llamadas.models import LlamadaCumpleanos, LlamadaRtm, LlamadaSoat

        hoy = timezone.localdate()
        limite = hoy + timedelta(days=DIAS_VENCIMIENTO_PROXIMO)
        inicio_mes = hoy.replace(day=1)
        manuales = ["DUPLICADO", "ANULADO", "NO"]
        return Response(
            {
                "dias_horizonte": DIAS_VENCIMIENTO_PROXIMO,
                "rtm_por_vencer": Revision.objects.exclude(estado__in=manuales)
                .filter(fecha_venc_certificado__range=(hoy, limite))
                .count(),
                "soat_por_vencer": Soat.objects.exclude(estado__in=manuales)
                .filter(fecha_venc_soat__range=(hoy, limite))
                .count(),
                "llamadas_hoy": {
                    "cumpleanos": LlamadaCumpleanos.objects.filter(fecha__date=hoy).count(),
                    "rtm": LlamadaRtm.objects.filter(fecha=hoy).count(),
                    "soat": LlamadaSoat.objects.filter(fecha=hoy).count(),
                },
                "cumpleanos_hoy": Contacto.objects.filter(
                    dia_nac=hoy.day, mes_nac=hoy.month, estado="habilitado", contactar_cumpleanos=True
                ).count(),
                "contactos_nuevos_mes": Contacto.objects.filter(fecha_registro__date__gte=inicio_mes).count(),
            }
        )
