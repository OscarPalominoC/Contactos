# Plan de Implementación: Importación segura de bases de datos SQL y sesión persistente

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que la opción *Cargar respaldo* del frontend pueda importar cualquier `.sql` (en particular volcados MySQL del sistema anterior como `CONTACTOS2026-11-07.sql`) sin dejar el software roto ni la base a medio cargar; que importe los usuarios legados con `CLAVE_TEMPORAL_INICIAL`, y que la sesión del frontend persista.

**Architecture:** Toda restauración pasa por una **compuerta de análisis** (`analizar_dump`) que revisa la estructura del archivo antes de tocar la base. Si pasa, se genera un **respaldo automático previo** y la importación corre en **una sola transacción** (todo o nada). Los volcados de PostgreSQL propios se restauran con `psql --single-transaction -v ON_ERROR_STOP=1`; cualquier otro SQL se rechaza. La sesión se vuelve persistente con un refresh token de vida configurable, renovación *single-flight* (sin carreras entre pestañas) y el cierre por inactividad apagado por defecto.

**Tech Stack:** Django 5 + DRF + simplejwt (RS256), PostgreSQL 17, pytest; React 18 + TypeScript + axios + TanStack Query, Vitest.

**Spec:** `resultados.md` (análisis del dump) + mensajes del usuario del 16-11-2026: *"si se importan los usuarios, la clave a utilizar será la CLAVE_TEMPORAL_INICIAL declarada en el .env del backend"* y *"permite la persistencia de la sesión, eso de andar cerrando la sesión a cada rato en el frontend es desesperante"*.

---

## 0. Diagnóstico: qué rompe hoy y qué no

Simulación en seco de `importar_legado` sobre `CONTACTOS2026-11-07.sql` (parser y conversores reales, sin escribir en la BD, verificando `max_length`, `NULL` y rango de enteros de cada campo):

| Tabla legada | Origen | Rechazadas | Duplicadas | Campos que exceden el modelo |
|---|---:|---:|---:|---|
| marca | 544 | 0 | 0 | ninguno |
| linea | 8,757 | 0 | 5 | ninguno |
| contacto | 54,084 | 0 | 0 | ninguno |
| moto | 62,774 | 0 | 3 | ninguno |
| revision | 132,677 | 0 | 2 | ninguno |
| soat1 | 134,951 | 0 | 1 | ninguno |
| bitacora_llamadas | 220,992 | 0 | 0 | ninguno |
| bitacora_llamadas_rtmyg | 122,388 | 110 | 0 | ninguno |
| bitacora_llamadas_soat | 120,268 | 42 | 0 | ninguno |
| entrada_sistema | 38,749 | 0 | 0 | ninguno |

**Este archivo concreto se convierte sin errores.** Lo que puede romper el software está en el **camino de importación**, y aparece con este archivo en cuanto algo falla a mitad, o con el próximo archivo que llegue:

1. **Sin atomicidad.** `importar_legado.handle` vacía las 10 tablas en una transacción que confirma, y luego carga cada tabla en transacciones separadas. Si falla en la tabla 6 (línea truncada → `ValueError`/`IndexError` del parser, texto más largo que el campo → `DataError`, corte de luz), las tablas 6–10 **quedan vacías** y el CRM sin datos.
2. **Sin validar estructura.** Un volcado al que le falte `contacto`, o con otra cantidad de columnas, o truncado (subida incompleta, sin `-- Dump completed`) se acepta: la tabla que falta queda vacía.
3. **Cualquier SQL que no sea MySQL va a `psql` sin control**: sin `ON_ERROR_STOP` ni `--single-transaction` (restauración parcial) y sin verificar que sea un respaldo de Check (un `.sql` cualquiera ejecuta lo que traiga).
4. **El estado se queda en "ejecutando".** En `restaurar_base_datos`, si `call_command("importar_legado")` lanza una excepción no se escribe el error: el tablero muestra "ejecutando" hasta el corte de 15 min.
5. **No hay respaldo previo automático**: lo registrado después del 07-11-2026 se pierde si el operador olvida respaldar.
6. **Subida en RAM**: `FILE_UPLOAD_MAX_MEMORY_SIZE = 500 MB` deja el `.sql` de 122 MB entero en memoria; además, subir dos veces el mismo nombre sobrescribe el archivo anterior sin avisar.

**Sesión.** Causas probables de los cierres frecuentes (a confirmar con las pruebas de las Tareas 7–8):
- `Layouts.tsx` cierra la sesión tras **30 min sin teclado ni clic** (leer o desplazarse no cuenta como actividad).
- **Carreras de renovación**: `focus` y `visibilitychange` se disparan juntos al volver a la pestaña, y `StrictMode` monta dos veces el efecto de inicio. Son dos `POST /auth/refresh` con la misma cookie; con rotación y lista negra, el segundo recibe 401. Si ese 401 cae en el interceptor, la sesión se limpia. Lo mismo pasa entre pestañas.
- **El interceptor cierra sesión ante cualquier fallo del refresh**, también por red caída o 5xx (por ejemplo, con el backend ocupado o reiniciando durante una restauración).
- El refresh token dura 7 días.

