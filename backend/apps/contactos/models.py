"""Contactos (clientes). Sucesor de la tabla legada `contacto`."""

from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.comun.models import Auditable

MESES = [
    (1, "Enero"),
    (2, "Febrero"),
    (3, "Marzo"),
    (4, "Abril"),
    (5, "Mayo"),
    (6, "Junio"),
    (7, "Julio"),
    (8, "Agosto"),
    (9, "Septiembre"),
    (10, "Octubre"),
    (11, "Noviembre"),
    (12, "Diciembre"),
]
ESTADOS_CONTACTO = [("habilitado", "Habilitado"), ("inhabilitado", "Inhabilitado")]


class Contacto(Auditable):
    nip = models.CharField("documento (nip)", max_length=30, primary_key=True)
    nombre = models.CharField(max_length=255)
    telefono = models.CharField(max_length=100, blank=True, default="")
    celular = models.CharField(max_length=100, blank=True, default="")
    dia_nac = models.PositiveSmallIntegerField("día de nacimiento", null=True, blank=True)
    mes_nac = models.PositiveSmallIntegerField("mes de nacimiento", choices=MESES, null=True, blank=True)
    direccion = models.CharField(max_length=255, blank=True, default="")
    correo = models.CharField(max_length=100, blank=True, default="")
    usuario = models.CharField("registrado por", max_length=255, blank=True, default="")
    estado = models.CharField(max_length=20, choices=ESTADOS_CONTACTO, default="habilitado", db_index=True)
    fecha_registro = models.DateTimeField(null=True, blank=True, db_index=True)
    cumple_confir = models.BooleanField("cumpleaños confirmado", default=False)
    contactar_cumpleanos = models.BooleanField("desea ser contactado para cumpleaños", default=True, db_index=True)
    contactar_soat = models.BooleanField("desea ser contactado para SOAT", default=True, db_index=True)
    contactar_rtm = models.BooleanField("desea ser contactado para RTM", default=True, db_index=True)

    class Meta:
        db_table = "contactos_contacto"
        ordering = ["nombre"]
        verbose_name = "contacto"
        verbose_name_plural = "contactos"
        indexes = [
            GinIndex(name="contacto_nombre_trgm", fields=["nombre"], opclasses=["gin_trgm_ops"]),
            models.Index(fields=["mes_nac", "dia_nac"], name="contacto_cumple_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.nip})"
