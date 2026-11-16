"""Preferencias de contacto (consentimiento por canal: cumpleaños, SOAT y RTM)."""

import pytest

from apps.contactos.models import Contacto
from tests.conftest import ClienteApi

CAMPOS = ("contactar_cumpleanos", "contactar_soat", "contactar_rtm")


@pytest.mark.django_db
class TestPreferenciasContacto:
    def test_campos_por_defecto_verdaderos(self) -> None:
        contacto = Contacto.objects.create(nip="123456", nombre="CLIENTE NUEVO")
        contacto.refresh_from_db()
        for campo in CAMPOS:
            assert getattr(contacto, campo) is True

    def test_lectura_expone_preferencias(self, api_usuario: ClienteApi, contacto: Contacto) -> None:
        datos = api_usuario.get(f"/api/v1/contactos/{contacto.nip}").json()
        for campo in CAMPOS:
            assert datos[campo] is True

    def test_crear_con_preferencias(self, api_usuario: ClienteApi) -> None:
        respuesta = api_usuario.post(
            "/api/v1/contactos",
            {"nip": "77777", "nombre": "CLIENTE SIN SOAT", "contactar_soat": False},
        )
        assert respuesta.status_code == 201, respuesta.json()
        assert respuesta.json()["contactar_soat"] is False
        assert respuesta.json()["contactar_rtm"] is True

    def test_editar_preferencias(self, api_usuario: ClienteApi, contacto: Contacto) -> None:
        respuesta = api_usuario.patch(
            f"/api/v1/contactos/{contacto.nip}",
            {"contactar_cumpleanos": False, "contactar_soat": False, "contactar_rtm": False},
        )
        assert respuesta.status_code == 200, respuesta.json()
        contacto.refresh_from_db()
        assert (contacto.contactar_cumpleanos, contacto.contactar_soat, contacto.contactar_rtm) == (False, False, False)

    def test_cumpleanos_imposible_fuerza_no_contactar(self, api_usuario: ClienteApi, contacto: Contacto) -> None:
        respuesta = api_usuario.patch(
            f"/api/v1/contactos/{contacto.nip}", {"dia_nac": 31, "mes_nac": 2, "contactar_cumpleanos": True}
        )
        assert respuesta.status_code == 200, respuesta.json()
        assert respuesta.json()["contactar_cumpleanos"] is False

    def test_editar_otro_campo_de_contacto_con_31_febrero(self, api_usuario: ClienteApi) -> None:
        Contacto.objects.create(nip="31F", nombre="FEBRERO", dia_nac=31, mes_nac=2, contactar_cumpleanos=False)
        respuesta = api_usuario.patch("/api/v1/contactos/31F", {"celular": "3001112233", "contactar_cumpleanos": True})
        assert respuesta.status_code == 200, respuesta.json()
        assert respuesta.json()["contactar_cumpleanos"] is False
        assert respuesta.json()["celular"] == "3001112233"
