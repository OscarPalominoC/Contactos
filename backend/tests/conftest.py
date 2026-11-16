"""Fixtures compartidas de las pruebas."""

from datetime import date, timedelta
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.contactos.models import Contacto
from apps.cuentas.models import Usuario
from apps.llamadas.models import LlamadaCumpleanos, LlamadaRtm, LlamadaSoat
from apps.revisiones.models import Revision, Soat
from apps.vehiculos.models import Linea, Marca, Moto

CLAVE = "Clave-Segura-2026!"


@pytest.fixture(autouse=True)
def _sin_axes(settings: Any) -> None:
    """Desactiva el bloqueo de axes salvo en las pruebas que lo verifican y limpia los contadores de límite."""
    from django.core.cache import cache

    settings.AXES_ENABLED = False
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def grupos(django_db_setup: Any, db: Any) -> None:
    """Los grupos y permisos los crea la migración cuentas.0002_roles."""
    return


def crear_usuario(nip: str = "900001", rol: str = "administrador", clave: str = CLAVE, **extra: Any) -> Usuario:
    usuario = Usuario.objects.create_user(nip, f"USUARIO DE PRUEBA {nip}", clave, rol=rol, **extra)
    usuario.debe_cambiar_clave = False
    usuario.save(update_fields=["debe_cambiar_clave"])
    return usuario


@pytest.fixture
def admin_usuario(grupos: None) -> Usuario:
    return crear_usuario("900001", "administrador")


@pytest.fixture
def usuario_operativo(grupos: None) -> Usuario:
    return crear_usuario("900002", "usuario")


@pytest.fixture
def tecnico(grupos: None) -> Usuario:
    return crear_usuario("900003", "tecnico")


class ClienteApi(APIClient):
    """Cliente que agrega Idempotency-Key y X-Request-ID automáticamente."""

    contador = 0

    def _cabeceras(self, extra: dict[str, Any]) -> dict[str, Any]:
        ClienteApi.contador += 1
        extra.setdefault("HTTP_IDEMPOTENCY_KEY", f"clave-prueba-{ClienteApi.contador}")
        return extra

    def post(self, path: str, data: Any = None, format: str = "json", **extra: Any) -> Any:  # noqa: A002
        return super().post(path, data, format=format, **self._cabeceras(extra))

    def patch(self, path: str, data: Any = None, format: str = "json", **extra: Any) -> Any:  # noqa: A002
        return super().patch(path, data, format=format, **self._cabeceras(extra))

    def put(self, path: str, data: Any = None, format: str = "json", **extra: Any) -> Any:  # noqa: A002
        return super().put(path, data, format=format, **self._cabeceras(extra))


@pytest.fixture
def api() -> ClienteApi:
    return ClienteApi()


@pytest.fixture
def api_admin(api: ClienteApi, admin_usuario: Usuario) -> ClienteApi:
    api.force_authenticate(admin_usuario)
    return api


@pytest.fixture
def api_usuario(api: ClienteApi, usuario_operativo: Usuario) -> ClienteApi:
    api.force_authenticate(usuario_operativo)
    return api


@pytest.fixture
def contacto(db: Any) -> Contacto:
    return Contacto.objects.create(
        nip="1000000001",
        nombre="CLIENTE DE PRUEBA",
        celular="3000000000",
        dia_nac=15,
        mes_nac=5,
        estado="habilitado",
        fecha_registro=timezone.now(),
    )


@pytest.fixture
def marca(db: Any) -> Marca:
    return Marca.objects.create(codigo="HO", nombre="HONDA")


@pytest.fixture
def linea(marca: Marca) -> Linea:
    return Linea.objects.create(linea="XR 190L", marca=marca)


@pytest.fixture
def moto(contacto: Contacto, linea: Linea) -> Moto:
    return Moto.objects.create(placa="ABC12D", marca="HONDA", modelo="2024", linea=linea.linea, contacto=contacto)


@pytest.fixture
def revision(moto: Moto) -> Revision:
    hoy = timezone.localdate()
    return Revision.objects.create(
        certificado="CERT-001",
        moto=moto,
        fecha_certificado=hoy,
        fecha_venc_certificado=hoy + timedelta(days=365),
        estado="VIGENTE",
    )


@pytest.fixture
def soat(moto: Moto) -> Soat:
    hoy = timezone.localdate()
    return Soat.objects.create(
        soat="12345-MUNDIAL", moto=moto, fecha_soat=hoy, fecha_venc_soat=hoy + timedelta(days=365), estado="VIGENTE"
    )


@pytest.fixture
def llamada_rtm(moto: Moto) -> LlamadaRtm:
    objetivo = timezone.localdate() + timedelta(days=10)
    return LlamadaRtm.objects.create(
        id=f"{moto.placa}.{objetivo:%Y-%m-%d}", fecha=objetivo, moto=moto, estado="realizada", num_llamadas=1
    )


@pytest.fixture
def llamada_soat(moto: Moto) -> LlamadaSoat:
    objetivo = timezone.localdate() + timedelta(days=10)
    return LlamadaSoat.objects.create(
        id=f"{moto.placa}.{objetivo:%Y-%m-%d}",
        fecha=objetivo,
        moto=moto,
        estado="realizada",
        motivo_llamada="soat",
        num_llamadas=1,
    )


@pytest.fixture
def llamada_cumpleanos(contacto: Contacto) -> LlamadaCumpleanos:
    return LlamadaCumpleanos.objects.create(fecha=timezone.now(), contacto=contacto, estado="realizada")


@pytest.fixture
def hoy() -> date:
    return timezone.localdate()
