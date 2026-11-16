"""Saneamiento de fechas legadas: años transpuestos, fechas insalvables y cumpleaños inexistentes."""

import importlib
from datetime import date

import pytest
from django.apps import apps as registro_apps

from apps.comun.fechas_util import (
    es_cumpleanos_valido,
    fecha_segura,
    sanear_ano_transpuesto,
    sanear_fecha_soat,
    sanear_par,
)
from apps.contactos.models import Contacto
from apps.revisiones.models import Revision, Soat
from apps.vehiculos.models import Moto
from tests.conftest import ClienteApi


class TestSanearAnoTranspuesto:
    def test_ano_02xx_pasa_a_20xx(self) -> None:
        assert sanear_ano_transpuesto(date(227, 2, 14)) == date(2027, 2, 14)
        assert sanear_ano_transpuesto(date(220, 6, 4)) == date(2020, 6, 4)

    def test_fecha_valida_no_cambia(self) -> None:
        assert sanear_ano_transpuesto(date(2018, 7, 21)) == date(2018, 7, 21)
        assert sanear_ano_transpuesto(date(1990, 1, 1)) == date(1990, 1, 1)
        assert sanear_ano_transpuesto(date(2100, 12, 31)) == date(2100, 12, 31)

    def test_insalvable_es_none(self) -> None:
        assert sanear_ano_transpuesto(date(3196, 5, 1)) is None
        assert sanear_ano_transpuesto(date(1899, 12, 30)) is None
        assert sanear_ano_transpuesto(date(2101, 1, 1)) is None
        assert sanear_ano_transpuesto(None) is None

    def test_29_febrero_02xx_conserva_bisiesto(self) -> None:
        assert sanear_ano_transpuesto(date(228, 2, 29)) == date(2028, 2, 29)


class TestSanearFechaSoat:
    def test_siglo_erroneo_se_corrige_con_vencimiento(self) -> None:
        assert sanear_fecha_soat(date(3017, 7, 21), date(2018, 7, 21)) == date(2017, 7, 21)

    def test_expedicion_valida_no_cambia(self) -> None:
        assert sanear_fecha_soat(date(2017, 11, 13), date(2016, 11, 13)) == date(2017, 11, 13)

    def test_sin_correlacion_es_none(self) -> None:
        assert sanear_fecha_soat(date(3196, 7, 21), date(2018, 7, 21)) is None
        assert sanear_fecha_soat(date(3017, 7, 22), date(2018, 7, 21)) is None
        assert sanear_fecha_soat(date(2103, 8, 5), date(2104, 8, 5)) is None
        assert sanear_fecha_soat(date(3017, 7, 21), None) is None

    def test_vencimiento_con_siglo_erroneo(self) -> None:
        assert sanear_par(date(2025, 4, 3), date(2426, 4, 3)) == (date(2025, 4, 3), date(2026, 4, 3))
        assert sanear_par(date(2019, 6, 4), date(220, 6, 4)) == (date(2019, 6, 4), date(2020, 6, 4))
        assert sanear_par(date(2021, 1, 5), date(2223, 1, 5)) == (date(2021, 1, 5), None)
        assert sanear_par(None, None) == (None, None)

    def test_correlacion_con_29_febrero_inexistente_es_none(self) -> None:
        assert sanear_par(date(3020, 2, 29), date(2021, 2, 28)) == (None, date(2021, 2, 28))
        assert sanear_par(date(2019, 2, 28), date(3020, 2, 29)) == (date(2019, 2, 28), None)


class TestCumpleanosYFechaSegura:
    def test_cumpleanos(self) -> None:
        assert es_cumpleanos_valido(31, 2) is False
        assert es_cumpleanos_valido(30, 2) is False
        assert es_cumpleanos_valido(29, 2) is True
        assert es_cumpleanos_valido(31, 4) is False
        assert es_cumpleanos_valido(31, 12) is True
        assert es_cumpleanos_valido(None, 5) is False
        assert es_cumpleanos_valido(5, 13) is False
        assert es_cumpleanos_valido(0, 1) is False

    def test_fecha_segura(self) -> None:
        assert fecha_segura(date(2020, 1, 1)) == date(2020, 1, 1)
        assert fecha_segura(date(3196, 1, 1)) is None
        assert fecha_segura(date(227, 1, 1)) is None
        assert fecha_segura(None) is None


