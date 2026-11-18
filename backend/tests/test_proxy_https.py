"""Despliegue detrás de nginx con TLS y bajo un subpath (/contactos/)."""

import runpy
from pathlib import Path

import pytest
from django.conf import settings
from django.http import HttpResponse
from django.middleware.security import SecurityMiddleware
from django.test import RequestFactory

RUTA_SETTINGS = Path(settings.BASE_DIR) / "config" / "settings.py"


@pytest.mark.unit
def test_confia_en_x_forwarded_proto_del_proxy():
    assert settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")


def _middleware_ssl(settings):
    settings.SECURE_SSL_REDIRECT = True
    return SecurityMiddleware(lambda peticion: HttpResponse("ok"))


@pytest.mark.unit
def test_peticion_https_via_proxy_no_se_redirige(settings):
    middleware = _middleware_ssl(settings)
    peticion = RequestFactory().get("/api/v1/auth/refresh", HTTP_X_FORWARDED_PROTO="https")
    assert middleware(peticion).status_code == 200


@pytest.mark.unit
def test_peticion_http_sin_proxy_si_se_redirige(settings):
    middleware = _middleware_ssl(settings)
    peticion = RequestFactory().get("/api/v1/auth/refresh")
    assert middleware(peticion).status_code == 301


@pytest.mark.unit
def test_ruta_cookie_refresco_por_defecto(monkeypatch):
    monkeypatch.delenv("REFRESH_COOKIE_PATH", raising=False)
    assert runpy.run_path(str(RUTA_SETTINGS))["REFRESH_COOKIE_PATH"] == "/api/v1/auth"


@pytest.mark.unit
def test_ruta_cookie_refresco_configurable_por_entorno(monkeypatch):
    monkeypatch.setenv("REFRESH_COOKIE_PATH", "/contactos/api/v1/auth")
    assert runpy.run_path(str(RUTA_SETTINGS))["REFRESH_COOKIE_PATH"] == "/contactos/api/v1/auth"
