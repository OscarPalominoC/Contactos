"""Configuración de Django para Check Contactos.

Fail-fast: si falta una variable crítica en `.env`, la aplicación no arranca
(skill backend §4).
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

ENVIRONMENT: str = env.str("ENVIRONMENT", default="production")
# DEBUG solo se activa con ENVIRONMENT=local explícito.
DEBUG: bool = env.bool("DEBUG", default=False) and ENVIRONMENT == "local"
SECRET_KEY: str = env.str("SECRET_KEY")
ALLOWED_HOSTS: list[str] = env.list("ALLOWED_HOSTS")
if ENVIRONMENT == "local" or DEBUG:
    if "*" not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append("*")
ADMIN_URL: str = env.str("ADMIN_URL")
if ADMIN_URL.strip("/") == "admin":
    raise environ.ImproperlyConfigured("ADMIN_URL no puede ser la ruta predeterminada /admin/.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "corsheaders",
    "axes",
    "apps.comun",
    "apps.cuentas",
    "apps.contactos",
    "apps.vehiculos",
    "apps.revisiones",
    "apps.llamadas",
]

MIDDLEWARE = [
    "apps.comun.middleware.RequestIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "csp.middleware.CSPMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = 60
DATABASES["default"]["ATOMIC_REQUESTS"] = True

AUTH_USER_MODEL = "cuentas.Usuario"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
# Política relajada para desarrollo local: mínimo 5 caracteres; puede incluir nombre o documento.
# Se conserva el historial para que el cambio obligatorio de la clave temporal no la repita.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 5}},
    {"NAME": "apps.cuentas.validadores.HistorialClavesValidator"},
]
# Duración de la sesión en días; cada renovación (rotación del refresh) reinicia la ventana completa.
SESION_DIAS: int = env.int("SESION_DIAS", default=30)
CLAVE_TEMPORAL_INICIAL: str = env.str("CLAVE_TEMPORAL_INICIAL", default="CheckLTDA!")

# django-axes: 5 intentos fallidos bloquean nip + IP durante 1 hora.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_USERNAME_FORM_FIELD = "nip"
AXES_LOCKOUT_CALLABLE = "apps.cuentas.servicios.respuesta_bloqueo"

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Límite de subida para archivos de respaldo SQL (hasta 500 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 524288000
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # las subidas grandes van a un archivo temporal

# --- API REST: errores RFC 7807, page[number]/page[size], X-Request-ID, Idempotency-Key ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.cuentas.autenticacion.AutenticacionJWT"],
    "DEFAULT_PERMISSION_CLASSES": [
        "apps.cuentas.permisos.CambioClaveCompletado",
        "apps.cuentas.permisos.PermisosDeModelo",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.comun.paginacion.PaginacionEstandar",
    "DEFAULT_FILTER_BACKENDS": [
        "apps.comun.filtros.FiltroCorchetes",
        "apps.comun.filtros.OrdenSort",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "EXCEPTION_HANDLER": "apps.comun.errores.manejador_problemas",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {"autenticacion": "10/min", "usuario": "600/min"},
    "DEFAULT_THROTTLE_CLASSES": ["apps.comun.limites.LimiteUsuario"],
    "UNAUTHENTICATED_USER": None,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Check Contactos API",
    "DESCRIPTION": "API REST de CDA Check Motos: contactos, motos, RTM, SOAT y llamadas.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "COMPONENT_SPLIT_REQUEST": True,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
    "SERVE_AUTHENTICATION": ["rest_framework.authentication.SessionAuthentication"],
    "ENUM_NAME_OVERRIDES": {
        "EstadoContactoEnum": "apps.contactos.models.ESTADOS_CONTACTO",
        "EstadoDocumentoEnum": "apps.revisiones.models.ESTADOS_DOCUMENTO",
        "EstadoLlamadaEnum": "apps.llamadas.models.ESTADOS_LLAMADA",
        "EstadoLlamadaElegibleEnum": "apps.llamadas.serializers.ESTADOS_ELEGIBLES",
        "EstadoEditableEnum": [("VIGENTE", "VIGENTE"), ("DUPLICADO", "DUPLICADO"), ("ANULADO", "ANULADO")],
        "RolEnum": "apps.cuentas.models.ROLES",
    },
}

# --- JWT RS256 (skill backend §3.1-§3.2) ---
JWT_PRIVATE_KEY = (BASE_DIR / env.str("JWT_PRIVATE_KEY_PATH")).read_text(encoding="ascii")
JWT_PUBLIC_KEY = (BASE_DIR / env.str("JWT_PUBLIC_KEY_PATH")).read_text(encoding="ascii")
SIMPLE_JWT = {
    "ALGORITHM": "RS256",
    "SIGNING_KEY": JWT_PRIVATE_KEY,
    "VERIFYING_KEY": JWT_PUBLIC_KEY,
    "ISSUER": env.str("JWT_ISSUER"),
    "AUDIENCE": env.str("JWT_AUDIENCE"),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=SESION_DIAS),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "USER_ID_FIELD": "nip",
    "USER_ID_CLAIM": "sub",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("apps.cuentas.autenticacion.AccessConKid",),
    "CHECK_REVOKE_TOKEN": True,
}
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"
REFRESH_COOKIE_SECURE = ENVIRONMENT != "local"

# --- CORS, CSRF y cabeceras (skill backend §3.6) ---
CORS_ALLOWED_ORIGINS: list[str] = env.list("CORS_ALLOWED_ORIGINS")
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?$",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS = ["authorization", "content-type", "x-xsrf-token", "x-request-id", "idempotency-key"]
CORS_EXPOSE_HEADERS = ["X-Request-ID", "Retry-After"]
CSRF_TRUSTED_ORIGINS = list(
    set(
        CORS_ALLOWED_ORIGINS
        + [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://192.168.1.50:5174",
        ]
    )
)
CSRF_COOKIE_NAME = "XSRF-TOKEN"
CSRF_HEADER_NAME = "HTTP_X_XSRF_TOKEN"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = ENVIRONMENT != "local"
SESSION_COOKIE_SECURE = ENVIRONMENT != "local"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = SESION_DIAS * 24 * 3600
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
if ENVIRONMENT != "local":
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

CSP_DEFAULT_SRC = ("'self'",)
CSP_IMG_SRC = ("'self'", "data:")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_SCRIPT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)

# --- Logs sin datos personales (skill backend §3.8) ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "apps.comun.middleware.FiltroRequestId"},
        "sin_datos_personales": {"()": "apps.comun.middleware.FiltroDatosPersonales"},
    },
    "formatters": {
        "estandar": {"format": "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "consola": {
            "class": "logging.StreamHandler",
            "formatter": "estandar",
            "filters": ["request_id", "sin_datos_personales"],
        },
    },
    "root": {"handlers": ["consola"], "level": "INFO"},
}
