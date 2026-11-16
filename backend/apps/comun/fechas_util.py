"""Saneamiento de fechas heredadas del sistema legado.

Reglas (ver auditoría `fechas.md`):
- Rango plausible de fechas de negocio: 1990 a 2100.
- Año `02XX` (se omitió el 2 inicial, p. ej. `0227`) → `20XX`.
- Año con el siglo mal digitado (`3017`, `2426`) se corrige solo si la otra fecha del par
  (expedición/vencimiento) lo confirma: mismo día y mes, y año a un año de distancia.
- Todo lo demás es insalvable: se trata como `None` y no se muestra.
"""

import calendar
from datetime import date

ANO_MINIMO = 1990
ANO_MAXIMO = 2100


def fecha_segura(fecha: date | None) -> date | None:
    """La fecha si está en el rango plausible; si no, `None`."""
    if fecha is None or not ANO_MINIMO <= fecha.year <= ANO_MAXIMO:
        return None
    return fecha


def _con_ano(fecha: date, ano: int) -> date | None:
    try:
        return fecha.replace(year=ano)
    except ValueError:  # 29 de febrero en año no bisiesto
        return None


def sanear_ano_transpuesto(fecha: date | None) -> date | None:
    """Corrige `02XX` → `20XX`; devuelve la fecha si ya es válida y `None` si es insalvable."""
    if fecha is None:
        return None
    if fecha_segura(fecha) is not None:
        return fecha
    if 200 <= fecha.year <= 299:
        return fecha_segura(_con_ano(fecha, fecha.year + 1800))
    return None


def _correlacionar(cruda: date, referencia: date, ano_esperado: int) -> date | None:
    """`cruda` con año `ano_esperado` si coinciden día, mes y los dos últimos dígitos del año."""
    if (cruda.month, cruda.day) != (referencia.month, referencia.day) or cruda.year % 100 != ano_esperado % 100:
        return None
    return fecha_segura(_con_ano(cruda, ano_esperado))


def sanear_par(inicio: date | None, fin: date | None) -> tuple[date | None, date | None]:
    """Sanea un par expedición/vencimiento (vigencia de un año). Lo insalvable queda en `None`."""
    limpio_inicio = sanear_ano_transpuesto(inicio)
    limpio_fin = sanear_ano_transpuesto(fin)
    if limpio_inicio is None and inicio is not None and limpio_fin is not None:
        limpio_inicio = _correlacionar(inicio, limpio_fin, limpio_fin.year - 1)
    if limpio_fin is None and fin is not None and limpio_inicio is not None:
        limpio_fin = _correlacionar(fin, limpio_inicio, limpio_inicio.year + 1)
    return limpio_inicio, limpio_fin


def sanear_fecha_soat(expedicion: date | None, vencimiento: date | None) -> date | None:
    """Fecha de expedición saneada usando el vencimiento como referencia."""
    return sanear_par(expedicion, vencimiento)[0]


def es_cumpleanos_valido(dia: int | None, mes: int | None) -> bool:
    """Día y mes existen en el calendario (29 de febrero es válido)."""
    if dia is None or mes is None or not 1 <= mes <= 12:
        return False
    return 1 <= dia <= calendar.monthrange(2000, mes)[1]
