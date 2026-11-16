"""Llamadas por hacer calculadas desde los vencimientos (RTM y SOAT), propietario visible y búsqueda."""

from datetime import date, timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.contactos.models import Contacto
from apps.llamadas.models import LlamadaRtm, LlamadaSoat
from apps.revisiones.models import Revision, Soat
from apps.vehiculos.models import Moto
from tests.conftest import ClienteApi

HOY = date(2026, 11, 15)


@pytest.fixture(autouse=True)
def _hoy_fijo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(timezone, "localdate", lambda *a, **k: HOY)


def duenio(nip: str, **extra: Any) -> Contacto:
    return Contacto.objects.create(nip=nip, nombre=f"DUEÑO {nip}", celular="3001234567", **extra)


def moto(placa: str, contacto: Contacto) -> Moto:
    return Moto.objects.create(placa=placa, marca="HONDA", contacto=contacto)


def rtm(placa: str, vence: date, cert: str | None = None, estado: str = "VIGENTE") -> Revision:
    return Revision.objects.create(
        certificado=cert or f"C-{placa}-{vence:%Y%m%d}",
        moto_id=placa,
        fecha_certificado=vence - timedelta(days=365),
        fecha_venc_certificado=vence,
        estado=estado,
    )


def soat(placa: str, vence: date, estado: str = "VIGENTE") -> Soat:
    return Soat.objects.create(
        soat=f"{placa}{vence:%Y%m%d}-MUNDIAL",
        moto_id=placa,
        fecha_soat=vence - timedelta(days=365),
        fecha_venc_soat=vence,
        estado=estado,
    )


def por_llamar(api: ClienteApi, recurso: str, **filtros: str) -> list[dict[str, Any]]:
    parametros = {f"filter[{k}]": v for k, v in filtros.items()} | {"page[size]": 100}
    respuesta = api.get(f"/api/v1/{recurso}/por-llamar", parametros)
    assert respuesta.status_code == 200, respuesta.json()
    filas: list[dict[str, Any]] = respuesta.json()["data"]
    return filas


@pytest.mark.django_db
class TestRtmPorLlamar:
    def test_lista_vencimientos_del_rango_sin_llamada_realizada(self, api_usuario: ClienteApi) -> None:
        moto("AAA11A", duenio("1"))
        moto("BBB22B", duenio("2"))
        moto("CCC33C", duenio("3"))
        rtm("AAA11A", HOY + timedelta(days=5))
        rtm("BBB22B", HOY + timedelta(days=40))  # fuera del rango
        rtm("CCC33C", HOY + timedelta(days=3))
        LlamadaRtm.objects.create(
            id=f"CCC33C.{HOY + timedelta(days=3)}", moto_id="CCC33C", fecha=HOY + timedelta(days=3)
        )
        filas = por_llamar(api_usuario, "llamadas-rtm", desde=str(HOY), hasta=str(HOY + timedelta(days=30)))
        assert [f["placa"] for f in filas] == ["AAA11A"]
        fila = filas[0]
        assert fila["fecha"] == str(HOY + timedelta(days=5))
        assert fila["propietario_nombre"] == "DUEÑO 1"
        assert fila["propietario_nip"] == "1"
        assert fila["celular"] == "3001234567"
        assert fila["llamada_id"] is None
        assert fila["num_llamadas"] == 0

    def test_por_defecto_hoy_mas_30_dias(self, api_usuario: ClienteApi) -> None:
        moto("AAA11A", duenio("1"))
        moto("BBB22B", duenio("2"))
        moto("DDD44D", duenio("4"))
        rtm("AAA11A", HOY)
        rtm("BBB22B", HOY + timedelta(days=30))
        rtm("DDD44D", HOY - timedelta(days=1))
        assert {f["placa"] for f in por_llamar(api_usuario, "llamadas-rtm")} == {"AAA11A", "BBB22B"}

    def test_moto_que_ya_renovo_no_se_llama(self, api_usuario: ClienteApi) -> None:
        moto("AAA11A", duenio("1"))
        rtm("AAA11A", HOY + timedelta(days=5))
        rtm("AAA11A", HOY + timedelta(days=370))  # ya hizo la nueva revisión
        assert por_llamar(api_usuario, "llamadas-rtm") == []

    def test_revision_anulada_no_cuenta_ni_bloquea(self, api_usuario: ClienteApi) -> None:
        moto("AAA11A", duenio("1"))
        rtm("AAA11A", HOY + timedelta(days=5))
        rtm("AAA11A", HOY + timedelta(days=370), estado="ANULADO")
        rtm("AAA11A", HOY + timedelta(days=8), cert="OTRA", estado="DUPLICADO")
        assert [f["placa"] for f in por_llamar(api_usuario, "llamadas-rtm")] == ["AAA11A"]

    def test_respeta_consentimiento_y_estado_del_titular(self, api_usuario: ClienteApi) -> None:
        moto("AAA11A", duenio("1", contactar_rtm=False))
        moto("BBB22B", duenio("2", estado="inhabilitado"))
        rtm("AAA11A", HOY + timedelta(days=5))
        rtm("BBB22B", HOY + timedelta(days=5))
        assert por_llamar(api_usuario, "llamadas-rtm") == []

    def test_intento_fallido_aparece_con_su_llamada_y_al_final(self, api_usuario: ClienteApi) -> None:
        moto("AAA11A", duenio("1"))
        moto("BBB22B", duenio("2"))
        rtm("AAA11A", HOY + timedelta(days=2))
        rtm("BBB22B", HOY + timedelta(days=9))
        LlamadaRtm.objects.create(
            id=f"AAA11A.{HOY + timedelta(days=2)}",
            moto_id="AAA11A",
            fecha=HOY + timedelta(days=2),
            estado="ocupada",
            num_llamadas=2,
        )
        filas = por_llamar(api_usuario, "llamadas-rtm")
        assert [f["placa"] for f in filas] == ["BBB22B", "AAA11A"]
        assert filas[1]["llamada_id"] == f"AAA11A.{HOY + timedelta(days=2)}"
        assert filas[1]["estado"] == "ocupada"
        assert filas[1]["num_llamadas"] == 2

    def test_rango_invertido_es_error(self, api_usuario: ClienteApi) -> None:
        respuesta = api_usuario.get(
            "/api/v1/llamadas-rtm/por-llamar", {"filter[desde]": "2026-12-01", "filter[hasta]": "2026-11-01"}
        )
        assert respuesta.status_code == 422


