"""Modelos transversales: idempotencia, rechazos de importación y auditoría."""

from django.conf import settings
from django.db import models


class Auditable(models.Model):
    """Campos de auditoría comunes a las tablas de negocio."""

    creado_en = models.DateTimeField(null=True, blank=True, editable=False)
    actualizado_en = models.DateTimeField(null=True, blank=True, editable=False)
    creado_por = models.CharField(max_length=255, blank=True, default="", editable=False)
    actualizado_por = models.CharField(max_length=255, blank=True, default="", editable=False)

    class Meta:
        abstract = True


class ClaveIdempotencia(models.Model):
    """Respuesta guardada de una petición POST/PUT/PATCH durante 24 h."""

    clave = models.CharField(max_length=100)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    metodo = models.CharField(max_length=10)
    ruta = models.CharField(max_length=500)
    huella_cuerpo = models.CharField(max_length=64)
    estado_respuesta = models.PositiveSmallIntegerField()
    cuerpo_respuesta = models.JSONField(null=True)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "comun_clave_idempotencia"
        constraints = [models.UniqueConstraint(fields=["clave", "usuario"], name="uq_idempotencia_clave_usuario")]
        verbose_name = "clave de idempotencia"
        verbose_name_plural = "claves de idempotencia"


class ImportacionRechazo(models.Model):
    """Fila del legado que no se pudo importar, con el motivo."""

    tabla = models.CharField(max_length=60, db_index=True)
    fila_origen = models.TextField()
    motivo = models.CharField(max_length=255)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comun_importacion_rechazo"
        verbose_name = "rechazo de importación"
        verbose_name_plural = "rechazos de importación"


class RegistroAuditoria(models.Model):
    """Cambio realizado desde la API (quién, qué, cuándo)."""

    ACCIONES = [("crear", "Crear"), ("actualizar", "Actualizar"), ("eliminar", "Eliminar"), ("anular", "Anular")]

    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    usuario = models.CharField(max_length=255)
    accion = models.CharField(max_length=20, choices=ACCIONES)
    modelo = models.CharField(max_length=60)
    objeto_id = models.CharField(max_length=255)
    cambios = models.JSONField(default=dict)
    request_id = models.CharField(max_length=36, blank=True, default="")

    class Meta:
        db_table = "comun_registro_auditoria"
        ordering = ["-fecha"]
        verbose_name = "registro de auditoría"
        verbose_name_plural = "registros de auditoría"
