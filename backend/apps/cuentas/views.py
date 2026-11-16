"""Vistas de autenticación (login, refresh, logout, cambio de clave, yo), JWKS y usuarios."""

import contextlib
import hmac
from typing import Any

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from apps.comun.errores import problema
from apps.comun.excepciones import CambioClaveRequerido, DatosInvalidos
from apps.comun.limites import LimiteAutenticacion
from apps.comun.vistas import BaseViewSet, auditar
from apps.cuentas.autenticacion import RefreshConKid as RefreshToken
from apps.cuentas.autenticacion import jwk_publica
from apps.cuentas.filtros import FiltroUsuarios
from apps.cuentas.models import Usuario
from apps.cuentas.permisos import CambioClaveCompletado, SoloAdministrador
from apps.cuentas.serializers import (
    AccesoSerializer,
    CambioClaveSerializer,
    LoginSerializer,
    MiNombreSerializer,
    UsuarioEscrituraSerializer,
    UsuarioSerializer,
    YoSerializer,
)
from apps.cuentas.servicios import cambiar_clave, registrar_ingreso, reiniciar_clave

MENSAJE_CREDENCIALES = "Credenciales inválidas."


def _vida_acceso() -> int:
    return int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds())


def _respuesta_con_tokens(refresh: Any, estado: int = 200) -> Response:
    respuesta = Response({"access": str(refresh.access_token), "expira_en": _vida_acceso()}, status=estado)
    respuesta.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        str(refresh),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="Lax",
        path=settings.REFRESH_COOKIE_PATH,
    )
    return respuesta


