"""Correcciones del code-review final: fechas legadas al editar, estado con vencimiento basura, inhabilitados."""

from datetime import date

import pytest
from django.utils import timezone

from apps.contactos.models import Contacto
from apps.llamadas.models import LlamadaCumpleanos, LlamadaRtm
from apps.revisiones.models import Revision, Soat
from apps.vehiculos.models import Moto
from tests.conftest import ClienteApi


@pytest.mark.django_db
class TestFechasLegadasAlEditar:
    def test_editar_moto_conserva_fecha_insalvable_que_el_cliente_vio_vacia(self, api_usuario: ClienteApi, moto: Moto) -> None:
        moto.fecha_venc_soat = date(3017, 5, 1)
        moto.save()
        respuesta = api_usuario.patch(f"/api/v1/motos/{moto.placa}", {"nro_soat": "123", "fecha_venc_soat": None})
        assert respuesta.status_code == 200, respuesta.json()
        moto.refresh_from_db()
        assert moto.fecha_venc_soat == date(3017, 5, 1)
        assert moto.nro_soat == "123"

    def test_editar_moto_puede_cambiar_la_fecha_insalvable(self, api_usuario: ClienteApi, moto: Moto) -> None:
        moto.fecha_venc_soat = date(3017, 5, 1)
        moto.save()
        api_usuario.patch(f"/api/v1/motos/{moto.placa}", {"fecha_venc_soat": "2027-05-01"})
        moto.refresh_from_db()
        assert moto.fecha_venc_soat == date(2027, 5, 1)

    def test_editar_revision_con_vencimiento_legado_sugiere_uno_valido(self, api_usuario: ClienteApi, moto: Moto) -> None:
        Revision.objects.create(
            certificado="R-LEG", moto=moto, fecha_certificado=date(2017, 3, 1), fecha_venc_certificado=date(1899, 3, 1)
        )
        respuesta = api_usuario.patch("/api/v1/revisiones/R-LEG", {"estado": "DUPLICADO", "fecha_venc_certificado": None})
        assert respuesta.status_code == 200, respuesta.json()
        assert respuesta.json()["fecha_venc_certificado"] == "2018-03-01"

    def test_editar_soat_con_vencimiento_legado_sugiere_uno_valido(self, api_usuario: ClienteApi, moto: Moto) -> None:
        Soat.objects.create(soat="7-SURA", moto=moto, fecha_soat=date(2017, 3, 1), fecha_venc_soat=date(1899, 3, 1))
        respuesta = api_usuario.patch("/api/v1/soats/7-SURA", {"estado": "DUPLICADO", "fecha_venc_soat": None})
        assert respuesta.status_code == 200, respuesta.json()
        assert respuesta.json()["fecha_venc_soat"] == "2018-03-01"


@pytest.mark.django_db
def test_vencimiento_basura_no_se_muestra_vigente(api_usuario: ClienteApi, moto: Moto) -> None:
    Soat.objects.create(soat="9-SURA", moto=moto, fecha_soat=date(2017, 1, 1), fecha_venc_soat=date(3017, 1, 1))
    assert api_usuario.get("/api/v1/soats/9-SURA").json()["estado_actual"] == "VENCIDO"


@pytest.mark.django_db
def test_pendientes_excluyen_contactos_inhabilitados(api_usuario: ClienteApi) -> None:
    hoy = timezone.localdate()
    inhabilitado = Contacto.objects.create(nip="INH", nombre="NO LLAMAR", estado="inhabilitado")
    moto = Moto.objects.create(placa="INH01", marca="HONDA", contacto=inhabilitado)
    LlamadaCumpleanos.objects.create(contacto=inhabilitado, fecha=timezone.now(), estado="sin_estado")
    LlamadaRtm.objects.create(id=f"INH01.{hoy:%Y-%m-%d}", moto=moto, fecha=hoy, estado="sin_estado")
    for recurso in ("llamadas-cumpleanos", "llamadas-rtm"):
        respuesta = api_usuario.get(f"/api/v1/{recurso}", {"filter[pendiente]": "true"})
        assert respuesta.json()["meta"]["page"]["total"] == 0, recurso
