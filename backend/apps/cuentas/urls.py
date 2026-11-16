from django.urls import path

from apps.cuentas.views import CambioClaveView, CsrfView, LoginView, LogoutView, RefreshView, YoView

urlpatterns = [
    path("csrf", CsrfView.as_view(), name="auth-csrf"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("refresh", RefreshView.as_view(), name="auth-refresh"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("cambio-clave", CambioClaveView.as_view(), name="auth-cambio-clave"),
    path("yo", YoView.as_view(), name="auth-yo"),
]