## Global Constraints

- Nunca ejecutar SQL del volcado MySQL: solo se extraen valores (`apps/comun/legado.py`). Se mantiene.
- La columna legada `usuario.clave` **nunca se lee** (ni para log, ni para rechazo, ni para el informe). Las cuentas importadas usan `settings.CLAVE_TEMPORAL_INICIAL`, con hash Argon2id y `debe_cambiar_clave=True`.
- Ninguna fila se descarta en silencio: rechazo → `comun_importacion_rechazo`; recorte o mapeo → contador en `Resultado.normalizadas`.
- Regla de cuadre del informe: `insertadas + rechazadas + duplicadas + omitidas == origen`.
- Si la importación falla, la base queda exactamente como estaba (una sola transacción).
- La restauración solo se ejecuta desde el equipo servidor (`es_cliente_servidor_local`) y solo la hace un administrador. Se mantiene.
- Errores de API en RFC 7807 con las excepciones de `apps/comun/excepciones.py` (`DatosInvalidos`, `Conflicto`, `PermisoDenegado`).
- Textos de interfaz en español; accesibilidad WCAG 2.1 AA (identidad en `SKILLS/`).
- Cobertura backend ≥ 85 % (`pytest.ini`).
- Nada de este trabajo se documenta para SOPROTECO.

## Review Focus

1. **Volcado truncado** (subida cortada, disco lleno): debe rechazarse en el análisis, sin vaciar nada → test en Tarea 1 (`test_volcado_sin_marca_final_es_invalido`).
2. **Fallo a mitad de importación** con datos actuales cargados: la base debe quedar intacta → test en Tarea 2 (`test_fallo_a_mitad_no_modifica_datos`).
3. **Cuentas legadas con rol administrador** (en este dump hay 5, entre ellas cuentas de prueba como `01` y `5000`) que quedan con la clave temporal compartida: el análisis debe advertirlo y el diálogo mostrarlo → tests en Tareas 1 y 6.
4. **Cuenta actual del administrador** (`1096212902`) presente también en el legado: no se le cambia la clave ni el rol, y quien restaura no pierde la sesión → test en Tarea 3 (`test_no_modifica_usuario_existente`).
5. **Backend caído u ocupado durante la renovación** (por ejemplo, mientras restaura): el frontend no debe cerrar la sesión por un error de red o 5xx → test en Tarea 8 (`no expira la sesión ante error de red en refresh`).

---

## Estructura de archivos

| Archivo | Acción | Responsabilidad |
|---|---|---|
| `backend/apps/comun/analisis_dump.py` | Crear | Escaneo estructural rápido del `.sql` (tipo, tablas, columnas, completitud, advertencias) |
| `backend/apps/comun/management/commands/importar_legado.py` | Modificar | Importación atómica, compuerta, recorte de longitudes, usuarios, progreso |
| `backend/apps/comun/management/commands/restaurar_base_datos.py` | Modificar | Orquestación: análisis → respaldo previo → importar/psql → estado siempre cerrado |
| `backend/apps/comun/servicios_respaldo.py` | Modificar | Validación síncrona antes de lanzar, flag usuarios, subida sin sobrescribir |
| `backend/apps/comun/views_respaldo.py`, `serializers_respaldo.py`, `config/api_urls.py` | Modificar | Endpoint `POST /respaldos/analizar`, `importar_usuarios`, `progreso` |
| `backend/config/settings.py`, `backend/.env.example` | Modificar | `SESION_DIAS`, `FILE_UPLOAD_MAX_MEMORY_SIZE` |
| `backend/tests/fabricas_dump.py` | Crear | Generador de volcados sintéticos válidos (CREATE TABLE + INSERT + marca final) |
| `backend/tests/test_analisis_dump.py` | Crear | Tests de la Tarea 1 |
| `backend/tests/test_importacion.py`, `test_respaldos.py`, `test_autenticacion.py` | Modificar | Tests de las Tareas 2–5 y 7 |
| `frontend/src/features/tablero/TarjetaRespaldo.tsx`, `services/esquemas.ts` | Modificar | Diálogo de análisis previo, casilla de usuarios, progreso |
| `frontend/src/services/apiClient.ts`, `app/sesion.tsx`, `layouts/Layouts.tsx` | Modificar | Refresh *single-flight*, expiración solo por 401, inactividad configurable |
| `docs/manual-admin.md` | Modificar | Procedimiento de restauración y variables nuevas |