@pytest.mark.django_db
class TestSoatPorLlamar:
    def test_lista_vencimientos_de_soat(self, api_usuario: ClienteApi) -> None:
        moto("AAA11A", duenio("1"))
        moto("BBB22B", duenio("2", contactar_soat=False))
        soat("AAA11A", HOY + timedelta(days=4))
        soat("BBB22B", HOY + timedelta(days=4))
        filas = por_llamar(api_usuario, "llamadas-soat")
        assert [(f["placa"], f["fecha"]) for f in filas] == [("AAA11A", str(HOY + timedelta(days=4)))]

    def test_llamada_realizada_lo_saca(self, api_usuario: ClienteApi) -> None:
        moto("AAA11A", duenio("1"))
        soat("AAA11A", HOY + timedelta(days=4))
        LlamadaSoat.objects.create(
            id=f"AAA11A.{HOY + timedelta(days=4)}",
            moto_id="AAA11A",
            fecha=HOY + timedelta(days=4),
            motivo_llamada="soat",
        )
        assert por_llamar(api_usuario, "llamadas-soat") == []


@pytest.mark.django_db
class TestPropietarioYBusqueda:
    def test_moto_trae_nombre_del_propietario(self, api_usuario: ClienteApi) -> None:
        moto("AAA11A", duenio("1"))
        fila = api_usuario.get("/api/v1/motos", {"filter[q]": "AAA"}).json()["data"][0]
        assert fila["nombre_contacto"] == "DUEÑO 1"

    def test_moto_de_propietario_inexistente(self, api_usuario: ClienteApi) -> None:
        Moto.objects.create(placa="ZZZ99Z", marca="HONDA", contacto_id="NOEXISTE")
        fila = api_usuario.get("/api/v1/motos", {"filter[q]": "ZZZ"}).json()["data"][0]
        assert fila["nombre_contacto"] is None

    @pytest.mark.parametrize(("recurso", "crear"), [("revisiones", rtm), ("soats", soat)])
    def test_revision_y_soat_traen_propietario(self, api_usuario: ClienteApi, recurso: str, crear: Any) -> None:
        moto("AAA11A", duenio("1"))
        crear("AAA11A", HOY + timedelta(days=5))
        fila = api_usuario.get(f"/api/v1/{recurso}", {"filter[q]": "aaa11a"}).json()["data"][0]
        assert fila["propietario_nombre"] == "DUEÑO 1"
        assert fila["propietario_nip"] == "1"

    def test_buscar_revision_por_certificado_o_placa(self, api_usuario: ClienteApi) -> None:
        moto("AAA11A", duenio("1"))
        moto("BBB22B", duenio("2"))
        rtm("AAA11A", HOY, cert="98765")
        rtm("BBB22B", HOY, cert="11111")

        def certificados(q: str) -> set[str]:
            datos = api_usuario.get("/api/v1/revisiones", {"filter[q]": q}).json()["data"]
            return {r["certificado"] for r in datos}

        assert certificados("9876") == {"98765"}
        assert certificados("BBB") == {"11111"}

    def test_buscar_soat_por_poliza_o_placa(self, api_usuario: ClienteApi) -> None:
        moto("AAA11A", duenio("1"))
        Soat.objects.create(soat="555-SURA", moto_id="AAA11A", fecha_venc_soat=HOY)

        def polizas(q: str) -> set[str]:
            return {s["soat"] for s in api_usuario.get("/api/v1/soats", {"filter[q]": q}).json()["data"]}

        assert polizas("555") == {"555-SURA"}
        assert polizas("aaa1") == {"555-SURA"}

    def test_contactos_ordenan_por_cumpleanos_y_celular(self, api_usuario: ClienteApi) -> None:
        Contacto.objects.create(nip="A", nombre="A", dia_nac=1, mes_nac=12, celular="300")
        Contacto.objects.create(nip="B", nombre="B", dia_nac=20, mes_nac=1, celular="320")
        Contacto.objects.create(nip="C", nombre="C", dia_nac=5, mes_nac=1, celular="310")

        def orden(sort: str) -> list[str]:
            return [c["nip"] for c in api_usuario.get("/api/v1/contactos", {"sort": sort}).json()["data"]]

        assert orden("cumpleanos") == ["C", "B", "A"]
        assert orden("-cumpleanos") == ["A", "B", "C"]
        assert orden("celular") == ["A", "C", "B"]
