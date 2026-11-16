"""Fábricas de volcados SQL sintéticos para probar el análisis y la restauración."""

from apps.comun.management.commands.importar_legado import TABLAS

COLUMNAS_USUARIO = ("nip", "nombre", "clave", "tipo")


def volcado_mysql(
    inserts: str,
    *,
    omitir: set[str] = frozenset(),  # type: ignore[assignment]
    columnas: dict[str, int] | None = None,
    completo: bool = True,
    con_usuario: bool = True,
) -> str:
    """Volcado MySQL mínimo: encabezado, un CREATE TABLE por tabla de `TABLAS`, los `inserts` dados y el pie."""
    columnas = columnas or {}
    partes = [
        "-- MySQL dump 10.13  Distrib 8.0.21, for Win64 (x86_64)\n--\n-- Host: localhost    Database: contactos\n\n"
    ]
    for tabla in TABLAS:
        if tabla.legada in omitir:
            continue
        cantidad = columnas.get(tabla.legada, tabla.columnas)
        cuerpo = ",\n".join(f"  `c{i}` varchar(50) DEFAULT NULL" for i in range(1, cantidad + 1))
        partes.append(f"CREATE TABLE `{tabla.legada}` (\n{cuerpo}\n) ENGINE=MyISAM DEFAULT CHARSET=latin1;\n\n")
    if con_usuario:
        cuerpo = ",\n".join(f"  `{c}` varchar(50) DEFAULT NULL" for c in COLUMNAS_USUARIO)
        partes.append(f"CREATE TABLE `usuario` (\n{cuerpo}\n) ENGINE=MyISAM DEFAULT CHARSET=latin1;\n\n")
    partes.append(inserts if inserts.endswith("\n") or not inserts else inserts + "\n")
    if completo:
        partes.append("\n-- Dump completed on 2026-11-07 13:12:23\n")
    return "".join(partes)


def volcado_postgres(cuerpo: str = "") -> str:
    """Respaldo `pg_dump` mínimo de Check Contactos."""
    return (
        "--\n-- PostgreSQL database dump\n--\n\n"
        "CREATE TABLE public.contactos_contacto (\n    id bigint NOT NULL\n);\n\n"
        "CREATE TABLE public.cuentas_usuario (\n    id bigint NOT NULL\n);\n\n"
        f"{cuerpo}\n--\n-- PostgreSQL database dump complete\n--\n"
    )
