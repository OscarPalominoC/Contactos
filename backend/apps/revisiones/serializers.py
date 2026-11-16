"""Serializers de revisiones RTM y SOAT."""

import re
from datetime import date
from typing import Any

from rest_framework import serializers

from apps.comun.excepciones import Conflicto
from apps.comun.fechas_util import fecha_segura
from apps.comun.serializers import FechasSegurasMixin, SerializerEstricto
from apps.revisiones.models import Revision, Soat
from apps.vehiculos.models import Moto
from apps.vehiculos.serializers import normalizar_placa

ESTADOS_EDITABLES = ["VIGENTE", "DUPLICADO", "ANULADO"]


def _propietario(campo: str) -> serializers.CharField:
    """Dato del titular de la moto; None si la moto o el contacto no existen (legado sin integridad)."""
    return serializers.CharField(source=f"moto.contacto.{campo}", read_only=True, default=None, allow_null=True)


class RevisionSerializer(FechasSegurasMixin, serializers.ModelSerializer):  # type: ignore[type-arg]
    placa = serializers.CharField(source="moto_id", read_only=True)
    estado_actual = serializers.CharField(read_only=True)
    propietario_nip = _propietario("nip")
    propietario_nombre = _propietario("nombre")

    class Meta:
        model = Revision
        fields = [
            "certificado",
            "placa",
            "propietario_nip",
            "propietario_nombre",
            "soat",
            "fecha_soat",
            "fecha_venc_soat",
            "fecha_certificado",
            "fecha_venc_certificado",
            "nro_autodeclaracion_runt",
            "nro_solicitud_runt",
            "nro_certificado_runt",
            "fecha_registro_runt",
            "estado",
            "estado_actual",
            "usuario",
            "fecha_registro",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "actualizado_por",
        ]
        read_only_fields = fields


class RevisionEscrituraSerializer(SerializerEstricto):
    placa = serializers.CharField(max_length=10, write_only=True)
    estado = serializers.ChoiceField(choices=[(e, e) for e in ESTADOS_EDITABLES], default="VIGENTE")

    class Meta:
        model = Revision
        fields = [
            "certificado",
            "placa",
            "soat",
            "fecha_soat",
            "fecha_venc_soat",
            "fecha_certificado",
            "fecha_venc_certificado",
            "nro_autodeclaracion_runt",
            "nro_solicitud_runt",
            "nro_certificado_runt",
            "fecha_registro_runt",
            "estado",
        ]
        extra_kwargs: dict[str, dict[str, Any]] = {"certificado": {"validators": []}}

    def validate_certificado(self, valor: str) -> str:
        limpio = valor.strip().upper()
        if not limpio:
            raise serializers.ValidationError("El número de certificado es obligatorio.")
        if self.instance is not None and limpio != self.instance.certificado:
            raise serializers.ValidationError("El número de certificado no se puede cambiar.")
        if self.instance is None and Revision.objects.filter(certificado=limpio).exists():
            raise Conflicto("Ya existe una revisión con ese certificado.")
        return limpio

    def validate_placa(self, valor: str) -> str:
        limpio = normalizar_placa(valor)
        if not Moto.objects.filter(placa=limpio).exists():
            raise serializers.ValidationError("No existe una moto con esa placa.")
        return limpio

    def validate(self, datos: dict[str, Any]) -> dict[str, Any]:
        if "placa" in datos:
            datos["moto_id"] = datos.pop("placa")
        # Las fechas insalvables guardadas cuentan como vacías (el cliente nunca las vio).
        inicio = datos.get("fecha_certificado") or fecha_segura(getattr(self.instance, "fecha_certificado", None))
        vence = datos.get("fecha_venc_certificado") or fecha_segura(
            getattr(self.instance, "fecha_venc_certificado", None)
        )
        if inicio is not None and vence is None:
            datos["fecha_venc_certificado"] = vence = sugerir_vencimiento(inicio)
        if inicio is not None and vence is not None and vence <= inicio:
            raise serializers.ValidationError(
                {"fecha_venc_certificado": ["El vencimiento debe ser posterior a la fecha del certificado."]}
            )
        return datos


def sugerir_vencimiento(inicio: date) -> date:
    """Un año después; el 29 de febrero pasa al 28 de febrero."""
    try:
        return inicio.replace(year=inicio.year + 1)
    except ValueError:
        return inicio.replace(year=inicio.year + 1, day=28)


class SoatSerializer(FechasSegurasMixin, serializers.ModelSerializer):  # type: ignore[type-arg]
    placa = serializers.CharField(source="moto_id", read_only=True)
    estado_actual = serializers.CharField(read_only=True)
    aseguradora = serializers.CharField(read_only=True)
    propietario_nip = _propietario("nip")
    propietario_nombre = _propietario("nombre")

    class Meta:
        model = Soat
        fields = [
            "soat",
            "placa",
            "propietario_nip",
            "propietario_nombre",
            "aseguradora",
            "fecha_soat",
            "fecha_venc_soat",
            "estado",
            "estado_actual",
            "usuario",
            "fecha_registro",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "actualizado_por",
        ]
        read_only_fields = fields


class SoatEscrituraSerializer(SerializerEstricto):
    placa = serializers.CharField(max_length=10, write_only=True)
    numero = serializers.CharField(max_length=100, write_only=True, help_text="Número de la póliza.")
    aseguradora = serializers.CharField(max_length=100, write_only=True)
    estado = serializers.ChoiceField(choices=[(e, e) for e in ESTADOS_EDITABLES], default="VIGENTE")

    class Meta:
        model = Soat
        fields = ["numero", "aseguradora", "placa", "fecha_soat", "fecha_venc_soat", "estado"]

    def validate_placa(self, valor: str) -> str:
        limpio = normalizar_placa(valor)
        if not Moto.objects.filter(placa=limpio).exists():
            raise serializers.ValidationError("No existe una moto con esa placa.")
        return limpio

    def validate_numero(self, valor: str) -> str:
        limpio = re.sub(r"\s+", "", valor).upper()
        if not limpio:
            raise serializers.ValidationError("El número de la póliza es obligatorio.")
        return limpio

    def validate_aseguradora(self, valor: str) -> str:
        return " ".join(valor.upper().split()).replace("-", " ")

    def validate(self, datos: dict[str, Any]) -> dict[str, Any]:
        if "placa" in datos:
            datos["moto_id"] = datos.pop("placa")
        numero = datos.pop("numero", None)
        aseguradora = datos.pop("aseguradora", None)
        if numero and aseguradora:
            clave = f"{numero}-{aseguradora}"
            if self.instance is None:
                if Soat.objects.filter(soat=clave).exists():
                    raise Conflicto("Ya existe una póliza con ese número y aseguradora.")
                datos["soat"] = clave
            elif clave != self.instance.soat:
                raise serializers.ValidationError({"numero": ["El número y la aseguradora no se pueden cambiar."]})
        elif self.instance is None:
            raise serializers.ValidationError("Indique el número y la aseguradora.")
        inicio = datos.get("fecha_soat") or fecha_segura(getattr(self.instance, "fecha_soat", None))
        vence = datos.get("fecha_venc_soat") or fecha_segura(getattr(self.instance, "fecha_venc_soat", None))
        if inicio is not None and vence is None:
            datos["fecha_venc_soat"] = vence = sugerir_vencimiento(inicio)
        if inicio is not None and vence is not None and vence <= inicio:
            raise serializers.ValidationError(
                {"fecha_venc_soat": ["El vencimiento debe ser posterior a la fecha del SOAT."]}
            )
        return datos
