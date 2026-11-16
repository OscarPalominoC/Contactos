"""Cumpleaños por rango de fechas (día/mes sin año) y nombre del contacto en la bitácora."""

from typing import Any

import pytest
from django.utils import timezone

from apps.contactos.models import Contacto
from apps.llamadas.models import LlamadaCumpleanos
from tests.conftest import ClienteApi


def _nips(respuesta: Any) -> set[str]:
    assert respuesta.status_code == 200, respuesta.json()
    return {c["nip"] for c in respuesta.json()["data"]}


@pytest.fixture
def cumpleaneros(db: Any) -> None:
    for nip, dia, mes in [
        ("C0110", 10, 1),
        ("C0228", 28, 2),
        ("C0229", 29, 2),
        ("C0301", 1, 3),
        ("C1115", 15, 11),
        ("C1120", 20, 11),
        ("C1231", 31, 12),
    ]:
        Contacto.objects.create(nip=nip, nombre=f"CLIENTE {nip}", dia_nac=dia, mes_nac=mes)
    Contacto.objects.create(nip="SINFECHA", nombre="SIN FECHA")


@pytest.mark.django_db
@pytest.mark.usefixtures("cumpleaneros")
class TestCumpleanosRango:
    def consultar(self, api: ClienteApi, desde: str = "", hasta: str = "") -> set[str]:
        params = {"page[size]": 100}
        if desde:
            params["filter[cumple_desde]"] = desde
        if hasta:
            params["filter[cumple_hasta]"] = hasta
        return _nips(api.get("/api/v1/contactos", params))

    def test_rango_dentro_del_mismo_ano(self, api_usuario: ClienteApi) -> None:
        assert self.consultar(api_usuario, "2026-11-15", "2026-11-20") == {"C1115", "C1120"}

    def test_un_solo_dia(self, api_usuario: ClienteApi) -> None:
        assert self.consultar(api_usuario, "2026-11-15", "2026-11-15") == {"C1115"}

    def test_rango_que_cruza_el_fin_de_ano(self, api_usuario: ClienteApi) -> None:
        assert self.consultar(api_usuario, "2026-12-25", "2027-01-10") == {"C1231", "C0110"}

    def test_29_de_febrero_entra_en_ano_no_bisiesto(self, api_usuario: ClienteApi) -> None:
        assert self.consultar(api_usuario, "2027-02-28", "2027-03-01") == {"C0228", "C0229", "C0301"}

    def test_rango_de_un_ano_o_mas_trae_todos_los_que_tienen_fecha(self, api_usuario: ClienteApi) -> None:
        todos = {"C0110", "C0228", "C0229", "C0301", "C1115", "C1120", "C1231"}
        assert self.consultar(api_usuario, "2026-01-01", "2027-01-01") == todos

    def test_solo_desde_o_solo_hasta_es_un_dia(self, api_usuario: ClienteApi) -> None:
        assert self.consultar(api_usuario, desde="2026-11-20") == {"C1120"}
        assert self.consultar(api_usuario, hasta="2026-02-28") == {"C0228"}

    def test_desde_posterior_a_hasta_es_error(self, api_usuario: ClienteApi) -> None:
        respuesta = api_usuario.get(
            "/api/v1/contactos", {"filter[cumple_desde]": "2026-11-20", "filter[cumple_hasta]": "2026-11-15"}
        )
        assert respuesta.status_code == 422  # convención del proyecto para datos inválidos


@pytest.mark.django_db
class TestNombreEnBitacoraCumpleanos:
    def test_lectura_incluye_nombre_del_contacto(self, api_usuario: ClienteApi, contacto: Contacto) -> None:
        LlamadaCumpleanos.objects.create(contacto=contacto, fecha=timezone.now())
        fila = api_usuario.get("/api/v1/llamadas-cumpleanos").json()["data"][0]
        assert fila["nombre"] == contacto.nombre
        assert fila["nip"] == contacto.nip

    def test_contacto_inexistente_da_nombre_nulo(self, api_usuario: ClienteApi) -> None:
        LlamadaCumpleanos.objects.create(contacto_id="NOEXISTE", fecha=timezone.now())
        fila = api_usuario.get("/api/v1/llamadas-cumpleanos").json()["data"][0]
        assert fila["nombre"] is None
