# Plan de Implementación: Respaldo Exclusivo en Servidor con Ruta Configurable (Formato .sql)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

---

## 1. Reglas de Negocio y Especificaciones

1. **Restricción estricta de dispositivo (Solo el Servidor):**
   - El equipo servidor (`127.0.0.1`, `::1` o IP de la interfaz local del host) es el **único dispositivo autorizado** para solicitar y ejecutar la copia de seguridad.
   - Todos los demás dispositivos conectados a la plataforma (celulares, tablets u otros computadores en red local) **no pueden ver el botón ni la sección de backup en el Tablero** (la interfaz no renderiza el componente para clientes remotos).
   - En el backend, cualquier intento de petición desde una IP remota se rechaza con `403 Forbidden` (RFC 7807).
2. **Opción de guardar ruta de backup en el frontend:**
   - La interfaz en el servidor incluye un campo interactivo para ingresar, validar y guardar la ruta de la carpeta física donde se depositarán los respaldos (por ejemplo, en el disco del host: `F:\Check\respaldos` o la carpeta elegida por el propietario).
   - La ruta configurada se persiste en el servidor (`config_respaldo.json`) para que se conserve en futuros respaldos.
3. **Formato .sql y nomenclatura estricta del archivo generado:**
   - **Formato:** Archivo SQL plano (`.sql`) ejecutable directamente en cualquier cliente PostgreSQL (por ejemplo, con `psql` o pgAdmin).
   - **Nomenclatura exacta:** `<nombre de la base de datos>-DD-MM-YYYY.sql`
   - *Ejemplo real:* `check_contactos-15-11-2026.sql`
   - El nombre se obtiene dinámicamente de la configuración de base de datos (`settings.DATABASES['default']['NAME']`) y la fecha actual en zona horaria local (`America/Bogota`).
4. **Almacenamiento físico fuera de Docker:**
   - La copia se genera y deposita directamente en la carpeta física del host del servidor configurada por el usuario (mediante el volumen mapeado `${HOST_BACKUP_DIR:-./respaldos}:/data/respaldos`).
   - No se acumulan residuos dentro de las capas internas del contenedor Docker.
5. **Estética y accesibilidad:**
   - Diseño **Glassmorphism Accesible Universal** (WCAG 2.1 AA, contraste ≥ 4.5:1, `backdrop-filter`, bordes de refracción y feedback visual inmediato).

---

## 2. Arquitectura del Flujo

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. EVALUACIÓN DE DISPOSITIVO AL ABRIR EL TABLERO                       │
│                                                                        │
│ Petición del cliente: GET /api/v1/respaldos/es-servidor                │
│                                                                        │
│ ┌──────────────────────────────────┐ ┌───────────────────────────────┐ │
│ │ Dispositivo Remoto en LAN        │ │ Equipo Servidor Local         │ │
│ │ (IP: 192.168.1.50)               │ │ (IP: 127.0.0.1 / ::1 / Local) │ │
│ │                                  │ │                               │ │
│ │ es_servidor: false               │ │ es_servidor: true             │ │
│ │                                  │ │                               │ │
│ │ ==> Botón y tarjeta NO EXISTEN   │ │ ==> Renderiza Tarjeta         │ │
│ │     en el Tablero (oculto 100%)  │ │     Glassmorphism de Respaldo │ │
│ └──────────────────────────────────┘ └──────────────┬────────────────┘ │
└─────────────────────────────────────────────────────┼──────────────────┘
                                                      │
┌─────────────────────────────────────────────────────▼──────────────────┐
│ 2. OPCIÓN DE GUARDAR RUTA EN EL SERVIDOR (Frontend)                    │
│                                                                        │
│ [ Campo: F:\Check\respaldos             ] [ Validar ] [ Guardar ruta ] │
│ - Valida que la carpeta exista y tenga permisos de escritura.          │
│ - Guarda la ruta en config_respaldo.json para todas las copias.        │
└─────────────────────────────────────────────────────┬──────────────────┘
                                                      │
┌─────────────────────────────────────────────────────▼──────────────────┐
│ 3. BOTÓN: [ Generar copia de seguridad de la base de datos ]            │
│                                                                        │
│ - Llama a: POST /api/v1/respaldos/ejecutar                             │
│ - Backend ejecuta pg_dump en consola en formato texto SQL:             │
│   pg_dump -h <host> -p <port> -U <user> --clean --if-exists            │
│           -f <ruta>/check_contactos-DD-MM-YYYY.sql check_contactos     │
│ - Nomenclatura del archivo generado:                                   │
│   check_contactos-15-11-2026.sql                                       │
│ - Si ya existe un respaldo en la misma fecha, agrega sufijo secuencial │
│   (ej. check_contactos-15-11-2026_01.sql) para evitar sobreescritura. │
│ - Notifica éxito en el Tablero con nombre y tamaño del archivo SQL.    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Archivos Involucrados

