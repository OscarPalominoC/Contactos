"""Importador del legado: parser, normalizadores, conteos exactos, idempotencia y cuentas temporales."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.comun import normalizacion as n
from apps.comun.legado import filas_de_tabla, reparar_texto
from apps.comun.models import ImportacionRechazo
from apps.contactos.models import Contacto
from apps.cuentas.models import Ingreso, Usuario
from apps.llamadas.models import LlamadaCumpleanos, LlamadaRtm, LlamadaSoat
from apps.revisiones.models import Revision, Soat
from apps.vehiculos.models import Linea, Marca, Moto
from tests.fabricas_dump import volcado_mysql

BOGOTA = ZoneInfo("America/Bogota")

DUMP_SINTETICO = """-- MySQL dump
INSERT INTO `marca` VALUES ('HO','HONDA'),('YA','YAMAHA');
INSERT INTO `linea` VALUES ('XR 190L','HO'),('XR 190L','YA'),('FZ','YA');
INSERT INTO `contacto` VALUES ('100','PE\xd1A L\xd3PEZ ANA','0','300',15,'Febrero','ND','ND','OP','habilitado','2026-11-06 13:56:15',1),('200','O\\'BRIEN, JUAN','601','0',0,'ND','CRA 1','A@B.CO','OP',NULL,NULL,NULL);
INSERT INTO `moto` VALUES ('ABC12D','HONDA','2024','XR 190L','0','0000-00-00','15/03/2027','100','0','2026-03-15','0000-00-00'),('ZZZ99Z','YAMAHA','2020','FZ','0','','','999','0','','');
INSERT INTO `revision` VALUES (NULL,'C1',NULL,NULL,'2026-11-06','2027-11-06','ABC12D','0','1','C1','2026-11-06','VIGENTE','2026-11-06 17:57:05','OP'),(NULL,'C2',NULL,NULL,'2020-01-01','2021-01-01','ABC12D','0','1','C2','2020-01-01',NULL,NULL,'OP');
INSERT INTO `soat1` VALUES ('9-MUNDIAL','2026-11-07','2027-11-07','ABC12D','VIGENTE','OP','2026-11-07 12:42:17'),('8-SURA','2025-01-01','2026-01-01','','VENCIDO','OP','2025-01-01 10:00:00');
INSERT INTO `bitacora_llamadas` VALUES (1,'2026-11-07 00:00:00','norealizada','nd','100','cumplea\xf1os','OP','1'),(2,'2026-11-07 00:00:00','no realizada','LINEA 1\\r\\nLINEA 2','100','cumplea\xf1os','OP','2 ; 2026-11-07 09:00:00 ; 2026-11-07 10:00:00'),(3,'2026-11-07 00:00:00',' ','','100','cumplea\xf1os','OP','');
INSERT INTO `bitacora_llamadas_rtmyg` VALUES ('ABC12D.2026-11-08','2026-11-08','realizada',' NO CONTESTA \\r\\n NO CONTESTA','ABC12D','rtmyg','OP','2','2026-11-06 16:02:39 ; 2026-11-06 16:39:35'),('ABC12D.','0000-00-00','realizada','X','ABC12D','rtmyg','OP','1','');
INSERT INTO `bitacora_llamadas_soat` VALUES ('ABC12D.2026-11-08','2026-11-08','realizadasinexito','X','ABC12D','soat','OP','2026-11-06 17:15:08','1');
INSERT INTO `entrada_sistema` VALUES (1,'08:09:47 AM, 07 / 11 / 2026','100'),(2,'12:30:00 PM, 07 / 11 / 2026','100'),(3,'roto','100');
INSERT INTO `usuario` VALUES ('100','ANA','clave-legada-que-no-se-usa','usuario');
"""


@pytest.fixture
def dump(tmp_path: Path) -> Path:
    ruta = tmp_path / "legado.sql"
    ruta.write_bytes(volcado_mysql(DUMP_SINTETICO).encode("latin-1"))
    return ruta


class TestParser:
    def test_valores_comillas_escapes_y_null(self, dump: Path) -> None:
        filas = list(filas_de_tabla(dump, "contacto"))
        assert len(filas) == 2
        assert filas[0][1] == "PEÑA LÓPEZ ANA"
        assert filas[1][1] == "O'BRIEN, JUAN"
        assert filas[1][9] is None
        assert list(filas_de_tabla(dump, "bitacora_llamadas"))[1][3] == "LINEA 1\r\nLINEA 2"

    def test_tabla_inexistente(self, dump: Path) -> None:
        assert list(filas_de_tabla(dump, "no_existe")) == []

    def test_caracter_inesperado(self, tmp_path: Path) -> None:
        ruta = tmp_path / "malo.sql"
        ruta.write_text("INSERT INTO `marca` VALUES ('A','B')X;\n", encoding="latin-1")
        with pytest.raises(ValueError, match="inesperado"):
            list(filas_de_tabla(ruta, "marca"))

    def test_comilla_doble_sql(self, tmp_path: Path) -> None:
        ruta = tmp_path / "comilla.sql"
        ruta.write_text("INSERT INTO `marca` VALUES ('A''B','C');\n", encoding="latin-1")
        assert list(filas_de_tabla(ruta, "marca")) == [["A'B", "C"]]

    def test_reparar_mojibake(self) -> None:
        assert reparar_texto("PEÃ\x91A") == "PEÑA"
        assert reparar_texto("PEÑA") == "PEÑA"
        assert reparar_texto("Ã") == "Ã"


class TestNormalizadores:
    @pytest.mark.parametrize(
        "valor,esperado",
        [
            ("2026-11-07", date(2026, 11, 7)),
            ("15/03/2027", date(2027, 3, 15)),
            ("01-02-2020", date(2020, 2, 1)),
            ("0000-00-00", None),
            ("", None),
            (None, None),
            ("1900-01-01", None),
            ("<NA>", None),
        ],
    )
    def test_fecha(self, valor: str | None, esperado: date | None) -> None:
        assert n.fecha(valor) == esperado

    def test_fecha_hora(self) -> None:
        assert n.fecha_hora("2026-11-07 10:20:30") == datetime(2026, 11, 7, 10, 20, 30, tzinfo=BOGOTA)
        assert n.fecha_hora("2026-11-07") == datetime(2026, 11, 7, tzinfo=BOGOTA)
        assert n.fecha_hora("0000-00-00 00:00:00") is None
        assert n.fecha_hora("basura") is None

    def test_fecha_entrada_sistema(self) -> None:
        assert n.fecha_entrada_sistema("08:09:47 AM, 07 / 11 / 2026") == datetime(2026, 11, 7, 8, 9, 47, tzinfo=BOGOTA)
        assert n.fecha_entrada_sistema("12:30:00 PM, 07 / 11 / 2026").hour == 12  # type: ignore[union-attr]
        assert n.fecha_entrada_sistema("12:05:00 AM, 07 / 11 / 2026").hour == 0  # type: ignore[union-attr]
        assert n.fecha_entrada_sistema("01:00:00 AM, 31 / 02 / 2026") is None
        assert n.fecha_entrada_sistema("roto") is None

    @pytest.mark.parametrize(
        "valor,esperado", [("Febrero", 2), ("febrero", 2), ("JULIO ", 7), ("ND", None), ("No", None)]
    )
    def test_mes(self, valor: str, esperado: int | None) -> None:
        assert n.mes(valor) == esperado

    def test_varios(self) -> None:
        assert n.dia("15") == 15
        assert n.dia("0") is None
        assert n.dia("x") is None
        assert n.estado_llamada("no realizada") == "no_realizada"
        assert n.estado_llamada(" ") == "sin_estado"
        assert n.estado_contacto(None) == "habilitado"
        assert n.estado_documento(None) == "VENCIDO"
        assert n.estado_documento("duplicado") == "DUPLICADO"
        assert n.entero("x", 7) == 7
        assert n.placa(" abc-12d ") == "ABC12D"
        assert n.intentos_llamada("2 ; 2026-11-07 09:00:00") == (2, "2026-11-07 09:00:00")
        assert n.intentos_llamada("2026-11-07 09:00:00") == (None, "2026-11-07 09:00:00")
        assert n.texto_multilinea(" A \r\n\r\n B ") == "A\nB"
        assert n.texto_multilinea(None) == ""


@pytest.mark.django_db
class TestComandoImportar:
    def test_conteos_exactos_e_idempotencia(self, dump: Path, tmp_path: Path) -> None:
        informe = tmp_path / "informe.md"
        for _ in range(2):
            call_command("importar_legado", str(dump), informe=informe)
        assert Marca.objects.count() == 2
        assert Linea.objects.count() == 2
        assert Contacto.objects.count() == 2
        assert Moto.objects.count() == 2
        assert Revision.objects.count() == 2
        assert Soat.objects.count() == 2
        assert LlamadaCumpleanos.objects.count() == 3
        assert LlamadaRtm.objects.count() == 1
        assert LlamadaSoat.objects.count() == 1
        assert Ingreso.objects.count() == 2
        assert ImportacionRechazo.objects.count() == 3
        texto = informe.read_text(encoding="utf-8")
        assert "| contacto | 2 | 2 | 0 | 0 | 0 | Sí |" in texto
        assert "motos sin contacto: 1" in texto
        assert "100" not in texto.split("## Huérfanos")[0].split("|---|")[1].replace("| 100", "")

    def test_normalizacion_aplicada(self, dump: Path, tmp_path: Path) -> None:
        call_command("importar_legado", str(dump), informe=tmp_path / "i.md")
        ana = Contacto.objects.get(nip="100")
        assert ana.nombre == "PEÑA LÓPEZ ANA"
        assert ana.mes_nac == 2 and ana.dia_nac == 15
        assert ana.direccion == "" and ana.correo == "" and ana.telefono == ""
        assert ana.cumple_confir is True
        juan = Contacto.objects.get(nip="200")
        assert juan.estado == "habilitado" and juan.correo == "a@b.co" and juan.dia_nac is None
        moto = Moto.objects.get(placa="ABC12D")
        assert moto.fecha_venc_soat is None
        assert moto.fecha_venc_rtmg == date(2027, 3, 15)
        assert Revision.objects.get(certificado="C2").estado == "VENCIDO"
        assert Soat.objects.get(soat="8-SURA").moto_id is None
        estados = sorted(LlamadaCumpleanos.objects.values_list("estado", flat=True))
        assert estados == ["no_realizada", "no_realizada", "sin_estado"]
        segunda = LlamadaCumpleanos.objects.get(id=2)
        assert segunda.observacion == "LINEA 1\nLINEA 2"
        assert segunda.num_llamadas == 2
        assert LlamadaCumpleanos.objects.get(id=1).observacion == ""
        rtm = LlamadaRtm.objects.get()
        assert rtm.observacion == "NO CONTESTA\nNO CONTESTA" and rtm.num_llamadas == 2
        assert LlamadaSoat.objects.get().estado == "realizada_sin_exito"
        nueva = LlamadaCumpleanos.objects.create(fecha=datetime(2026, 1, 1, tzinfo=BOGOTA), contacto_id="100")
        assert nueva.id == 4

    def test_solo_algunas_tablas(self, dump: Path, tmp_path: Path) -> None:
        call_command("importar_legado", str(dump), tablas=["marca"], informe=tmp_path / "i.md")
        assert Marca.objects.count() == 2
        assert Contacto.objects.count() == 0

    def test_archivo_inexistente(self, tmp_path: Path) -> None:
        with pytest.raises(CommandError):
            call_command("importar_legado", str(tmp_path / "no.sql"))

    def test_columnas_incorrectas_van_a_rechazos(self, tmp_path: Path) -> None:
        ruta = tmp_path / "corto.sql"
        ruta.write_text(volcado_mysql("INSERT INTO `marca` VALUES ('A'),('','X');\n"), encoding="latin-1")
        call_command("importar_legado", str(ruta), tablas=["marca"], informe=tmp_path / "i.md")
        motivos = sorted(ImportacionRechazo.objects.values_list("motivo", flat=True))
        assert motivos == ["código vacío", "se esperaban 2 columnas y llegaron 1"]


@pytest.mark.django_db
def test_crear_cuentas_temporales(tmp_path: Path, grupos: Any) -> None:
    archivo = tmp_path / "credenciales.json"
    archivo.write_text(
        json.dumps(
            [
                {"nip": "100", "nombre": "ANA", "tipo": "administrador", "clave_temporal": "Tmp-Clave-0001-Ab"},
                {"nip": "200", "nombre": "LUIS", "tipo": "desconocido", "clave_temporal": "Tmp-Clave-0002-Cd"},
            ]
        ),
        encoding="utf-8",
    )
    call_command("crear_cuentas_temporales", str(archivo), conservar_archivo=True)
    assert archivo.exists()
    call_command("crear_cuentas_temporales", str(archivo))
    assert not archivo.exists()
    ana = Usuario.objects.get(nip="100")
    assert ana.check_password("Tmp-Clave-0001-Ab")
    assert ana.password.startswith("argon2")
    assert ana.debe_cambiar_clave and ana.is_staff
    assert Usuario.objects.get(nip="200").rol == "usuario"
    with pytest.raises(CommandError):
        call_command("crear_cuentas_temporales", str(archivo))


@pytest.mark.django_db
def test_importar_aplica_saneamiento_de_fechas(tmp_path: Path) -> None:
    """En una BD nueva el entrypoint migra antes de importar: el importador debe sanear por sí mismo."""
    ruta = tmp_path / "legado.sql"
    ruta.write_bytes(
        volcado_mysql(
            "INSERT INTO `contacto` VALUES ('31F','FEBRERO','0','300',31,'Febrero','ND','ND','OP','habilitado',NULL,0),"
            "('OK1','VALIDO','0','300',10,'Marzo','ND','ND','OP','habilitado',NULL,0);\n"
            "INSERT INTO `moto` VALUES ('MYC04D','HONDA','2017','','0','2017-07-21','2018-07-21','31F','0','','');\n"
            "INSERT INTO `soat1` VALUES ('1318-SURA','3017-07-21','2018-07-21','MYC04D','VIGENTE','OP',NULL);\n"
        ).encode("latin-1")
    )
    call_command("importar_legado", str(ruta), tablas=["contacto", "moto", "soat1"], informe=tmp_path / "i.md")
    assert Contacto.objects.get(nip="31F").contactar_cumpleanos is False
    assert Contacto.objects.get(nip="OK1").contactar_cumpleanos is True
    assert Soat.objects.get(soat="1318-SURA").fecha_soat == date(2017, 7, 21)


def _escribir(tmp_path: Path, inserts: str, **opciones: Any) -> Path:
    ruta = tmp_path / "v.sql"
    ruta.write_bytes(volcado_mysql(inserts, **opciones).encode("latin-1"))
    return ruta


@pytest.mark.django_db
class TestImportacionSegura:
    def test_fallo_a_mitad_no_modifica_datos(self, tmp_path: Path) -> None:
        Contacto.objects.create(nip="OLD", nombre="VIEJO")
        Moto.objects.create(placa="OLD1", contacto_id="OLD")
        antes = ImportacionRechazo.objects.count()
        ruta = _escribir(
            tmp_path,
            "INSERT INTO `marca` VALUES ('HO','HONDA');\n"
            "INSERT INTO `contacto` VALUES ('100','ANA','0','300',15,'Febrero','ND','ND','OP','habilitado',NULL,0);\n"
            "INSERT INTO `revision` VALUES (NULL,'C1'\n",
        )
        with pytest.raises(CommandError) as error:
            call_command("importar_legado", str(ruta), informe=tmp_path / "i.md")
        assert str(error.value) == (
            "El volcado tiene datos ilegibles en la tabla `revision`; no se modificó la base de datos."
        )
        assert Contacto.objects.filter(nip="OLD").exists()
        assert Moto.objects.count() == 1
        assert Marca.objects.count() == 0
        assert ImportacionRechazo.objects.count() == antes

    def test_error_inesperado_no_expone_valores(self, dump: Path, tmp_path: Path) -> None:
        from unittest.mock import patch

        with (
            patch(IMPORTAR + ".importar_tabla", side_effect=RuntimeError("fila con NIP 100 y placa ABC12D")),
            pytest.raises(CommandError) as error,
        ):
            call_command("importar_legado", str(dump), informe=tmp_path / "i.md")
        mensaje = str(error.value)
        assert mensaje == "No se pudo importar el volcado (RuntimeError); no se modificó la base de datos."
        assert "100" not in mensaje and "ABC12D" not in mensaje

    def test_cuadre_fallido_deja_informe_y_revierte(self, dump: Path, tmp_path: Path) -> None:
        from unittest.mock import patch

        from apps.comun.management.commands import importar_legado as modulo

        real = modulo.importar_tabla

        def descuadrada(ruta: Path, tabla: Any) -> Any:
            resultado = real(ruta, tabla)
            if tabla.legada == "marca":
                resultado.origen += 1
            return resultado

        Contacto.objects.create(nip="OLD", nombre="VIEJO")
        informe = tmp_path / "i.md"
        with patch(IMPORTAR + ".importar_tabla", side_effect=descuadrada), pytest.raises(CommandError, match="cuadran"):
            call_command("importar_legado", str(dump), informe=informe)
        texto = informe.read_text(encoding="utf-8")
        assert texto.index("IMPORTACIÓN REVERTIDA: hay tablas que no cuadran") < texto.index("| Tabla legada")
        assert "| marca | 3 | 2 | 0 | 0 | 0 | NO |" in texto
        assert Contacto.objects.filter(nip="OLD").exists()
        assert Marca.objects.count() == 0

    def test_importar_dump_reutiliza_analisis(self, dump: Path) -> None:
        from unittest.mock import patch

        from apps.comun.analisis_dump import analizar_dump
        from apps.comun.management.commands.importar_legado import importar_dump

        analisis = analizar_dump(dump)
        with patch("apps.comun.analisis_dump.analizar_dump") as mock_analizar:
            importar_dump(dump, importar_usuarios=False, analisis=analisis)
        assert not mock_analizar.called
        assert Marca.objects.count() == 2

    def test_volcado_invalido_no_borra_nada(self, tmp_path: Path) -> None:
        Contacto.objects.create(nip="OLD", nombre="VIEJO")
        ruta = _escribir(tmp_path, "INSERT INTO `marca` VALUES ('HO','HONDA');\n", omitir={"contacto"})
        with pytest.raises(CommandError, match="Falta la tabla"):
            call_command("importar_legado", str(ruta), informe=tmp_path / "i.md")
        assert Contacto.objects.filter(nip="OLD").exists()

    def test_texto_largo_se_recorta(self, tmp_path: Path) -> None:
        larga = "X" * 600
        ruta = _escribir(
            tmp_path,
            f"INSERT INTO `contacto` VALUES ('100','ANA','0','300',15,'Febrero','{larga}','ND','OP','habilitado',NULL,0);\n",  # noqa: S608
        )
        informe = tmp_path / "i.md"
        call_command("importar_legado", str(ruta), tablas=["contacto"], informe=informe)
        maximo = Contacto._meta.get_field("direccion").max_length
        assert len(Contacto.objects.get(nip="100").direccion) == maximo
        assert "direccion recortado a" in informe.read_text(encoding="utf-8")

    def test_pk_larga_se_rechaza(self, tmp_path: Path) -> None:
        ruta = _escribir(tmp_path, f"INSERT INTO `marca` VALUES ('{'M' * 60}','X');\n")  # noqa: S608
        call_command("importar_legado", str(ruta), tablas=["marca"], informe=tmp_path / "i.md")
        rechazo = ImportacionRechazo.objects.get()
        assert "excede" in rechazo.motivo
        assert Marca.objects.count() == 0

    def test_al_avanzar_recibe_cada_tabla(self, dump: Path) -> None:
        from apps.comun.management.commands.importar_legado import importar_dump

        registro: list[tuple[str, int, int]] = []
        importar_dump(dump, al_avanzar=lambda t, i, total: registro.append((t, i, total)))
        assert len(registro) == 10
        assert registro[-1] == ("entrada_sistema", 10, 10)


CLAVE_INICIAL = "Temporal#2026x"
IMPORTAR = "apps.comun.management.commands.importar_legado"


@pytest.mark.django_db
class TestImportacionUsuarios:
    @pytest.fixture(autouse=True)
    def _clave_inicial(self, settings: Any) -> None:
        settings.CLAVE_TEMPORAL_INICIAL = CLAVE_INICIAL

    def test_importa_usuarios_con_clave_temporal_inicial(self, dump: Path, tmp_path: Path, grupos: Any) -> None:
        informe = tmp_path / "i.md"
        call_command("importar_legado", str(dump), informe=informe)
        u = Usuario.objects.get(nip="100")
        assert u.check_password(CLAVE_INICIAL)
        assert not u.check_password("clave-legada-que-no-se-usa")
        assert u.debe_cambiar_clave
        assert u.rol == "usuario"
        assert u.nombre == "ANA"
        assert "| usuario | 1 | 1 | 0 | 0 | 0 | Sí |" in informe.read_text(encoding="utf-8")

    def test_no_modifica_usuario_existente(self, dump: Path, tmp_path: Path, grupos: Any) -> None:
        Usuario.objects.create_user("100", "ADMIN", "Actual#2026xx", rol="administrador")
        informe = tmp_path / "i.md"
        call_command("importar_legado", str(dump), informe=informe)
        u = Usuario.objects.get(nip="100")
        assert u.check_password("Actual#2026xx")
        assert u.rol == "administrador"
        assert u.nombre == "ADMIN"
        assert "| usuario | 1 | 0 | 0 | 0 | 1 | Sí |" in informe.read_text(encoding="utf-8")

    def test_tipo_desconocido_mapea_a_usuario(self, tmp_path: Path, grupos: Any) -> None:
        ruta = _escribir(
            tmp_path, "INSERT INTO `usuario` VALUES ('300','LUIS','x','gerente'),('400','EVA','x','Administrador');\n"
        )
        informe = tmp_path / "i.md"
        call_command("importar_legado", str(ruta), informe=informe)
        assert Usuario.objects.get(nip="300").rol == "usuario"
        assert Usuario.objects.get(nip="400").rol == "administrador"
        assert Usuario.objects.get(nip="300").is_active
        assert not Usuario.objects.get(nip="400").is_active
        assert "usuario: tipo 'gerente' → usuario (1)" in informe.read_text(encoding="utf-8")

    def test_sin_clave_temporal_no_crea_usuarios(self, dump: Path, tmp_path: Path, grupos: Any, settings: Any) -> None:
        settings.CLAVE_TEMPORAL_INICIAL = ""
        informe = tmp_path / "i.md"
        call_command("importar_legado", str(dump), informe=informe)
        assert not Usuario.objects.filter(nip="100").exists()
        assert Contacto.objects.count() == 2
        texto = informe.read_text(encoding="utf-8")
        assert "CLAVE_TEMPORAL_INICIAL no configurada" in texto
        assert "| usuario | 1 | 0 | 0 | 0 | 1 | Sí |" in texto

    def test_sin_usuarios_flag(self, dump: Path, tmp_path: Path, grupos: Any) -> None:
        call_command("importar_legado", str(dump), "--sin-usuarios", informe=tmp_path / "i.md")
        assert not Usuario.objects.filter(nip="100").exists()
        assert Contacto.objects.count() == 2

    def test_nip_vacio_o_largo_se_rechaza_sin_la_clave(self, tmp_path: Path, grupos: Any) -> None:
        ruta = _escribir(
            tmp_path,
            f"INSERT INTO `usuario` VALUES ('','SIN NIP','SECRETO-LEGADO','usuario'),('{'9' * 21}','LARGO','SECRETO-LEGADO','usuario');\n",  # noqa: S608
        )
        informe = tmp_path / "i.md"
        call_command("importar_legado", str(ruta), informe=informe)
        rechazos = list(ImportacionRechazo.objects.filter(tabla="usuario"))
        assert len(rechazos) == 2
        assert all("SECRETO-LEGADO" not in r.fila_origen for r in rechazos)
        assert "SECRETO-LEGADO" not in informe.read_text(encoding="utf-8")
        assert Usuario.objects.count() == 0

    def test_reimportar_no_duplica_rechazos(self, tmp_path: Path, grupos: Any) -> None:
        ruta = _escribir(tmp_path, "INSERT INTO `usuario` VALUES ('','SIN NIP','x','usuario');\n")
        for _ in range(2):
            call_command("importar_legado", str(ruta), informe=tmp_path / "i.md")
        assert ImportacionRechazo.objects.filter(tabla="usuario").count() == 1

    def test_admin_legado_se_crea_inactivo(self, tmp_path: Path, grupos: Any) -> None:
        ruta = _escribir(
            tmp_path,
            "INSERT INTO `usuario` VALUES ('01','PRUEBA','x',' Administrador '),('7','OPERADOR','x','usuario');\n",
        )
        informe = tmp_path / "i.md"
        call_command("importar_legado", str(ruta), informe=informe)
        admin = Usuario.objects.get(nip="01")
        assert admin.rol == "administrador"
        assert not admin.is_active
        assert admin.check_password(CLAVE_INICIAL)
        assert Usuario.objects.get(nip="7").is_active
        assert "usuario: administrador legado creado inactivo (1)" in informe.read_text(encoding="utf-8")

    def test_clave_publica_por_defecto_crea_usuarios_y_lo_advierte(
        self, tmp_path: Path, grupos: Any, settings: Any
    ) -> None:
        settings.CLAVE_TEMPORAL_INICIAL = f"  {settings.CLAVE_TEMPORAL_PUBLICA} "
        ruta = _escribir(
            tmp_path,
            "INSERT INTO `usuario` VALUES ('01','PRUEBA','x','administrador'),('7','OPERADOR','x','usuario');\n",
        )
        informe = tmp_path / "i.md"
        call_command("importar_legado", str(ruta), informe=informe)
        operador = Usuario.objects.get(nip="7")
        assert operador.is_active and operador.check_password(settings.CLAVE_TEMPORAL_PUBLICA)
        assert operador.debe_cambiar_clave
        assert not Usuario.objects.get(nip="01").is_active
        texto = informe.read_text(encoding="utf-8")
        assert "CLAVE_TEMPORAL_INICIAL es la clave pública por defecto: cámbiela en backend/.env (1)" in texto
        assert "| usuario | 2 | 2 | 0 | 0 | 0 | Sí |" in texto
