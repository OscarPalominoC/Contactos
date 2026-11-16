"""Serializers de llamadas."""

from typing import Any

from django.utils import timezone
from rest_framework import serializers

from apps.comun.excepciones import Conflicto
from apps.comun.serializers import FechasSegurasMixin, SerializerEstricto
from apps.contactos.models import Contacto
from apps.llamadas.models import ESTADOS_LLAMADA, LlamadaCumpleanos, LlamadaRtm, LlamadaSoat
from apps.vehiculos.models import Moto
from apps.vehiculos.serializers import normalizar_placa

ESTADOS_ELEGIBLES = [e for e in ESTADOS_LLAMADA if e[0] != "sin_estado"]
CAMPOS_LECTURA = [
    "estado",
    "estado_nombre",
    "observacion",
    "usuario",
    "num_llamadas",
    "intentos",
    "creado_en",
    "actualizado_en",
    "creado_por",
    "actualizado_por",
]


def agregar_intento(intentos: str) -> str:
    marca = timezone.localtime().strftime("%Y-%m-%d %H:%M:%S")
    return f"{intentos} ; {marca}" if intentos else marca


class LlamadaCumpleanosSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    nip = serializers.CharField(source="contacto_id", read_only=True)
    nombre = serializers.CharField(source="contacto.nombre", read_only=True, default=None, allow_null=True)
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = LlamadaCumpleanos
        fields = ["id", "fecha", "nip", "nombre", "motivo_llamada", *CAMPOS_LECTURA]
        read_only_fields = fields


class LlamadaCumpleanosEscrituraSerializer(SerializerEstricto):
    nip = serializers.CharField(max_length=30, write_only=True)
    estado = serializers.ChoiceField(choices=ESTADOS_ELEGIBLES)

    class Meta:
        model = LlamadaCumpleanos
        fields = ["nip", "estado", "observacion"]

    def validate_nip(self, valor: str) -> str:
        limpio = valor.strip().upper()
        if not Contacto.objects.filter(nip=limpio).exists():
            raise serializers.ValidationError("No existe un contacto con ese documento.")
        return limpio

    def validate(self, datos: dict[str, Any]) -> dict[str, Any]:
        if "nip" in datos:
            if self.instance is not None and datos["nip"] != self.instance.contacto_id:
                raise serializers.ValidationError({"nip": ["El contacto de una llamada no se puede cambiar."]})
            datos["contacto_id"] = datos.pop("nip")
        if self.instance is None:
            datos["fecha"] = timezone.now()
            datos["intentos"] = agregar_intento("")
        return datos


class _LlamadaPlacaLectura(FechasSegurasMixin, serializers.ModelSerializer):  # type: ignore[type-arg]
    placa = serializers.CharField(source="moto_id", read_only=True)
    estado_nombre = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        fields = ["id", "fecha", "placa", "motivo_llamada", *CAMPOS_LECTURA]
        read_only_fields = fields


class LlamadaRtmSerializer(_LlamadaPlacaLectura):
    class Meta(_LlamadaPlacaLectura.Meta):
        model = LlamadaRtm


class LlamadaSoatSerializer(_LlamadaPlacaLectura):
    class Meta(_LlamadaPlacaLectura.Meta):
        model = LlamadaSoat


class _LlamadaPlacaEscritura(SerializerEstricto):
    """Registrar un intento: si ya existe la llamada de esa placa y fecha objetivo, se suma el intento (409 al crear)."""

    placa = serializers.CharField(max_length=10, write_only=True)
    estado = serializers.ChoiceField(choices=ESTADOS_ELEGIBLES)
    fecha = serializers.DateField(help_text="Fecha objetivo (vencimiento al que se refiere la llamada).")

    class Meta:
        fields = ["placa", "fecha", "estado", "observacion"]

    def validate_placa(self, valor: str) -> str:
        limpio = normalizar_placa(valor)
        if not Moto.objects.filter(placa=limpio).exists():
            raise serializers.ValidationError("No existe una moto con esa placa.")
        return limpio

    def validate(self, datos: dict[str, Any]) -> dict[str, Any]:
        modelo = self.Meta.model  # type: ignore[attr-defined]
        if self.instance is None:
            placa = datos.pop("placa", None)
            if placa is None:
                raise serializers.ValidationError({"placa": ["La placa es obligatoria."]})
            identificador = f"{placa}.{datos['fecha']:%Y-%m-%d}"
            if modelo.objects.filter(id=identificador).exists():
                raise Conflicto("Ya hay una llamada para esa placa y fecha; registre el intento en ella.")
            datos.update(id=identificador, moto_id=placa, intentos=agregar_intento(""), num_llamadas=1)
        else:
            if "placa" in datos and datos.pop("placa") != self.instance.moto_id:
                raise serializers.ValidationError({"placa": ["La placa de una llamada no se puede cambiar."]})
            if "fecha" in datos and datos["fecha"] != self.instance.fecha:
                raise serializers.ValidationError({"fecha": ["La fecha objetivo no se puede cambiar."]})
        return datos


class LlamadaRtmEscrituraSerializer(_LlamadaPlacaEscritura):
    class Meta(_LlamadaPlacaEscritura.Meta):
        model = LlamadaRtm

    def create(self, datos: dict[str, Any]) -> LlamadaRtm:
        datos.setdefault("motivo_llamada", "rtmyg")
        return super().create(datos)  # type: ignore[no-any-return]


class LlamadaSoatEscrituraSerializer(_LlamadaPlacaEscritura):
    class Meta(_LlamadaPlacaEscritura.Meta):
        model = LlamadaSoat

    def create(self, datos: dict[str, Any]) -> LlamadaSoat:
        datos.setdefault("motivo_llamada", "soat")
        return super().create(datos)  # type: ignore[no-any-return]


class IntentoSerializer(SerializerEstricto):
    """Nuevo intento sobre una llamada existente."""

    estado = serializers.ChoiceField(choices=ESTADOS_ELEGIBLES)
    observacion = serializers.CharField(allow_blank=True, max_length=2000)

    class Meta:
        model = LlamadaRtm
        fields = ["estado", "observacion"]