def _borrar_cookie(respuesta: Response) -> Response:
    respuesta.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH, samesite="Lax")
    return respuesta


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Entrega la cookie XSRF-TOKEN para proteger refresh y logout."""

    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]

    @extend_schema(summary="Obtener cookie CSRF", tags=["Autenticación"], responses={204: None})
    def get(self, request: Request) -> Response:
        return Response(status=status.HTTP_204_NO_CONTENT)


class VistaPublica(APIView):
    """Vista sin autenticación previa que responde 401 (no 403) con WWW-Authenticate: Bearer."""

    authentication_classes: list[Any] = []
    permission_classes = [AllowAny]

    def get_authenticate_header(self, request: Request) -> str:
        return 'Bearer realm="api"'


@method_decorator(transaction.non_atomic_requests, name="dispatch")
class LoginView(VistaPublica):
    """Ingreso con nip y contraseña. Devuelve el token de acceso; el refresh va en cookie HttpOnly.

    No atómica: el registro del intento fallido debe persistir aunque la respuesta sea 401.
    """

    permission_classes = [AllowAny]
    throttle_classes = [LimiteAutenticacion]

    @extend_schema(
        summary="Iniciar sesión",
        description="Valida las credenciales (Argon2id). Tras 5 fallos la combinación nip + IP se bloquea 1 hora (429).",
        tags=["Autenticación"],
        request=LoginSerializer,
        responses={200: AccesoSerializer},
    )
    def post(self, request: Request) -> Response:
        datos = LoginSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        nip = datos.validated_data["nip"].strip()
        usuario = authenticate(request._request, nip=nip, password=datos.validated_data["password"])
        if getattr(request._request, "axes_locked_out", False):
            from apps.cuentas.servicios import respuesta_bloqueo

            return respuesta_bloqueo(request._request)  # type: ignore[no-any-return]
        if usuario is None or not usuario.is_active:
            registrar_ingreso(request._request, nip, exitoso=False)
            # Se responde sin lanzar la excepción para que DRF no revierta el registro del intento.
            respuesta = problema(401, MENSAJE_CREDENCIALES, "credenciales-invalidas", request.path)
            respuesta["WWW-Authenticate"] = 'Bearer realm="api"'
            return respuesta
        registrar_ingreso(request._request, nip, exitoso=True)
        return _respuesta_con_tokens(RefreshToken.for_user(usuario))


class RefreshView(VistaPublica):
    """Renueva el token de acceso con la cookie de refresco (rotación + lista negra). Requiere X-XSRF-TOKEN."""

    throttle_classes = [LimiteAutenticacion]

    @extend_schema(summary="Renovar sesión", tags=["Autenticación"], request=None, responses={200: AccesoSerializer})
    @method_decorator(ensure_csrf_cookie)
    def post(self, request: Request) -> Response:
        _verificar_csrf(request)
        token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not token:
            raise AuthenticationFailed("No hay sesión activa.")
        try:
            anterior = RefreshToken(token)  # type: ignore[arg-type]
            usuario = Usuario.objects.get(nip=anterior["sub"])
        except (TokenError, Usuario.DoesNotExist, KeyError) as exc:
            raise AuthenticationFailed("La sesión expiró o fue revocada.") from exc
        if not usuario.is_active:
            raise AuthenticationFailed("La sesión expiró o fue revocada.")
        anterior.blacklist()
        return _respuesta_con_tokens(RefreshToken.for_user(usuario))


class LogoutView(VistaPublica):
    """Cierra la sesión: pone el refresh en lista negra y borra la cookie."""

    @extend_schema(summary="Cerrar sesión", tags=["Autenticación"], request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        _verificar_csrf(request)
        token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if token:
            with contextlib.suppress(TokenError):
                RefreshToken(token).blacklist()  # type: ignore[arg-type]
        return _borrar_cookie(Response(status=status.HTTP_204_NO_CONTENT))


class CambioClaveView(APIView):
    """Cambio de la propia clave. Es la única acción permitida mientras la clave sea temporal."""

    permission_classes = [CambioClaveCompletado]
    permite_clave_temporal = True

    @extend_schema(
        summary="Cambiar mi clave",
        tags=["Autenticación"],
        request=CambioClaveSerializer,
        responses={200: AccesoSerializer},
    )
    def post(self, request: Request) -> Response:
        datos = CambioClaveSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        usuario: Usuario = request.user  # type: ignore[assignment]
        if not usuario.check_password(datos.validated_data["clave_actual"]):
            raise DatosInvalidos("La clave actual no es correcta.")
        from django.core.exceptions import ValidationError as ErrorDjango
        from rest_framework.exceptions import ValidationError

        try:
            cambiar_clave(usuario, datos.validated_data["clave_nueva"])
        except ErrorDjango as exc:
            raise ValidationError({"clave_nueva": list(exc.messages)}) from exc
        return _respuesta_con_tokens(RefreshToken.for_user(usuario))


class YoView(APIView):
    """Datos de la sesión actual."""

    permission_classes = [CambioClaveCompletado]
    permite_clave_temporal = True

    @extend_schema(summary="Usuario actual", tags=["Autenticación"], responses={200: YoSerializer})
    def get(self, request: Request) -> Response:
        return Response(YoSerializer(request.user).data)

    @extend_schema(
        summary="Cambiar mi nombre", tags=["Autenticación"], request=MiNombreSerializer, responses={200: YoSerializer}
    )
    def patch(self, request: Request) -> Response:
        usuario: Usuario = request.user  # type: ignore[assignment]
        if usuario.debe_cambiar_clave:
            raise CambioClaveRequerido()
        datos = MiNombreSerializer(usuario, data=request.data)
        datos.is_valid(raise_exception=True)
        anterior = usuario.nombre
        datos.save()
        auditar(request, "actualizar", usuario, {"nombre": [anterior, usuario.nombre]})
        return Response(YoSerializer(usuario).data)


def _verificar_csrf(request: Request) -> None:
    """Doble envío: la cabecera X-XSRF-TOKEN debe ser igual a la cookie XSRF-TOKEN (comparación en tiempo constante)."""
    from rest_framework.exceptions import PermissionDenied

    cookie = request.COOKIES.get(settings.CSRF_COOKIE_NAME, "")
    cabecera = request.headers.get("X-XSRF-TOKEN", "")
    if len(cookie) < 32 or not cabecera or not hmac.compare_digest(cookie.encode(), cabecera.encode()):
        raise PermissionDenied("Falta o es inválido el token CSRF.")


@require_GET
def jwks(request: HttpRequest) -> JsonResponse:
    """Claves públicas para validar los JWT (RS256)."""
    return JsonResponse({"keys": [jwk_publica()]})


@extend_schema(tags=["Usuarios"])
class UsuarioViewSet(BaseViewSet):
    """Administración de cuentas (solo administrador)."""

    queryset = Usuario.objects.all().order_by("nombre")
    serializer_class = UsuarioSerializer
    serializer_escritura = UsuarioEscrituraSerializer
    permission_classes = [CambioClaveCompletado, SoloAdministrador]
    lookup_field = "nip"
    campos_orden = ("nombre", "nip", "rol")
    filterset_class = FiltroUsuarios

    def perform_create(self, serializer: Any) -> None:
        datos = serializer.validated_data
        usuario = Usuario.objects.create_user(datos["nip"], datos["nombre"], None, rol=datos["rol"])
        usuario.is_active = datos.get("is_active", True)
        usuario.save(update_fields=["is_active"])
        self._clave_temporal = reiniciar_clave(usuario, inicial=True)
        serializer.instance = usuario
        auditar(self.request, "crear", usuario, {"nip": usuario.nip, "rol": usuario.rol})

    def perform_update(self, serializer: Any) -> None:
        usuario = serializer.save()
        usuario.sincronizar_grupo()
        if not usuario.is_active:
            from apps.cuentas.servicios import revocar_sesiones

            revocar_sesiones(usuario)
        auditar(self.request, "actualizar", usuario, serializer.validated_data)

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        guardada = self._respuesta_guardada()
        if guardada is not None:
            return guardada
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if Usuario.objects.filter(nip=serializer.validated_data["nip"]).exists():
            from apps.comun.excepciones import Conflicto

            raise Conflicto("Ya existe un usuario con ese nip.")
        self.perform_create(serializer)
        cuerpo = dict(UsuarioSerializer(serializer.instance).data)
        cuerpo["clave_temporal"] = self._clave_temporal
        return Response(cuerpo, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Reiniciar clave temporal", request=None, responses={200: UsuarioSerializer})
    @action(detail=True, methods=["post"], url_path="reiniciar-clave")
    def reiniciar_clave(self, request: Request, nip: str | None = None) -> Response:
        guardada = self._respuesta_guardada()
        if guardada is not None:
            return guardada
        usuario = self.get_object()
        temporal = reiniciar_clave(usuario)
        auditar(request, "actualizar", usuario, {"accion": "reinicio de clave"})
        cuerpo = dict(UsuarioSerializer(usuario).data)
        cuerpo["clave_temporal"] = temporal
        return Response(cuerpo)
