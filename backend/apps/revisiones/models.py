"""Revisiones técnico-mecánicas (RTM) y pólizas SOAT."""

from datetime import date

from django.db import models
from django.utils import timezone

from apps.comun.fechas_util import fecha_segura
from apps.comun.models import Auditable

ESTADOS_DOCUMENTO = [
    ("VIGENTE", "Vigente"),
    ("VENCIDO", "Vencido"),
    ("DUPLICADO", "Duplicado"),
    ("ANULADO", "Anulado"),
    ("NO", "No (valor legado)"),
]
ESTADOS_MANUALES = {"DUPLICADO", "ANULADO", "NO"}


def estado_calculado(estado_guardado: str, vencimiento: date | None) -> str:
    """VIGENTE/VENCIDO se calculan con la fecha de vencimiento; DUPLICADO y ANULADO los marca un usuario."""
    if estado_guardado in ESTADOS_MANUALES:
        return estado_guardado
    if vencimiento is not None and fecha_segura(vencimiento) is None:
        return "VENCIDO"  # vencimiento basura del legado (3017, 1899…): no se puede afirmar que esté vigente
    if vencimiento is None:
        return estado_guardado or "VENCIDO"
    return "VIGENTE" if vencimiento >= timezone.localdate() else "VENCIDO"


class Revision(Auditable):
    """Sucesor de `revision`."""

    certificado = models.CharField(max_length=45, primary_key=True)
    soat = models.CharField(max_length=45, blank=True, default="")
    fecha_soat = models.DateField(null=True, blank=True)
    fecha_venc_soat = models.DateField(null=True, blank=True)
    fecha_certificado = models.DateField(null=True, blank=True)
    fecha_venc_certificado = models.DateField(null=True, blank=True, db_index=True)
    moto = models.ForeignKey(
        "vehiculos.Moto", on_delete=models.PROTECT, db_constraint=False, db_column="placa", related_name="revisiones"
    )
    nro_autodeclaracion_runt = models.CharField(max_length=50, blank=True, default="")
    nro_solicitud_runt = models.CharField(max_length=50, blank=True, default="")
    nro_certificado_runt = models.CharField(max_length=50, blank=True, default="")
    fecha_registro_runt = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_DOCUMENTO, default="VIGENTE", db_index=True)
    fecha_registro = models.DateTimeField(null=True, blank=True, db_index=True)
    usuario = models.CharField("registrado por", max_length=255, blank=True, default="")

    class Meta:
        db_table = "revisiones_revision"
        ordering = ["-fecha_certificado"]
        verbose_name = "revisión RTM"
        verbose_name_plural = "revisiones RTM"

    def __str__(self) -> str:
        return f"{self.certificado} ({self.moto_id})"

    @property
    def estado_actual(self) -> str:
        return estado_calculado(self.estado, self.fecha_venc_certificado)


class Soat(Auditable):
    """Sucesor de `soat1`. La clave es `numero-ASEGURADORA`."""

    soat = models.CharField("póliza", max_length=255, primary_key=True)
    fecha_soat = models.DateField(null=True, blank=True)
    fecha_venc_soat = models.DateField(null=True, blank=True, db_index=True)
    moto = models.ForeignKey(
        "vehiculos.Moto",
        on_delete=models.PROTECT,
        db_constraint=False,
        db_column="placa",
        related_name="soats",
        null=True,
        blank=True,
    )
    estado = models.CharField(max_length=20, choices=ESTADOS_DOCUMENTO, default="VIGENTE", db_index=True)
    usuario = models.CharField("registrado por", max_length=255, blank=True, default="")
    fecha_registro = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "revisiones_soat"
        ordering = ["-fecha_soat"]
        verbose_name = "SOAT"
        verbose_name_plural = "SOAT"

    def __str__(self) -> str:
        return self.soat

    @property
    def aseguradora(self) -> str:
        return self.soat.rsplit("-", 1)[1] if "-" in self.soat else ""

    @property
    def estado_actual(self) -> str:
        return estado_calculado(self.estado, self.fecha_venc_soat)
