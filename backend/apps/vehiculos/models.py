"""Vehículos: marcas, líneas y motos."""

from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.comun.models import Auditable


class Marca(Auditable):
    codigo = models.CharField(max_length=50, primary_key=True)
    nombre = models.CharField(max_length=255)

    class Meta:
        db_table = "vehiculos_marca"
        ordering = ["nombre"]
        verbose_name = "marca"
        verbose_name_plural = "marcas"

    def __str__(self) -> str:
        return self.nombre


class Linea(Auditable):
    linea = models.CharField(max_length=50, primary_key=True)
    marca = models.ForeignKey(
        Marca, on_delete=models.PROTECT, db_constraint=False, db_column="codigo_marca", related_name="lineas"
    )

    class Meta:
        db_table = "vehiculos_linea"
        ordering = ["linea"]
        verbose_name = "línea"
        verbose_name_plural = "líneas"

    def __str__(self) -> str:
        return self.linea


class Moto(Auditable):
    """Sucesor de `moto`. Marca y línea se guardan como texto del legado y se relacionan por nombre."""

    placa = models.CharField(max_length=6, primary_key=True)
    marca = models.CharField(max_length=100, db_index=True)
    modelo = models.CharField("modelo (año)", max_length=4, blank=True, default="")
    linea = models.CharField(max_length=100, blank=True, default="")
    contacto = models.ForeignKey(
        "contactos.Contacto",
        on_delete=models.PROTECT,
        db_constraint=False,
        db_column="nip_contacto",
        related_name="motos",
    )
    nro_soat = models.CharField(max_length=100, blank=True, default="")
    fecha_soat = models.DateField(null=True, blank=True)
    fecha_venc_soat = models.DateField(null=True, blank=True)
    nro_certificado = models.CharField(max_length=50, blank=True, default="")
    fecha_rtmg = models.DateField("fecha RTM", null=True, blank=True)
    fecha_venc_rtmg = models.DateField("vencimiento RTM", null=True, blank=True)

    class Meta:
        db_table = "vehiculos_moto"
        ordering = ["placa"]
        verbose_name = "moto"
        verbose_name_plural = "motos"
        indexes = [GinIndex(name="moto_placa_trgm", fields=["placa"], opclasses=["gin_trgm_ops"])]

    def __str__(self) -> str:
        return self.placa
