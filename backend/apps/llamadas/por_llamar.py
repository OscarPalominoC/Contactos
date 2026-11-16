"""Llamadas por hacer, calculadas desde los vencimientos.

Las tablas de llamadas son una bitácora de lo ya llamado (casi todo «realizada»), así que la lista de
a quién llamar no puede salir de ellas: sale de las RTM y SOAT que vencen en el rango. Por cada placa
se toma su documento más reciente (sin anulados/duplicados); si la moto ya renovó, su vencimiento
nuevo queda fuera del rango y no se le llama. Se excluye lo que ya tiene una llamada «realizada» para
esa placa y fecha, y solo se incluyen titulares habilitados que autorizan el canal. Los intentos sin
éxito se muestran con su llamada, al final de la lista.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from django.db.models import Case, Exists, F, IntegerField, OuterRef, Q, QuerySet, Subquery, Value, When
from django.utils import timezone
from rest_framework import serializers

from apps.comun.excepciones import DatosInvalidos
from apps.llamadas.models import LlamadaRtm, LlamadaSoat
from apps.revisiones.models import ESTADOS_MANUALES, Revision, Soat

DIAS_POR_DEFECTO = 30


@dataclass(frozen=True)
class Canal:
    documento: type[Revision] | type[Soat]
    clave: str
    vencimiento: str
    llamada: type[LlamadaRtm] | type[LlamadaSoat]
    consentimiento: str


RTM = Canal(Revision, "certificado", "fecha_venc_certificado", LlamadaRtm, "contactar_rtm")
SOAT = Canal(Soat, "soat", "fecha_venc_soat", LlamadaSoat, "contactar_soat")


def rango(parametros: Any) -> tuple[date, date]:
    """filter[desde]/filter[hasta] (AAAA-MM-DD); por defecto hoy a hoy + 30 días."""

    def leer(clave: str) -> date | None:
        texto = parametros.get(f"filter[{clave}]")
        if not texto:
            return None
        try:
            return date.fromisoformat(texto)
        except ValueError as error:
            raise DatosInvalidos(f"Fecha no válida en {clave}: use AAAA-MM-DD.") from error

    hoy = timezone.localdate()
    desde = leer("desde") or hoy
    hasta = leer("hasta") or max(desde, hoy) + timedelta(days=DIAS_POR_DEFECTO)
    if desde > hasta:
        raise DatosInvalidos("La fecha inicial no puede ser posterior a la final.")
    return desde, hasta


def por_llamar(canal: Canal, desde: date, hasta: date) -> QuerySet[Any]:
    venc, clave = canal.vencimiento, canal.clave
    vigentes = canal.documento.objects.exclude(estado__in=ESTADOS_MANUALES)
    posterior = vigentes.filter(moto_id=OuterRef("moto_id")).filter(
        Q(**{f"{venc}__gt": OuterRef(venc)}) | Q(**{venc: OuterRef(venc), f"{clave}__gt": OuterRef(clave)})
    )
    llamadas = canal.llamada.objects.filter(moto_id=OuterRef("moto_id"), fecha=OuterRef(venc))
    return (
        vigentes.filter(
            **{f"{venc}__range": (desde, hasta), "moto__contacto__estado": "habilitado"},
            **{f"moto__contacto__{canal.consentimiento}": True},
        )
        .exclude(Exists(posterior))
        .exclude(Exists(llamadas.filter(estado="realizada")))
        .annotate(
            fecha_objetivo=F(venc),
            propietario_nip=F("moto__contacto_id"),
            propietario_nombre=F("moto__contacto__nombre"),
            celular=F("moto__contacto__celular"),
            llamada_id=Subquery(llamadas.values("id")[:1]),
            llamada_estado=Subquery(llamadas.values("estado")[:1]),
            llamada_intentos=Subquery(llamadas.values("num_llamadas")[:1]),
            llamada_observacion=Subquery(llamadas.values("observacion")[:1]),
            _intentada=Case(
                When(llamada_id__isnull=True, then=Value(0)), default=Value(1), output_field=IntegerField()
            ),
        )
        .order_by("_intentada", venc, "moto_id")
    )


class PorLlamarSerializer(serializers.Serializer):  # type: ignore[type-arg]
    placa = serializers.CharField(source="moto_id")
    fecha = serializers.DateField(source="fecha_objetivo")
    propietario_nip = serializers.CharField()
    propietario_nombre = serializers.CharField()
    celular = serializers.CharField()
    llamada_id = serializers.CharField(allow_null=True)
    estado = serializers.SerializerMethodField()
    num_llamadas = serializers.SerializerMethodField()
    observacion = serializers.SerializerMethodField()

    def get_estado(self, fila: Any) -> str:
        return str(fila.llamada_estado or "sin_llamar")

    def get_num_llamadas(self, fila: Any) -> int:
        return int(fila.llamada_intentos or 0)

    def get_observacion(self, fila: Any) -> str:
        return str(fila.llamada_observacion or "")
