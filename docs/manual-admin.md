---
persona: oscar
ia: Claude Code (Claude Opus 5.5)
actualizado: 2026-11-16 18:05
zona_horaria: America/Bogota
---
# Manual de administración — Check Contactos

## Django Admin

- **URL:** `http://127.0.0.1:8000/<ADMIN_URL>` (el valor de `ADMIN_URL` está en `backend/.env`). La ruta `/admin/` no existe a propósito.
- **Acceso:** solo usuarios con rol `administrador` (`is_staff`). El ingreso usa la misma clave y el mismo bloqueo por intentos fallidos que la aplicación.
- **Funciones:**
  - Ver y editar contactos, motos, RTM, SOAT, llamadas y catálogos, con búsqueda, filtros y navegación por fecha.
  - En **Usuarios**, la acción **Reiniciar clave temporal** muestra la clave nueva una sola vez y obliga a cambiarla. Reiniciar también levanta el bloqueo de axes.
  - **Común → Registros de auditoría:** quién creó, editó o anuló qué, y cuándo (solo lectura).
  - **Común → Rechazos de importación:** las filas del legado que no se pudieron cargar, con el motivo.
  - **Cuentas → Ingresos:** los ingresos exitosos y fallidos, más los 38 749 heredados de `entrada_sistema`.
  - **Axes:** intentos y bloqueos de acceso.

## Roles (propuesta pendiente de confirmar con la empresa)

| Recurso | administrador | ingeniero | técnico | usuario |
|---|---|---|---|---|
| Contactos | CRUD | Ver | Ver | Ver, crear y editar |
| Motos | CRUD | Ver y editar | Ver | Ver, crear y editar |
| Marcas y líneas | CRUD | CRUD | Ver | Ver |
| Revisiones RTM | CRUD y anular | Ver, crear y editar | Ver y crear | Ver, crear y editar |
| SOAT | CRUD y anular | Ver | Ver | Ver, crear y editar |
| Llamadas | CRUD | Ver | Ver | Ver, crear y editar |
| Usuarios y Admin | Sí | No | No | No |

La matriz se carga con la migración `cuentas/0002_roles.py`. Para cambiarla, cree una migración nueva; no edite una migración ya aplicada.

## Importación del legado

```bash
cd backend
.venv/Scripts/python.exe manage.py importar_legado ../CONTACTOS_recuperado_2026-11-07.sql
```

Resultado de la carga del 2026-11-14 (detalle en `logs/importacion-2026-11-14-1655.md`):

| Tabla legada | Origen | Insertadas | Rechazadas | Claves repetidas |
|---|---|---|---|---|
| contacto | 54 084 | 54 084 | 0 | 0 |
| moto | 62 774 | 62 771 | 0 | 3 |
| marca / linea | 544 / 8 757 | 544 / 8 752 | 0 | 0 / 5 |
| revision | 132 677 | 132 675 | 0 | 2 |
| soat1 | 134 951 | 134 950 | 0 | 1 |
| bitacora_llamadas | 220 992 | 220 992 | 0 | 0 |
| bitacora_llamadas_rtmyg | 122 388 | 122 278 | 110 (fecha `0000-00-00`) | 0 |
| bitacora_llamadas_soat | 120 268 | 120 226 | 42 (fecha `0000-00-00`) | 0 |
| entrada_sistema | 38 749 | 38 749 | 0 | 0 |

En todas las tablas, insertadas + rechazadas + repetidas = origen; ninguna fila se perdió. Las rechazadas y repetidas quedan en **Rechazos de importación**.

Huérfanos que se conservaron (la empresa decide qué hacer con ellos):

| Caso | Cantidad |
|---|---|
| Motos sin contacto | 3 642 |
| Llamadas de cumpleaños sin contacto | 519 |
| Revisiones con placa sin moto | 18 |
| SOAT con placa sin moto | 28 |
| Llamadas RTM con placa sin moto | 31 |
| Llamadas SOAT con placa sin moto | 23 |

## Restaurar un respaldo

Desde **Tablero → Cargar respaldo** (solo un administrador, y solo desde el equipo servidor) o con `manage.py restaurar_base_datos --origen <ruta.sql>`.

