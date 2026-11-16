"""Filtros por rango de fechas y por consentimiento de contacto en contactos y llamadas."""

from datetime import date, datetime, timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.contactos.models import Contacto
from apps.llamadas.models import LlamadaCumpleanos, LlamadaRtm, LlamadaSoat
from apps.vehiculos.models import Moto
from tests.conftest import ClienteApi


def ids(api: ClienteApi, recurso: str, **filtros: Any) -> set[Any]:
    parametros = {f"filter[{k}]": v for k, v in filtros.items()}
    respuesta = api.get(f"/api/v1/{recurso}", parametros)
    assert respuesta.status_code == 200, respuesta.json()
    clave = "nip" if recurso == "contactos" else "id"
    return {fila[clave] for fila in respuesta.json()["data"]}


def contacto(nip: str, **extra: Any) -> Contacto:
    return Contacto.objects.create(nip=nip, nombre=f"CLIENTE {nip}", dia_nac=10, mes_nac=3, **extra)


def moto(placa: str, duenio: Contacto) -> Moto:
    return Moto.objects.create(placa=placa, marca="HONDA", contacto=duenio)


def en_bogota(dia: date) -> datetime:
    return datetime(dia.year, dia.month, dia.day, 10, 0, tzinfo=timezone.get_current_timezone())


@pytest.mark.django_db
class TestFiltroContactosPorConsentimiento:
    @pytest.mark.parametrize("campo", ["contactar_cumpleanos", "contactar_soat", "contactar_rtm"])
    def test_filtra_true_y_false(self, api_usuario: ClienteApi, campo: str) -> None:
        contacto("SI1")
        contacto("NO1", **{campo: False})
        assert ids(api_usuario, "contactos", **{campo: "true"}) == {"SI1"}
        assert ids(api_usuario, "contactos", **{campo: "false"}) == {"NO1"}


@pytest.mark.django_db
class TestLlamadasCumpleanos:
    def test_rango_y_consentimiento_en_pendientes(self, api_usuario: ClienteApi) -> None:
        hoy = timezone.localdate()
        si = contacto("SI1")
        no = contacto("NO1", contactar_cumpleanos=False)
        dentro = LlamadaCumpleanos.objects.create(contacto=si, fecha=en_bogota(hoy), estado="no_realizada")
        fuera = LlamadaCumpleanos.objects.create(
            contacto=si, fecha=en_bogota(hoy - timedelta(days=10)), estado="no_realizada"
        )
        sin_permiso = LlamadaCumpleanos.objects.create(contacto=no, fecha=en_bogota(hoy), estado="no_realizada")
        rango = {"desde": (hoy - timedelta(days=1)).isoformat(), "hasta": hoy.isoformat()}

        assert ids(api_usuario, "llamadas-cumpleanos", pendiente="true", **rango) == {dentro.id}
        # El historial conserva todas las llamadas del rango, incluso las de quien ya no desea contacto.
        assert ids(api_usuario, "llamadas-cumpleanos", **rango) == {dentro.id, sin_permiso.id}
        assert ids(api_usuario, "llamadas-cumpleanos", consentimiento="true", **rango) == {dentro.id}
        assert ids(api_usuario, "llamadas-cumpleanos", consentimiento="false") == {sin_permiso.id}
        assert fuera.id in ids(api_usuario, "llamadas-cumpleanos")


@pytest.mark.django_db
class TestLlamadasPorPlaca:
    @pytest.mark.parametrize(
        ("recurso", "modelo", "campo"),
        [("llamadas-rtm", LlamadaRtm, "contactar_rtm"), ("llamadas-soat", LlamadaSoat, "contactar_soat")],
    )
    def test_rango_y_consentimiento_del_titular(
        self, api_usuario: ClienteApi, recurso: str, modelo: Any, campo: str
    ) -> None:
        hoy = timezone.localdate()
        moto_si = moto("SI001", contacto("SI1"))
        moto_no = moto("NO001", contacto("NO1", **{campo: False}))

        def llamada(m: Moto, dia: date, estado: str = "no_realizada") -> str:
            return modelo.objects.create(id=f"{m.placa}.{dia:%Y-%m-%d}", moto=m, fecha=dia, estado=estado).id

        dentro = llamada(moto_si, hoy)
        fuera = llamada(moto_si, hoy + timedelta(days=30))
        sin_permiso = llamada(moto_no, hoy)
        rango = {"desde": hoy.isoformat(), "hasta": (hoy + timedelta(days=7)).isoformat()}

        assert ids(api_usuario, recurso, pendiente="true", **rango) == {dentro}
        assert ids(api_usuario, recurso, **rango) == {dentro, sin_permiso}
        assert ids(api_usuario, recurso, consentimiento="false") == {sin_permiso}
        assert ids(api_usuario, recurso, consentimiento="true") == {dentro, fuera}

    def test_pendientes_excluyen_fechas_insalvables(self, api_usuario: ClienteApi) -> None:
        m = moto("LZB56D", contacto("SI1"))
        LlamadaRtm.objects.create(id="LZB56D.3196-01-01", moto=m, fecha=date(3196, 1, 1), estado="sin_estado")
        valida = LlamadaRtm.objects.create(
            id="LZB56D.2026-01-01", moto=m, fecha=date(2026, 1, 1), estado="sin_estado"
        ).id
        assert ids(api_usuario, "llamadas-rtm", pendiente="true") == {valida}
        datos = api_usuario.get("/api/v1/llamadas-rtm", {"filter[placa]": "LZB56D"}).json()["data"]
        assert {d["fecha"] for d in datos} == {None, "2026-01-01"}


@pytest.mark.django_db
def test_tablero_ignora_cumpleanos_sin_consentimiento(api_usuario: ClienteApi) -> None:
    hoy = timezone.localdate()
    Contacto.objects.create(nip="A1", nombre="CON PERMISO", dia_nac=hoy.day, mes_nac=hoy.month)
    Contacto.objects.create(
        nip="A2", nombre="SIN PERMISO", dia_nac=hoy.day, mes_nac=hoy.month, contactar_cumpleanos=False
    )
    assert api_usuario.get("/api/v1/tablero").json()["cumpleanos_hoy"] == 1