@pytest.mark.django_db
class TestSerializacionSegura:
    def test_revision_con_fecha_insalvable_se_expone_null(self, api_usuario: ClienteApi, moto: Moto) -> None:
        Revision.objects.create(
            certificado="CERT-RARO",
            moto=moto,
            fecha_certificado=date(3196, 5, 1),
            fecha_venc_certificado=date(1899, 12, 30),
            fecha_soat=date(2012, 1, 1),
        )
        datos = api_usuario.get("/api/v1/revisiones/CERT-RARO").json()
        assert datos["fecha_certificado"] is None
        assert datos["fecha_venc_certificado"] is None
        assert datos["fecha_soat"] == "2012-01-01"

    def test_soat_con_fecha_insalvable_se_expone_null(self, api_usuario: ClienteApi, moto: Moto) -> None:
        Soat.objects.create(
            soat="1-SURA", moto=moto, fecha_soat=date(3196, 7, 21), fecha_venc_soat=date(2300, 7, 21), estado="VENCIDO"
        )
        datos = api_usuario.get("/api/v1/soats/1-SURA").json()
        assert datos["fecha_soat"] is None
        assert datos["fecha_venc_soat"] is None
        assert datos["estado_actual"] == "VENCIDO"

    def test_moto_con_fecha_insalvable_se_expone_null(self, api_usuario: ClienteApi, moto: Moto) -> None:
        moto.fecha_venc_soat = date(3196, 1, 1)
        moto.fecha_rtmg = date(2020, 1, 1)
        moto.save()
        datos = api_usuario.get(f"/api/v1/motos/{moto.placa}").json()
        assert datos["fecha_venc_soat"] is None
        assert datos["fecha_rtmg"] == "2020-01-01"


@pytest.mark.django_db
class TestMigracionSaneamiento:
    def _ejecutar(self) -> None:
        modulo = importlib.import_module("apps.contactos.migrations.0003_sanear_fechas_y_preferencias")
        modulo.sanear(registro_apps, None)

    def test_marca_cumpleanos_invalidos_y_corrige_transposiciones(self, moto: Moto) -> None:
        Contacto.objects.create(nip="31F", nombre="FEBRERO TREINTA Y UNO", dia_nac=31, mes_nac=2)
        Contacto.objects.create(nip="31A", nombre="ABRIL TREINTA Y UNO", dia_nac=31, mes_nac=4)
        Contacto.objects.create(nip="OK1", nombre="CUMPLE VALIDO", dia_nac=29, mes_nac=2)
        Revision.objects.create(
            certificado="R1", moto=moto, fecha_certificado=date(2026, 2, 14), fecha_venc_certificado=date(227, 2, 14)
        )
        Revision.objects.create(
            certificado="R2", moto=moto, fecha_certificado=date(3196, 5, 1), fecha_venc_certificado=date(2012, 5, 1)
        )
        Soat.objects.create(soat="S1-SURA", moto=moto, fecha_soat=date(3017, 7, 21), fecha_venc_soat=date(2018, 7, 21))
        moto.fecha_soat = date(2025, 4, 3)
        moto.fecha_venc_soat = date(2426, 4, 3)
        moto.save()

        self._ejecutar()

        assert Contacto.objects.get(nip="31F").contactar_cumpleanos is False
        assert Contacto.objects.get(nip="31A").contactar_cumpleanos is False
        assert Contacto.objects.get(nip="OK1").contactar_cumpleanos is True
        assert Revision.objects.get(certificado="R1").fecha_venc_certificado == date(2027, 2, 14)
        # Insalvable: se conserva el dato original para trazabilidad (la API lo expone como null).
        assert Revision.objects.get(certificado="R2").fecha_certificado == date(3196, 5, 1)
        assert Soat.objects.get(soat="S1-SURA").fecha_soat == date(2017, 7, 21)
        moto.refresh_from_db()
        assert moto.fecha_venc_soat == date(2026, 4, 3)

    def test_permite_reactivar_manualmente(self, api_usuario: ClienteApi) -> None:
        Contacto.objects.create(nip="31F", nombre="FEBRERO TREINTA Y UNO", dia_nac=31, mes_nac=2)
        self._ejecutar()
        respuesta = api_usuario.patch(
            "/api/v1/contactos/31F", {"dia_nac": 28, "mes_nac": 2, "contactar_cumpleanos": True}
        )
        assert respuesta.status_code == 200, respuesta.json()
        assert respuesta.json()["contactar_cumpleanos"] is True
