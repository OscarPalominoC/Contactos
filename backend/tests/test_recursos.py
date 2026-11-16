"""CRUD de contactos, motos, catálogos, revisiones, SOAT, llamadas, tablero y ficha 360."""

from datetime import timedelta
from typing import Any

import pytest

from apps.comun.models import RegistroAuditoria
from apps.contactos.models import Contacto
from apps.llamadas.models import LlamadaRtm
from apps.revisiones.models import Revision, Soat
from apps.vehiculos.models import Linea, Marca, Moto
from tests.conftest import ClienteApi

pytestmark = pytest.mark.django_db


class TestContactos:
    def test_crear_normaliza_y_audita(self, api_usuario: ClienteApi) -> None:
        respuesta = api_usuario.post(
            "/api/v1/contactos",
            {"nip": " 1 234 567 ", "nombre": "  maria   perez ", "correo": "MARIA@EJEMPLO.TEST", "mes_nac": 3},
        )
        assert respuesta.status_code == 201, respuesta.json()
        cuerpo = respuesta.json()
        assert cuerpo["nip"] == "1234567"
        assert cuerpo["nombre"] == "MARIA PEREZ"
        assert cuerpo["correo"] == "maria@ejemplo.test"
        assert cuerpo["mes_nac_nombre"] == "Marzo"
        assert cuerpo["creado_por"] == "USUARIO DE PRUEBA 900002"
        assert RegistroAuditoria.objects.filter(accion="crear", objeto_id="1234567").exists()

    def test_duplicado_409(self, api_usuario: ClienteApi, contacto: Contacto) -> None:
        respuesta = api_usuario.post("/api/v1/contactos", {"nip": contacto.nip, "nombre": "OTRO NOMBRE"})
        assert respuesta.status_code == 409

    @pytest.mark.parametrize(
        "campo,valor",
        [("correo", "no-es-correo"), ("dia_nac", 40), ("mes_nac", 13), ("nombre", "a"), ("nip", "!!")],
    )
    def test_validaciones_422(self, api_usuario: ClienteApi, campo: str, valor: Any) -> None:
        datos = {"nip": "7654321", "nombre": "PERSONA VALIDA", campo: valor}
        respuesta = api_usuario.post("/api/v1/contactos", datos)
        assert respuesta.status_code == 422
        assert campo in respuesta.json()["errors"]

    def test_editar_e_inhabilitar(self, api_usuario: ClienteApi, contacto: Contacto) -> None:
        respuesta = api_usuario.patch(
            f"/api/v1/contactos/{contacto.nip}", {"estado": "inhabilitado", "celular": "  311 "}
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["estado"] == "inhabilitado"
        assert respuesta.json()["celular"] == "311"
        assert api_usuario.patch(f"/api/v1/contactos/{contacto.nip}", {"nip": "999"}).status_code == 422

    def test_buscar(self, api_usuario: ClienteApi, contacto: Contacto) -> None:
        assert api_usuario.get("/api/v1/contactos", {"filter[q]": "cliente"}).json()["meta"]["page"]["total"] == 1
        assert api_usuario.get("/api/v1/contactos", {"filter[q]": "1000"}).json()["meta"]["page"]["total"] == 1
        assert api_usuario.get("/api/v1/contactos", {"filter[q]": "  "}).json()["meta"]["page"]["total"] == 1

    def test_ficha_360(
        self,
        api_usuario: ClienteApi,
        contacto: Contacto,
        revision: Revision,
        soat: Soat,
        llamada_rtm: Any,
        llamada_soat: Any,
        llamada_cumpleanos: Any,
        django_assert_max_num_queries: Any,
    ) -> None:
        with django_assert_max_num_queries(16):
            ficha = api_usuario.get(f"/api/v1/contactos/{contacto.nip}/ficha").json()
        assert ficha["contacto"]["nip"] == contacto.nip
        assert [m["placa"] for m in ficha["motos"]] == ["ABC12D"]
        assert len(ficha["revisiones"]) == 1
        assert ficha["revisiones"][0]["estado_actual"] == "VIGENTE"
        assert ficha["soats"][0]["aseguradora"] == "MUNDIAL"
        assert len(ficha["llamadas_rtm"]) == len(ficha["llamadas_soat"]) == len(ficha["llamadas_cumpleanos"]) == 1


class TestMotos:
    def test_crear(self, api_usuario: ClienteApi, contacto: Contacto, linea: Linea) -> None:
        datos = {
            "placa": "xyz 98e",
            "marca": "honda",
            "linea": "XR 190L",
            "modelo": "2025",
            "nip_contacto": contacto.nip,
        }
        respuesta = api_usuario.post("/api/v1/motos", datos)
        assert respuesta.status_code == 201, respuesta.json()
        assert respuesta.json()["placa"] == "XYZ98E"
        assert respuesta.json()["nip_contacto"] == contacto.nip

    def test_linea_de_otra_marca_422(self, api_usuario: ClienteApi, contacto: Contacto, linea: Linea) -> None:
        Marca.objects.create(codigo="YA", nombre="YAMAHA")
        datos = {"placa": "XYZ98E", "marca": "YAMAHA", "linea": "XR 190L", "nip_contacto": contacto.nip}
        respuesta = api_usuario.post("/api/v1/motos", datos)
        assert respuesta.status_code == 422
        assert "linea" in respuesta.json()["errors"]

    @pytest.mark.parametrize("campo,valor", [("placa", "A1"), ("modelo", "20"), ("nip_contacto", "no-existe")])
    def test_validaciones(self, api_usuario: ClienteApi, contacto: Contacto, campo: str, valor: str) -> None:
        datos = {"placa": "XYZ98E", "marca": "HONDA", "nip_contacto": contacto.nip, campo: valor}
        assert api_usuario.post("/api/v1/motos", datos).status_code == 422

    def test_duplicada_y_detalle(self, api_usuario: ClienteApi, moto: Moto) -> None:
        datos = {"placa": moto.placa, "marca": "HONDA", "nip_contacto": moto.contacto_id}
        assert api_usuario.post("/api/v1/motos", datos).status_code == 409
        detalle = api_usuario.get(f"/api/v1/motos/{moto.placa}").json()
        assert detalle["propietario"]["nombre"] == "CLIENTE DE PRUEBA"
        assert api_usuario.get("/api/v1/motos", {"filter[q]": "abc"}).json()["meta"]["page"]["total"] == 1

    def test_editar_no_cambia_placa(self, api_usuario: ClienteApi, moto: Moto) -> None:
        assert api_usuario.patch(f"/api/v1/motos/{moto.placa}", {"placa": "ZZZ11Z"}).status_code == 422
        assert api_usuario.patch(f"/api/v1/motos/{moto.placa}", {"modelo": "2023"}).json()["modelo"] == "2023"


class TestCatalogos:
    def test_admin_crea_y_borra_marca(self, api_admin: ClienteApi) -> None:
        assert api_admin.post("/api/v1/marcas", {"codigo": "kt", "nombre": "ktm"}).json() == {
            "codigo": "KT",
            "nombre": "KTM",
        }
        assert api_admin.post("/api/v1/marcas", {"codigo": "KT", "nombre": "KTM"}).status_code == 409
        assert api_admin.delete("/api/v1/marcas/KT").status_code == 204
        assert not Marca.objects.filter(codigo="KT").exists()

    def test_no_borra_marca_en_uso(self, api_admin: ClienteApi, moto: Moto) -> None:
        assert api_admin.delete("/api/v1/marcas/HO").status_code == 409
        assert api_admin.delete("/api/v1/lineas/XR 190L").status_code == 409

    def test_lineas_por_marca(self, api_admin: ClienteApi, linea: Linea) -> None:
        cuerpo = api_admin.get("/api/v1/lineas", {"filter[marca]": "HO"}).json()
        assert cuerpo["data"][0]["marca_nombre"] == "HONDA"
        nueva = api_admin.post("/api/v1/lineas", {"linea": "cb 125", "marca": "HO"})
        assert nueva.status_code == 201
        assert api_admin.post("/api/v1/lineas", {"linea": "CB 125", "marca": "HO"}).status_code == 409
        assert api_admin.delete("/api/v1/lineas/CB 125").status_code == 204

    def test_usuario_no_crea_catalogo(self, api_usuario: ClienteApi) -> None:
        assert api_usuario.post("/api/v1/marcas", {"codigo": "X", "nombre": "X"}).status_code == 403


class TestRevisionesYSoat:
    def test_crear_revision_sugiere_vencimiento(self, api_usuario: ClienteApi, moto: Moto, hoy: Any) -> None:
        datos = {"certificado": "cert-9", "placa": "abc12d", "fecha_certificado": hoy.isoformat()}
        respuesta = api_usuario.post("/api/v1/revisiones", datos)
        assert respuesta.status_code == 201, respuesta.json()
        cuerpo = respuesta.json()
        assert cuerpo["certificado"] == "CERT-9"
        assert cuerpo["fecha_venc_certificado"] == hoy.replace(year=hoy.year + 1).isoformat()
        assert cuerpo["estado_actual"] == "VIGENTE"

    def test_revision_validaciones(self, api_usuario: ClienteApi, moto: Moto, revision: Revision, hoy: Any) -> None:
        assert api_usuario.post("/api/v1/revisiones", {"certificado": "CERT-001", "placa": "ABC12D"}).status_code == 409
        assert api_usuario.post("/api/v1/revisiones", {"certificado": "X1", "placa": "NOPE1"}).status_code == 422
        malo = {
            "certificado": "X2",
            "placa": "ABC12D",
            "fecha_certificado": hoy.isoformat(),
            "fecha_venc_certificado": (hoy - timedelta(days=1)).isoformat(),
        }
        assert api_usuario.post("/api/v1/revisiones", malo).status_code == 422
        assert api_usuario.post("/api/v1/revisiones", {"certificado": " ", "placa": "ABC12D"}).status_code == 422
        assert (
            api_usuario.patch(f"/api/v1/revisiones/{revision.certificado}", {"certificado": "OTRO"}).status_code == 422
        )

    def test_filtros_por_estado_calculado(
        self, api_usuario: ClienteApi, revision: Revision, moto: Moto, hoy: Any
    ) -> None:
        Revision.objects.create(certificado="VIEJA", moto=moto, fecha_venc_certificado=hoy - timedelta(days=3))
        Revision.objects.create(certificado="DUP", moto=moto, estado="DUPLICADO", fecha_venc_certificado=hoy)
        total = lambda **f: api_usuario.get(  # noqa: E731
            "/api/v1/revisiones", {f"filter[{k}]": v for k, v in f.items()}
        ).json()["meta"]["page"]["total"]
        assert total(estado="VIGENTE") == 1
        assert total(estado="VENCIDO") == 1
        assert total(estado="DUPLICADO") == 1
        assert total(vence_desde=hoy.isoformat(), vence_hasta=(hoy + timedelta(days=400)).isoformat()) == 2
        datos = api_usuario.get("/api/v1/revisiones/VIEJA").json()
        assert datos["estado_actual"] == "VENCIDO"

    def test_anular_revision(self, api_usuario: ClienteApi, revision: Revision) -> None:
        respuesta = api_usuario.post(f"/api/v1/revisiones/{revision.certificado}/anular")
        assert respuesta.status_code == 200
        assert respuesta.json()["estado_actual"] == "ANULADO"
        assert api_usuario.post(f"/api/v1/revisiones/{revision.certificado}/anular").status_code == 409
        assert RegistroAuditoria.objects.filter(accion="anular").count() == 1

    def test_crear_soat(self, api_usuario: ClienteApi, moto: Moto, hoy: Any) -> None:
        datos = {
            "numero": " 999 888 ",
            "aseguradora": "seguros  bolivar",
            "placa": "ABC12D",
            "fecha_soat": hoy.isoformat(),
        }
        respuesta = api_usuario.post("/api/v1/soats", datos)
        assert respuesta.status_code == 201, respuesta.json()
        assert respuesta.json()["soat"] == "999888-SEGUROS BOLIVAR"
        assert respuesta.json()["aseguradora"] == "SEGUROS BOLIVAR"
        assert api_usuario.post("/api/v1/soats", datos).status_code == 409

    def test_soat_validaciones_y_edicion(self, api_usuario: ClienteApi, soat: Soat, hoy: Any) -> None:
        assert api_usuario.post("/api/v1/soats", {"placa": "ABC12D"}).status_code == 422
        malo = {
            "numero": "1",
            "aseguradora": "X",
            "placa": "ABC12D",
            "fecha_soat": hoy.isoformat(),
            "fecha_venc_soat": hoy.isoformat(),
        }
        assert api_usuario.post("/api/v1/soats", malo).status_code == 422
        ruta = f"/api/v1/soats/{soat.soat}"
        assert api_usuario.patch(ruta, {"estado": "DUPLICADO"}).json()["estado_actual"] == "DUPLICADO"
        assert api_usuario.patch(ruta, {"numero": "1", "aseguradora": "OTRA"}).status_code == 422
        assert api_usuario.get("/api/v1/soats", {"filter[estado]": "DUPLICADO"}).json()["meta"]["page"]["total"] == 1
        assert api_usuario.post(f"{ruta}/anular").status_code == 200


class TestLlamadas:
    def test_cumpleanos_crear_e_intento(self, api_usuario: ClienteApi, contacto: Contacto) -> None:
        creada = api_usuario.post(
            "/api/v1/llamadas-cumpleanos",
            {"nip": contacto.nip, "estado": "realizada", "observacion": "<b>FELICITADO</b>"},
        )
        assert creada.status_code == 201, creada.json()
        cuerpo = creada.json()
        assert cuerpo["observacion"] == "<b>FELICITADO</b>"
        assert cuerpo["num_llamadas"] == 1
        intento = api_usuario.post(
            f"/api/v1/llamadas-cumpleanos/{cuerpo['id']}/intentos", {"estado": "ocupada", "observacion": "segunda"}
        )
        assert intento.json()["num_llamadas"] == 2
        assert intento.json()["estado_nombre"] == "Ocupada"
        assert api_usuario.post("/api/v1/llamadas-cumpleanos", {"nip": "no", "estado": "realizada"}).status_code == 422
        assert api_usuario.patch(f"/api/v1/llamadas-cumpleanos/{cuerpo['id']}", {"nip": "otro"}).status_code == 422

    @pytest.mark.parametrize("recurso", ["llamadas-rtm", "llamadas-soat"])
    def test_llamada_por_placa(self, api_usuario: ClienteApi, moto: Moto, hoy: Any, recurso: str) -> None:
        datos = {"placa": "abc12d", "fecha": hoy.isoformat(), "estado": "no_realizada", "observacion": "NO CONTESTA"}
        creada = api_usuario.post(f"/api/v1/{recurso}", datos)
        assert creada.status_code == 201, creada.json()
        assert creada.json()["id"] == f"ABC12D.{hoy:%Y-%m-%d}"
        assert api_usuario.post(f"/api/v1/{recurso}", datos).status_code == 409
        ruta = f"/api/v1/{recurso}/ABC12D.{hoy:%Y-%m-%d}"
        assert (
            api_usuario.post(f"{ruta}/intentos", {"estado": "realizada", "observacion": ""}).json()["num_llamadas"] == 2
        )
        assert api_usuario.patch(ruta, {"fecha": (hoy + timedelta(days=1)).isoformat()}).status_code == 422
        assert api_usuario.patch(ruta, {"placa": "ZZZ11Z"}).status_code == 422
        assert api_usuario.patch(ruta, {"observacion": "EDITADA"}).json()["observacion"] == "EDITADA"
        listado = api_usuario.get(f"/api/v1/{recurso}", {"filter[placa]": "ABC12D", "filter[estado]": "realizada"})
        assert listado.json()["meta"]["page"]["total"] == 1

    def test_validaciones_placa(self, api_usuario: ClienteApi, hoy: Any) -> None:
        sin_moto = {"placa": "NOPE1", "fecha": hoy.isoformat(), "estado": "realizada"}
        assert api_usuario.post("/api/v1/llamadas-rtm", sin_moto).status_code == 422

    def test_estado_sin_estado_no_elegible(self, api_usuario: ClienteApi, llamada_rtm: LlamadaRtm) -> None:
        respuesta = api_usuario.post(
            f"/api/v1/llamadas-rtm/{llamada_rtm.id}/intentos", {"estado": "sin_estado", "observacion": ""}
        )
        assert respuesta.status_code == 422


def test_tablero(api_usuario: ClienteApi, contacto: Contacto, moto: Moto, hoy: Any, llamada_cumpleanos: Any) -> None:
    Revision.objects.create(certificado="PRONTO", moto=moto, fecha_venc_certificado=hoy + timedelta(days=5))
    Soat.objects.create(soat="1-X", moto=moto, fecha_venc_soat=hoy + timedelta(days=29))
    Contacto.objects.create(nip="55", nombre="CUMPLE HOY", dia_nac=hoy.day, mes_nac=hoy.month)
    datos = api_usuario.get("/api/v1/tablero").json()
    assert datos["rtm_por_vencer"] == 1
    assert datos["soat_por_vencer"] == 1
    assert datos["cumpleanos_hoy"] == 1
    assert datos["llamadas_hoy"]["cumpleanos"] == 1
    assert datos["contactos_nuevos_mes"] >= 1
