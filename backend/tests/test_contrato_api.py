"""Contrato de la API: RFC 7807, X-Request-ID, paginación, filtros, orden, idempotencia y sin exportación."""

import uuid
from typing import Any

import pytest
from django.urls import get_resolver

from apps.contactos.models import Contacto
from tests.conftest import ClienteApi

pytestmark = pytest.mark.django_db


def crear_contactos(cantidad: int) -> None:
    Contacto.objects.bulk_create(
        Contacto(nip=f"20{i:06d}", nombre=f"PERSONA {i:03d}", mes_nac=(i % 12) + 1, dia_nac=1) for i in range(cantidad)
    )


def test_x_request_id_se_genera_y_se_respeta(api_admin: ClienteApi) -> None:
    generado = api_admin.get("/api/v1/contactos")
    uuid.UUID(generado["X-Request-ID"])
    propio = str(uuid.uuid4())
    assert api_admin.get("/api/v1/contactos", HTTP_X_REQUEST_ID=propio)["X-Request-ID"] == propio
    invalido = api_admin.get("/api/v1/contactos", HTTP_X_REQUEST_ID="<script>")
    assert invalido["X-Request-ID"] != "<script>"


def test_error_404_es_rfc7807(api_admin: ClienteApi) -> None:
    respuesta = api_admin.get("/api/v1/contactos/no-existe", HTTP_X_REQUEST_ID=str(uuid.uuid4()))
    assert respuesta.status_code == 404
    assert respuesta["Content-Type"] == "application/problem+json"
    cuerpo = respuesta.json()
    assert set(cuerpo) >= {"type", "title", "status", "detail", "instance", "request_id"}
    assert cuerpo["request_id"] == respuesta["X-Request-ID"]
    assert cuerpo["instance"] == "/api/v1/contactos/no-existe"


def test_paginacion_sobre_data_meta_links(api_admin: ClienteApi) -> None:
    crear_contactos(30)
    respuesta = api_admin.get("/api/v1/contactos", {"page[number]": 2, "page[size]": 10})
    cuerpo = respuesta.json()
    assert len(cuerpo["data"]) == 10
    assert cuerpo["meta"]["page"] == {"number": 2, "size": 10, "total": 30, "total_pages": 3}
    assert "page%5Bnumber%5D=3" in cuerpo["links"]["next"]
    assert "page%5Bnumber%5D=1" in cuerpo["links"]["prev"]


def test_paginacion_maximo_100_y_valores_invalidos(api_admin: ClienteApi) -> None:
    crear_contactos(120)
    assert len(api_admin.get("/api/v1/contactos", {"page[size]": 500}).json()["data"]) == 100
    assert len(api_admin.get("/api/v1/contactos", {"page[size]": "abc"}).json()["data"]) == 25
    assert api_admin.get("/api/v1/contactos", {"page[number]": 99}).status_code == 404


def test_filtro_lista_blanca(api_admin: ClienteApi) -> None:
    crear_contactos(24)
    assert api_admin.get("/api/v1/contactos", {"filter[mes_nac]": 3}).json()["meta"]["page"]["total"] == 2
    rechazado = api_admin.get("/api/v1/contactos", {"filter[clave]": "x"})
    assert rechazado.status_code == 422
    assert "Filtro no permitido" in rechazado.json()["detail"]


def test_orden_lista_blanca(api_admin: ClienteApi) -> None:
    crear_contactos(5)
    nombres = [c["nombre"] for c in api_admin.get("/api/v1/contactos", {"sort": "-nombre"}).json()["data"]]
    assert nombres == sorted(nombres, reverse=True)
    assert api_admin.get("/api/v1/contactos", {"sort": "password"}).status_code == 422


def test_post_sin_idempotency_key_es_422(api_admin: ClienteApi) -> None:
    respuesta = api_admin.post("/api/v1/contactos", {"nip": "123456", "nombre": "PERSONA"}, HTTP_IDEMPOTENCY_KEY="")
    assert respuesta.status_code == 422
    assert "Idempotency-Key" in respuesta.json()["detail"]


