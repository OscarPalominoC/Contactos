"""Grupos por rol con sus permisos de modelo (propuesta del plan §10, pendiente de confirmar con la empresa)."""

from django.db import migrations

VER, CREAR, EDITAR, BORRAR = "view", "add", "change", "delete"
TODO = [VER, CREAR, EDITAR, BORRAR]

MATRIZ = {
    "administrador": {
        "contactos.contacto": TODO, "vehiculos.moto": TODO, "vehiculos.marca": TODO, "vehiculos.linea": TODO,
        "revisiones.revision": TODO, "revisiones.soat": TODO, "llamadas.llamadacumpleanos": TODO,
        "llamadas.llamadartm": TODO, "llamadas.llamadasoat": TODO, "cuentas.usuario": TODO,
        "cuentas.ingreso": [VER], "comun.registroauditoria": [VER], "comun.importacionrechazo": [VER, BORRAR],
    },
    "ingeniero": {
        "contactos.contacto": [VER], "vehiculos.moto": [VER, EDITAR], "vehiculos.marca": TODO,
        "vehiculos.linea": TODO, "revisiones.revision": [VER, CREAR, EDITAR], "revisiones.soat": [VER],
        "llamadas.llamadacumpleanos": [VER], "llamadas.llamadartm": [VER], "llamadas.llamadasoat": [VER],
    },
    "tecnico": {
        "contactos.contacto": [VER], "vehiculos.moto": [VER], "vehiculos.marca": [VER], "vehiculos.linea": [VER],
        "revisiones.revision": [VER, CREAR], "revisiones.soat": [VER], "llamadas.llamadacumpleanos": [VER],
        "llamadas.llamadartm": [VER], "llamadas.llamadasoat": [VER],
    },
    "usuario": {
        "contactos.contacto": [VER, CREAR, EDITAR], "vehiculos.moto": [VER, CREAR, EDITAR],
        "vehiculos.marca": [VER], "vehiculos.linea": [VER], "revisiones.revision": [VER, CREAR, EDITAR],
        "revisiones.soat": [VER, CREAR, EDITAR], "llamadas.llamadacumpleanos": [VER, CREAR, EDITAR],
        "llamadas.llamadartm": [VER, CREAR, EDITAR], "llamadas.llamadasoat": [VER, CREAR, EDITAR],
    },
}


def crear_roles(apps, schema_editor):  # type: ignore[no-untyped-def]
    from django.contrib.auth.management import create_permissions

    for config in apps.get_app_configs():
        config.models_module = True
        create_permissions(config, apps=apps, verbosity=0)
        config.models_module = None
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for rol, modelos in MATRIZ.items():
        grupo, _ = Group.objects.get_or_create(name=rol)
        permisos = []
        for etiqueta, acciones in modelos.items():
            app_label, modelo = etiqueta.split(".")
            for accion in acciones:
                permisos.append(
                    Permission.objects.get(content_type__app_label=app_label, codename=f"{accion}_{modelo}")
                )
        grupo.permissions.set(permisos)


def quitar_roles(apps, schema_editor):  # type: ignore[no-untyped-def]
    apps.get_model("auth", "Group").objects.filter(name__in=MATRIZ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("cuentas", "0001_initial"),
        ("contactos", "0001_initial"),
        ("vehiculos", "0001_initial"),
        ("revisiones", "0001_initial"),
        ("llamadas", "0001_initial"),
        ("comun", "0002_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(crear_roles, quitar_roles)]
