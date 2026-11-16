#!/bin/sh
set -e

echo "=========================================================="
echo "  Iniciando contenedor backend de Check Contactos"
echo "=========================================================="

cd /app/backend

# 1. Asegurar directorio de claves RSA y generarlas si no existen
JWT_PRIV="${JWT_PRIVATE_KEY_PATH:-keys/jwt_private.pem}"
JWT_PUB="${JWT_PUBLIC_KEY_PATH:-keys/jwt_public.pem}"

# Ajustar rutas relativas al directorio /app/backend
case "$JWT_PRIV" in
  /*) FULL_PRIV="$JWT_PRIV" ;;
  *) FULL_PRIV="/app/backend/$JWT_PRIV" ;;
esac

case "$JWT_PUB" in
  /*) FULL_PUB="$JWT_PUB" ;;
  *) FULL_PUB="/app/backend/$JWT_PUB" ;;
esac

if [ ! -f "$FULL_PRIV" ] || [ ! -f "$FULL_PUB" ]; then
    echo "==> Generando par de claves RSA 2048 para JWT en $JWT_PRIV..."
    mkdir -p "$(dirname "$FULL_PRIV")"
    openssl genpkey -algorithm RSA -out "$FULL_PRIV" -pkeyopt rsa_keygen_bits:2048 2>/dev/null
    openssl rsa -pubout -in "$FULL_PRIV" -out "$FULL_PUB" 2>/dev/null
    chmod 600 "$FULL_PRIV"
    chmod 644 "$FULL_PUB"
    echo "==> Claves RSA generadas correctamente."
fi

# 2. Esperar conexión a PostgreSQL
echo "==> Esperando conexión con PostgreSQL..."
python - << 'EOF'
import os
import sys
import time
import psycopg

db_url = os.environ.get("DATABASE_URL", "")
max_intentos = 30
intentos = 0

while intentos < max_intentos:
    try:
        conn = psycopg.connect(db_url)
        conn.close()
        print("==> PostgreSQL está listo para aceptar conexiones.")
        sys.exit(0)
    except Exception as e:
        intentos += 1
        time.sleep(1)

print("==> ERROR: Tiempo de espera agotado para conectar a PostgreSQL.", file=sys.stderr)
sys.exit(1)
EOF

# 3. Aplicar migraciones
echo "==> Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

# 4. Recopilar archivos estáticos
echo "==> Recopilando archivos estáticos..."
python manage.py collectstatic --noinput

# 5. Carga de datos legados si está habilitado
CARGAR="${CARGAR_BASE_DATOS:-true}"
DUMP="${DUMP_SQL_PATH:-/data/CONTACTOS_recuperado_2026-11-07.sql}"

if [ "$CARGAR" = "true" ] || [ "$CARGAR" = "1" ]; then
    echo "==> Comprobando si se requiere importar el dump legado..."
    HAY_DATOS=$(python - << 'EOF'
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.contactos.models import Contacto

if Contacto.objects.exists():
    print("SI")
else:
    print("NO")
EOF
    )

    if [ "$HAY_DATOS" = "NO" ]; then
        if [ -f "$DUMP" ]; then
            echo "==> Importando dump legado desde $DUMP..."
            python manage.py importar_legado "$DUMP"

            echo "==> Inicializando usuarios y credenciales temporales..."
            mkdir -p /app/logs
            export CLAVE_TEMPORAL_INICIAL="${CLAVE_TEMPORAL_INICIAL:-CheckLTDA!}"
            python /app/scripts/generar_credenciales.py "$DUMP" /app/CREDENCIALES_TEMPORALES.md /tmp/credenciales_temporales.json "2026-11-14"
            python manage.py crear_cuentas_temporales /tmp/credenciales_temporales.json
            echo "==> Base de datos inicializada y usuarios creados exitosamente."
        else
            echo "==> AVISO: Archivo dump '$DUMP' no encontrado. Se omite la importación inicial."
        fi
    else
        echo "==> La base de datos ya contiene registros (Contacto.objects.exists() == True)."
        echo "==> Se omite la importación automática para preservar el estado actual."
    fi
fi

echo "==> Iniciando servicio backend..."
exec "$@"