---

### Task 1: Compuerta de análisis del volcado

**Files:**
- Create: `backend/apps/comun/analisis_dump.py`
- Create: `backend/tests/fabricas_dump.py`
- Test: `backend/tests/test_analisis_dump.py`

**Interfaces:**
- Consumes: `TABLAS` de `importar_legado.py` (nombre legado + columnas esperadas).
- Produces:
  ```python
  TipoDump = Literal["mysql_legado", "postgres_check", "desconocido"]

  @dataclass
  class TablaDump:
      nombre: str
      columnas: list[str]
      filas_aprox: int          # tuplas en los INSERT (conteo de "),(" + 1 por línea INSERT)

  @dataclass
  class InformeDump:
      tipo: TipoDump
      completo: bool
      tablas: dict[str, TablaDump]
      errores: list[str]
      advertencias: list[str]
      usuarios: int             # filas de `usuario` (0 si no está)
      usuarios_admin: int       # de ellas, con tipo == "administrador"
      @property
      def valido(self) -> bool: ...   # not errores

  def analizar_dump(ruta: Path) -> InformeDump
  ```
  `fabricas_dump.py`: `volcado_mysql(inserts: str, *, omitir: set[str] = frozenset(), columnas: dict[str, int] | None = None, completo: bool = True, con_usuario: bool = True) -> str`. Genera un encabezado `-- MySQL dump 10.13`, un `CREATE TABLE` por cada tabla de `TABLAS` (columnas `c1..cN` con la N esperada, salvo lo indicado en `columnas`), `usuario` con `nip,nombre,clave,tipo`, los `inserts` dados y `-- Dump completed on ...` si `completo`. Y `volcado_postgres(cuerpo: str = "") -> str` con encabezado y pie de `pg_dump` y `CREATE TABLE public.contactos_contacto` / `public.cuentas_usuario`.

Reglas (se leen líneas en **bytes**, solo comparando prefijos; no se decodifican los INSERT; el archivo de 122 MB debe analizarse en pocos segundos):
- `mysql_legado`: alguna de las primeras 30 líneas contiene `MySQL dump` o `MariaDB`.
  - Falta `-- Dump completed` → error `"El archivo está incompleto: falta la marca final del volcado."`
  - Tabla de `TABLAS` sin `CREATE TABLE` → error `"Falta la tabla `{t}` en el volcado."`
  - Columnas distintas de `Tabla.columnas` → error `"La tabla `{t}` tiene {n} columnas; se esperaban {m}."`
  - `usuario` presente con columnas ≠ `["nip","nombre","clave","tipo"]` → error.
  - Tabla requerida sin INSERT → advertencia `"La tabla `{t}` está vacía: sus datos actuales se reemplazarán por nada."`
  - Tablas no soportadas → una advertencia `"{k} tablas del sistema anterior no se importan."`
  - `usuarios_admin > 0` → advertencia `"{k} cuentas con rol administrador quedarán con la clave temporal inicial."`
  - `usuarios` y `usuarios_admin` se cuentan parseando **solo** la línea INSERT de `usuario` con `_parsear_valores` (columnas 0, 1 y 3; la 2 se ignora).
- `postgres_check`: la primera línea no vacía es `-- PostgreSQL database dump`, el archivo termina con `-- PostgreSQL database dump complete` y contiene `CREATE TABLE public.contactos_contacto` y `CREATE TABLE public.cuentas_usuario`. Si falta algo → error `"No es un respaldo completo de Check Contactos."`
- Otro caso → `desconocido` con error `"Formato no reconocido: solo se aceptan respaldos de Check Contactos o volcados MySQL del sistema anterior."`

- [ ] **Step 1: Escribir los tests que fallan** en `test_analisis_dump.py`:
  - `test_volcado_mysql_valido` → `valido`, `tipo == "mysql_legado"`, `tablas["contacto"].filas_aprox == 2` para un INSERT de 2 tuplas.
  - `test_volcado_sin_marca_final_es_invalido` → `volcado_mysql(..., completo=False)` da `not valido` y el error contiene `"incompleto"`.
  - `test_falta_tabla_requerida` → `omitir={"contacto"}` y el error contiene ``"`contacto`"``.
  - `test_columnas_distintas` → `columnas={"moto": 10}` y el error contiene `"10 columnas; se esperaban 11"`.
  - `test_advierte_admins_legados` → INSERT de usuario con 2 filas `'administrador'`: `usuarios_admin == 2` y hay advertencia.
  - `test_tabla_requerida_vacia_advierte` (sin INSERT de `marca`): `valido` sigue en True y hay advertencia.
  - `test_postgres_propio_valido` / `test_postgres_ajeno_invalido` (`volcado_postgres` sin `cuentas_usuario`).
  - `test_sql_arbitrario_desconocido` → `"DROP TABLE cuentas_usuario;"` da `tipo == "desconocido"` y `not valido`.
  - `test_dump_real_es_valido`, marcado `@pytest.mark.skipif(not Path("../CONTACTOS2026-11-07.sql").exists())`: `valido`, `len(tablas) == 62`, `usuarios == 23`, `usuarios_admin == 5`.
