"""Bitácoras de llamadas: cumpleaños (por contacto), RTM y SOAT (por placa)."""

from django.db import models

from apps.comun.models import Auditable

ESTADOS_LLAMADA = [
    ("realizada", "Realizada"),
    ("no_realizada", "No realizada"),
    ("realizada_sin_exito", "Realizada sin éxito"),
    ("ocupada", "Ocupada"),
    ("sin_estado", "Sin estado"),
]
MOTIVOS = [("cumpleanos", "Cumpleaños"), ("rtmyg", "RTM y gases"), ("soat", "SOAT")]


class LlamadaBase(Auditable):
    estado = models.CharField(max_length=30, choices=ESTADOS_LLAMADA, default="realizada", db_index=True)
    observacion = models.TextField(blank=True, default="")
    usuario = models.CharField(max_length=255, blank=True, default="")
    num_llamadas = models.PositiveIntegerField(default=1)
    intentos = models.TextField(
        "marcas de tiempo de los intentos", blank=True, default="", help_text="Fechas y horas separadas por ';'."
    )

    class Meta:
        abstract = True


class LlamadaCumpleanos(LlamadaBase):
    """Sucesor de `bitacora_llamadas`."""

    fecha = models.DateTimeField(db_index=True)
    contacto = models.ForeignKey(
        "contactos.Contacto",
        on_delete=models.PROTECT,
        db_constraint=False,
        db_column="nip",
        related_name="llamadas_cumpleanos",
    )
    motivo_llamada = models.CharField(max_length=20, choices=MOTIVOS, default="cumpleanos")

    class Meta:
        db_table = "llamadas_cumpleanos"
        ordering = ["-fecha", "-id"]
        verbose_name = "llamada de cumpleaños"
        verbose_name_plural = "llamadas de cumpleaños"

    def __str__(self) -> str:
        return f"{self.contacto_id} {self.fecha:%Y-%m-%d}"


class LlamadaPlaca(LlamadaBase):
    """Base de las llamadas por placa. `id` = PLACA.AAAA-MM-DD (fecha objetivo)."""

    id = models.CharField(max_length=20, primary_key=True)
    fecha = models.DateField(db_index=True)
    motivo_llamada = models.CharField(max_length=20, choices=MOTIVOS, default="rtmyg")

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.id


class LlamadaRtm(LlamadaPlaca):
    """Sucesor de `bitacora_llamadas_rtmyg`."""

    moto = models.ForeignKey(
        "vehiculos.Moto", on_delete=models.PROTECT, db_constraint=False, db_column="placa", related_name="llamadas_rtm"
    )

    class Meta:
        db_table = "llamadas_rtm"
        ordering = ["-fecha"]
        verbose_name = "llamada de RTM"
        verbose_name_plural = "llamadas de RTM"


class LlamadaSoat(LlamadaPlaca):
    """Sucesor de `bitacora_llamadas_soat`."""

    moto = models.ForeignKey(
        "vehiculos.Moto", on_delete=models.PROTECT, db_constraint=False, db_column="placa", related_name="llamadas_soat"
    )

    class Meta:
        db_table = "llamadas_soat"
        ordering = ["-fecha"]
        verbose_name = "llamada de SOAT"
        verbose_name_plural = "llamadas de SOAT"
