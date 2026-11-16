"""Vistas API para consulta, configuración y ejecución del respaldo de la base de datos."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.excepciones import DatosInvalidos, PermisoDenegado
from apps.comun.serializers_respaldo import (
    EsServidorResponseSerializer,
    RespaldoEjecucionResponseSerializer,
    RespaldoEstadoResponseSerializer,
    RutaConfigRequestSerializer,
    RutaConfigResponseSerializer,
    RutaValidacionRequestSerializer,
    RutaValidacionResponseSerializer,
)
from apps.comun.servicios_respaldo import (
    ejecutar_respaldo_consola,
    es_cliente_servidor_local,
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