1. **Análisis previo.** Antes de tocar nada, el archivo se analiza y el diálogo muestra el tipo (PostgreSQL o volcado MySQL legado), las tablas que se importarán, las que no, y la cantidad de cuentas. Un archivo incompleto (sin la marca final, por ejemplo una subida cortada o un disco lleno) se bloquea con el motivo «incompleto» y no se modifica la base.
2. **Respaldo previo automático.** Si el análisis es válido, se crea un respaldo de la base actual en la carpeta de respaldos configurada. Si no se puede crear, la restauración se cancela y la base no cambia.
3. **Importación todo o nada.** El volcado MySQL se importa en una sola transacción: si algo falla, la base queda exactamente como estaba. El progreso se muestra por tabla (1/10 … 10/10) y, en las demás etapas, con un texto («Analizando archivo…», «Creando respaldo previo…»). Si un archivo corrupto falla a mitad de la importación, la base queda intacta y el error indica la tabla con datos ilegibles. El respaldo previo nunca borra, al depurar los antiguos, el archivo que se está restaurando.
4. **Qué se importa.** Las 10 tablas de Check Contactos (contacto, moto, marca, línea, revisión, SOAT, llamadas y entrada al sistema) y las cuentas de usuario. Las demás tablas del sistema anterior (51 en el volcado del 2026-11-07) **no se importan**; el diálogo lo advierte.
5. **Cuentas importadas.** Se crean con la clave `CLAVE_TEMPORAL_INICIAL` y el cambio de clave es obligatorio en el primer ingreso. La columna de claves del legado nunca se lee. **Las cuentas que ya existen no se tocan** (ni su clave ni su rol), de modo que quien restaura conserva su sesión. **Las cuentas con rol administrador se crean inactivas**: el análisis lo advierte y un administrador actual debe activarlas desde **Usuarios** (active solo las que correspondan a personas reales; las de prueba, como `01` o `5000`, déjelas inactivas). **Si `CLAVE_TEMPORAL_INICIAL` es el valor por defecto público del código**, las cuentas se importan igual, pero el análisis lo advierte y el informe pide cambiarla: quien conozca ese valor podría entrar a una cuenta importada que aún no haya cambiado su clave. Defina una clave propia en `backend/.env` antes de restaurar. Si la variable está vacía, no se importa ninguna cuenta. Con `--sin-usuarios` no se importan cuentas.
6. **Informe.** Queda en `logs/importacion-AAAA-MM-DD-HHMM.md`. Cada tabla debe cuadrar: insertadas + rechazadas + repetidas + omitidas = origen. Las filas rechazadas quedan en **Rechazos de importación**. Si alguna tabla no cuadra, la importación se revierte completa y el informe se escribe igual, encabezado con «IMPORTACIÓN REVERTIDA», para ubicar la tabla con problemas.

## Variables de entorno (`backend/.env` y frontend)

| Variable | Qué hace | Valor por defecto |
|---|---|---|
| `CLAVE_TEMPORAL_INICIAL` | Clave de las cuentas importadas del legado. **Defina la suya**: el código trae un valor por defecto público; si se mantiene, el análisis y el informe de importación lo advierten. | Tiene un valor por defecto público en el código: reemplácelo definiendo el suyo en `backend/.env` (`CLAVE_TEMPORAL_INICIAL=<defina una clave propia>`). |
| `SESION_DIAS` | Días de duración de la sesión; se renueva con el uso. | 30 |
| `VITE_INACTIVIDAD_MINUTOS` | Frontend. Minutos de inactividad tras los cuales se cierra la sesión. | Sin definir: no se cierra por inactividad |

## Cuentas y claves

- **Origen de las cuentas:** se crearon con `crear_cuentas_temporales`. La columna `clave` del legado nunca se leyó.
- **Entrega de claves:** `CREDENCIALES_TEMPORALES.md` se entrega en persona. Destrúyalo cuando todos hayan cambiado su clave. En la pantalla Usuarios, quien aún no la ha cambiado aparece con la insignia «Clave temporal»; en Django Admin se puede filtrar por «debe cambiar clave».
- **Desactivar una cuenta:** cierra todas sus sesiones al instante.
- **Política de claves (desarrollo local):** mínimo 5 caracteres; se permite incluir nombre o documento. Solo se impide repetir la clave actual o una de las 3 anteriores. Se define en `AUTH_PASSWORD_VALIDATORS` (`backend/config/settings.py`); para producción conviene volver a exigir longitud ≥ 12 y los validadores de similitud, claves comunes y solo numéricas.
- **Cambiar el propio nombre:** cada usuario lo hace desde su nombre en la barra superior (`PATCH /api/v1/auth/yo`, queda en la auditoría). No disponible mientras la clave sea temporal.
- **Auditoría de accesibilidad:** `scripts\e2e.ps1` corre axe-core (WCAG 2.1 A/AA) en todas las pantallas. Contra Docker: `E2E_URL=http://localhost:5174` y, si no está descargado el navegador de Playwright, `E2E_CANAL=chrome`.

## Operación

- **Arranque:** `scripts\iniciar.ps1`.
- **Respaldo:** `scripts\respaldar.ps1`.
- **Rendimiento medido** en el equipo local con los datos reales (50 peticiones por ruta):

  | Ruta | p95 |
  |---|---|
  | Listados de 120 a 220 mil filas | ≤ 194 ms |
  | Búsqueda de contactos por nombre | 84 ms |
  | Tablero | 284 ms |

  Todas quedan por debajo del objetivo de 1 s.
- **Errores:** cada respuesta trae `X-Request-ID`. El mismo código aparece en el aviso de la pantalla y en los registros de la consola del backend.