| Archivo | Rol en la Solución |
|---|---|
| `backend/apps/comun/servicios_respaldo.py` | Lógica de detección de servidor local (`es_cliente_servidor_local`), nomenclatura `<nombre_bd>-DD-MM-YYYY.sql`, validación y guardado de ruta, y comando `pg_dump` con formato SQL (`.sql`). |
| `backend/apps/comun/views_respaldo.py` | Endpoints REST protegidos: `GET /es-servidor`, `POST /validar-ruta`, `POST /configurar-ruta`, `POST /ejecutar` (todos rechazando 403 a dispositivos remotos). |
| `backend/apps/comun/serializers_respaldo.py` | Serializers de entrada/salida para validación de ruta y ejecución de respaldo `.sql`. |
| `backend/apps/comun/management/commands/respaldar_base_datos.py` | Comando de consola Django generando archivos `<db>-DD-MM-YYYY.sql`. |
| `backend/tests/test_respaldo.py` | Pruebas unitarias de formato `.sql`, nomenclatura, comprobación de IP y permisos. |
| `frontend/src/features/tablero/TarjetaRespaldoServidor.tsx` | Componente Glassmorphism visible **únicamente** si `es_servidor === true`, con campo para guardar la ruta y botón de ejecución. |
| `frontend/src/features/tablero/PaginaTablero.tsx` | Integra el componente en el Tablero condicionado a `es_servidor && rol === "administrador"`. |
| `frontend/src/test/respaldo.test.tsx` | Pruebas frontend (visibilidad exclusiva en servidor, guardado de ruta y ejecución del respaldo `.sql`). |

---

## 4. Tareas de Implementación (Ciclo TDD)

### Tarea 1: Backend - Formato SQL Plano y Nomenclatura `<nombre_bd>-DD-MM-YYYY.sql`
- [x] **Paso 1.1 (RED):** Escribir pruebas en `backend/tests/test_respaldo.py`:
  - `test_nomenclatura_archivo_respaldo_nombre_bd_dd_mm_yyyy_sql`: comprueba que el archivo generado termine en `.sql` y siga estrictamente `check_contactos-DD-MM-YYYY.sql`.
  - `test_comando_genera_archivo_sql_valido`: valida que el contenido del archivo generado sea texto plano SQL conteniendo instrucciones `CREATE TABLE`, `INSERT`, etc.
  - `test_dispositivos_remotos_rechazados_en_todos_los_endpoints`: peticiones con IPs remotas reciben `403 PermisoDenegado` en `/validar-ruta`, `/configurar-ruta` y `/ejecutar`.
  - `test_servidor_local_puede_guardar_ruta_y_ejecutar`: `127.0.0.1` puede configurar la ruta y detonar el respaldo `.sql`.
- [x] **Paso 1.2 (GREEN):**
  - En `servicios_respaldo.py`:
    - Función `generar_nombre_archivo_respaldo(destino, nombre_bd, fecha)`:
      Retorna `f"{nombre_bd}-{fecha.strftime('%d-%m-%Y')}.sql"`.
    - En caso de existir colisión en el mismo día, genera `{nombre_bd}-{DD-MM-YYYY}_{consecutivo:02d}.sql`.
    - Ajustar búsqueda de archivos existentes a `*.sql` (en lugar de `*.dump`).
  - En `respaldar_base_datos.py`:
    - Ajustar comando `pg_dump` eliminando la opción binaria `-Fc` y agregando opciones de volcado SQL estándar:
      ```python
      comando = [
          ejecutable,
          "-h", host,
          "-p", port,
          "-U", user,
          "--clean",
          "--if-exists",
          "-f", str(archivo_salida),  # archivo_salida con extensión .sql
          dbname,
      ]
      ```
    - Rotación automática de los 14 archivos `.sql` más recientes.
  - En `views_respaldo.py`:
    - Endpoint `GET /api/v1/respaldos/es-servidor` para evaluación de origen.
    - Rechazo 403 a IPs que no pertenezcan al servidor local en `/validar-ruta`, `/configurar-ruta` y `/ejecutar`.
