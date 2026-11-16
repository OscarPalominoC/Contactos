---
persona: oscar
ia: Claude Code (Claude Opus 5.5)
actualizado: 2026-11-14 17:45
zona_horaria: America/Bogota
---
# Check Contactos

Aplicación web local de CDA Check Motos para gestionar contactos, motos, revisiones técnico-mecánicas (RTM), pólizas SOAT y la bitácora de llamadas. Reemplaza el sistema legado de MySQL con datos importados del respaldo del 2026-11-07.

| Capa | Tecnología |
|---|---|
| Backend | Python 3.13, Django 5.2 LTS, Django Admin, Django REST Framework, JWT RS256 (simplejwt), django-axes, Argon2id |
| Base de datos | PostgreSQL 18 local del proyecto (`.pgdata`, puerto 5433) |
| Frontend | React 18, TypeScript, Vite 6, Tailwind 4, TanStack Query, Zustand, Axios, Zod, React Router |

## Arranque con Docker

Para levantar todo el stack (PostgreSQL 17 con `pg_trgm`, Backend Django 5 con Gunicorn e importación automática del dump legado, y Frontend React 18 con Nginx):

```bash
docker compose up -d --build
```

- **Frontend (React SPA):** <http://localhost:5174> (configurable con `CHECK_FRONTEND_PORT`)
- **Backend API REST:** <http://localhost:8080/api/v1> (configurable con `CHECK_BACKEND_PORT`)
- **Django Admin:** <http://localhost:8080/gestion-c2447da1/> (o a través del proxy en <http://localhost:5174/gestion-c2447da1/>)
- **Documentación OpenAPI:** <http://localhost:8080/docs> y `/redoc`

El contenedor backend espera a PostgreSQL, genera automáticamente el par de llaves RSA 2048 para JWT si no existen, aplica las migraciones, recopila estáticos y, si la base de datos está vacía, importa automáticamente `CONTACTOS_recuperado_2026-11-07.sql` e inicializa las 23 cuentas de usuario temporales con Argon2id.

Para ejecutar la importación manualmente en Docker en cualquier momento:
```bash
docker compose run --rm backend python manage.py importar_legado /data/CONTACTOS_recuperado_2026-11-07.sql
```

## Arranque diario local (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\iniciar.ps1
```

- Aplicación: <http://localhost:5173>
- API: <http://127.0.0.1:8000/api/v1> · documentación OpenAPI en `/docs` y `/redoc` (solo administradores con sesión en el admin).
- Django Admin: `http://127.0.0.1:8000/<ADMIN_URL>` (valor de `ADMIN_URL` en `backend/.env`; nunca es `/admin/`).

Los usuarios ingresan con su documento y la clave temporal de `CREDENCIALES_TEMPORALES.md` (entregarla en persona). El sistema obliga a cambiarla en el primer ingreso.

## Instalación desde cero

1. **Base de datos** (clúster propio del proyecto, no toca el servicio PostgreSQL del sistema):
   ```bash
   PG="/c/Program Files/PostgreSQL/18/bin"
   "$PG/initdb.exe" -D .pgdata -U check_super --pwfile=.secrets/pg_superuser.txt -E UTF8 --locale=C -A scram-sha-256
   # en .pgdata/postgresql.conf: port = 5433 y listen_addresses = 'localhost'
   "$PG/pg_ctl.exe" -D .pgdata -l logs/postgres.log -w start
   # crear el rol check_app (sin superusuario) y la base check_contactos con la extensión pg_trgm
   ```
2. **Backend**:
   ```bash
   cd backend
   python -m venv .venv
   .venv/Scripts/python.exe -m pip install -r requirements-dev.txt
   cp .env.example .env            # completar valores; generar claves RSA en backend/keys/
   .venv/Scripts/python.exe manage.py migrate
   .venv/Scripts/python.exe manage.py importar_legado ../CONTACTOS_recuperado_2026-11-07.sql
   .venv/Scripts/python.exe manage.py crear_cuentas_temporales ../scripts/credenciales_temporales.json
   ```
   `importar_legado` es idempotente (vacía y vuelve a cargar cada tabla) y deja el informe en `logs/importacion-<fecha>.md`. `crear_cuentas_temporales` borra el JSON al terminar.
3. **Frontend**:
   ```bash
   cd frontend
   npm ci
   npm run dev
   ```

## Verificación

| Comando | Resultado esperado |
|---|---|
| `cd backend && .venv/Scripts/python.exe -m pytest` | 126 pruebas, cobertura ≥ 85 % (actual 97 %) |
| `.venv/Scripts/ruff.exe check apps config tests` | sin hallazgos |
| `.venv/Scripts/bandit.exe -r apps config` | sin hallazgos |
| `.venv/Scripts/pip-audit.exe -r requirements.txt` | sin vulnerabilidades conocidas |
| `ENVIRONMENT=production DEBUG=False manage.py check --deploy` | solo el aviso de HSTS preload (requiere HTTPS) |
| `cd frontend && npm run test:cov` | 68 pruebas, cobertura ≥ 85 % (actual 94 % líneas) |
| `npm run lint && npm run typecheck && npm run build` | sin errores |
| `npm audit --audit-level=high` | 0 vulnerabilidades |

## Respaldos

```powershell
powershell -ExecutionPolicy Bypass -File scripts\respaldar.ps1
```

Genera `respaldos/check_contactos-<fecha>.dump` con `pg_dump` y conserva los 14 más recientes. Para restaurar: `pg_restore -h localhost -p 5433 -U check_super -d check_contactos --clean <archivo>`. Se sugiere programarlo a diario en el Programador de tareas de Windows.

## Estructura

```
backend/
  config/            settings (fail-fast con django-environ), urls, api_urls
  apps/comun/        errores RFC 7807, paginación, filtros, X-Request-ID, idempotencia, auditoría, importador
  apps/cuentas/      usuario (nip), JWT RS256 + JWKS, cambio obligatorio de clave, roles, ingresos
  apps/contactos/    contactos y ficha 360
  apps/vehiculos/    motos, marcas, líneas
  apps/revisiones/   RTM, SOAT, tablero
  apps/llamadas/     bitácoras de cumpleaños, RTM y SOAT
  tests/             pytest
frontend/src/
  app/               router, sesión, rutas protegidas, estado de UI
  layouts/           AppLayout / AuthLayout
  components/ui/     Boton, Campos, TablaPaginada, Dialogo, Aviso, EstadoVacio, Insignias
  features/          una carpeta por pantalla
  services/          apiClient (Axios), tokenStore, esquemas Zod
  utils/             formateadores puros, hooks de consultas
docs/                Habeas Data (borrador) y manuales
logs/                informes de importación (sin datos personales)
```

## Seguridad: puntos clave

- Las claves del sistema legado **no se migraron**. Cada cuenta tiene una clave temporal aleatoria con hash Argon2id y debe cambiarse en el primer ingreso (mínimo 12 caracteres, distinta del documento y del nombre, sin repetir las últimas 3).
- 5 intentos fallidos bloquean la combinación usuario + IP durante 1 hora (django-axes); el administrador lo levanta reiniciando la clave.
- El token de acceso dura 5 minutos y vive solo en memoria del navegador; el de refresco va en cookie HttpOnly con rotación y lista negra, y exige el token CSRF.
- No existe ninguna exportación ni descarga de listados (regla RN-12).
- `.env`, claves RSA, `.pgdata`, `.secrets`, respaldos, dumps `.sql` y `CREDENCIALES_TEMPORALES.md` están fuera de Git.
