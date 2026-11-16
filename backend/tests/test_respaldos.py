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

pytestmark = pytest.mark.django_db

ESTADO_URL = "/api/v1/respaldos/estado"
ES_SERVIDOR_URL = "/api/v1/respaldos/es-servidor"
VALIDAR_URL = "/api/v1/respaldos/validar-ruta"
CONFIGURAR_URL = "/api/v1/respaldos/configurar-ruta"
EJECUTAR_URL = "/api/v1/respaldos/ejecutar"


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
