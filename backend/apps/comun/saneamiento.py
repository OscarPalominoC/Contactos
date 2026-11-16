"""Saneamiento de datos heredados del legado (ver `fechas.md`).

1. Cumpleaños inexistentes (31 de febrero y demás combinaciones imposibles) → `contactar_cumpleanos=False`.
2. Fechas de RTM, SOAT y motos con año transpuesto evidente se corrigen; las insalvables se conservan
   por trazabilidad (la API las expone como `null`).

Lo usan la migración `contactos.0003` (con el registro histórico de modelos) y el importador del legado.
"""

from typing import Any

from django.db.models import Q

from apps.comun.fechas_util import ANO_MAXIMO, ANO_MINIMO, sanear_par

PARES = [
    ("revisiones", "Revision", [("fecha_certificado", "fecha_venc_certificado"), ("fecha_soat", "fecha_venc_soat")]),
    ("revisiones", "Soat", [("fecha_soat", "fecha_venc_soat")]),
    ("vehiculos", "Moto", [("fecha_soat", "fecha_venc_soat"), ("fecha_rtmg", "fecha_venc_rtmg")]),
]


def _fuera_de_rango(campo: str) -> Q:
    return Q(**{f"{campo}__year__lt": ANO_MINIMO}) | Q(**{f"{campo}__year__gt": ANO_MAXIMO})


def _cumpleanos_imposible() -> Q:
    return (
        Q(mes_nac=2, dia_nac__gt=29)
        | Q(mes_nac__in=[4, 6, 9, 11], dia_nac__gt=30)
        | Q(dia_nac__gt=31)
        | Q(dia_nac=0)
        | Q(mes_nac__gt=12)
        | Q(mes_nac=0)
    )


def sanear_datos_legados(apps: Any) -> dict[str, int]:
    """Aplica el saneamiento; `apps` es `django.apps.apps` o el registro histórico de una migración."""
    contacto = apps.get_model("contactos", "Contacto")
    desactivados = contacto.objects.filter(_cumpleanos_imposible()).update(contactar_cumpleanos=False)
    conteo = {"cumpleanos_desactivados": desactivados, "fechas_corregidas": 0}

    for app, modelo, pares in PARES:
        clase = apps.get_model(app, modelo)
        for inicio, fin in pares:
            sospechosos = clase.objects.filter(_fuera_de_rango(inicio) | _fuera_de_rango(fin))
            for fila in sospechosos.iterator():
                original = (getattr(fila, inicio), getattr(fila, fin))
                limpio = sanear_par(*original)
                cambios = {
                    campo: despues
                    for campo, antes, despues in zip((inicio, fin), original, limpio, strict=True)
                    if despues is not None and despues != antes
                }
                if cambios:
                    clase.objects.filter(pk=fila.pk).update(**cambios)
                    conteo["fechas_corregidas"] += 1
    return conteo
