"""Matriz rol × acción × recurso y administración de usuarios."""

from typing import Any

import pytest

from apps.cuentas.models import Usuario
from tests.conftest import ClienteApi, crear_usuario

pytestmark = pytest.mark.django_db

# (recurso, rol) → (puede ver, puede crear)
MATRIZ = {
    "contactos": {
        "administrador": (True, True),
        "ingeniero": (True, False),
        "tecnico": (True, False),
        "usuario": (True, True),
    },
    "marcas": {
        "administrador": (True, True),
        "ingeniero": (True, True),
        "tecnico": (True, False),
        "usuario": (True, False),
    },
    "revisiones": {
        "administrador": (True, True),
        "ingeniero": (True, True),
        "tecnico": (True, True),
        "usuario": (True, True),
    },
    "soats": {
        "administrador": (True, True),
        "ingeniero": (True, False),
        "tecnico": (True, False),
        "usuario": (True, True),
    },
    "llamadas-rtm": {
        "administrador": (True, True),
        "ingeniero": (True, False),
        "tecnico": (True, False),
        "usuario": (True, True),
    },
    "usuarios": {
        "administrador": (True, True),
        "ingeniero": (False, False),
        "tecnico": (False, False),
        "usuario": (False, False),
    },
}


@pytest.mark.parametrize("recurso", MATRIZ)
@pytest.mark.parametrize("rol", ["administrador", "ingeniero", "tecnico", "usuario"])
def test_matriz_roles(api: ClienteApi, grupos: None, recurso: str, rol: str) -> None:
    usuario = crear_usuario(f"8{len(rol)}{len(recurso)}", rol)
    api.force_authenticate(usuario)
    ver, crear = MATRIZ[recurso][rol]
    assert (api.get(f"/api/v1/{recurso}").status_code == 200) is ver
    estado_crear = api.post(f"/api/v1/{recurso}", {}).status_code
    if crear:
        assert estado_crear in (201, 422), estado_crear
    else:
        assert estado_crear == 403


def test_solo_admin_tiene_staff(grupos: None) -> None:
    admin = crear_usuario("700001", "administrador")
    otro = crear_usuario("700002", "usuario")
    assert admin.is_staff and not otro.is_staff


class TestAdministracionUsuarios:
    def test_crear_usuario_devuelve_clave_temporal_una_vez(self, api_admin: ClienteApi, settings: Any) -> None:
        respuesta = api_admin.post("/api/v1/usuarios", {"nip": "600001", "nombre": "nuevo empleado", "rol": "usuario"})
        assert respuesta.status_code == 201, respuesta.json()
        cuerpo = respuesta.json()
        assert cuerpo["clave_temporal"] == settings.CLAVE_TEMPORAL_INICIAL
        assert cuerpo["debe_cambiar_clave"] is True
        usuario = Usuario.objects.get(nip="600001")
        assert usuario.nombre == "NUEVO EMPLEADO"
        assert usuario.check_password(cuerpo["clave_temporal"])
        assert "clave_temporal" not in api_admin.get("/api/v1/usuarios/600001").json()
        assert api_admin.post("/api/v1/usuarios", {"nip": "600001", "nombre": "X", "rol": "usuario"}).status_code == 409

    def test_crear_usuario_asigna_clave_temporal_inicial(self, api_admin: ClienteApi, settings: Any) -> None:
        respuesta = api_admin.post(
            "/api/v1/usuarios", {"nip": "600002", "nombre": "EMPLEADO CLAVE INICIAL", "rol": "usuario"}
        )
        assert respuesta.status_code == 201
        assert respuesta.json()["clave_temporal"] == settings.CLAVE_TEMPORAL_INICIAL
        usuario = Usuario.objects.get(nip="600002")
        assert usuario.check_password(settings.CLAVE_TEMPORAL_INICIAL)

    def test_reiniciar_clave(self, api_admin: ClienteApi, usuario_operativo: Usuario) -> None:
        respuesta = api_admin.post(f"/api/v1/usuarios/{usuario_operativo.nip}/reiniciar-clave")
        assert respuesta.status_code == 200
        usuario_operativo.refresh_from_db()
        assert usuario_operativo.debe_cambiar_clave is True
        assert usuario_operativo.check_password(respuesta.json()["clave_temporal"])

    def test_cambiar_rol_y_desactivar(self, api_admin: ClienteApi, usuario_operativo: Usuario) -> None:
        ruta = f"/api/v1/usuarios/{usuario_operativo.nip}"
        respuesta = api_admin.patch(ruta, {"rol": "administrador", "is_active": False})
        assert respuesta.status_code == 200
        usuario_operativo.refresh_from_db()
        assert usuario_operativo.is_staff is True
        assert [g.name for g in usuario_operativo.groups.all()] == ["administrador"]
        assert usuario_operativo.is_active is False
        assert api_admin.patch(ruta, {"nip": "otro"}).json()["nip"] == usuario_operativo.nip

    def test_filtros_usuarios(self, api_admin: ClienteApi, usuario_operativo: Usuario) -> None:
        total = lambda **f: api_admin.get(  # noqa: E731
            "/api/v1/usuarios", {f"filter[{k}]": v for k, v in f.items()}
        ).json()["meta"]["page"]["total"]
        assert total(rol="usuario") == 1
        assert total(q="900002") == 1
        assert total(activo="true") == 2


def test_admin_django_url_no_predeterminada(client: Any, admin_usuario: Usuario, settings: Any) -> None:
    assert client.get("/admin/").status_code == 404
    assert client.get(f"/{settings.ADMIN_URL}").status_code == 302
    client.force_login(admin_usuario)
    for ruta in [
        "",
        "contactos/contacto/",
        "vehiculos/moto/",
        "revisiones/revision/",
        "revisiones/soat/",
        "llamadas/llamadacumpleanos/",
        "llamadas/llamadartm/",
        "llamadas/llamadasoat/",
        "cuentas/usuario/",
        "cuentas/ingreso/",
        "comun/registroauditoria/",
        "comun/importacionrechazo/",
        "vehiculos/marca/",
        "vehiculos/linea/",
    ]:
        assert client.get(f"/{settings.ADMIN_URL}{ruta}").status_code == 200, ruta


def test_admin_accion_reiniciar_clave(
    client: Any, admin_usuario: Usuario, usuario_operativo: Usuario, settings: Any
) -> None:
    client.force_login(admin_usuario)
    respuesta = client.post(
        f"/{settings.ADMIN_URL}cuentas/usuario/",
        {"action": "accion_reiniciar_clave", "_selected_action": [usuario_operativo.nip]},
        follow=True,
    )
    assert "nueva clave temporal" in respuesta.content.decode()
    usuario_operativo.refresh_from_db()
    assert usuario_operativo.debe_cambiar_clave is True


def test_admin_login_registra_ingreso(client: Any, admin_usuario: Usuario, settings: Any) -> None:
    from apps.cuentas.models import Ingreso
    from tests.conftest import CLAVE

    client.post(f"/{settings.ADMIN_URL}login/", {"username": "900001", "password": "mala"})
    client.post(f"/{settings.ADMIN_URL}login/", {"username": "900001", "password": CLAVE})
    assert Ingreso.objects.filter(origen="admin", exitoso=False).count() == 1
    assert Ingreso.objects.filter(origen="admin", exitoso=True).count() == 1
