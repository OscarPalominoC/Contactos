"""Serializadores DTO para endpoints de respaldo de base de datos."""

from rest_framework import serializers


class RutaValidacionRequestSerializer(serializers.Serializer):
    """Solicitud para validar una ruta en el disco del servidor."""

    ruta = serializers.CharField(
        max_length=500,
        required=True,
        help_text="Ruta absoluta de la carpeta en el servidor (ej: F:\\Check\\respaldos).",
    )


class RutaValidacionResponseSerializer(serializers.Serializer):
    """Resultado de la validación de una ruta en el servidor."""

    valida = serializers.BooleanField(help_text="Indica si la ruta es válida y tiene permisos de escritura.")
    ruta = serializers.CharField(help_text="Ruta normalizada en el servidor.")
    mensaje = serializers.CharField(help_text="Detalle descriptivo de la validación.")


class RutaConfigRequestSerializer(serializers.Serializer):
    """Solicitud para establecer la ruta configurada de respaldos."""

    ruta = serializers.CharField(
        max_length=500,
        required=True,
        help_text="Ruta absoluta validada donde se guardarán los respaldos en el servidor.",
    )


class RutaConfigResponseSerializer(serializers.Serializer):
    """Confirmación del cambio de ruta configurada."""

    ruta_configurada = serializers.CharField(help_text="Nueva ruta configurada en el servidor.")
    mensaje = serializers.CharField(help_text="Confirmación de actualización.")


class RespaldoUltimoSerializer(serializers.Serializer):
    """Información del archivo de respaldo más reciente."""

    archivo = serializers.CharField(help_text="Nombre del archivo SQL.")
    tamano_bytes = serializers.IntegerField(help_text="Tamaño en bytes.")
    tamano_formateado = serializers.CharField(help_text="Tamaño formateado (ej: 17.2 MB).")
    creado_en = serializers.CharField(help_text="Fecha de creación en formato ISO.")


class EsServidorResponseSerializer(serializers.Serializer):
    """Respuesta que indica si la petición proviene del equipo servidor."""

    es_servidor = serializers.BooleanField(help_text="True si la petición se realiza desde el equipo servidor.")


class RespaldoEstadoResponseSerializer(serializers.Serializer):
    """Estado general del subsistema de respaldos."""

    es_servidor_local = serializers.BooleanField(
        help_text="True si la petición actual proviene directamente del servidor."
    )
    ruta_configurada = serializers.CharField(help_text="Ruta actual donde se guardan los respaldos en el servidor.")
    ejecutando = serializers.BooleanField(help_text="True si hay un proceso de respaldo en curso en el servidor.")
    ultimo_respaldo = RespaldoUltimoSerializer(
        allow_null=True,
        required=False,
        help_text="Detalle del último archivo de respaldo disponible.",
    )
    total_respaldos = serializers.IntegerField(help_text="Cantidad de archivos SQL conservados en la ruta.")
    ultimo_resultado = serializers.CharField(
        allow_null=True,
        required=False,
        help_text="Mensaje del último resultado de ejecución.",
    )


class RespaldoEjecucionResponseSerializer(serializers.Serializer):
    """Respuesta al iniciar el respaldo por consola."""

    mensaje = serializers.CharField(help_text="Mensaje descriptivo del inicio de la tarea.")
    ruta_destino = serializers.CharField(help_text="Carpeta del servidor donde se guardará el archivo.")
    iniciado_en = serializers.CharField(help_text="Marca de tiempo ISO del inicio.")