def test_idempotencia_repite_respuesta_y_detecta_conflicto(api_admin: ClienteApi) -> None:
    datos = {"nip": "123456", "nombre": "persona nueva"}
    primera = api_admin.post("/api/v1/contactos", datos, HTTP_IDEMPOTENCY_KEY="clave-1")
    assert primera.status_code == 201
    repetida = api_admin.post("/api/v1/contactos", datos, HTTP_IDEMPOTENCY_KEY="clave-1")
    assert repetida.status_code == 201
    assert repetida["Idempotent-Replayed"] == "true"
    assert repetida.json() == primera.json()
    assert Contacto.objects.filter(nip="123456").count() == 1
    distinta = api_admin.post("/api/v1/contactos", {**datos, "nombre": "otra"}, HTTP_IDEMPOTENCY_KEY="clave-1")
    assert distinta.status_code == 409


def test_campos_desconocidos_rechazados(api_admin: ClienteApi) -> None:
    respuesta = api_admin.post("/api/v1/contactos", {"nip": "123456", "nombre": "PERSONA", "is_staff": True})
    assert respuesta.status_code == 422
    assert "is_staff" in respuesta.json()["errors"]


def test_metodo_no_permitido_es_405(api_admin: ClienteApi, contacto: Contacto) -> None:
    respuesta = api_admin.delete(f"/api/v1/contactos/{contacto.nip}")
    assert respuesta.status_code == 405
    assert respuesta["Content-Type"] == "application/problem+json"


def test_sin_rutas_de_exportacion() -> None:
    """RN-12: ninguna ruta de exportación o descarga de listados."""
    prohibidas = ("export", "csv", "xlsx", "xls", "pdf", "descarga", "download", "imprimir", "print")

    def rutas(patrones: Any, prefijo: str = "") -> list[str]:
        resultado: list[str] = []
        for patron in patrones:
            texto = prefijo + str(patron.pattern)
            if hasattr(patron, "url_patterns"):
                resultado += rutas(patron.url_patterns, texto)
            else:
                resultado.append(texto.lower())
        return resultado

    todas = rutas(get_resolver().url_patterns)
    assert todas
    assert not [r for r in todas if any(p in r for p in prohibidas) and "admin" not in r and "jsi18n" not in r]


def test_listado_sin_n_mas_1(api_admin: ClienteApi, django_assert_max_num_queries: Any) -> None:
    crear_contactos(50)
    with django_assert_max_num_queries(8):
        assert api_admin.get("/api/v1/contactos", {"page[size]": 50}).status_code == 200


def test_esquema_openapi_solo_para_staff(api: ClienteApi, admin_usuario: Any) -> None:
    assert api.get("/api/schema/").status_code in (401, 403)
    api.force_login(admin_usuario)
    respuesta = api.get("/api/schema/")
    assert respuesta.status_code == 200
    assert b"/api/v1/contactos" in respuesta.content
    assert api.get("/docs").status_code == 200
    assert api.get("/redoc").status_code == 200


def test_cabeceras_de_seguridad(api_admin: ClienteApi) -> None:
    respuesta = api_admin.get("/api/v1/contactos")
    assert respuesta["X-Content-Type-Options"] == "nosniff"
    assert respuesta["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in respuesta["Content-Security-Policy"]


def test_cors_solo_origen_permitido(api_admin: ClienteApi) -> None:
    permitido = api_admin.get("/api/v1/contactos", HTTP_ORIGIN="http://localhost:5173")
    assert permitido["Access-Control-Allow-Origin"] == "http://localhost:5173"
    ajeno = api_admin.get("/api/v1/contactos", HTTP_ORIGIN="http://evil.example")
    assert "Access-Control-Allow-Origin" not in ajeno
