"""Login, refresh con rotación, logout, cambio obligatorio de clave, bloqueo y JWKS."""

from typing import Any

import jwt
import pytest
from django.conf import settings

from apps.cuentas.models import Ingreso, Usuario
from tests.conftest import CLAVE, ClienteApi, crear_usuario

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"


def iniciar(api: ClienteApi, nip: str = "900001", clave: str = CLAVE) -> Any:
    return api.post(LOGIN, {"nip": nip, "password": clave}, REMOTE_ADDR="10.0.0.1")


def csrf(api: ClienteApi) -> dict[str, str]:
    api.get("/api/v1/auth/csrf")
    return {"HTTP_X_XSRF_TOKEN": api.cookies[settings.CSRF_COOKIE_NAME].value}


def test_login_correcto_entrega_acceso_y_cookie_httponly(api: ClienteApi, admin_usuario: Usuario) -> None:
    respuesta = iniciar(api)
    assert respuesta.status_code == 200
    assert set(respuesta.data) == {"access", "expira_en"}
    assert respuesta.data["expira_en"] == 300
    cookie = respuesta.cookies[settings.REFRESH_COOKIE_NAME]
    assert cookie["httponly"] is True
    assert cookie["path"] == "/api/v1/auth"
    assert cookie["samesite"] == "Lax"
    assert "refresh" not in respuesta.data
    assert Ingreso.objects.filter(nip_usuario="900001", exitoso=True).count() == 1


def test_token_rs256_con_kid_iss_aud(api: ClienteApi, admin_usuario: Usuario) -> None:
    token = iniciar(api).data["access"]
    cabecera = jwt.get_unverified_header(token)
    assert cabecera["alg"] == "RS256"
    jwks = api.get("/.well-known/jwks.json").json()
    assert cabecera["kid"] == jwks["keys"][0]["kid"]
    clave = jwt.PyJWK(jwks["keys"][0]).key
    datos = jwt.decode(token, clave, algorithms=["RS256"], audience="check-contactos-web", issuer="check-contactos")
    assert datos["sub"] == "900001"


def test_token_hs256_forjado_es_rechazado(api: ClienteApi, admin_usuario: Usuario) -> None:
    falso = jwt.encode({"sub": "900001", "token_type": "access"}, "s" * 64, algorithm="HS256")
    respuesta = api.get("/api/v1/auth/yo", HTTP_AUTHORIZATION=f"Bearer {falso}")
    assert respuesta.status_code == 401
    assert respuesta["WWW-Authenticate"].startswith("Bearer")


@pytest.mark.parametrize("nip,clave", [("900001", "incorrecta-123"), ("no-existe", CLAVE)])
def test_login_fallido_mensaje_generico(api: ClienteApi, admin_usuario: Usuario, nip: str, clave: str) -> None:
    respuesta = iniciar(api, nip, clave)
    assert respuesta.status_code == 401
    assert respuesta.data["detail"] == "Credenciales inválidas."
    assert respuesta["Content-Type"] == "application/problem+json"
    assert respuesta.data["request_id"]
    assert Ingreso.objects.filter(nip_usuario=nip, exitoso=False).count() == 1


def test_usuario_inactivo_no_ingresa(api: ClienteApi, admin_usuario: Usuario) -> None:
    admin_usuario.is_active = False
    admin_usuario.save()
    assert iniciar(api).status_code == 401


def test_bloqueo_al_quinto_intento(api: ClienteApi, admin_usuario: Usuario, settings: Any) -> None:
    settings.AXES_ENABLED = True
    for _ in range(4):
        assert iniciar(api, clave="incorrecta-123").status_code == 401
    quinto = iniciar(api, clave="incorrecta-123")
    assert quinto.status_code == 429
    bloqueado = iniciar(api)
    assert bloqueado.status_code == 429
    assert bloqueado["Retry-After"] == "3600"
    assert bloqueado.json()["type"] == "/problemas/cuenta-bloqueada"


def test_sin_token_401_y_con_token_sin_permiso_403(api: ClienteApi, tecnico: Usuario) -> None:
    sin_token = api.get("/api/v1/contactos")
    assert sin_token.status_code == 401
    assert sin_token["WWW-Authenticate"].startswith("Bearer")
    token = iniciar(api, "900003").data["access"]
    sin_permiso = api.get("/api/v1/usuarios", HTTP_AUTHORIZATION=f"Bearer {token}")
    assert sin_permiso.status_code == 403


