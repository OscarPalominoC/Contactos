"""Serializers base: rechazan campos desconocidos (asignación masiva)."""

from typing import Any

from django.db import models
from rest_framework import serializers


class EstrictoMixin:
    """Rechaza campos que no estén declarados en el serializer."""

    def to_internal_value(self, data: Any) -> Any:
        if isinstance(data, dict):
            conocidos = set(self.fields)  # type: ignore[attr-defined]
            desconocidos = sorted(set(data) - conocidos)
            if desconocidos:
                raise serializers.ValidationError({campo: ["Campo no permitido."] for campo in desconocidos})
        return super().to_internal_value(data)  # type: ignore[misc]


class SerializerEstricto(EstrictoMixin, serializers.ModelSerializer):  # type: ignore[type-arg]
    """ModelSerializer con fields explícitos y rechazo de campos extra.

    `instance` se declara como Any porque cada subclase trabaja con su propio modelo y en
    validate_* se consultan atributos concretos (placa, certificado, soat...).
    """

    instance: Any

    def to_internal_value(self, data: Any) -> Any:
        datos = super().to_internal_value(data)
        return conservar_fechas_legadas(self.instance, datos)


def conservar_fechas_legadas(instancia: Any, datos: dict[str, Any]) -> dict[str, Any]:
    """Un `null` sobre una fecha insalvable del legado no la borra: el cliente la recibió como `null` (oculta).

    Así, editar cualquier otro campo conserva el dato original por trazabilidad. Enviar una fecha válida sí la reemplaza.
    """
    if instancia is None:
        return datos
    from datetime import date

    from apps.comun.fechas_util import fecha_segura

    for campo in [c for c, v in datos.items() if v is None]:
        guardada = getattr(instancia, campo, None)
        if isinstance(guardada, date) and fecha_segura(guardada) is None:
            datos.pop(campo)
    return datos


class FechaSeguraField(serializers.DateField):
    """Fecha de solo lectura: las fechas insalvables del legado (año fuera de 1990-2100) salen como null."""

    def to_representation(self, value: Any) -> Any:
        from apps.comun.fechas_util import fecha_segura

        segura = fecha_segura(value) if value else None
        return None if segura is None else super().to_representation(segura)


class FechasSegurasMixin:
    """En serializers de lectura, todo `DateField` del modelo se expone con `FechaSeguraField`."""

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        models.DateField: FechaSeguraField,
    }
