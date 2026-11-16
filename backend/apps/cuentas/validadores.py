"""Validador: impide reutilizar la clave actual (la temporal) y las 3 anteriores."""

from typing import Any

from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError

HISTORIAL = 3


class HistorialClavesValidator:
    def validate(self, password: str, user: Any = None) -> None:
        if user is None or not getattr(user, "pk", None):
            return
        if user.password and user.check_password(password):
            raise ValidationError("La nueva clave no puede ser igual a la actual.", code="clave_repetida")
        for anterior in user.claves_anteriores.all()[:HISTORIAL]:
            if check_password(password, anterior.hash_clave):
                raise ValidationError(
                    f"La nueva clave no puede ser una de sus últimas {HISTORIAL} claves.", code="clave_repetida"
                )

    def get_help_text(self) -> str:
        return f"No puede repetir la clave actual ni las últimas {HISTORIAL}."