- [ ] **Step 2:** `cd backend && pytest tests/test_analisis_dump.py -v` → FAIL (`ModuleNotFoundError: apps.comun.analisis_dump`).
- [ ] **Step 3:** Implementar `fabricas_dump.py` y `analizar_dump` según las reglas.
- [ ] **Step 4:** `pytest tests/test_analisis_dump.py -v` → PASS.
- [ ] **Step 5:** Commit `feat(respaldo): analizar estructura del volcado antes de restaurar`.

---

### Task 2: Importación atómica, con compuerta y recorte de longitudes

**Files:**
- Modify: `backend/apps/comun/management/commands/importar_legado.py`
- Test: `backend/tests/test_importacion.py`

**Interfaces:**
- Consumes: `analizar_dump`, `volcado_mysql` (Tarea 1).
- Produces:
  ```python
  @dataclass
  class Resultado: ...  # + omitidas: int = 0

  AlAvanzar = Callable[[str, int, int], None]   # (tabla_legada, indice_1_based, total)

  def importar_dump(ruta: Path, *, elegidas: set[str] | None = None,
                    importar_usuarios: bool = True,
                    al_avanzar: AlAvanzar | None = None) -> tuple[list[Resultado], dict[str, int]]
      # (resultados por tabla, huérfanos). Lanza CommandError si el análisis no es válido o algo falla.

  def ajustar_longitudes(instancia: models.Model, resultado: Resultado) -> None
  ```
  El comando `importar_legado` agrega `--sin-usuarios` y delega en `importar_dump`; el informe Markdown sigue igual (columna "Omitidas" nueva).

Comportamiento:
- `importar_dump` llama a `analizar_dump`. Si no es válido o `tipo != "mysql_legado"` → `CommandError("; ".join(errores))` **antes** de cualquier `DELETE`.
- Todo (vaciado, carga de las 10 tablas, usuarios de la Tarea 3, `sanear_datos_legados`, reinicio de secuencias, verificación de cuadre) ocurre dentro de **un** `transaction.atomic()`. El `atomic` interno de `importar_tabla` pasa a ser un savepoint. Si no cuadra, se lanza dentro del bloque y se revierte todo.
- `ajustar_longitudes` se llama en `importar_tabla` después de `convertir`: `CharField` con `max_length` excedido; si es la PK → `FilaInvalidaError(f"{campo} excede {n} caracteres")`; si no, se recorta y se cuenta `r.contar(f"{campo} recortado a {n} caracteres")`.
- Se corrige el docstring: son 10 tablas de datos más `usuario`.

- [ ] **Step 1: Tests que fallan.** Pasar `DUMP_SINTETICO` por `volcado_mysql(...)` (el fixture `dump` actual) para que los tests existentes superen la compuerta. Agregar:
  - `test_fallo_a_mitad_no_modifica_datos`: crear `Contacto(nip="OLD")` y `Moto(placa="OLD1")`; volcado válido cuyo INSERT de `revision` está truncado (`"INSERT INTO `revision` VALUES (NULL,'C1'"`). `call_command("importar_legado", ...)` lanza `CommandError`; `Contacto.objects.filter(nip="OLD").exists()`, `Moto.objects.count() == 1` y `ImportacionRechazo.objects.count()` igual al de antes.
  - `test_volcado_invalido_no_borra_nada`: `omitir={"contacto"}` → `CommandError` con `"Falta la tabla"` y `Contacto` intacto.
  - `test_texto_largo_se_recorta`: contacto con dirección de 600 caracteres → se inserta con `len(direccion) == max_length` y el informe contiene `"direccion recortado a"`.
  - `test_pk_larga_se_rechaza`: placa de 40 caracteres → 1 `ImportacionRechazo` con `"excede"`.
  - `test_al_avanzar_recibe_cada_tabla`: `importar_dump(..., al_avanzar=registro.append-like)` registra 10 llamadas, la última `("entrada_sistema", 10, total)`.
- [ ] **Step 2:** `pytest tests/test_importacion.py -v` → los nuevos FAIL.
- [ ] **Step 3:** Implementar `importar_dump`, `ajustar_longitudes`, `omitidas` y el comando delegando.
- [ ] **Step 4:** `pytest tests/test_importacion.py -v` → PASS (también los tests previos de conteos e idempotencia).
- [ ] **Step 5:** Commit `fix(importacion): importar el legado en una sola transacción y validar longitudes`.

