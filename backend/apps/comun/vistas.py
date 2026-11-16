"""Base de ViewSets: idempotencia, auditoría y respuestas sin exportación."""

import hashlib
import json
from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Model
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from apps.comun.excepciones import Conflicto, DatosInvalidos
from apps.comun.middleware import request_id_actual
from apps.comun.models import ClaveIdempotencia, RegistroAuditoria

METODOS_IDEMPOTENTES = {"POST", "PUT", "PATCH"}
VIGENCIA_IDEMPOTENCIA = timedelta(hours=24)


def huella(datos: Any) -> str:
    return hashlib.sha256(json.dumps(datos, sort_keys=True, default=str).encode()).hexdigest()


class IdempotenciaMixin:
    """Exige Idempotency-Key en POST/PUT/PATCH y repite la respuesta guardada ante reintentos."""

    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)  # type: ignore[misc]
        self._registro_idempotencia: ClaveIdempotencia | None = None
        self._clave_idem: str | None = None
        if request.method not in METODOS_IDEMPOTENTES:
            return
        clave = request.headers.get("Idempotency-Key", "").strip()
        if not clave or len(clave) > 100:
            raise DatosInvalidos("La cabecera Idempotency-Key es obligatoria en POST, PUT y PATCH.")
        self._clave_idem = clave
        self._huella = huella(request.data)
        limite = timezone.now() - VIGENCIA_IDEMPOTENCIA
        usuario: Any = request.user
        ClaveIdempotencia.objects.filter(usuario=usuario, creado_en__lt=limite).delete()
        existente = ClaveIdempotencia.objects.filter(clave=clave, usuario=usuario).first()
        if existente is not None:
            if existente.huella_cuerpo != self._huella or existente.ruta != request.path:
                raise Conflicto("La Idempotency-Key ya se usó con otra petición.")
            self._registro_idempotencia = existente

    def handle_exception(self, exc: Exception) -> Response:
        respuesta: Response = super().handle_exception(exc)  # type: ignore[misc]
        return respuesta

    def finalize_response(self, request: Request, response: Any, *args: Any, **kwargs: Any) -> Any:
        clave = getattr(self, "_clave_idem", None)
        if clave and getattr(self, "_registro_idempotencia", None) is None and 200 <= response.status_code < 300:
            try:
                with transaction.atomic():
                    ClaveIdempotencia.objects.create(
                        clave=clave,
                        usuario=request.user,  # type: ignore[misc]
                        metodo=request.method or "",
                        ruta=request.path,
                        huella_cuerpo=self._huella,
                        estado_respuesta=response.status_code,
                        cuerpo_respuesta=response.data,
                    )
            except IntegrityError:
                pass
        return super().finalize_response(request, response, *args, **kwargs)  # type: ignore[misc]

    def _respuesta_guardada(self) -> Response | None:
        registro = getattr(self, "_registro_idempotencia", None)
        if registro is None:
            return None
        respuesta = Response(registro.cuerpo_respuesta, status=registro.estado_respuesta)
        respuesta["Idempotent-Replayed"] = "true"
        return respuesta


def _nombre_usuario(request: Request) -> str:
    usuario = request.user
    return getattr(usuario, "nombre", "") or getattr(usuario, "nip", "")


def auditar(request: Request, accion: str, instancia: Model, cambios: dict[str, Any] | None = None) -> None:
    RegistroAuditoria.objects.create(
        usuario=getattr(request.user, "nip", ""),
        accion=accion,
        modelo=instancia._meta.label,
        objeto_id=str(instancia.pk),
        cambios=json.loads(json.dumps(cambios or {}, default=str)),
        request_id=request_id_actual.get(),
    )


class BaseViewSet(
    IdempotenciaMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,  # type: ignore[type-arg]
):
    """CRUD sin DELETE (se anula o inhabilita). Audita cada escritura."""

    campos_orden: tuple[str, ...] = ()
    serializer_escritura: type[BaseSerializer[Any]] | None = None

    def get_serializer_class(self) -> type[BaseSerializer[Any]]:
        if self.action in {"create", "update", "partial_update"} and self.serializer_escritura is not None:
            return self.serializer_escritura
        return super().get_serializer_class()

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        guardada = self._respuesta_guardada()
        if guardada is not None:
            return guardada
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return self.respuesta_lectura(serializer.instance, 201)

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        guardada = self._respuesta_guardada()
        if guardada is not None:
            return guardada
        parcial = kwargs.pop("partial", False)
        instancia = self.get_object()
        serializer = self.get_serializer(instancia, data=request.data, partial=parcial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return self.respuesta_lectura(serializer.instance, 200)

    def respuesta_lectura(self, instancia: Any, estado: int) -> Response:
        """Las escrituras responden con el serializer de lectura (incluye campos calculados y de auditoría)."""
        instancia.refresh_from_db()
        clase = super().get_serializer_class()
        return Response(clase(instancia, context=self.get_serializer_context()).data, status=estado)

    def perform_create(self, serializer: BaseSerializer[Any]) -> None:
        ahora = timezone.now()
        quien = _nombre_usuario(self.request)
        extra: dict[str, Any] = {}
        modelo = serializer.Meta.model  # type: ignore[attr-defined]
        nombres = {f.name for f in modelo._meta.get_fields()}
        if "creado_en" in nombres:
            extra.update(creado_en=ahora, actualizado_en=ahora, creado_por=quien, actualizado_por=quien)
        if "usuario" in nombres and "usuario" not in serializer.validated_data:
            extra["usuario"] = quien
        if "fecha_registro" in nombres:
            extra["fecha_registro"] = ahora
        instancia = serializer.save(**extra)
        auditar(self.request, "crear", instancia, serializer.validated_data)

    def perform_update(self, serializer: BaseSerializer[Any]) -> None:
        extra: dict[str, Any] = {}
        modelo = serializer.Meta.model  # type: ignore[attr-defined]
        if "actualizado_en" in {f.name for f in modelo._meta.get_fields()}:
            extra.update(actualizado_en=timezone.now(), actualizado_por=_nombre_usuario(self.request))
        instancia = serializer.save(**extra)
        auditar(self.request, "actualizar", instancia, serializer.validated_data)