def test_refresh_rota_y_rechaza_reuso(api: ClienteApi, admin_usuario: Usuario) -> None:
    iniciar(api)
    anterior = api.cookies[settings.REFRESH_COOKIE_NAME].value
    cabecera = csrf(api)
    nuevo = api.post(REFRESH, **cabecera)
    assert nuevo.status_code == 200
    assert api.cookies[settings.REFRESH_COOKIE_NAME].value != anterior
    api.cookies[settings.REFRESH_COOKIE_NAME] = anterior
    reuso = api.post(REFRESH, **cabecera)
    assert reuso.status_code == 401


def test_refresh_sin_csrf_es_rechazado(api: ClienteApi, admin_usuario: Usuario) -> None:
    iniciar(api)
    assert api.post(REFRESH).status_code == 403


def test_refresh_sin_cookie(api: ClienteApi) -> None:
    assert api.post(REFRESH, **csrf(api)).status_code == 401


def test_refresh_usuario_desactivado(api: ClienteApi, admin_usuario: Usuario) -> None:
    iniciar(api)
    cabecera = csrf(api)
    Usuario.objects.filter(nip="900001").update(is_active=False)
    assert api.post(REFRESH, **cabecera).status_code == 401


def test_logout_invalida_refresh(api: ClienteApi, admin_usuario: Usuario) -> None:
    iniciar(api)
    token = api.cookies[settings.REFRESH_COOKIE_NAME].value
    cabecera = csrf(api)
    assert api.post("/api/v1/auth/logout", **cabecera).status_code == 204
    api.cookies[settings.REFRESH_COOKIE_NAME] = token
    assert api.post(REFRESH, **cabecera).status_code == 401


def test_logout_con_token_invalido(api: ClienteApi) -> None:
    cabecera = csrf(api)
    api.cookies[settings.REFRESH_COOKIE_NAME] = "basura"
    assert api.post("/api/v1/auth/logout", **cabecera).status_code == 204


def test_clave_temporal_obliga_a_cambiar(api: ClienteApi, grupos: None) -> None:
    usuario = crear_usuario("900010", "usuario", "Temporal-Clave-1x")
    usuario.debe_cambiar_clave = True
    usuario.save()
    acceso = iniciar(api, "900010", "Temporal-Clave-1x").data["access"]
    auth = {"HTTP_AUTHORIZATION": f"Bearer {acceso}"}
    bloqueado = api.get("/api/v1/contactos", **auth)
    assert bloqueado.status_code == 403
    assert bloqueado.data["type"] == "/problemas/cambio-clave-requerido"
    assert api.get("/api/v1/auth/yo", **auth).data["debe_cambiar_clave"] is True

    debil = api.post("/api/v1/auth/cambio-clave", {"clave_actual": "Temporal-Clave-1x", "clave_nueva": "123"}, **auth)
    assert debil.status_code == 422
    assert "clave_nueva" in debil.data["errors"]
    igual = api.post(
        "/api/v1/auth/cambio-clave", {"clave_actual": "Temporal-Clave-1x", "clave_nueva": "Temporal-Clave-1x"}, **auth
    )
    assert igual.status_code == 422
    errada = api.post(
        "/api/v1/auth/cambio-clave", {"clave_actual": "otra", "clave_nueva": "Nueva-Clave-Larga-9"}, **auth
    )
    assert errada.status_code == 422

    ok = api.post(
        "/api/v1/auth/cambio-clave", {"clave_actual": "Temporal-Clave-1x", "clave_nueva": "Nueva-Clave-Larga-9"}, **auth
    )
    assert ok.status_code == 200
    usuario.refresh_from_db()
    assert usuario.debe_cambiar_clave is False
    assert usuario.clave_cambiada_en is not None
    nuevo = {"HTTP_AUTHORIZATION": f"Bearer {ok.data['access']}"}
    assert api.get("/api/v1/contactos", **nuevo).status_code == 200


