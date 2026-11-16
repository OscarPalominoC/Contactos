"""Cuenta propia: cambiar el nombre desde el menú de usuario y política de clave relajada (desarrollo local)."""

import pytest
from rest_framework.test import APIClient

from apps.cuentas.models import Usuario
from tests.conftest import CLAVE, ClienteApi, crear_usuario


@pytest.mark.django_db
class TestCambiarMiNombre:
    def test_actualiza_y_normaliza_el_nombre(self, api_usuario: ClienteApi, usuario_operativo: Usuario) -> None:
        respuesta = api_usuario.patch("/api/v1/auth/yo", {"nombre": "  oscar   palomino "})
        assert respuesta.status_code == 200, respuesta.json()
        assert respuesta.json()["nombre"] == "OSCAR PALOMINO"
        usuario_operativo.refresh_from_db()
        assert usuario_operativo.nombre == "OSCAR PALOMINO"

    def test_rechaza_nombre_vacio_o_corto(self, api_usuario: ClienteApi) -> None:
        respuesta = api_usuario.patch("/api/v1/auth/yo", {"nombre": " a "})
        assert respuesta.status_code == 422
        assert "nombre" in respuesta.json()["errors"]

    def test_no_permite_cambiar_otros_campos(self, api_usuario: ClienteApi) -> None:
        assert api_usuario.patch("/api/v1/auth/yo", {"rol": "administrador"}).status_code == 422

    def test_con_clave_temporal_primero_debe_cambiarla(self, api: ClienteApi, grupos: None) -> None:
        usuario = crear_usuario("900009", "usuario")
        usuario.debe_cambiar_clave = True
        usuario.save(update_fields=["debe_cambiar_clave"])
        api.force_authenticate(usuario)
        assert api.patch("/api/v1/auth/yo", {"nombre": "NUEVO NOMBRE"}).status_code == 403

    def test_requiere_sesion(self) -> None:
        assert APIClient().patch("/api/v1/auth/yo", {"nombre": "X Y Z"}, format="json").status_code == 401


@pytest.mark.django_db
class TestPoliticaDeClave:
    def _cambiar(self, api: ClienteApi, nueva: str) -> int:
        return api.post("/api/v1/auth/cambio-clave", {"clave_actual": CLAVE, "clave_nueva": nueva}).status_code

    def test_acepta_5_caracteres_aunque_incluya_el_nombre(self, api_usuario: ClienteApi) -> None:
        # El usuario de prueba se llama «USUARIO DE PRUEBA 900002».
        assert self._cambiar(api_usuario, "prueba") == 200

    def test_acepta_solo_numeros_y_el_documento(self, api_usuario: ClienteApi) -> None:
        assert self._cambiar(api_usuario, "900002") == 200

    def test_rechaza_menos_de_5(self, api_usuario: ClienteApi) -> None:
        respuesta = api_usuario.post("/api/v1/auth/cambio-clave", {"clave_actual": CLAVE, "clave_nueva": "abcd"})
        assert respuesta.status_code == 422
        assert "5" in " ".join(respuesta.json()["errors"]["clave_nueva"])

    def test_sigue_sin_permitir_repetir_la_actual(self, api_usuario: ClienteApi) -> None:
        assert self._cambiar(api_usuario, CLAVE) == 422
