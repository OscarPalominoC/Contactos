from django.apps import AppConfig


class CuentasConfig(AppConfig):
    name = "apps.cuentas"
    verbose_name = "Cuentas"

    def ready(self) -> None:
        from apps.cuentas import esquema, senales  # noqa: F401