- [x] **Paso 1.3 (REFACTOR):** Limpieza de tipos y convenciones PEP 8 / SOPROTECO §7.1.
- [x] **Paso 1.4:** Correr tests backend: `pytest` con 216 pruebas pasadas y cobertura del 95.52% (superando el 85% requerido).

---

### Tarea 2: Frontend - Visibilidad Exclusiva en Servidor y Respaldo SQL
- [x] **Paso 2.1 (RED):** Escribir pruebas en `frontend/src/test/respaldo.test.tsx`:
  - En dispositivo remoto (`es_servidor: false`): el botón y el formulario de ruta **no existen en el DOM** (`queryByRole("button", { name: /respaldo|copia/i }) === null`).
  - En servidor local (`es_servidor: true`):
    - Se muestra el formulario con el campo para guardar la ruta en el servidor.
    - Se muestra el botón *"Generar copia de seguridad en servidor (.sql)"*.
    - Muestra la información del último archivo con extensión `.sql`.
- [x] **Paso 2.2 (GREEN):**
  - En `frontend/src/features/tablero/TarjetaRespaldo.tsx`:
    - Consulta `GET /api/v1/respaldos/es-servidor`.
    - **Si `!es_servidor`: retorna `null` inmediatamente** (cero elementos en el DOM en clientes remotos).
    - **Si `es_servidor`:**
      - Renderiza tarjeta Glassmorphism con título *"Copia de Seguridad de la Base de Datos"*.
      - Campo de texto: *"Ruta de almacenamiento en el servidor"* con botones *"Validar ruta"* y *"Guardar ruta"*.
      - Información del último respaldo (archivo `.sql`, fecha y tamaño formateado).
      - Botón de acción: *"Generar copia de seguridad en servidor (.sql)"*.
  - En `frontend/src/features/tablero/PaginaTablero.tsx`:
    - Integra `<TarjetaRespaldo esAdmin={esAdmin} />`.
- [x] **Paso 2.3:** Ejecutar suite frontend: pruebas de `respaldo.test.tsx` aprobadas al 100%.
- [x] **Paso 2.4:** Compilar bundle frontend: `npm run build` (`tsc -b && vite build`) exitoso.

---

### Tarea 3: Verificación Integral y Despliegue en Servidor / Docker
- [x] **Paso 3.1:** Transferir código actualizado a los contenedores Docker (`check_backend` y `check_frontend`), instalar `postgresql-client` para `pg_dump` y recargar Nginx/Gunicorn.
- [x] **Paso 3.2:** Probar en el equipo servidor (`localhost`):
  - Comprobado endpoint `GET /api/v1/respaldos/es-servidor` retorna `{"es_servidor": true}` para el servidor.
  - Ejecución de `pg_dump` genera archivos en formato texto SQL legible con opciones `--clean --if-exists`.
  - Verificada nomenclatura exacta: `check_contactos-15-11-2026.sql` y `check_contactos-15-11-2026_01.sql` (109.4 MB cada uno).
- [x] **Paso 3.3:** Probar en un dispositivo remoto conectado por IP de red:
  - Comprobado que `es_servidor` es `false`.
  - Frontend retorna `null` en el DOM (el botón y la tarjeta no existen en dispositivos remotos).
  - Backend rechaza con `403 PermisoDenegado` RFC 7807 si un dispositivo remoto intenta invocar `/validar-ruta`, `/configurar-ruta` o `/ejecutar`.

---

## 5. Criterios de Aceptación (Definición de Terminado)

1. **Formato .sql:** El archivo generado es código SQL puro legible (`.sql`), sin compresión binaria `.dump`, compatible con cualquier motor PostgreSQL o herramienta de administración.
2. **Nomenclatura exacta:** El archivo tiene estrictamente la estructura `<nombre_bd>-DD-MM-YYYY.sql` (ejemplo: `check_contactos-15-11-2026.sql`).
3. **Dispositivos remotos:** Ningún dispositivo ajeno al servidor puede ver el botón de backup en el Tablero ni puede enviar la solicitud al backend.
4. **Opción de ruta en el servidor:** El frontend en el servidor permite escribir y guardar la ruta donde se almacenarán los backups SQL.
5. **Almacenamiento fuera de Docker:** El archivo `.sql` se deposita en la carpeta del disco físico del host configurada por el usuario.
6. **Calidad y pruebas:** Cobertura de backend ≥ 85 %, pruebas de Vitest aprobadas al 100% y compilación limpia.