---

### Task 3: Importación de usuarios legados con `CLAVE_TEMPORAL_INICIAL`

**Files:**
- Modify: `backend/apps/comun/management/commands/importar_legado.py`
- Test: `backend/tests/test_importacion.py`

**Interfaces:**
- Consumes: `importar_dump` (Tarea 2), `filas_de_tabla`, `Usuario`, `ROLES`, `Usuario.sincronizar_grupo()`.
- Produces: `def importar_usuarios(ruta: Path) -> Resultado` (`tabla="usuario"`), llamada desde `importar_dump` dentro de la misma transacción cuando `importar_usuarios=True`.

Reglas:
- Se usan solo las columnas 0 (`nip`), 1 (`nombre`) y 3 (`tipo`). **La columna 2 (`clave`) no se lee**, y `fila_origen` de los rechazos de esta tabla guarda `repr([f[0], f[1], f[3]])`.
- `nip = n.mayusculas_sin_espacios(f[0])`: si está vacío o supera 20 caracteres → rechazo.
- `nombre = n.texto(f[1]).upper()`. `rol = tipo.lower()` si está en `ROLES`; si no, `"usuario"` y `r.contar("tipo '{x}' → usuario")`.
- Si el `nip` **ya existe** en `cuentas_usuario` → no se toca nada (clave, rol, nombre, estado) y cuenta en `omitidas`. Los usuarios nunca se borran.
- Usuario nuevo: `set_password(settings.CLAVE_TEMPORAL_INICIAL.strip())`, `debe_cambiar_clave=True`, `is_active=True`, `sincronizar_grupo()`.
- Si `CLAVE_TEMPORAL_INICIAL` está vacía → no se crea ninguna cuenta, todas cuentan como `omitidas` y se agrega `r.contar("CLAVE_TEMPORAL_INICIAL no configurada: usuarios no importados")`. La restauración de datos continúa.

- [ ] **Step 1: Tests que fallan** (con `@override_settings(CLAVE_TEMPORAL_INICIAL="Temporal#2026x")`, el fixture `grupos` y el dump sintético, que ya trae `('100','ANA','clave-legada-que-no-se-usa','usuario')`):
  - `test_importa_usuarios_con_clave_temporal_inicial`: `u = Usuario.objects.get(nip="100")`, `u.check_password("Temporal#2026x")`, `not u.check_password("clave-legada-que-no-se-usa")`, `u.debe_cambiar_clave`, `u.rol == "usuario"`.
  - `test_no_modifica_usuario_existente`: crear un admin `nip="100"` con clave `"Actual#2026xx"` y rol `administrador`; tras importar, `check_password("Actual#2026xx")` y el rol sigue igual; `omitidas == 1`.
  - `test_tipo_desconocido_mapea_a_usuario` (`'gerente'`).
  - `test_sin_clave_temporal_no_crea_usuarios` (`CLAVE_TEMPORAL_INICIAL=""`): `Usuario.objects.filter(nip="100").exists()` es False y la importación termina con éxito.
  - `test_sin_usuarios_flag`: `call_command("importar_legado", dump, "--sin-usuarios")` no crea `100`.
  - `test_clave_legada_no_aparece_en_rechazos_ni_informe`: un usuario con nip vacío y clave `"SECRETO-LEGADO"` → ningún `ImportacionRechazo.fila_origen` ni el texto del informe contiene `"SECRETO-LEGADO"`.
- [ ] **Step 2:** `pytest tests/test_importacion.py -k usuario -v` → FAIL.
- [ ] **Step 3:** Implementar `importar_usuarios` y conectarlo en `importar_dump`.
- [ ] **Step 4:** `pytest tests/test_importacion.py -v` → PASS.
- [ ] **Step 5:** Commit `feat(importacion): importar usuarios legados con CLAVE_TEMPORAL_INICIAL y cambio obligatorio`.

---

### Task 4: Orquestación robusta de `restaurar_base_datos`

**Files:**
- Modify: `backend/apps/comun/management/commands/restaurar_base_datos.py`
- Test: `backend/tests/test_respaldos.py`

**Interfaces:**
- Consumes: `analizar_dump` (T1), `importar_dump` (T2/T3), comando `respaldar_base_datos --destino`, `obtener_ruta_respaldo`, `escribir_estado_ejecucion`.
- Produces: comando `restaurar_base_datos --origen <ruta> [--sin-usuarios]`. Claves que escribe en el archivo de estado: `ejecutando`, `accion="restaurar"`, `etapa` ∈ {`"analizando"`, `"respaldo_previo"`, `"importando"`, `"finalizado"`}, `tabla_actual`, `avance`, `total`, `respaldo_previo` (nombre del archivo), `exitoso`, `mensaje` | `error`.

