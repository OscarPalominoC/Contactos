"""Serializers de cuentas."""

from typing import Any

from rest_framework import serializers

from apps.comun.serializers import EstrictoMixin, SerializerEstricto
from apps.cuentas.models import ROLES, Usuario


class LoginSerializer(EstrictoMixin, serializers.Serializer):  # type: ignore[type-arg]
    """Credenciales de ingreso."""

    nip = serializers.CharField(max_length=20, help_text="Usuario (nip).")
    password = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)


class CambioClaveSerializer(EstrictoMixin, serializers.Serializer):  # type: ignore[type-arg]
    """Cambio de la propia clave."""

    clave_actual = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)
    clave_nueva = serializers.CharField(max_length=128, write_only=True, trim_whitespace=False)


class AccesoSerializer(serializers.Serializer):  # type: ignore[type-arg]
    """Respuesta de login y refresh. El refresh token viaja solo en cookie HttpOnly."""

    access = serializers.CharField()
    expira_en = serializers.IntegerField(help_text="Segundos de vida del token de acceso.")


class YoSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    permisos = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = ["nip", "nombre", "rol", "debe_cambiar_clave", "permisos"]
        read_only_fields = fields

    def get_permisos(self, obj: Usuario) -> list[str]:
        return sorted(obj.get_all_permissions())


class MiNombreSerializer(SerializerEstricto):
    """El propio usuario solo puede cambiar su nombre visible."""

    class Meta:
        model = Usuario
        fields = ["nombre"]

    def validate_nombre(self, valor: str) -> str:
        limpio = " ".join(valor.upper().split())
        if len(limpio) < 3:
            raise serializers.ValidationError("Escriba su nombre (mínimo 3 letras).")
        return limpio


class UsuarioSerializer(serializers.ModelSerializer):  # type: ignore[type-arg]
    class Meta:
        model = Usuario
        fields = ["nip", "nombre", "rol", "is_active", "debe_cambiar_clave", "last_login", "clave_cambiada_en"]
        read_only_fields = fields


class UsuarioEscrituraSerializer(SerializerEstricto):
    rol = serializers.ChoiceField(choices=ROLES)

    class Meta:
        model = Usuario
        fields = ["nip", "nombre", "rol", "is_active"]
        extra_kwargs: dict[str, dict[str, Any]] = {"nip": {"validators": []}}

    def validate_nip(self, valor: str) -> str:
        from apps.comun.excepciones import Conflicto

        limpio = valor.strip()
        if self.instance is None and Usuario.objects.filter(nip=limpio).exists():
            raise Conflicto("Ya existe un usuario con ese nip.")
        return limpio

    def validate_nombre(self, valor: str) -> str:
        return " ".join(valor.upper().split())

    def update(self, instance: Usuario, validated_data: dict[str, Any]) -> Usuario:
        validated_data.pop("nip", None)
        actualizado: Usuario = super().update(instance, validated_data)
        return actualizado
