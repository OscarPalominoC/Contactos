"""Saneamiento de datos heredados.

1. Cumpleaños inexistentes (31 de febrero y demás combinaciones imposibles) → `contactar_cumpleanos=False`.
   El usuario puede reactivarlo a mano cuando el cliente rectifique su fecha.
2. Fechas de RTM, SOAT y motos con año transpuesto evidente (`0227` → `2027`; `3017` con vencimiento
   `2018` → `2017`). Las fechas insalvables se conservan tal cual por trazabilidad: la API las expone
   como `null` y la interfaz muestra `—`.
"""

from django.db import migrations

from apps.comun.saneamiento import sanear_datos_legados


def sanear(apps, schema_editor):
    sanear_datos_legados(apps)


class Migration(migrations.Migration):
    dependencies = [
        ("contactos", "0002_contacto_preferencias_contacto"),
        ("revisiones", "0001_initial"),
        ("vehiculos", "0001_initial"),
    ]

    operations = [migrations.RunPython(sanear, migrations.RunPython.noop)]
