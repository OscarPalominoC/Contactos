import os
from django.conf import settings
from django.test import RequestFactory
from unittest.mock import patch
import pytest
from apps.comun.vistas import vista_salud

@pytest.mark.unit
def test_vps_ip_en_allowed_hosts_y_cors():
    assert "72.61.0.102" in settings.ALLOWED_HOSTS
    assert any("72.61.0.102" in origin for origin in settings.CORS_ALLOWED_ORIGINS)
    assert any("frontend" in origin for origin in settings.CORS_ALLOWED_ORIGINS)
    assert "admin@admin.com" == settings.SUPERADMIN_NIP

@pytest.mark.unit
def test_vista_salud_responde_ok():
    factory = RequestFactory()
    request = factory.get("/salud")
    with patch("django.db.connection.ensure_connection", return_value=None):
        response = vista_salud(request)
        assert response.status_code == 200
        assert b"ok" in response.content

@pytest.mark.unit
def test_vista_salud_responde_error_si_falla_bd():
    factory = RequestFactory()
    request = factory.get("/salud")
    with patch("django.db.connection.ensure_connection", side_effect=Exception("Fallo DB")):
        response = vista_salud(request)
        assert response.status_code == 503
        assert b"error" in response.content


