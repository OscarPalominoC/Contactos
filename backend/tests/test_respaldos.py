"""Pruebas unitarias y de integración para la funcionalidad de respaldos de base de datos."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.comun.servicios_respaldo import (
    ARCHIVO_CONFIG_RESPALDO,
    ARCHIVO_ESTADO_RESPALDO,
    es_cliente_servidor_local,
    es_ruta_absoluta,
    formatear_tamano,
    generar_nombre_archivo_respaldo,
    guardar_ruta_respaldo,
    mapear_ruta_windows_a_posix,
    obtener_estado_respaldo,
    obtener_ruta_respaldo,
    resolver_ruta_sistema,
    validar_ruta_servidor,
)
from apps.cuentas.models import Usuario
from tests.conftest import ClienteApi, crear_usuario
from tests.fabricas_dump import volcado_mysql, volcado_postgres
from tests.test_importacion import DUMP_SINTETICO

pytestmark = pytest.mark.django_db

ESTADO_URL = "/api/v1/respaldos/estado"
ES_SERVIDOR_URL = "/api/v1/respaldos/es-servidor"
VALIDAR_URL = "/api/v1/respaldos/validar-ruta"
CONFIGURAR_URL = "/api/v1/respaldos/configurar-ruta"
EJECUTAR_URL = "/api/v1/respaldos/ejecutar"
EXPLORAR_URL = "/api/v1/respaldos/explorar"
RESTAURAR_URL = "/api/v1/respaldos/restaurar"
SUBIR_URL = "/api/v1/respaldos/subir"
ANALIZAR_URL = "/api/v1/respaldos/analizar"


@pytest.fixture(autouse=True)
def limpiar_archivos_test():
    """Limpia los archivos de configuración y estado antes y después de cada prueba."""
    if ARCHIVO_ESTADO_RESPALDO.exists():
        ARCHIVO_ESTADO_RESPALDO.unlink(missing_ok=True)
    yield
    if ARCHIVO_ESTADO_RESPALDO.exists():
        ARCHIVO_ESTADO_RESPALDO.unlink(missing_ok=True)


def test_formatear_tamano():
    assert formatear_tamano(500) == "500 B"
    assert formatear_tamano(2048) == "2.0 KB"
    assert formatear_tamano(5 * 1024 * 1024) == "5.0 MB"
    assert formatear_tamano(2 * 1024 * 1024 * 1024) == "2.00 GB"


def test_es_ruta_absoluta():
    # Rutas Windows
    assert es_ruta_absoluta(r"F:\Prueba") is True
    assert es_ruta_absoluta(r"F:\Check\respaldos") is True
    assert es_ruta_absoluta(r"C:\Backups") is True
    assert es_ruta_absoluta("d:/datos/respaldos") is True
    assert es_ruta_absoluta(r"\\servidor\compartido") is True

    # Rutas POSIX
    assert es_ruta_absoluta("/app/respaldos") is True
    assert es_ruta_absoluta("/data/respaldos") is True

    # Rutas relativas o vacías
    assert es_ruta_absoluta("carpeta_relativa") is False
    assert es_ruta_absoluta("./subcarpeta") is False
    assert es_ruta_absoluta("") is False


def test_resolver_ruta_sistema_windows_y_posix():
    # En cualquier OS, una ruta POSIX se resuelve como Path POSIX o WindowsPath según el SO
    ruta_posix = resolver_ruta_sistema("/data/respaldos")
    assert "data" in str(ruta_posix) and "respaldos" in str(ruta_posix)

    # Verificación de mapeo entre Windows y contenedor Docker Linux
    assert mapear_ruta_windows_a_posix(r"F:\Prueba") == "/mnt/f/Prueba"
    assert mapear_ruta_windows_a_posix(r"F:\Check\respaldos") == "/mnt/f/Check/respaldos"
    assert mapear_ruta_windows_a_posix(r"C:\Backups") == "/mnt/c/Backups"
    assert mapear_ruta_windows_a_posix("/data/respaldos") == "/data/respaldos"


def test_validar_ruta_servidor(tmp_path: Path):
    # Ruta vacía
    valida, mensaje, ruta = validar_ruta_servidor("")
    assert valida is False
    assert "no puede estar vacía" in mensaje

    # Ruta relativa
    valida, mensaje, ruta = validar_ruta_servidor("carpeta_relativa")
    assert valida is False
    assert "debe ser absoluta" in mensaje

    # Carpeta que no existe con crear_si_no_existe=False
    no_existe = tmp_path / "carpeta_fantasma"
    valida, mensaje, ruta = validar_ruta_servidor(str(no_existe), crear_si_no_existe=False)
    assert valida is False
    assert "no existe" in mensaje

    # Carpeta que no existe con crear_si_no_existe=True (la crea y valida)
    carpeta_nueva = tmp_path / "nueva_carpeta_respaldos"
    assert not carpeta_nueva.exists()
    valida, mensaje, ruta = validar_ruta_servidor(str(carpeta_nueva), crear_si_no_existe=True)
    assert valida is True
    assert carpeta_nueva.exists()
    assert ruta == carpeta_nueva.resolve()

    # Carpeta existente válida
    valida, mensaje, ruta = validar_ruta_servidor(str(tmp_path))
    assert valida is True
    assert ruta == tmp_path.resolve()


def test_guardar_y_obtener_ruta_respaldo(tmp_path: Path):
    guardada = guardar_ruta_respaldo(str(tmp_path))
    assert guardada == str(tmp_path)
    assert obtener_ruta_respaldo() == tmp_path.resolve()


def test_estado_requiere_administrador(api_usuario: ClienteApi):
    # Usuario normal no administrador -> 403
    resp = api_usuario.get(ESTADO_URL)
    assert resp.status_code == 403


def test_estado_consulta_correcta_admin(api_admin: ClienteApi):
    resp = api_admin.get(ESTADO_URL, REMOTE_ADDR="127.0.0.1")
    assert resp.status_code == 200
    assert resp.data["es_servidor_local"] is True
    assert "ruta_configurada" in resp.data
    assert "ejecutando" in resp.data
    assert resp.data["ejecutando"] is False


def test_estado_detecta_dispositivo_remoto(api_admin: ClienteApi):
    resp = api_admin.get(ESTADO_URL, REMOTE_ADDR="192.168.1.222")
    assert resp.status_code == 200
    assert resp.data["es_servidor_local"] is False


def test_validar_ruta_rechaza_dispositivo_remoto(api_admin: ClienteApi, tmp_path: Path):
    resp = api_admin.post(
        VALIDAR_URL,
        {"ruta": str(tmp_path)},
        REMOTE_ADDR="192.168.1.222",
        HTTP_IDEMPOTENCY_KEY="key-remoto-1",
    )
    assert resp.status_code == 403
    assert "solo puede realizarse directamente desde el equipo servidor" in resp.data["detail"]


def test_validar_ruta_local_exitosa(api_admin: ClienteApi, tmp_path: Path):
    resp = api_admin.post(
        VALIDAR_URL,
        {"ruta": str(tmp_path)},
        REMOTE_ADDR="127.0.0.1",
        HTTP_IDEMPOTENCY_KEY="key-local-val-1",
    )
    assert resp.status_code == 200
    assert resp.data["valida"] is True
    assert resp.data["ruta"] == str(tmp_path)


def test_validar_ruta_local_carpeta_invalida(api_admin: ClienteApi, tmp_path: Path):
    # Archivo en lugar de carpeta
    archivo = tmp_path / "archivo_no_carpeta.txt"
    archivo.write_text("prueba", encoding="utf-8")
    resp = api_admin.post(
        VALIDAR_URL,
        {"ruta": str(archivo)},
        REMOTE_ADDR="127.0.0.1",
        HTTP_IDEMPOTENCY_KEY="key-local-val-2",
    )
    assert resp.status_code == 422
    assert "no corresponde a una carpeta" in resp.data["detail"]

    # Ruta relativa
    resp_rel = api_admin.post(
        VALIDAR_URL,
        {"ruta": "ruta_relativa"},
        REMOTE_ADDR="127.0.0.1",
        HTTP_IDEMPOTENCY_KEY="key-local-val-3",
    )
    assert resp_rel.status_code == 422
    assert "debe ser absoluta" in resp_rel.data["detail"]


def test_configurar_ruta_rechaza_dispositivo_remoto(api_admin: ClienteApi, tmp_path: Path):
    resp = api_admin.post(
        CONFIGURAR_URL,
        {"ruta": str(tmp_path)},
        REMOTE_ADDR="192.168.1.222",
        HTTP_IDEMPOTENCY_KEY="key-remoto-cfg-1",
    )
    assert resp.status_code == 403


def test_configurar_ruta_local_guarda_exitosamente(api_admin: ClienteApi, tmp_path: Path):
    resp = api_admin.post(
        CONFIGURAR_URL,
        {"ruta": str(tmp_path)},
        REMOTE_ADDR="127.0.0.1",
        HTTP_IDEMPOTENCY_KEY="key-local-cfg-1",
    )
    assert resp.status_code == 200
    assert resp.data["ruta_configurada"] == str(tmp_path)
    assert obtener_ruta_respaldo() == tmp_path.resolve()


def test_generar_nombre_archivo_respaldo_nomenclatura_y_colisiones(tmp_path: Path):
    from datetime import datetime

    fecha = datetime(2026, 11, 15, 14, 30)
    # Primer archivo del día
    archivo1 = generar_nombre_archivo_respaldo(tmp_path, "check_contactos", fecha)
    assert archivo1.name == "check_contactos-15-11-2026.sql"

    # Simular que ya existe
    archivo1.write_text("dummy", encoding="utf-8")

    # Segundo archivo del mismo día -> sufijo _01
    archivo2 = generar_nombre_archivo_respaldo(tmp_path, "check_contactos", fecha)
    assert archivo2.name == "check_contactos-15-11-2026_01.sql"

    archivo2.write_text("dummy", encoding="utf-8")

    # Tercer archivo -> sufijo _02
    archivo3 = generar_nombre_archivo_respaldo(tmp_path, "check_contactos", fecha)
    assert archivo3.name == "check_contactos-15-11-2026_02.sql"


def test_es_servidor_endpoint(api_admin: ClienteApi):
    # Desde localhost directo
    resp_local = api_admin.get(ES_SERVIDOR_URL, REMOTE_ADDR="127.0.0.1")
    assert resp_local.status_code == 200
    assert resp_local.data["es_servidor"] is True

    # Detrás de Nginx/Docker en localhost:5174 (Host es 127.0.0.1 o localhost)
    resp_docker_local = api_admin.get(
        ES_SERVIDOR_URL,
        HTTP_HOST="127.0.0.1:5174",
        REMOTE_ADDR="172.19.0.4",
        HTTP_X_FORWARDED_FOR="172.19.0.1",
    )
    assert resp_docker_local.status_code == 200
    assert resp_docker_local.data["es_servidor"] is True

    resp_docker_localhost = api_admin.get(
        ES_SERVIDOR_URL,
        HTTP_HOST="localhost:5174",
        REMOTE_ADDR="172.19.0.4",
        HTTP_X_FORWARDED_FOR="172.19.0.1",
    )
    assert resp_docker_localhost.status_code == 200
    assert resp_docker_localhost.data["es_servidor"] is True

    # Desde IP remota
    resp_remoto = api_admin.get(ES_SERVIDOR_URL, HTTP_HOST="192.168.1.50:5174", REMOTE_ADDR="192.168.1.150")
    assert resp_remoto.status_code == 200
    assert resp_remoto.data["es_servidor"] is False


def test_es_servidor_docker_gateway_con_host_local(api_admin: ClienteApi):
    """TDD RED→GREEN: Cuando el usuario navega en localhost:5174 en el servidor,
    Nginx (dentro del contenedor frontend) reenvía al backend con:
    - Host: localhost:5174 (preservado del navegador)
    - X-Real-IP: 172.19.0.1 (gateway Docker = la máquina host)
    - X-Forwarded-For: 172.19.0.1
    - REMOTE_ADDR: 172.19.0.4 (IP interna del contenedor frontend)
    
    Esto DEBE considerarse local porque:
    1. El Host dice localhost (solo el servidor puede acceder a localhost)
    2. La IP del gateway Docker (172.19.0.0/16) corresponde a la máquina host
    """
    # Escenario 1: Servidor accede via localhost:5174, Nginx reenvia
    resp = api_admin.get(
        ES_SERVIDOR_URL,
        HTTP_HOST="localhost:5174",
        REMOTE_ADDR="172.19.0.4",
        HTTP_X_REAL_IP="172.19.0.1",
        HTTP_X_FORWARDED_FOR="172.19.0.1",
    )
    assert resp.status_code == 200
    assert resp.data["es_servidor"] is True

    # Escenario 2: Servidor accede via 127.0.0.1:5174, Nginx reenvia 
    resp2 = api_admin.get(
        ES_SERVIDOR_URL,
        HTTP_HOST="127.0.0.1:5174",
        REMOTE_ADDR="172.19.0.4",
        HTTP_X_REAL_IP="172.19.0.1",
        HTTP_X_FORWARDED_FOR="172.19.0.1",
    )
    assert resp2.status_code == 200
    assert resp2.data["es_servidor"] is True

    # Escenario 3: Dispositivo REMOTO accede via IP LAN, NO debe ser servidor
    resp3 = api_admin.get(
        ES_SERVIDOR_URL,
        HTTP_HOST="192.168.1.50:5174",
        REMOTE_ADDR="172.19.0.4",
        HTTP_X_REAL_IP="192.168.1.100",
        HTTP_X_FORWARDED_FOR="192.168.1.100",
    )
    assert resp3.status_code == 200
    assert resp3.data["es_servidor"] is False

    # Escenario 4: Dispositivo REMOTO con gateway Docker en X-Forwarded-For pero Host remoto
    resp4 = api_admin.get(
        ES_SERVIDOR_URL,
        HTTP_HOST="192.168.1.50:5174",
        REMOTE_ADDR="172.19.0.4",
        HTTP_X_REAL_IP="172.19.0.1",
        HTTP_X_FORWARDED_FOR="172.19.0.1, 192.168.1.100",
    )
    assert resp4.status_code == 200
    assert resp4.data["es_servidor"] is False


def test_es_cliente_servidor_local_con_ips_docker():
    """TDD: Prueba directa de la función es_cliente_servidor_local con escenarios Docker."""
    from django.test import RequestFactory
    rf = RequestFactory()
    
    # Gateway Docker + Host localhost = local (servidor accediendo desde localhost)
    req = rf.get("/", HTTP_HOST="localhost:5174", REMOTE_ADDR="172.19.0.4",
                 HTTP_X_REAL_IP="172.19.0.1", HTTP_X_FORWARDED_FOR="172.19.0.1")
    assert es_cliente_servidor_local(req) is True
    
    # Gateway Docker + Host 127.0.0.1 = local
    req2 = rf.get("/", HTTP_HOST="127.0.0.1:5174", REMOTE_ADDR="172.19.0.4",
                  HTTP_X_REAL_IP="172.19.0.1", HTTP_X_FORWARDED_FOR="172.19.0.1")
    assert es_cliente_servidor_local(req2) is True
    
    # IP LAN real + Host remoto = NO local (otro dispositivo en la red)
    req3 = rf.get("/", HTTP_HOST="192.168.1.50:5174", REMOTE_ADDR="172.19.0.4",
                  HTTP_X_REAL_IP="192.168.1.100", HTTP_X_FORWARDED_FOR="192.168.1.100")
    assert es_cliente_servidor_local(req3) is False
    
    # Host remoto aunque X-Real-IP sea gateway Docker = NO local
    # (un dispositivo remoto no accede por localhost)
    req4 = rf.get("/", HTTP_HOST="192.168.1.50:5174", REMOTE_ADDR="172.19.0.4",
                  HTTP_X_REAL_IP="172.19.0.1", HTTP_X_FORWARDED_FOR="172.19.0.1")
    assert es_cliente_servidor_local(req4) is False


@patch("apps.comun.servicios_respaldo.subprocess.Popen")
def test_ejecutar_respaldo_rechaza_remoto_y_acepta_servidor(mock_popen: MagicMock, api_admin: ClienteApi):
    # Dispositivo remoto recibe 403 Forbidden
    resp_remoto = api_admin.post(
        EJECUTAR_URL,
        {},
        REMOTE_ADDR="192.168.1.80",
        HTTP_IDEMPOTENCY_KEY="key-ejecutar-remoto-1",
    )
    assert resp_remoto.status_code == 403
    assert not mock_popen.called

    # Dispositivo local en servidor (127.0.0.1) ejecuta exitosamente
    resp_local = api_admin.post(
        EJECUTAR_URL,
        {},
        REMOTE_ADDR="127.0.0.1",
        HTTP_IDEMPOTENCY_KEY="key-ejecutar-local-1",
    )
    assert resp_local.status_code == 202
    assert "iniciada por consola en el servidor" in resp_local.data["mensaje"]
    assert mock_popen.called


@patch("apps.comun.servicios_respaldo.leer_estado_ejecucion")
def test_ejecutar_respaldo_conflicto_si_ya_ejecutando(mock_estado: MagicMock, api_admin: ClienteApi):
    mock_estado.return_value = {"ejecutando": True}
    resp = api_admin.post(
        EJECUTAR_URL,
        {},
        REMOTE_ADDR="127.0.0.1",
        HTTP_IDEMPOTENCY_KEY="key-ejecutar-conflict",
    )
    assert resp.status_code == 409


@patch("apps.comun.management.commands.respaldar_base_datos.subprocess.run")
@patch("apps.comun.management.commands.respaldar_base_datos.buscar_pg_dump")
def test_comando_management_respalda_y_depura_antiguos(
    mock_pg_dump: MagicMock, mock_run: MagicMock, tmp_path: Path
):
    mock_pg_dump.return_value = "pg_dump.exe"
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc

    # Crear 16 archivos sql falsos para probar que depura los excedentes a 14
    for i in range(16):
        archivo = tmp_path / f"check_contactos-{i:02d}-11-2026.sql"
        archivo.write_text("CREATE TABLE test();", encoding="utf-8")

    call_command("respaldar_base_datos", destino=str(tmp_path))

    # Debe haber ejecutado pg_dump
    assert mock_run.called
    args_llamada = mock_run.call_args[0][0]
    assert "--clean" in args_llamada
    assert "--if-exists" in args_llamada
    assert "-Fc" not in args_llamada

    # Debe haber depurado para que queden máximo 14
    sqls_restantes = list(tmp_path.glob("*.sql"))
    assert len(sqls_restantes) <= 14


# ==============================================================================
# Pruebas TDD para Exploración de Archivos y Restauración / Carga de Respaldo
# ==============================================================================

def test_explorar_rechaza_dispositivo_remoto(api_admin: ClienteApi):
    resp = api_admin.get(EXPLORAR_URL, REMOTE_ADDR="192.168.1.150")
    assert resp.status_code == 403
    assert "solo puede realizarse directamente desde el equipo servidor" in resp.data["detail"]


def test_explorar_requiere_administrador(api_usuario: ClienteApi):
    resp = api_usuario.get(EXPLORAR_URL, REMOTE_ADDR="127.0.0.1")
    assert resp.status_code == 403


def test_explorar_directorio_exitoso(api_admin: ClienteApi, tmp_path: Path):
    # Crear carpetas hijas y archivos sql
    carpeta_a = tmp_path / "subcarpeta_a"
    carpeta_a.mkdir()
    carpeta_b = tmp_path / "subcarpeta_b"
    carpeta_b.mkdir()

    sql1 = tmp_path / "backup_2026.sql"
    sql1.write_text("CREATE TABLE test();", encoding="utf-8")
    sql2 = tmp_path / "otro_backup.sql"
    sql2.write_text("CREATE TABLE test2();", encoding="utf-8")

    # Archivo no sql que no debe aparecer en archivos_sql
    txt = tmp_path / "notas.txt"
    txt.write_text("notas", encoding="utf-8")

    resp = api_admin.get(f"{EXPLORAR_URL}?ruta={tmp_path}", REMOTE_ADDR="127.0.0.1")
    assert resp.status_code == 200
    datos = resp.data
    assert "ruta_actual" in datos
    assert "carpetas" in datos
    assert "subcarpeta_a" in datos["carpetas"]
    assert "subcarpeta_b" in datos["carpetas"]
    assert "archivos_sql" in datos
    nombres_sql = [a["nombre"] for a in datos["archivos_sql"]]
    assert "backup_2026.sql" in nombres_sql
    assert "otro_backup.sql" in nombres_sql
    assert "notas.txt" not in nombres_sql
    assert "unidades_disponibles" in datos
    assert len(datos["unidades_disponibles"]) > 0


def test_explorar_directorio_inexistente(api_admin: ClienteApi, tmp_path: Path):
    no_existe = tmp_path / "no_existe_carpeta_123"
    resp = api_admin.get(f"{EXPLORAR_URL}?ruta={no_existe}", REMOTE_ADDR="127.0.0.1")
    assert resp.status_code == 422
    assert "no existe" in resp.data["detail"]


def test_explorar_ruta_relativa_invalida(api_admin: ClienteApi):
    resp = api_admin.get(f"{EXPLORAR_URL}?ruta=carpeta_relativa", REMOTE_ADDR="127.0.0.1")
    assert resp.status_code == 422
    assert "debe ser absoluta" in resp.data["detail"]


def test_restaurar_rechaza_dispositivo_remoto(api_admin: ClienteApi, tmp_path: Path):
    archivo_sql = tmp_path / "backup.sql"
    archivo_sql.write_text("SELECT 1;", encoding="utf-8")
    resp = api_admin.post(
        RESTAURAR_URL,
        {"ruta_archivo": str(archivo_sql)},
        REMOTE_ADDR="192.168.1.150",
        HTTP_IDEMPOTENCY_KEY="key-restaurar-remoto",
    )
    assert resp.status_code == 403


def test_restaurar_archivo_inexistente(api_admin: ClienteApi, tmp_path: Path):
    archivo_falso = tmp_path / "archivo_fantasma.sql"
    resp = api_admin.post(
        RESTAURAR_URL,
        {"ruta_archivo": str(archivo_falso)},
        REMOTE_ADDR="127.0.0.1",
        HTTP_IDEMPOTENCY_KEY="key-restaurar-falso",
    )
    assert resp.status_code == 422
    assert "no existe" in resp.data["detail"]


def test_restaurar_archivo_no_sql(api_admin: ClienteApi, tmp_path: Path):
    archivo_txt = tmp_path / "archivo.txt"
    archivo_txt.write_text("hola", encoding="utf-8")
    resp = api_admin.post(
        RESTAURAR_URL,
        {"ruta_archivo": str(archivo_txt)},
        REMOTE_ADDR="127.0.0.1",
        HTTP_IDEMPOTENCY_KEY="key-restaurar-no-sql",
    )
    assert resp.status_code == 422
    assert "extensión .sql" in resp.data["detail"]


@patch("apps.comun.servicios_respaldo.subprocess.Popen")
def test_restaurar_exitoso_lanza_consola(mock_popen: MagicMock, api_admin: ClienteApi, tmp_path: Path):
    archivo_sql = tmp_path / "check_contactos-16-11-2026.sql"
    archivo_sql.write_text(volcado_postgres(), encoding="utf-8")

    resp = api_admin.post(
        RESTAURAR_URL,
        {"ruta_archivo": str(archivo_sql)},
        REMOTE_ADDR="127.0.0.1",
        HTTP_IDEMPOTENCY_KEY="key-restaurar-ok",
    )
    assert resp.status_code == 202
    assert "iniciada por consola en el servidor" in resp.data["mensaje"]
    assert resp.data["archivo"] == archivo_sql.name
    assert mock_popen.called


def test_subir_respaldo_rechaza_remoto(api_admin: ClienteApi):
    from django.core.files.uploadedfile import SimpleUploadedFile
    archivo = SimpleUploadedFile("backup.sql", b"SELECT 1;", content_type="application/sql")
    resp = api_admin.post(
        SUBIR_URL,
        {"archivo": archivo},
        format="multipart",
        REMOTE_ADDR="192.168.1.150",
    )
    assert resp.status_code == 403


def test_subir_respaldo_rechaza_no_sql(api_admin: ClienteApi):
    from django.core.files.uploadedfile import SimpleUploadedFile
    archivo = SimpleUploadedFile("script.py", b"print('hola')", content_type="text/x-python")
    resp = api_admin.post(
        SUBIR_URL,
        {"archivo": archivo},
        format="multipart",
        REMOTE_ADDR="127.0.0.1",
    )
    assert resp.status_code == 422
    assert "extensión .sql" in resp.data["detail"]


def test_subir_respaldo_exitoso(api_admin: ClienteApi, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.comun import servicios_respaldo
    monkeypatch.setattr(servicios_respaldo, "obtener_ruta_respaldo", lambda: tmp_path)

    archivo = SimpleUploadedFile("mi_backup.sql", b"CREATE TABLE x();", content_type="application/sql")
    resp = api_admin.post(
        SUBIR_URL,
        {"archivo": archivo},
        format="multipart",
        REMOTE_ADDR="127.0.0.1",
    )
    assert resp.status_code == 201
    assert resp.data["archivo"] == "mi_backup.sql"
    assert (tmp_path / "mi_backup.sql").exists()


@patch("apps.comun.management.commands.restaurar_base_datos.subprocess.run")
@patch("apps.comun.management.commands.restaurar_base_datos.buscar_psql")
def test_comando_management_restaurar_base_datos(mock_buscar_psql: MagicMock, mock_run: MagicMock, tmp_path: Path):
    mock_buscar_psql.return_value = "psql.exe"
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_run.return_value = mock_proc

    archivo_sql = tmp_path / "respaldo.sql"
    archivo_sql.write_text(volcado_postgres(), encoding="utf-8")

    with patch(RESTAURAR + ".generar_respaldo", return_value=Path("previo.sql")):
        call_command("restaurar_base_datos", origen=str(archivo_sql))
    assert mock_run.called
    args = mock_run.call_args[0][0]
    assert "-f" in args
    assert str(archivo_sql) in args


RESTAURAR = "apps.comun.management.commands.restaurar_base_datos"


def _estado() -> dict:
    return json.loads(ARCHIVO_ESTADO_RESPALDO.read_text(encoding="utf-8"))


def test_restaurar_rechaza_sql_desconocido(tmp_path: Path):
    archivo = tmp_path / "malo.sql"
    archivo.write_text("DROP TABLE cuentas_usuario;", encoding="utf-8")
    with patch(RESTAURAR + ".subprocess.run") as mock_run, pytest.raises(CommandError):
        call_command("restaurar_base_datos", origen=str(archivo))
    assert not mock_run.called
    estado = _estado()
    assert estado["ejecutando"] is False
    assert "Formato no reconocido" in estado["error"]


@patch(RESTAURAR + ".subprocess.run")
@patch(RESTAURAR + ".buscar_psql", return_value="psql.exe")
def test_restaurar_psql_usa_transaccion_unica(_psql: MagicMock, mock_run: MagicMock, tmp_path: Path):
    mock_run.return_value = MagicMock(returncode=0)
    archivo = tmp_path / "check.sql"
    archivo.write_text(volcado_postgres(), encoding="utf-8")
    with patch(RESTAURAR + ".generar_respaldo", return_value=Path("previo.sql")):
        call_command("restaurar_base_datos", origen=str(archivo))
    args = mock_run.call_args[0][0]
    assert "--single-transaction" in args
    assert "ON_ERROR_STOP=1" in args


def test_falla_respaldo_previo_no_importa(tmp_path: Path):
    archivo = tmp_path / "legado.sql"
    archivo.write_text(volcado_mysql(DUMP_SINTETICO), encoding="utf-8")
    with (
        patch(RESTAURAR + ".generar_respaldo", side_effect=CommandError("sin pg_dump")),
        patch(RESTAURAR + ".importar_dump") as mock_importar,
        pytest.raises(CommandError, match="respaldo previo"),
    ):
        call_command("restaurar_base_datos", origen=str(archivo))
    assert not mock_importar.called
    estado = _estado()
    assert estado["ejecutando"] is False and estado["exitoso"] is False
    assert "respaldo previo" in estado["error"]


def test_error_en_importacion_cierra_estado(tmp_path: Path):
    archivo = tmp_path / "legado.sql"
    archivo.write_text(volcado_mysql(DUMP_SINTETICO), encoding="utf-8")
    with (
        patch(RESTAURAR + ".generar_respaldo", return_value=Path("previo.sql")),
        patch(RESTAURAR + ".importar_dump", side_effect=RuntimeError("x")),
        pytest.raises(RuntimeError),
    ):
        call_command("restaurar_base_datos", origen=str(archivo))
    estado = _estado()
    assert estado["ejecutando"] is False
    assert estado["exitoso"] is False
    assert estado["error"] == "x"


@pytest.mark.django_db
def test_restaurar_legado_reporta_progreso(tmp_path: Path):
    archivo = tmp_path / "legado.sql"
    archivo.write_bytes(volcado_mysql(DUMP_SINTETICO).encode("latin-1"))
    escritos: list[dict] = []
    real = __import__("apps.comun.servicios_respaldo", fromlist=["x"]).escribir_estado_ejecucion

    def espia(datos: dict) -> None:
        escritos.append(dict(datos))
        real(datos)

    with (
        patch(RESTAURAR + ".generar_respaldo", return_value=Path("previo.sql")),
        patch(RESTAURAR + ".escribir_estado_ejecucion", side_effect=espia),
        patch(RESTAURAR + ".escribir_informe", return_value=tmp_path / "informe.md"),
    ):
        call_command("restaurar_base_datos", origen=str(archivo), sin_usuarios=True)
    final = _estado()
    assert final["etapa"] == "finalizado"
    assert final["exitoso"] is True
    assert final["ejecutando"] is False
    assert any(e.get("total") == 10 for e in escritos)
    assert any(e.get("etapa") == "importando" and e.get("ejecutando") for e in escritos)


# --- Análisis previo, opción de usuarios y subida sin sobrescribir ---------------------------


def _volcado_en(tmp_path: Path, **kwargs) -> Path:
    archivo = tmp_path / "legado.sql"
    archivo.write_bytes(volcado_mysql(DUMP_SINTETICO, **kwargs).encode("latin-1"))
    return archivo


def test_analizar_devuelve_informe(api_admin: ClienteApi, tmp_path: Path):
    archivo = _volcado_en(tmp_path)
    resp = api_admin.post(
        ANALIZAR_URL, {"ruta_archivo": str(archivo)}, REMOTE_ADDR="127.0.0.1", HTTP_IDEMPOTENCY_KEY="k-analizar-1"
    )
    assert resp.status_code == 200
    assert resp.data["valido"] is True
    assert resp.data["tipo"] == "mysql_legado"
    assert resp.data["tablas_importables"][0]["nombre"] == "marca"
    assert resp.data["usuarios"] == 1


def test_analizar_rechaza_remoto(api_admin: ClienteApi, tmp_path: Path):
    archivo = _volcado_en(tmp_path)
    resp = api_admin.post(
        ANALIZAR_URL, {"ruta_archivo": str(archivo)}, REMOTE_ADDR="192.168.1.150", HTTP_IDEMPOTENCY_KEY="k-analizar-2"
    )
    assert resp.status_code == 403


def test_analizar_requiere_admin(api_usuario: ClienteApi, tmp_path: Path):
    archivo = _volcado_en(tmp_path)
    resp = api_usuario.post(
        ANALIZAR_URL, {"ruta_archivo": str(archivo)}, REMOTE_ADDR="127.0.0.1", HTTP_IDEMPOTENCY_KEY="k-analizar-3"
    )
    assert resp.status_code == 403


@patch("apps.comun.servicios_respaldo.subprocess.Popen")
def test_restaurar_rechaza_invalido_sin_lanzar(mock_popen: MagicMock, api_admin: ClienteApi, tmp_path: Path):
    archivo = _volcado_en(tmp_path, completo=False)
    resp = api_admin.post(
        RESTAURAR_URL,
        {"ruta_archivo": str(archivo)},
        REMOTE_ADDR="127.0.0.1",
        HTTP_IDEMPOTENCY_KEY="k-restaurar-invalido",
    )
    assert resp.status_code == 422
    assert not mock_popen.called
    assert not ARCHIVO_ESTADO_RESPALDO.exists() or _estado()["ejecutando"] is False


@patch("apps.comun.servicios_respaldo.subprocess.Popen")
def test_restaurar_sin_usuarios_pasa_flag(mock_popen: MagicMock, api_admin: ClienteApi, tmp_path: Path):
    archivo = _volcado_en(tmp_path)
    resp = api_admin.post(
        RESTAURAR_URL,
        {"ruta_archivo": str(archivo), "importar_usuarios": False},
        REMOTE_ADDR="127.0.0.1",
        HTTP_IDEMPOTENCY_KEY="k-restaurar-sin-usuarios",
    )
    assert resp.status_code == 202
    assert "--sin-usuarios" in mock_popen.call_args[0][0]


@patch("apps.comun.servicios_respaldo.subprocess.Popen")
def test_restaurar_con_usuarios_por_defecto_no_pasa_flag(mock_popen: MagicMock, api_admin: ClienteApi, tmp_path: Path):
    archivo = _volcado_en(tmp_path)
    resp = api_admin.post(
        RESTAURAR_URL,
        {"ruta_archivo": str(archivo)},
        REMOTE_ADDR="127.0.0.1",
        HTTP_IDEMPOTENCY_KEY="k-restaurar-con-usuarios",
    )
    assert resp.status_code == 202
    assert "--sin-usuarios" not in mock_popen.call_args[0][0]


def test_estado_expone_progreso(api_admin: ClienteApi):
    ARCHIVO_ESTADO_RESPALDO.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_ESTADO_RESPALDO.write_text(
        json.dumps({"ejecutando": False, "etapa": "importando", "tabla_actual": "marca", "avance": 2, "total": 10}),
        encoding="utf-8",
    )
    resp = api_admin.get(ESTADO_URL, REMOTE_ADDR="127.0.0.1")
    assert resp.data["progreso"] == {"etapa": "importando", "tabla_actual": "marca", "avance": 2, "total": 10}


def test_estado_sin_progreso_es_nulo(api_admin: ClienteApi):
    resp = api_admin.get(ESTADO_URL, REMOTE_ADDR="127.0.0.1")
    assert resp.data["progreso"] is None


def test_subir_no_sobrescribe(api_admin: ClienteApi, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.comun import servicios_respaldo

    monkeypatch.setattr(servicios_respaldo, "obtener_ruta_respaldo", lambda: tmp_path)
    nombres = []
    for contenido in (b"uno", b"dos"):
        archivo = SimpleUploadedFile("a.sql", contenido, content_type="application/sql")
        resp = api_admin.post(SUBIR_URL, {"archivo": archivo}, format="multipart", REMOTE_ADDR="127.0.0.1")
        assert resp.status_code == 201
        nombres.append(resp.data["archivo"])
    assert nombres == ["a.sql", "a-1.sql"]
    assert (tmp_path / "a.sql").read_bytes() == b"uno"
    assert (tmp_path / "a-1.sql").read_bytes() == b"dos"


# --- Ola final: respaldo previo anidado, estado, mensajes y análisis único ------------------


RESPALDAR = "apps.comun.management.commands.respaldar_base_datos"


def _sql_con_antiguedad(carpeta: Path, nombre: str, horas: int) -> Path:
    import os
    import time

    archivo = carpeta / nombre
    archivo.write_text("-- x", encoding="utf-8")
    momento = time.time() - horas * 3600
    os.utime(archivo, (momento, momento))
    return archivo


@patch(RESPALDAR + ".subprocess.run", return_value=MagicMock(returncode=0))
@patch(RESPALDAR + ".buscar_pg_dump", return_value="pg_dump.exe")
def test_depuracion_no_borra_el_archivo_a_conservar(_pg: MagicMock, _run: MagicMock, tmp_path: Path):
    from apps.comun.management.commands.respaldar_base_datos import generar_respaldo

    origen = _sql_con_antiguedad(tmp_path, "origen.sql", 100)  # el más antiguo
    otros = [_sql_con_antiguedad(tmp_path, f"r{i:02d}.sql", i) for i in range(1, 16)]
    generar_respaldo(tmp_path, conservar=origen, escribir_estado=False)
    assert origen.exists()
    assert not otros[-1].exists()  # el más antiguo de los demás sí se depura
    assert len([o for o in otros if o.exists()]) == 14


@patch(RESPALDAR + ".subprocess.run", return_value=MagicMock(returncode=0))
@patch(RESPALDAR + ".buscar_pg_dump", return_value="pg_dump.exe")
def test_generar_respaldo_sin_estado_no_toca_el_archivo_de_estado(_pg: MagicMock, _run: MagicMock, tmp_path: Path):
    from apps.comun.management.commands.respaldar_base_datos import generar_respaldo

    archivo = generar_respaldo(tmp_path, escribir_estado=False)
    assert archivo.parent == tmp_path and archivo.suffix == ".sql"
    assert not ARCHIVO_ESTADO_RESPALDO.exists()


def test_restaurar_mantiene_ejecutando_hasta_el_final(tmp_path: Path):
    archivo = tmp_path / "legado.sql"
    archivo.write_bytes(volcado_mysql(DUMP_SINTETICO).encode("latin-1"))
    escritos: list[dict] = []
    real = __import__("apps.comun.servicios_respaldo", fromlist=["x"]).escribir_estado_ejecucion

    def espia(datos: dict) -> None:
        escritos.append(dict(datos))
        real(datos)

    with (
        patch(RESTAURAR + ".generar_respaldo", return_value=tmp_path / "check_contactos-16-11-2026.sql") as previo,
        patch(RESTAURAR + ".escribir_estado_ejecucion", side_effect=espia),
        patch(RESTAURAR + ".escribir_informe", return_value=tmp_path / "informe.md"),
    ):
        call_command("restaurar_base_datos", origen=str(archivo), sin_usuarios=True)
    assert previo.call_args.kwargs == {"conservar": archivo, "escribir_estado": False}
    assert [e["ejecutando"] for e in escritos[:-1]] == [True] * (len(escritos) - 1)
    assert escritos[-1]["ejecutando"] is False
    assert any(e.get("etapa") == "respaldo_previo" for e in escritos)
    assert _estado()["respaldo_previo"] == "check_contactos-16-11-2026.sql"


def test_restaurar_pasa_el_analisis_a_importar(tmp_path: Path):
    archivo = tmp_path / "legado.sql"
    archivo.write_bytes(volcado_mysql(DUMP_SINTETICO).encode("latin-1"))
    with (
        patch(RESTAURAR + ".generar_respaldo", return_value=tmp_path / "previo.sql"),
        patch(RESTAURAR + ".importar_dump", return_value=([], {})) as importar,
        patch(RESTAURAR + ".escribir_informe", return_value=tmp_path / "informe.md"),
    ):
        call_command("restaurar_base_datos", origen=str(archivo))
    analisis = importar.call_args.kwargs["analisis"]
    assert analisis.tipo == "mysql_legado" and analisis.valido


def test_fallo_al_escribir_informe_no_cambia_el_exito(tmp_path: Path):
    archivo = tmp_path / "legado.sql"
    archivo.write_bytes(volcado_mysql(DUMP_SINTETICO).encode("latin-1"))
    with (
        patch(RESTAURAR + ".generar_respaldo", return_value=tmp_path / "previo.sql"),
        patch(RESTAURAR + ".importar_dump", return_value=([], {})),
        patch(RESTAURAR + ".escribir_informe", side_effect=OSError("disco lleno")),
    ):
        call_command("restaurar_base_datos", origen=str(archivo))
    estado = _estado()
    assert estado["exitoso"] is True and estado["ejecutando"] is False


def test_mensaje_ruta_relativa_sin_retorno_de_carro():
    with pytest.raises(CommandError) as error:
        call_command("restaurar_base_datos", origen="respaldo.sql")
    assert "\r" not in str(error.value)
    assert "respaldo.sql" in str(error.value)


def _escribir_estado_crudo(datos: dict) -> None:
    ARCHIVO_ESTADO_RESPALDO.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_ESTADO_RESPALDO.write_text(json.dumps(datos), encoding="utf-8")


def test_estado_con_actualizacion_reciente_sigue_ejecutando():
    from datetime import timedelta

    from django.utils import timezone

    from apps.comun.servicios_respaldo import leer_estado_ejecucion

    ahora = timezone.now()
    _escribir_estado_crudo(
        {
            "ejecutando": True,
            "iniciado_en": (ahora - timedelta(minutes=20)).isoformat(),
            "actualizado_en": (ahora - timedelta(minutes=1)).isoformat(),
        }
    )
    assert leer_estado_ejecucion()["ejecutando"] is True


def test_estado_sin_actualizacion_reciente_se_aborta():
    from datetime import timedelta

    from django.utils import timezone

    from apps.comun.servicios_respaldo import leer_estado_ejecucion

    ahora = timezone.now()
    _escribir_estado_crudo(
        {
            "ejecutando": True,
            "iniciado_en": (ahora - timedelta(minutes=40)).isoformat(),
            "actualizado_en": (ahora - timedelta(minutes=16)).isoformat(),
        }
    )
    estado = leer_estado_ejecucion()
    assert estado["ejecutando"] is False
    assert "abortado" in estado["error"]


def test_escribir_estado_registra_actualizado_en():
    from apps.comun.servicios_respaldo import escribir_estado_ejecucion

    escribir_estado_ejecucion({"ejecutando": True})
    assert "actualizado_en" in _estado()


def test_analizar_y_restaurar_validan_la_ruta_igual(api_admin: ClienteApi, tmp_path: Path):
    archivo = tmp_path / "notas.txt"
    archivo.write_text("x", encoding="utf-8")
    mensajes = []
    for url, clave in ((ANALIZAR_URL, "k-ruta-1"), (RESTAURAR_URL, "k-ruta-2")):
        resp = api_admin.post(url, {"ruta_archivo": str(archivo)}, REMOTE_ADDR="127.0.0.1", HTTP_IDEMPOTENCY_KEY=clave)
        assert resp.status_code == 422
        mensajes.append(resp.json()["detail"])
    assert mensajes[0] == mensajes[1] == "El archivo a restaurar debe tener extensión .sql"