Flujo (todo el `handle` dentro de `try/except Exception` que **siempre** escribe `ejecutando=False, exitoso=False, error=str(exc)` y relanza):
1. `analizar_dump`. Si no es válido → error sin tocar nada.
2. `call_command("respaldar_base_datos", destino=str(obtener_ruta_respaldo()))`. Si falla → error `"No se pudo crear el respaldo previo; la base de datos no se modificó."`.
3. `mysql_legado` → `importar_dump(..., importar_usuarios=not sin_usuarios, al_avanzar=...)`, que escribe `etapa/tabla_actual/avance/total` en el estado.
4. `postgres_check` → `psql` con `-v ON_ERROR_STOP=1 --single-transaction` además de los argumentos actuales.
5. Se elimina `es_dump_mysql`.

- [ ] **Step 1: Tests que fallan**:
  - `test_restaurar_rechaza_sql_desconocido`: archivo `"DROP TABLE cuentas_usuario;"` → `CommandError`; `subprocess.run` (mock) no se llama; el estado tiene `ejecutando is False` y `"Formato no reconocido"` en `error`.
  - `test_restaurar_psql_usa_transaccion_unica`: `volcado_postgres()` y `subprocess.run` mockeado → `"--single-transaction" in args` y `"ON_ERROR_STOP=1" in args`.
  - `test_falla_respaldo_previo_no_importa`: mockear `call_command` de `respaldar_base_datos` para que lance; `importar_dump` (mock) no se llama; el error contiene `"respaldo previo"`.
  - `test_error_en_importacion_cierra_estado`: `importar_dump` mockeado con `RuntimeError("x")` → estado `ejecutando False`, `exitoso False`.
  - `test_restaurar_legado_reporta_progreso`: con el dump sintético y el respaldo mockeado, el último estado tiene `etapa == "finalizado"`, `exitoso`, y en algún momento se escribió `total == 10`.
  - Adaptar `test_comando_management_restaurar_base_datos` para usar `volcado_postgres()`.
