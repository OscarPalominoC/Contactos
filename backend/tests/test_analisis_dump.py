"""Compuerta de análisis: solo pasan respaldos completos y volcados MySQL con la estructura esperada."""

from pathlib import Path

import pytest

from apps.comun.analisis_dump import analizar_dump
from tests.fabricas_dump import volcado_mysql, volcado_postgres

DOS_CONTACTOS = (
    "INSERT INTO `contacto` VALUES ('1','A','0','3',1,'Enero','x','y','OP',NULL,NULL,1),"
    "('2','B','0','3',1,'Enero','x','y','OP',NULL,NULL,1);\n"
)
ADMINS = "INSERT INTO `usuario` VALUES ('01','A','secreta','administrador'),('5000','B','otra','administrador'),('7','C','z','usuario');\n"


def _escribir(tmp_path: Path, texto: str) -> Path:
    ruta = tmp_path / "volcado.sql"
    ruta.write_bytes(texto.encode("latin-1"))
    return ruta


def test_volcado_mysql_valido(tmp_path: Path) -> None:
    informe = analizar_dump(_escribir(tmp_path, volcado_mysql(DOS_CONTACTOS)))
    assert informe.valido
    assert informe.tipo == "mysql_legado"
    assert informe.tablas["contacto"].filas_aprox == 2


def test_volcado_sin_marca_final_es_invalido(tmp_path: Path) -> None:
    informe = analizar_dump(_escribir(tmp_path, volcado_mysql(DOS_CONTACTOS, completo=False)))
    assert not informe.valido
    assert any("incompleto" in e for e in informe.errores)


def test_falta_tabla_requerida(tmp_path: Path) -> None:
    informe = analizar_dump(_escribir(tmp_path, volcado_mysql("", omitir={"contacto"})))
    assert not informe.valido
    assert any("`contacto`" in e for e in informe.errores)


def test_columnas_distintas(tmp_path: Path) -> None:
    informe = analizar_dump(_escribir(tmp_path, volcado_mysql("", columnas={"moto": 10})))
    assert not informe.valido
    assert any("10 columnas; se esperaban 11" in e for e in informe.errores)


def test_advierte_admins_legados(tmp_path: Path) -> None:
    informe = analizar_dump(_escribir(tmp_path, volcado_mysql(ADMINS)))
    assert informe.usuarios == 3
    assert informe.usuarios_admin == 2
    assert any("2 cuentas con rol administrador" in a for a in informe.advertencias)


def test_tabla_requerida_vacia_advierte(tmp_path: Path) -> None:
    informe = analizar_dump(_escribir(tmp_path, volcado_mysql(DOS_CONTACTOS)))
    assert informe.valido
    assert any("`marca` está vacía" in a for a in informe.advertencias)


def test_usuario_con_columnas_distintas_es_invalido(tmp_path: Path) -> None:
    texto = (
        volcado_mysql("", con_usuario=False) + "CREATE TABLE `usuario` (\n  `nip` int,\n  `x` int\n) ENGINE=MyISAM;\n"
    )
    informe = analizar_dump(_escribir(tmp_path, texto))
    assert not informe.valido


def test_tablas_no_soportadas_advierten_una_vez(tmp_path: Path) -> None:
    texto = volcado_mysql("") + "CREATE TABLE `abono` (\n  `id` int\n) ENGINE=MyISAM;\n"
    informe = analizar_dump(_escribir(tmp_path, texto))
    assert [a for a in informe.advertencias if "no se importan" in a] == [
        "1 tablas del sistema anterior no se importan."
    ]


def test_postgres_propio_valido(tmp_path: Path) -> None:
    informe = analizar_dump(_escribir(tmp_path, volcado_postgres()))
    assert informe.valido
    assert informe.tipo == "postgres_check"


def test_postgres_ajeno_invalido(tmp_path: Path) -> None:
    texto = volcado_postgres().replace("public.cuentas_usuario", "public.otra")
    informe = analizar_dump(_escribir(tmp_path, texto))
    assert not informe.valido
    assert informe.errores == ["No es un respaldo completo de Check Contactos."]


def test_sql_arbitrario_desconocido(tmp_path: Path) -> None:
    informe = analizar_dump(_escribir(tmp_path, "DROP TABLE cuentas_usuario;"))
    assert informe.tipo == "desconocido"
    assert not informe.valido


@pytest.mark.skipif(not Path("../CONTACTOS2026-11-07.sql").exists(), reason="no hay volcado real")
def test_dump_real_es_valido() -> None:
    informe = analizar_dump(Path("../CONTACTOS2026-11-07.sql"))
    assert informe.valido, informe.errores
    assert len(informe.tablas) == 62
    assert informe.usuarios == 23
    assert informe.usuarios_admin == 5


def test_usuario_mal_estructurado_con_inserts_informa_sin_fallar(tmp_path: Path) -> None:
    texto = (
        volcado_mysql("", con_usuario=False)  # noqa: S608
        + "CREATE TABLE `usuario` (\n  `nip` int,\n  `x` int\n) ENGINE=MyISAM;\n"
        + "INSERT INTO `usuario` VALUES ('1','a'),('2','b');\n"
    )
    informe = analizar_dump(_escribir(tmp_path, texto))
    assert not informe.valido
    assert any("`usuario`" in e for e in informe.errores)


@pytest.mark.parametrize(
    "insert", ["INSERT INTO `usuario` VALUES ('1','a','b','administrador'", "INSERT INTO `usuario` VALUES ('1'"]
)
def test_insert_usuario_malformado_es_error(tmp_path: Path, insert: str) -> None:
    informe = analizar_dump(_escribir(tmp_path, volcado_mysql(insert + "\n")))
    assert not informe.valido


@pytest.mark.parametrize("linea", ["CREATE TABLE `sin_cierre\n", "INSERT INTO `sin_cierre VALUES (1);\n"])
def test_linea_sin_cierre_de_comilla_es_error(tmp_path: Path, linea: str) -> None:
    informe = analizar_dump(_escribir(tmp_path, volcado_mysql(linea)))
    assert not informe.valido
    assert any("malformadas" in e for e in informe.errores)
