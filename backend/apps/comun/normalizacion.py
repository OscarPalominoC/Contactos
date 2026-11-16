"""Normalizadores puros de los datos legados (probados con pruebas unitarias)."""

import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from apps.comun.legado import reparar_texto

ZONA = ZoneInfo("America/Bogota")

MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

ESTADOS_LLAMADA = {
    "realizada": "realizada",
    "norealizada": "no_realizada",
    "no realizada": "no_realizada",
    "realizadasinexito": "realizada_sin_exito",
    "ocupada": "ocupada",
}

PATRON_ENTRADA = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})\s*([AP]M),\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})$", re.I)


def texto(valor: str | None) -> str:
    """Repara mojibake y colapsa espacios; NULL → ''."""
    if valor is None:
        return ""
    return " ".join(reparar_texto(valor).split())


def texto_multilinea(valor: str | None) -> str:
    """Como `texto` pero conserva saltos de línea (observaciones)."""
    if valor is None:
        return ""
    lineas = [" ".join(linea.split()) for linea in reparar_texto(valor).replace("\r\n", "\n").split("\n")]
    return "\n".join(linea for linea in lineas if linea)


def mayusculas_sin_espacios(valor: str | None) -> str:
    return re.sub(r"\s+", "", texto(valor)).upper()


def fecha(valor: str | None) -> date | None:
    """'AAAA-MM-DD', 'DD/MM/AAAA' o 'DD-MM-AAAA'; '0000-00-00', '' y fechas inválidas → None."""
    limpio = texto(valor)
    if not limpio or limpio.startswith("0000") or limpio.startswith("1900-01-01"):
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(limpio[:10], formato).replace(tzinfo=ZONA).date()
        except ValueError:
            continue
    return None


def fecha_hora(valor: str | None) -> datetime | None:
    """'AAAA-MM-DD HH:MM:SS' en hora de Bogotá → datetime con zona."""
    limpio = texto(valor)
    if not limpio or limpio.startswith("0000"):
        return None
    try:
        return datetime.strptime(limpio[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZONA)
    except ValueError:
        dia = fecha(limpio)
        return datetime(dia.year, dia.month, dia.day, tzinfo=ZONA) if dia else None


def fecha_entrada_sistema(valor: str | None) -> datetime | None:
    """'08:09:47 AM, 07 / 11 / 2026' → datetime en America/Bogota."""
    coincidencia = PATRON_ENTRADA.match(texto(valor))
    if not coincidencia:
        return None
    hora, minuto, segundo, meridiano, dia, mes, anio = coincidencia.groups()
    h = int(hora) % 12 + (12 if meridiano.upper() == "PM" else 0)
    try:
        return datetime(int(anio), int(mes), int(dia), h, int(minuto), int(segundo), tzinfo=ZONA)
    except ValueError:
        return None


def mes(valor: str | None) -> int | None:
    return MESES.get(texto(valor).lower())


def dia(valor: str | None) -> int | None:
    try:
        numero = int(texto(valor) or 0)
    except ValueError:
        return None
    return numero if 1 <= numero <= 31 else None


def estado_llamada(valor: str | None) -> str:
    return ESTADOS_LLAMADA.get(texto(valor).lower(), "sin_estado")


def estado_contacto(valor: str | None) -> str:
    return "inhabilitado" if texto(valor).lower() == "inhabilitado" else "habilitado"


def estado_documento(valor: str | None) -> str:
    limpio = texto(valor).upper()
    return limpio if limpio in {"VIGENTE", "VENCIDO", "DUPLICADO", "NO"} else "VENCIDO"


def entero(valor: str | None, defecto: int = 0) -> int:
    try:
        return int(texto(valor))
    except ValueError:
        return defecto


def intentos_llamada(valor: str | None) -> tuple[int | None, str]:
    """`fecha_registro` de bitacora_llamadas: '1 ; 2026-11-07 10:00:00 ; ...' → (num_llamadas, marcas)."""
    partes = [p.strip() for p in texto(valor).split(";") if p.strip()]
    if partes and partes[0].isdigit():
        return int(partes[0]), " ; ".join(partes[1:])
    return None, " ; ".join(partes)


def placa(valor: str | None) -> str:
    return re.sub(r"[\s-]+", "", texto(valor)).upper()[:6]