- [ ] **Step 2:** `pytest tests/test_respaldos.py -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `pytest tests/test_respaldos.py -v` → PASS.
- [ ] **Step 5:** Commit `fix(respaldo): restauración con análisis previo, respaldo automático y estado siempre cerrado`.

---

### Task 5: API de análisis, opción de usuarios y subida a disco

**Files:**
- Modify: `backend/apps/comun/servicios_respaldo.py`, `views_respaldo.py`, `serializers_respaldo.py`, `backend/config/api_urls.py`, `backend/config/settings.py`
- Test: `backend/tests/test_respaldos.py`

**Interfaces:**
- Consumes: `analizar_dump`, `InformeDump` (T1); comando con `--sin-usuarios` (T4).
- Produces:
  - `POST /api/v1/respaldos/analizar` con body `{ruta_archivo: str}` → 200 `AnalisisDumpResponseSerializer`: `{tipo, valido, completo, errores: [str], advertencias: [str], usuarios: int, usuarios_admin: int, tablas_importables: [{nombre, filas_aprox}]}`. `tablas_importables` = las de `TABLAS` presentes, en ese orden. Solo admin y solo desde el servidor (`PermisoDenegado` si no).
  - `RestaurarRespaldoRequestSerializer.importar_usuarios = BooleanField(default=True)`.
  - `ejecutar_restauracion_consola(ruta_archivo_str: str, importar_usuarios: bool = True)`: tras validar la ruta, ejecuta `analizar_dump` en el momento; si no es válido → `DatosInvalidos(" ".join(errores))` **sin** escribir el estado ni lanzar el subproceso. Agrega `--sin-usuarios` si corresponde.
  - `RespaldoEstadoResponseSerializer.progreso`: objeto nullable `{etapa, tabla_actual, avance, total}` leído del archivo de estado.
  - `guardar_archivo_respaldo_subido`: si el nombre ya existe, guarda como `nombre-1.sql`, `nombre-2.sql`, …
  - `settings.FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024` (las subidas grandes van a un archivo temporal; el límite de 500M de nginx se mantiene).

- [ ] **Step 1: Tests que fallan**:
  - `test_analizar_devuelve_informe` (admin local, volcado sintético): 200, `valido is True`, `tablas_importables[0]["nombre"] == "marca"`.
  - `test_analizar_rechaza_remoto` → 403. `test_analizar_requiere_admin` → 403.
  - `test_restaurar_rechaza_invalido_sin_lanzar`: volcado `completo=False` → 400, `Popen` no llamado y el estado no queda `ejecutando`.
  - `test_restaurar_sin_usuarios_pasa_flag`: `importar_usuarios: false` → `"--sin-usuarios" in comando`.
  - `test_estado_expone_progreso`.
  - `test_subir_no_sobrescribe`: subir `a.sql` dos veces → la segunda respuesta tiene `archivo == "a-1.sql"`.
- [ ] **Step 2:** `pytest tests/test_respaldos.py -v` → FAIL.
- [ ] **Step 3:** Implementar y documentar en `extend_schema`.
- [ ] **Step 4:** `pytest -q` (suite completa, cobertura ≥ 85 %) → PASS.
- [ ] **Step 5:** Commit `feat(respaldo): endpoint de análisis previo y opción de importar usuarios`.

---

### Task 6: Frontend: análisis, confirmación y progreso de la restauración

**Files:**
- Modify: `frontend/src/features/tablero/TarjetaRespaldo.tsx`, `frontend/src/services/esquemas.ts`
- Test: `frontend/src/test/respaldo.test.tsx`

**Interfaces:**
- Consumes: `POST /respaldos/analizar`, `POST /respaldos/restaurar {ruta_archivo, importar_usuarios}`, `estado.progreso` (T5); `Dialogo` de `components/ui/Dialogo.tsx`.
- Produces: `analisisDumpSchema` (zod) y `progresoSchema` en `esquemas.ts`.

Comportamiento: al pulsar **"Restaurar base de datos"** se llama a *analizar* y se abre un `Dialogo` (título `"Confirmar restauración"`) con:
- el tipo (`"Volcado del sistema anterior (MySQL)"` / `"Respaldo de Check Contactos"`) y la tabla de `tablas_importables` con `filas_aprox`;
- los errores en un `Aviso` de error; si existen, el botón de confirmar queda deshabilitado;
- las advertencias en un `Aviso` de advertencia;
- si `usuarios > 0`: la casilla **"Importar {usuarios} usuarios del archivo"**, marcada por defecto, con la ayuda *"Las cuentas nuevas usarán la clave temporal inicial del servidor y deberán cambiarla al ingresar. Las cuentas existentes no se modifican."*;
- el texto *"Antes de reemplazar los datos se generará un respaldo automático."* y el botón **"Reemplazar datos y restaurar"**.

Mientras `estado.ejecutando`: la barra de progreso `role="progressbar"` con `aria-valuenow={avance}`, `aria-valuemax={total}` y la etiqueta `"Importando {tabla_actual} ({avance}/{total})"`.

- [ ] **Step 1: Tests que fallan** (mismo estilo de mocks que `respaldo.test.tsx`):
  - `muestra errores del análisis y deshabilita confirmar`.
  - `envía importar_usuarios=false al desmarcar la casilla`.
  - `muestra advertencia de administradores legados`.
  - `muestra progreso con aria-valuenow`.
- [ ] **Step 2:** `cd frontend && npx vitest run src/test/respaldo.test.tsx` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `npx vitest run && npx tsc -b && npx eslint src` → PASS.
- [ ] **Step 5:** Commit `feat(respaldo): confirmación con análisis previo y progreso de restauración`.

---

### Task 7: Sesión persistente: backend

**Files:**
- Modify: `backend/config/settings.py`, `backend/.env.example`
- Test: `backend/tests/test_autenticacion.py`

**Interfaces:**
- Produces: `settings.SESION_DIAS: int = env.int("SESION_DIAS", default=30)`. `SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] = timedelta(days=SESION_DIAS)` y `SESSION_COOKIE_AGE = SESION_DIAS * 24 * 3600`. La rotación ya hace la ventana deslizante: cada refresh emite una cookie nueva con la vida completa. `.env.example` documenta `SESION_DIAS=30`.

- [ ] **Step 1: Tests que fallan**:
  - `test_login_cookie_dura_sesion_dias`: `Set-Cookie` de `refresh_token` con `Max-Age=2592000`.
  - `test_refresh_renueva_vida_completa`: tras `/auth/refresh`, la nueva cookie también tiene `Max-Age=2592000`.
  - `test_cambio_de_clave_sigue_revocando`: tras `cambiar_clave`, el refresh anterior da 401 (no debe regresar).
- [ ] **Step 2:** `pytest tests/test_autenticacion.py -v` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `pytest tests/test_autenticacion.py -v` → PASS.
- [ ] **Step 5:** Commit `feat(auth): duración de sesión configurable (SESION_DIAS, 30 días por defecto)`.

---

### Task 8: Sesión persistente: frontend

**Files:**
- Modify: `frontend/src/services/apiClient.ts`, `frontend/src/app/sesion.tsx`, `frontend/src/layouts/Layouts.tsx`, `frontend/src/vite-env.d.ts`
- Test: `frontend/src/test/apiClient.test.ts`, `frontend/src/test/sesion.test.tsx`, `frontend/src/test/layout.test.tsx`

**Interfaces:**
- Produces:
  - `refrescarSesion(cliente)` *single-flight*: una promesa en curso compartida dentro de la pestaña y, si existe `navigator.locks`, envuelta en `navigator.locks.request("check-contactos-refresh", …)` para serializar entre pestañas. Firma sin cambios.
  - `export function esSesionExpirada(error: unknown): boolean`: true solo si el refresh respondió 401 o 403.
  - El interceptor llama a `alExpirarSesion` **solo** si `esSesionExpirada(errorRefresco)`; ante red caída o 5xx rechaza la petición original sin cerrar la sesión.
  - En `sesion.tsx`: lo mismo en el arranque (`catch` → `limpiar()` solo si `esSesionExpirada`; si no, estado `"autenticado"` pendiente de reintento al recuperar foco). `renovarSilencioso` omite la llamada si la última renovación exitosa fue hace menos de 60 s.
  - `Layouts.tsx`: `INACTIVIDAD_MS = Number(import.meta.env.VITE_INACTIVIDAD_MINUTOS ?? 0) * 60_000`. Con 0 el hook no programa temporizadores ni muestra aviso. Si se activa, también cuentan como actividad `wheel`, `scroll` y `mousemove` (con un intervalo mínimo de 5 s entre reinicios).

- [ ] **Step 1: Tests que fallan**:
  - `apiClient.test.ts`: `dos refrescos concurrentes hacen un solo POST /auth/refresh`; `no expira la sesión ante error de red en refresh` (refresh → error sin respuesta; `alExpirarSesion` no se llama); `expira la sesión con 401 en refresh`.
  - `layout.test.tsx`: `sin VITE_INACTIVIDAD_MINUTOS no cierra sesión tras 31 min` (timers falsos, `cerrar` no llamado y sin aviso); `con VITE_INACTIVIDAD_MINUTOS=1 avisa y cierra` (`vi.stubEnv`).
  - `sesion.test.tsx`: `arranque en StrictMode no cierra la sesión` (el adaptador da 200 en el primer refresh y 401 en el segundo; con *single-flight* solo se hace uno y el estado final es `"autenticado"`).
- [ ] **Step 2:** `npx vitest run` → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `npx vitest run && npx tsc -b && npx eslint src` → PASS.
- [ ] **Step 5:** Commit `fix(sesion): renovación sin carreras y sin cierre por inactividad por defecto`.

---

### Task 9: Verificación de punta a punta con el volcado real y documentación

**Files:**
- Modify: `docs/manual-admin.md`

- [ ] **Step 1:** Con el stack local (`scripts/iniciar.ps1`), restaurar `F:\Check\CONTACTOS2026-11-07.sql` desde *Tablero → Cargar respaldo*. Lo esperado:
  - el diálogo muestra el tipo MySQL, las 10 tablas, la advertencia de 52 tablas no importadas, 23 usuarios y la advertencia de 5 administradores;
  - se crea un respaldo previo en la carpeta configurada;
  - el progreso avanza 1/10 … 10/10;
  - el informe en `logs/importacion-*.md` cuadra en todas las filas, con las mismas cifras de la tabla de la sección 0 y `usuario` con `insertadas + omitidas = 23`.
- [ ] **Step 2:** Ingresar con un `nip` legado y `CLAVE_TEMPORAL_INICIAL` → la app obliga a cambiar la clave. El administrador actual sigue entrando con su clave de siempre.
- [ ] **Step 3: Prueba de atomicidad real.** Copiar el dump, cortarle los últimos 10 MB y restaurarlo → el diálogo lo bloquea por "incompleto". Copiar el dump, borrar `)` del final de una línea INSERT de `revision` (conservando la marca final) y restaurarlo → falla y los conteos de `contactos_contacto` y `vehiculos_moto` siguen iguales a los de antes.
- [ ] **Step 4: Sesión.** Ingresar, dejar la pestaña abierta 40 min sin tocarla, cambiar de pestaña varias veces, abrir una segunda pestaña y recargar ambas → la sesión sigue activa. Reiniciar el contenedor del backend con la app abierta → la sesión sigue activa cuando vuelve.
- [ ] **Step 5:** Actualizar `docs/manual-admin.md`: el flujo de restauración (análisis, respaldo previo automático, usuarios con clave temporal y cambio obligatorio, qué tablas no se importan) y las variables `CLAVE_TEMPORAL_INICIAL`, `SESION_DIAS` y `VITE_INACTIVIDAD_MINUTOS`.
- [ ] **Step 6:** `cd backend && pytest -q` y `cd frontend && npx vitest run` → todo en verde. Commit `docs: procedimiento de restauración segura y sesión persistente`.
