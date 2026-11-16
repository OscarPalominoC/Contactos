"""Serializers de contactos."""

import re
from typing import Any

from rest_framework import serializers

from apps.comun.fechas_util import es_cumpleanos_valido
from apps.comun.serializers import SerializerEstricto
from apps.contactos.models import Contacto

PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ContactoSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    mes_nac_nombre = serializers.CharField(source="get_mes_nac_display", read_only=True)

    class Meta:
        model = Contacto
        fields = [
            "nip",
            "nombre",
            "telefono",
            "celular",
            "dia_nac",
            "mes_nac",
            "mes_nac_nombre",
            "direccion",
            "correo",
            "estado",
            "usuario",
            "fecha_registro",
            "cumple_confir",
            "contactar_cumpleanos",
            "contactar_soat",
            "contactar_rtm",
            "creado_en",
            "actualizado_en",
            "creado_por",
            "actualizado_por",
        ]
        read_only_fields = fields


class ContactoEscrituraSerializer(SerializerEstricto):
    class Meta:
        model = Contacto
        fields = [
            "nip",
            "nombre",
            "telefono",
            "celular",
            "dia_nac",
            "mes_nac",
            "direccion",
            "correo",
            "estado",
            "cumple_confir",
            "contactar_cumpleanos",
            "contactar_soat",
            "contactar_rtm",
        ]
        extra_kwargs: dict[str, dict[str, Any]] = {"nip": {"validators": []}}

    def validate_nip(self, valor: str) -> str:
        limpio = re.sub(r"\s+", "", valor).upper()
        if not re.fullmatch(r"[0-9A-Z-]{3,30}", limpio):
            raise serializers.ValidationError("Use solo números, letras y guiones (3 a 30).")
        if self.instance is not None and limpio != self.instance.nip:
            raise serializers.ValidationError("El documento no se puede cambiar.")
        if self.instance is None and Contacto.objects.filter(nip=limpio).exists():
            from apps.comun.excepciones import Conflicto

            raise Conflicto("Ya existe un contacto con ese documento.")
        return limpio

    def validate_nombre(self, valor: str) -> str:
        limpio = " ".join(valor.upper().split())
        if len(limpio) < 3:
            raise serializers.ValidationError("Escriba el nombre completo.")
        return limpio

    def validate_correo(self, valor: str) -> str:
        limpio = valor.strip().lower()
        if limpio and not PATRON_CORREO.match(limpio):
            raise serializers.ValidationError("Escriba un correo válido, por ejemplo nombre@dominio.com.")
        return limpio

    def validate_dia_nac(self, valor: int | None) -> int | None:
        if valor is not None and not 1 <= valor <= 31:
            raise serializers.ValidationError("El día debe estar entre 1 y 31.")
        return valor

    def validate(self, datos: dict[str, Any]) -> dict[str, Any]:
        for campo in ("telefono", "celular", "direccion"):
            if campo in datos:
                datos[campo] = " ".join(str(datos[campo]).split())
        dia = datos.get("dia_nac", getattr(self.instance, "dia_nac", None))
        mes = datos.get("mes_nac", getattr(self.instance, "mes_nac", None))
        if dia is not None and mes is not None and not es_cumpleanos_valido(dia, mes):
            # Fecha inexistente (p. ej. 31 de febrero, centinela del legado): no se generan llamadas de cumpleaños.
            datos["contactar_cumpleanos"] = False
        return datos