def test_no_reutiliza_clave_anterior(api: ClienteApi, grupos: None) -> None:
    from apps.cuentas.servicios import cambiar_clave

    usuario = crear_usuario("900011", "usuario", "Primera-Clave-Larga-1")
    cambiar_clave(usuario, "Segunda-Clave-Larga-2")
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        cambiar_clave(usuario, "Primera-Clave-Larga-1")


def test_cambio_de_clave_invalida_token_anterior(api: ClienteApi, admin_usuario: Usuario) -> None:
    acceso = iniciar(api).data["access"]
    auth = {"HTTP_AUTHORIZATION": f"Bearer {acceso}"}
    api.post("/api/v1/auth/cambio-clave", {"clave_actual": CLAVE, "clave_nueva": "Otra-Clave-Muy-Larga-7"}, **auth)
    assert api.get("/api/v1/contactos", **auth).status_code == 401


def test_yo_devuelve_permisos(api: ClienteApi, usuario_operativo: Usuario) -> None:
    acceso = iniciar(api, "900002").data["access"]
    datos = api.get("/api/v1/auth/yo", HTTP_AUTHORIZATION=f"Bearer {acceso}").data
    assert datos["rol"] == "usuario"
    assert "contactos.view_contacto" in datos["permisos"]
    assert "cuentas.view_usuario" not in datos["permisos"]


def test_login_limita_peticiones(api: ClienteApi, admin_usuario: Usuario, settings: Any) -> None:
    from django.core.cache import cache

    cache.clear()
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK}
    respuestas = [iniciar(api, clave="mal-123456").status_code for _ in range(11)]
    assert respuestas[-1] == 429
    cache.clear()


def test_clave_temporal_inicial_configurada(settings: Any) -> None:
    from apps.cuentas.servicios import generar_clave_temporal

    assert settings.CLAVE_TEMPORAL_INICIAL == "CheckLTDA!"
    # Al inicializar cuentas (inicial=True) usa la variable de entorno
    assert generar_clave_temporal(inicial=True) == "CheckLTDA!"

    # Generación regular produce clave aleatoria segura de 16 caracteres
    aleatoria = generar_clave_temporal(inicial=False)
    assert len(aleatoria) == 16
    assert aleatoria != "CheckLTDA!"


def test_login_con_clave_temporal_inicial_exitosa(api: ClienteApi, settings: Any) -> None:
    usuario = crear_usuario("900020", "usuario", settings.CLAVE_TEMPORAL_INICIAL)
    usuario.debe_cambiar_clave = True
    usuario.save()
    respuesta = iniciar(api, "900020", settings.CLAVE_TEMPORAL_INICIAL)
    assert respuesta.status_code == 200
    assert respuesta.data["access"]
    yo = api.get("/api/v1/auth/yo", HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    assert yo.status_code == 200
    assert yo.data["debe_cambiar_clave"] is True


def test_login_cookie_dura_sesion_dias(api: ClienteApi, admin_usuario: Usuario) -> None:
    respuesta = iniciar(api)
    assert respuesta.cookies[settings.REFRESH_COOKIE_NAME]["max-age"] == 2592000


def test_refresh_renueva_vida_completa(api: ClienteApi, admin_usuario: Usuario) -> None:
    iniciar(api)
    nuevo = api.post(REFRESH, **csrf(api))
    assert nuevo.status_code == 200
    assert nuevo.cookies[settings.REFRESH_COOKIE_NAME]["max-age"] == 2592000


def test_cambio_de_clave_sigue_revocando(api: ClienteApi, admin_usuario: Usuario) -> None:
    acceso = iniciar(api).data["access"]
    anterior = api.cookies[settings.REFRESH_COOKIE_NAME].value
    cabecera = csrf(api)
    auth = {"HTTP_AUTHORIZATION": f"Bearer {acceso}"}
    cambio = api.post("/api/v1/auth/cambio-clave", {"clave_actual": CLAVE, "clave_nueva": "Otra-Clave-Muy-Larga-7"}, **auth)
    assert cambio.status_code == 200
    api.cookies[settings.REFRESH_COOKIE_NAME] = anterior  # el cambio emite una cookie nueva; se reusa la previa
    assert api.post(REFRESH, **cabecera).status_code == 401
