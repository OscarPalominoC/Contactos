"""Serializers de vehículos."""

import re
from typing import Any

from rest_framework import serializers

from apps.comun.excepciones import Conflicto
from apps.comun.serializers import FechasSegurasMixin, SerializerEstricto
from apps.contactos.models import Contacto
from apps.vehiculos.models import Linea, Marca, Moto


def normalizar_placa(valor: str) -> str:
    return re.sub(r"[\s-]+", "", valor).upper()


class MarcaSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    class Meta:
        model = Marca
        fields = ["codigo", "nombre"]
        read_only_fields = fields


class MarcaEscrituraSerializer(SerializerEstricto):
    class Meta:
        model = Marca
        fields = ["codigo", "nombre"]
        extra_kwargs: dict[str, dict[str, Any]] = {"codigo": {"validators": []}}

    def validate_codigo(self, valor: str) -> str:
        limpio = valor.strip().upper()
        if self.instance is None and Marca.objects.filter(codigo=limpio).exists():
            raise Conflicto("Ya existe una marca con ese código.")
        if self.instance is not None and limpio != self.instance.codigo:
            raise serializers.ValidationError("El código no se puede cambiar.")
        return limpio

    def validate_nombre(self, valor: str) -> str:
        return " ".join(valor.upper().split())


class LineaSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    marca_nombre = serializers.CharField(source="marca.nombre", read_only=True, default="")

    class Meta:
        model = Linea
        fields = ["linea", "marca", "marca_nombre"]
        read_only_fields = fields


class LineaEscrituraSerializer(SerializerEstricto):
    marca = serializers.PrimaryKeyRelatedField(queryset=Marca.objects.all())

    class Meta:
        model = Linea
        fields = ["linea", "marca"]
        extra_kwargs: dict[str, dict[str, Any]] = {"linea": {"validators": []}}

    def validate_linea(self, valor: str) -> str:
        limpio = " ".join(valor.upper().split())
        if self.instance is None and Linea.objects.filter(linea=limpio).exists():
            raise Conflicto("Ya existe esa línea.")
        if self.instance is not None and limpio != self.instance.linea:
            raise serializers.ValidationError("El nombre de la línea no se puede cambiar.")
        return limpio


class MotoSerializer(FechasSegurasMixin, serializers.ModelSerializer):  # type: ignore[type-arg]
    nip_contacto = serializers.CharField(source="contacto_id", read_only=True)
    nombre_contacto = serializers.CharField(source="contacto.nombre", read_only=True, default=None, allow_null=True)

    class Meta:
        model = Moto
        fields = [
            "placa",
            "marca",
            "modelo",
            "linea",
            "nip_contacto",
            "nombre_contacto",
            "nro_soat",
            "fecha_soat",
            "fecha_venc_soat",
            "nro_certificado",
            "fecha_rtmg",
            "fecha_venc_rtmg",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "actualizado_por",
        ]
        read_only_fields = fields


class MotoDetalleSerializer(MotoSerializer):
    propietario = serializers.SerializerMethodField()

    class Meta(MotoSerializer.Meta):
        fields = [*MotoSerializer.Meta.fields, "propietario"]
        read_only_fields = fields

    def get_propietario(self, obj: Moto) -> dict[str, str] | None:
        contacto = Contacto.objects.filter(nip=obj.contacto_id).only("nip", "nombre", "celular").first()
        if contacto is None:
            return None
        return {"nip": contacto.nip, "nombre": contacto.nombre, "celular": contacto.celular}


class MotoEscrituraSerializer(SerializerEstricto):
    nip_contacto = serializers.CharField(max_length=30, write_only=True)

    class Meta:
        model = Moto
        fields = [
            "placa",
            "marca",
            "modelo",
            "linea",
            "nip_contacto",
            "nro_soat",
            "fecha_soat",
            "fecha_venc_soat",
            "nro_certificado",
            "fecha_rtmg",
            "fecha_venc_rtmg",
        ]
        extra_kwargs: dict[str, dict[str, Any]] = {"placa": {"validators": [], "max_length": 10}}

    def validate_placa(self, valor: str) -> str:
        limpio = normalizar_placa(valor)
        if not re.fullmatch(r"[A-Z0-9]{5,6}", limpio):
            raise serializers.ValidationError("La placa debe tener 5 o 6 letras y números, por ejemplo ABC12D.")
        if self.instance is not None and limpio != self.instance.placa:
            raise serializers.ValidationError("La placa no se puede cambiar.")
        if self.instance is None and Moto.objects.filter(placa=limpio).exists():
            raise Conflicto("Ya existe una moto con esa placa.")
        return limpio

    def validate_modelo(self, valor: str) -> str:
        if valor and not re.fullmatch(r"\d{4}", valor):
            raise serializers.ValidationError("El modelo es el año de 4 dígitos.")
        return valor

    def validate_nip_contacto(self, valor: str) -> str:
        limpio = valor.strip().upper()
        if not Contacto.objects.filter(nip=limpio).exists():
            raise serializers.ValidationError("No existe un contacto con ese documento.")
        return limpio

    def validate(self, datos: dict[str, Any]) -> dict[str, Any]:
        marca = datos.get("marca", getattr(self.instance, "marca", ""))
        linea = datos.get("linea", getattr(self.instance, "linea", ""))
        if "marca" in datos:
            datos["marca"] = " ".join(datos["marca"].upper().split())
            marca = datos["marca"]
        if linea:
            registro = Linea.objects.select_related("marca").filter(linea=linea).first()
            if registro is not None and registro.marca.nombre != marca and registro.marca_id != marca:
                raise serializers.ValidationError({"linea": ["La línea no pertenece a la marca elegida."]})
        if "nip_contacto" in datos:
            datos["contacto_id"] = datos.pop("nip_contacto")
        return datos
