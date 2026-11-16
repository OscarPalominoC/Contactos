"""Vistas de contactos y ficha 360."""

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.comun.vistas import BaseViewSet
from apps.contactos.filtros import FiltroContactos
from apps.contactos.models import Contacto
from apps.contactos.serializers import ContactoEscrituraSerializer, ContactoSerializer

LIMITE_FICHA = 50


@extend_schema(tags=["Contactos"])
class ContactoViewSet(BaseViewSet):
    """Clientes. No se borran: se inhabilitan."""

    queryset = Contacto.objects.all()
    serializer_class = ContactoSerializer
    serializer_escritura = ContactoEscrituraSerializer
    filterset_class = FiltroContactos
    lookup_field = "nip"
    lookup_value_regex = "[^/]+"
    campos_orden = ("nombre", "nip", "fecha_registro", "mes_nac", "dia_nac", "celular", "cumpleanos")
    alias_orden = {"cumpleanos": ("mes_nac", "dia_nac")}

    def get_queryset(self) -> Any:
        return super().get_queryset().order_by("nombre", "nip")

    @extend_schema(
        summary="Ficha 360 del contacto", description="Datos del contacto con sus motos, RTM, SOAT y llamadas."
    )
    @action(detail=True, methods=["get"])
    def ficha(self, request: Request, nip: str | None = None) -> Response:
        from apps.llamadas.models import LlamadaCumpleanos, LlamadaRtm, LlamadaSoat
        from apps.llamadas.serializers import LlamadaCumpleanosSerializer, LlamadaRtmSerializer, LlamadaSoatSerializer
        from apps.revisiones.models import Revision, Soat
        from apps.revisiones.serializers import RevisionSerializer, SoatSerializer
        from apps.vehiculos.models import Moto
        from apps.vehiculos.serializers import MotoSerializer

        contacto = self.get_object()
        # Todo en la ficha pertenece a este contacto: las relaciones se asignan en memoria (sin consultas extra).
        motos = list(Moto.objects.filter(contacto_id=contacto.nip).order_by("placa"))
        for moto in motos:
            moto.contacto = contacto
        por_placa = {m.placa: m for m in motos}
        placas = list(por_placa)

        def con_moto(filas: Any) -> list[Any]:
            lista = list(filas)
            for fila in lista:
                if fila.moto_id in por_placa:
                    fila.moto = por_placa[fila.moto_id]
            return lista

        llamadas_cumple = list(
            LlamadaCumpleanos.objects.filter(contacto_id=contacto.nip).order_by("-fecha")[:LIMITE_FICHA]
        )
        for llamada in llamadas_cumple:
            llamada.contacto = contacto
        return Response(
            {
                "contacto": ContactoSerializer(contacto).data,
                "motos": MotoSerializer(motos, many=True).data,
                "revisiones": RevisionSerializer(
                    con_moto(Revision.objects.filter(moto_id__in=placas).order_by("-fecha_certificado")[:LIMITE_FICHA]),
                    many=True,
                ).data,
                "soats": SoatSerializer(
                    con_moto(Soat.objects.filter(moto_id__in=placas).order_by("-fecha_soat")[:LIMITE_FICHA]), many=True
                ).data,
                "llamadas_cumpleanos": LlamadaCumpleanosSerializer(llamadas_cumple, many=True).data,
                "llamadas_rtm": LlamadaRtmSerializer(
                    LlamadaRtm.objects.filter(moto_id__in=placas).order_by("-fecha")[:LIMITE_FICHA], many=True
                ).data,
                "llamadas_soat": LlamadaSoatSerializer(
                    LlamadaSoat.objects.filter(moto_id__in=placas).order_by("-fecha")[:LIMITE_FICHA], many=True
                ).data,
            }
        )
