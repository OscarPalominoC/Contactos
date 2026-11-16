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


class ProgresoRespaldoSerializer(serializers.Serializer):
    """Avance de una restauración en curso o finalizada."""

    etapa = serializers.CharField(help_text="Etapa actual: analizando, respaldo_previo, importando o finalizado.")
    tabla_actual = serializers.CharField(allow_null=True, required=False, help_text="Tabla que se está importando.")
    avance = serializers.IntegerField(allow_null=True, required=False, help_text="Tablas procesadas hasta ahora.")
    total = serializers.IntegerField(allow_null=True, required=False, help_text="Total de tablas a procesar.")


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
    progreso = ProgresoRespaldoSerializer(
        allow_null=True,
        required=False,
        help_text="Avance de la última restauración, o null si no hay etapa registrada.",
    )


class RespaldoEjecucionResponseSerializer(serializers.Serializer):
    """Respuesta al iniciar el respaldo por consola."""

    mensaje = serializers.CharField(help_text="Mensaje descriptivo del inicio de la tarea.")
    ruta_destino = serializers.CharField(help_text="Carpeta del servidor donde se guardará el archivo.")
    iniciado_en = serializers.CharField(help_text="Marca de tiempo ISO del inicio.")


class ArchivoSqlItemSerializer(serializers.Serializer):
    """Detalle de un archivo .sql encontrado al explorar carpetas en el servidor."""

    nombre = serializers.CharField(help_text="Nombre del archivo con extensión.")
    ruta_completa = serializers.CharField(help_text="Ruta absoluta completa del archivo en el servidor.")
    tamano_bytes = serializers.IntegerField(help_text="Tamaño del archivo en bytes.")
    tamano_formateado = serializers.CharField(help_text="Tamaño formateado en KB, MB o GB.")
    modificado_en = serializers.CharField(help_text="Fecha de última modificación en formato ISO.")


class ExploracionRutaResponseSerializer(serializers.Serializer):
    """Resultado de la exploración de carpetas y archivos en el servidor."""

    ruta_actual = serializers.CharField(help_text="Ruta absoluta de la carpeta explorada.")
    ruta_padre = serializers.CharField(
        allow_null=True, required=False, help_text="Ruta absoluta de la carpeta superior o null si es raíz."
    )
    carpetas = serializers.ListField(
        child=serializers.CharField(), help_text="Lista de nombres de subcarpetas disponibles."
    )
    archivos_sql = ArchivoSqlItemSerializer(
        many=True, help_text="Lista de archivos .sql disponibles en esta carpeta."
    )
    unidades_disponibles = serializers.ListField(
        child=serializers.CharField(), help_text="Letras de unidades o raíces montadas en el servidor."
    )


class RestaurarRespaldoRequestSerializer(serializers.Serializer):
    """Solicitud para restaurar la base de datos desde un archivo SQL."""

    ruta_archivo = serializers.CharField(
        max_length=500,
        required=True,
        help_text="Ruta absoluta en el disco del servidor al archivo .sql que se desea restaurar.",
    )
    importar_usuarios = serializers.BooleanField(
        default=True,
        help_text="Si es false, no se importan las cuentas de usuario del sistema anterior.",
    )


class AnalisisDumpRequestSerializer(serializers.Serializer):
    """Solicitud para analizar un archivo .sql antes de restaurarlo."""

    ruta_archivo = serializers.CharField(
        max_length=500,
        help_text="Ruta absoluta en el disco del servidor al archivo .sql que se desea analizar.",
    )


class TablaImportableSerializer(serializers.Serializer):
    """Tabla del volcado que se puede importar."""

    nombre = serializers.CharField(help_text="Nombre de la tabla en el volcado.")
    filas_aprox = serializers.IntegerField(help_text="Filas aproximadas contadas en los INSERT.")


class AnalisisDumpResponseSerializer(serializers.Serializer):
    """Informe del análisis previo de un volcado SQL."""

    tipo = serializers.CharField(help_text="mysql_legado, postgres_check o desconocido.")
    valido = serializers.BooleanField(help_text="True si el volcado puede restaurarse.")
    completo = serializers.BooleanField(help_text="True si el volcado termina con su marca final.")
    errores = serializers.ListField(child=serializers.CharField(), help_text="Motivos que impiden restaurar.")
    advertencias = serializers.ListField(child=serializers.CharField(), help_text="Avisos que no impiden restaurar.")
    usuarios = serializers.IntegerField(help_text="Cuentas de usuario encontradas en el volcado legado.")
    usuarios_admin = serializers.IntegerField(help_text="Cuentas con rol administrador en el volcado legado.")
    tablas_importables = TablaImportableSerializer(many=True, help_text="Tablas presentes, en orden de importación.")


class RestaurarRespaldoResponseSerializer(serializers.Serializer):
    """Confirmación del inicio del proceso de restauración de la base de datos."""

    mensaje = serializers.CharField(help_text="Mensaje descriptivo del inicio de la restauración.")
    archivo = serializers.CharField(help_text="Nombre del archivo SQL que se está restaurando.")
    iniciado_en = serializers.CharField(help_text="Marca de tiempo ISO del inicio.")


class SubirRespaldoResponseSerializer(serializers.Serializer):
    """Respuesta al subir un archivo de respaldo al servidor."""

    mensaje = serializers.CharField(help_text="Confirmación de la carga del archivo.")
    archivo = serializers.CharField(help_text="Nombre del archivo subido.")
    ruta_completa = serializers.CharField(help_text="Ruta completa donde quedó almacenado en el servidor.")
    tamano_formateado = serializers.CharField(help_text="Tamaño del archivo subido.")

