from io import StringIO
from unittest.mock import patch
import pytest
from django.core.management import call_command
from apps.cuentas.models import Usuario

@pytest.mark.django_db
def test_crear_superadmin_comando_exitoso():
    out = StringIO()
    call_command(
        "crear_superadmin",
        nip="admin@admin.com",
        password="ClaveSuperSegura2026!",
        nombre="Super Admin",
        stdout=out,
    )
    usuario = Usuario.objects.get(nip="admin@admin.com")
    assert usuario.nombre == "Super Admin"
    assert usuario.rol == "administrador"
    assert usuario.is_staff is True
    assert usuario.is_superuser is True
    assert usuario.debe_cambiar_clave is False
    assert usuario.check_password("ClaveSuperSegura2026!")
    assert "exitosamente" in out.getvalue()

@pytest.mark.django_db
def test_crear_superadmin_idempotente():
    out = StringIO()
    call_command("crear_superadmin", nip="admin@admin.com", password="P1!", stdout=out)
    call_command("crear_superadmin", nip="admin@admin.com", password="P2!", stdout=out)
    usuario = Usuario.objects.get(nip="admin@admin.com")
    assert usuario.check_password("P2!")
    assert Usuario.objects.filter(nip="admin@admin.com").count() == 1

@pytest.mark.django_db
def test_crear_superadmin_sin_password_omite():
    out = StringIO()
    with patch("django.conf.settings.SUPERADMIN_PASSWORD", None):
        call_command("crear_superadmin", nip="admin@admin.com", stdout=out)
        assert not Usuario.objects.filter(nip="admin@admin.com").exists()
        assert "SUPERADMIN_PASSWORD no está definida" in out.getvalue()

