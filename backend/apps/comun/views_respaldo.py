"""Vistas API para consulta, configuración y ejecución del respaldo de la base de datos."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.excepciones import DatosInvalidos, PermisoDenegado
from apps.comun.serializers_respaldo import (
    AnalisisDumpRequestSerializer,
    AnalisisDumpResponseSerializer,
    EsServidorResponseSerializer,
    ExploracionRutaResponseSerializer,
    RespaldoEjecucionResponseSerializer,
    RespaldoEstadoResponseSerializer,
    RestaurarRespaldoRequestSerializer,
    RestaurarRespaldoResponseSerializer,
    RutaConfigRequestSerializer,
    RutaConfigResponseSerializer,
    RutaValidacionRequestSerializer,
    RutaValidacionResponseSerializer,
    SubirRespaldoResponseSerializer,
)
from apps.comun.servicios_respaldo import (
    analizar_respaldo_servidor,
    ejecutar_respaldo_consola,
    ejecutar_restauracion_consola,
    es_cliente_servidor_local,
    explorar_directorio_servidor,
    guardar_archivo_respaldo_subido,
    guardar_ruta_respaldo,
    obtener_estado_respaldo,
    validar_ruta_servidor,
)
from apps.comun.vistas import IdempotenciaMixin
from apps.cuentas.permisos import CambioClaveCompletado, SoloAdministrador


class VistaEsServidor(APIView):
    """Indica si la petición proviene directamente del equipo servidor."""

    permission_classes = [CambioClaveCompletado, SoloAdministrador]

    @extend_schema(
        summary="Comprobar si el cliente es el equipo servidor",
        description="Retorna booleano es_servidor evaluando la IP de origen.",
        tags=["Respaldos"],
        responses={200: EsServidorResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        logger.info(
            "VistaEsServidor META: REMOTE_ADDR=%s, X-Forwarded-For=%s, X-Real-IP=%s, Host=%s",
            request._request.META.get("REMOTE_ADDR"),
            request._request.META.get("HTTP_X_FORWARDED_FOR"),
            request._request.META.get("HTTP_X_REAL_IP"),
            request._request.META.get("HTTP_HOST"),
        )
        es_local = es_cliente_servidor_local(request._request)
        return Response({"es_servidor": es_local}, status=status.HTTP_200_OK)


class VistaEstadoRespaldo(APIView):
    """Consulta el estado del subsistema de respaldo, último archivo y si la petición es local al servidor."""

    permission_classes = [CambioClaveCompletado, SoloAdministrador]

    @extend_schema(
        summary="Estado del respaldo de base de datos",
        tags=["Respaldos"],
        responses={200: RespaldoEstadoResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        estado = obtener_estado_respaldo(request._request)
        serializer = RespaldoEstadoResponseSerializer(estado)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VistaValidarRutaRespaldo(IdempotenciaMixin, APIView):
    """Valida la existencia y permisos de una ruta en el servidor. Solo permitido desde el equipo servidor."""

    permission_classes = [CambioClaveCompletado, SoloAdministrador]

    @extend_schema(
        summary="Validar ruta de respaldo en servidor",
        description="Comprueba que la ruta exista y tenga permisos de escritura. Solo ejecutable desde el propio servidor.",
        tags=["Respaldos"],
        request=RutaValidacionRequestSerializer,
        responses={200: RutaValidacionResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        if not es_cliente_servidor_local(request._request):
            raise PermisoDenegado(
                "La validación de carpetas del servidor solo puede realizarse directamente desde el equipo servidor."
            )

        datos = RutaValidacionRequestSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        ruta_candidata = datos.validated_data["ruta"]

        valida, mensaje, ruta_res = validar_ruta_servidor(ruta_candidata)
        if not valida:
            raise DatosInvalidos(mensaje)

        salida = {
            "valida": valida,
            "ruta": ruta_candidata,
            "mensaje": mensaje,
        }
        return Response(RutaValidacionResponseSerializer(salida).data, status=status.HTTP_200_OK)


class VistaConfigurarRutaRespaldo(IdempotenciaMixin, APIView):
    """Actualiza la ruta donde se guardarán los respaldos en el servidor. Solo ejecutable desde el equipo servidor."""

    permission_classes = [CambioClaveCompletado, SoloAdministrador]

    @extend_schema(
        summary="Configurar ruta de respaldo en servidor",
        description="Establece la carpeta del servidor para los respaldos. Restringido al equipo servidor.",
        tags=["Respaldos"],
        request=RutaConfigRequestSerializer,
        responses={200: RutaConfigResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        if not es_cliente_servidor_local(request._request):
            raise PermisoDenegado(
                "La ruta de almacenamiento solo puede configurarse directamente desde el equipo servidor."
            )

        datos = RutaConfigRequestSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        ruta_candidata = datos.validated_data["ruta"]

        valida, mensaje, ruta_res = validar_ruta_servidor(ruta_candidata)
        if not valida or not ruta_res:
            raise DatosInvalidos(f"Ruta inválida: {mensaje}")

        guardada = guardar_ruta_respaldo(ruta_candidata)
        salida = {
            "ruta_configurada": guardada,
            "mensaje": "Ruta de respaldo en el servidor configurada correctamente.",
        }
        return Response(RutaConfigResponseSerializer(salida).data, status=status.HTTP_200_OK)


class VistaEjecutarRespaldo(IdempotenciaMixin, APIView):
    """Ejecuta el respaldo de la base de datos por consola en el servidor. Restringido al equipo servidor."""

    permission_classes = [CambioClaveCompletado, SoloAdministrador]

    @extend_schema(
        summary="Ejecutar respaldo en el servidor por consola",
        description="Inicia el subproceso desacoplado de consola en el servidor para generar el archivo .sql con pg_dump.",
        tags=["Respaldos"],
        request=None,
        responses={202: RespaldoEjecucionResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        if not es_cliente_servidor_local(request._request):
            raise PermisoDenegado(
                "La copia de seguridad solo puede ser solicitada directamente desde el equipo servidor."
            )

        resultado = ejecutar_respaldo_consola()
        serializer = RespaldoEjecucionResponseSerializer(resultado)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class VistaExplorarArchivosRespaldo(APIView):
    """Explora carpetas y archivos .sql en el disco del servidor. Solo ejecutable desde el equipo servidor."""

    permission_classes = [CambioClaveCompletado, SoloAdministrador]

    @extend_schema(
        summary="Explorar carpetas y respaldos en el servidor",
        description="Lista subdirectorios y archivos .sql en la ruta indicada del servidor. Restringido al equipo servidor.",
        tags=["Respaldos"],
        parameters=[
            {
                "name": "ruta",
                "in": "query",
                "required": False,
                "description": "Ruta absoluta de la carpeta a explorar. Si se omite, se usa la configurada de respaldos.",
                "schema": {"type": "string"},
            }
        ],
        responses={200: ExploracionRutaResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        if not es_cliente_servidor_local(request._request):
            raise PermisoDenegado(
                "La exploración de archivos del servidor solo puede realizarse directamente desde el equipo servidor."
            )

        ruta_param = request.query_params.get("ruta")
        resultado = explorar_directorio_servidor(ruta_param)
        serializer = ExploracionRutaResponseSerializer(resultado)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VistaAnalizarRespaldo(IdempotenciaMixin, APIView):
    """Analiza un archivo .sql del servidor antes de restaurarlo. Solo desde el equipo servidor."""

    permission_classes = [CambioClaveCompletado, SoloAdministrador]

    @extend_schema(
        summary="Analizar un respaldo antes de restaurar",
        description="Clasifica el volcado y valida su estructura sin modificar la base de datos.",
        tags=["Respaldos"],
        request=AnalisisDumpRequestSerializer,
        responses={200: AnalisisDumpResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        if not es_cliente_servidor_local(request._request):
            raise PermisoDenegado(
                "El análisis de respaldos solo puede solicitarse directamente desde el equipo servidor."
            )

        datos = AnalisisDumpRequestSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        informe = analizar_respaldo_servidor(datos.validated_data["ruta_archivo"])
        return Response(AnalisisDumpResponseSerializer(informe).data, status=status.HTTP_200_OK)


class VistaRestaurarRespaldo(IdempotenciaMixin, APIView):
    """Ejecuta la restauración de la base de datos desde un archivo SQL. Restringido al equipo servidor."""

    permission_classes = [CambioClaveCompletado, SoloAdministrador]

    @extend_schema(
        summary="Restaurar base de datos en el servidor por consola",
        description="Inicia la restauración de la base de datos con psql a partir de un archivo .sql seleccionado.",
        tags=["Respaldos"],
        request=RestaurarRespaldoRequestSerializer,
        responses={202: RestaurarRespaldoResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        if not es_cliente_servidor_local(request._request):
            raise PermisoDenegado(
                "La restauración de la base de datos solo puede ser solicitada directamente desde el equipo servidor."
            )

        datos = RestaurarRespaldoRequestSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        ruta_archivo = datos.validated_data["ruta_archivo"]

        resultado = ejecutar_restauracion_consola(ruta_archivo, datos.validated_data["importar_usuarios"])
        serializer = RestaurarRespaldoResponseSerializer(resultado)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)


class VistaSubirRespaldo(APIView):
    """Recibe un archivo .sql y lo almacena en la carpeta de respaldos del servidor."""

    permission_classes = [CambioClaveCompletado, SoloAdministrador]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Subir archivo .sql de respaldo al servidor",
        description="Carga un archivo de respaldo al disco del servidor para su posterior restauración.",
        tags=["Respaldos"],
        request={"multipart/form-data": {"type": "object", "properties": {"archivo": {"type": "string", "format": "binary"}}}},
        responses={201: SubirRespaldoResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        if not es_cliente_servidor_local(request._request):
            raise PermisoDenegado(
                "La carga de archivos de respaldo solo puede realizarse directamente desde el equipo servidor."
            )

        archivo = request.FILES.get("archivo")
        if not archivo:
            raise DatosInvalidos("Debe adjuntar un archivo de respaldo con el campo 'archivo'.")

        resultado = guardar_archivo_respaldo_subido(archivo)
        serializer = SubirRespaldoResponseSerializer(resultado)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


