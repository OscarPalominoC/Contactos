# Análisis de la Base de Datos `CONTACTOS2026-11-07.sql` frente al Backend

**Fecha del análisis:** 16 de noviembre de 2026  
**Archivo analizado:** `F:\Check\CONTACTOS2026-11-07.sql` (122.13 MB / 128,064,188 bytes)  
**Entorno de destino:** Backend Django 5.x / PostgreSQL 17 (Dockerizado / Servidor Local)

---

## 1. Resumen Ejecutivo: ¿Rompe el backend?

| Método de carga | ¿Rompe el backend? | Diagnóstico |
|---|:---:|---|
| **Restauración directa con `psql`** (por consola SQL estándar) | **SÍ, TOTALMENTE** | Fallará de inmediato en la línea 1. El archivo es un dump nativo de **MySQL/MyISAM**, incompatible sintácticamente con PostgreSQL (tipos `int unsigned`, directivas `ENGINE=MyISAM`, comentarios `/*!40101 ... */`, nombres de tablas sin prefijo `app_`). |
| **Restauración mediante el sistema** (`TarjetaRespaldo` / `restaurar_base_datos`) | **NO** | El sistema cuenta con detección inteligente del dump legado de MySQL y redirige la carga hacia el motor de importación estructurada (`importar_legado.py`), el cual procesa los datos en streaming sin ejecutar SQL directo. |

---

## 2. Hallazgos Principales: ¿Qué le haría falta o qué riesgos existen?

Si se carga este archivo a través del módulo de restauración del sistema, el backend **NO se romperá**, pero se deben tener en cuenta las siguientes **4 advertencias críticas**:

### A. Riesgo de sobreescritura de datos nuevos
El proceso de importación del legado vacía (`DELETE`) las 10 tablas del dominio de negocio antes de insertar los registros del dump para garantizar idempotencia.  
> **Consecuencia:** Cualquier cliente, moto, revisión o llamada registrada en el sistema después del 7 de noviembre de 2026 se perderá si no se genera previamente un respaldo actual.

### B. Cuentas de usuario y claves de acceso (`usuario`)
En el archivo SQL existe una tabla `usuario` con 23 registros cuyas contraseñas (`clave`) están en texto plano (`varchar(10)`).  
El backend moderno de Check Contactos utiliza hashes criptográficos **Argon2id**, autenticación JWT RS256 y control de acceso basado en roles (`admin`, `supervisor`, `asesor`, `auditor`).  
> **Comportamiento:** El importador **NO toca la tabla de usuarios** de Django (`cuentas_usuario`). Esto es seguro porque evita que tu usuario administrador actual (ej. `1096212902`) sea borrado o desconfigurado.  
> **Qué hace falta:** Si hay usuarios del archivo antiguo que requieran ingresar al nuevo sistema, sus cuentas deben crearse o sincronizarse con el comando:
> ```bash
> python manage.py crear_cuentas_temporales scripts/credenciales_temporales.json
> ```
> O crearse directamente desde el panel de administración / gestión de usuarios de la interfaz.

### C. Existen 52 tablas del sistema antiguo que no se migran
El archivo `CONTACTOS2026-11-07.sql` contiene **62 tablas en total**. El sistema CRM actual de Check Contactos utiliza y migra únicamente las **10 tablas activas del negocio**.  
Las otras **52 tablas** corresponden a módulos del antiguo software de diagnóstico físico del CDA (calibración de gases, fichas de hardware, facturación antigua, RUNT, bitácoras de fallas de equipos, talleres mecánicos, etc.).  
> **Consecuencia:** Omitir estas 52 tablas **no rompe el backend**, pues no están definidas en los modelos del CRM actual. Sin embargo, si la empresa esperaba consultar facturas antiguas o registros de calibración de gases dentro de Check Contactos, esos datos no estarán disponibles en la interfaz.

### D. Registros rechazados y filas huérfanas
El dump original contiene datos con inconsistencias heredadas del sistema antiguo:
- **152 filas rechazadas** en llamadas RTM (110) y llamadas SOAT (42) debido a identificadores o formatos de fecha mal estructurados en el legado.
- **11 claves duplicadas** en el dump legado (`linea`: 5, `moto`: 3, `revision`: 2, `soat1`: 1).
- **3,642 motos huérfanas** cuyo documento de contacto no existe en la tabla de clientes.
- **519 llamadas de cumpleaños** asociadas a clientes inexistentes.
> **Comportamiento:** El backend **no se rompe** porque los modelos de Django tienen configurado `db_constraint=False` (claves foráneas lógicas sin restricción estricta de base de datos) y todas las filas rechazadas se guardan automáticamente en la tabla de auditoría `comun_importacion_rechazo`.

---

## 3. Mapeo Detallado de Tablas: Dump vs Backend

### 3.1. Tablas Activas del CRM Migradas (~896,000 registros)

Todas las tablas centrales del CRM coinciden exactamente en cantidad de columnas y estructura con los conversores del backend:

| Tabla en dump MySQL | Registros en dump | Modelo Django / Tabla PostgreSQL | Columnas esperadas | Estado |
|---|---:|---|:---:|:---:|
| `marca` | 544 | `vehiculos.Marca` (`vehiculos_marca`) | 2 | Coincide 100% |
| `linea` | 8,757 | `vehiculos.Linea` (`vehiculos_linea`) | 2 | Coincide 100% |
| `contacto` | 54,084 | `contactos.Contacto` (`contactos_contacto`) | 12 | Coincide 100% |
| `moto` | 62,774 | `vehiculos.Moto` (`vehiculos_moto`) | 11 | Coincide 100% |
| `revision` | 132,677 | `revisiones.Revision` (`revisiones_revision`) | 14 | Coincide 100% |
| `soat1` | 134,951 | `revisiones.Soat` (`revisiones_soat`) | 7 | Coincide 100% |
| `bitacora_llamadas` | 220,992 | `llamadas.LlamadaCumpleanos` (`llamadas_cumpleanos`) | 8 | Coincide 100% |
| `bitacora_llamadas_rtmyg` | 122,388 | `llamadas.LlamadaRtm` (`llamadas_rtm`) | 9 | Coincide 100% |
| `bitacora_llamadas_soat` | 120,268 | `llamadas.LlamadaSoat` (`llamadas_soat`) | 9 | Coincide 100% |
| `entrada_sistema` | 38,749 | `cuentas.Ingreso` (`cuentas_ingreso`) | 3 | Coincide 100% |
| **TOTAL** | **~896,184** | — | — | **Soportadas** |

---

### 3.2. Tablas Omitidas del Antiguo Sistema (52 Tablas)

Estas tablas pertenecen a la operación del CDA que no hace parte del CRM Check Contactos:

| Categoría | Tablas encontradas en `CONTACTOS2026-11-07.sql` |
|---|---|
| **Calibración y Gases** | `calibracion_gases` (20), `hermeticidad_gases` (8), `bitacora_gases` (0) |
| **Hardware y Mantenimiento de Pistas** | `verificacion_diaria` (1,211), `hardware_software` (102), `fecha_mantenimiento` (47), `hardware_caracteristicas` (30), `fecha_planmantenimientoycalibracion` (10), `mantenimiento_instalaciones` (6), `bitacora_fallas` (6), `hoja_de_vida_equipo` (5), `plandemantenimientoycalibracion` (5), `hardware` (3), `actividades_equipo` (2), `hardware_actividades` (1) |
| **Integraciones RUNT** | `runt_envios` (1,164), `runt` (917), `inscripcion_runt` (382) |
| **Facturación, Créditos y Tarifas** | `tarifa` (35), `detalle_factura` (6), `factura` (4), `temporal_factura` (1), `abono` (0), `credito` (0), `detalle_credito` (0), `lote_factura` (0) |
| **Talleres y Mecánicos** | `mecanico` (48), `taller` (45), `moto_mecanico` (10) |
| **Mercadeo y Encuestas** | `posibles_contactos` (115), `moto_posibles` (100), `contactos_mercadeo` (51), `motos_contactos_mercadeo` (50), `razon_llamada` (23), `contactos_soat` (15), `calificacion` (10), `pregunta` (6), `reporte_accioncopreme` (3), `plan_accion` (2), `seguimiento_resultados` (2), `encuesta` (1), `encuestado` (1) |
| **Catálogos Adicionales y Parámetros** | `cil_ton_pas` (24), `clase_vehiculo` (11), `soat` (11 - pólizas antiguas), `clase_vehiculo_soat` (9), `aseguradora` (8), `modelo` (35), `servicio` (2), `configuracion` (1), `practica` (0) |
| **Usuarios Antiguos** | `usuario` (23 registros con claves en texto plano) |

---

## 4. Normalizaciones y Saneamiento Automático del Backend

El backend incluye reglas automáticas para que los datos sucios del legado no rompan la aplicación:

1. **Reparación de Mojibake / Caracteres Especiales:**
   - Convierte automáticamente textos con doble codificación latin1/utf-8 (`Ã¡` → `á`, `Ã±` → `ñ`).
2. **Corrección de Años Transpuestos e Imposibles:**
   - Fechas con año `0227` se corrigen a `2027` si el par expedición/vencimiento es congruente.
   - Fechas imposibles (ej. año `3017` o `0000-00-00`) se normalizan a `null` para que no desborden los calendarios ni la lógica de fechas de Python/React.
3. **Cumpleaños Inexistentes (ej. 31 de Febrero):**
   - El saneamiento detecta combinaciones de día/mes no válidas y apaga la bandera `contactar_cumpleanos=False`, evitando llamadas fallidas en el módulo de cumpleaños.

---

## 5. Recomendaciones antes de cargar el archivo

Si decides cargar este archivo en el sistema:

1. **Generar un Respaldo de Seguridad Actual:**
   - En la pestaña *"Generar respaldo"*, haz clic en **"Generar copia de seguridad en servidor (.sql)"** para tener un punto de restauración con los datos actuales antes de sustituirlos.
2. **Cargar mediante la interfaz web:**
   - En la pestaña *"Cargar respaldo"*, pulsa el botón **`F:\Check`**, selecciona `CONTACTOS2026-11-07.sql` y pulsa **"Restaurar base de datos"**.
   - El proceso tardará aproximadamente **1.5 a 2 minutos** (debido a los ~896,000 registros). La interfaz mostrará el estado de avance en tiempo real.
3. **Validar las cuentas de acceso:**
   - Verifica que los usuarios que deban operar el sistema tengan sus contraseñas y roles configurados en la pestaña de Usuarios.

---

## 6. Conclusión

- **¿Rompe el backend?** **NO**, siempre que se cargue a través de la herramienta integrada del sistema (`TarjetaRespaldo` / `restaurar_base_datos`).
- **¿Qué le hace falta?**
  1. No sobreescribir datos nuevos sin antes haber sacado una copia de seguridad actual.
  2. Sincronizar o dar de alta en Django los usuarios que vayan a trabajar en el sistema, ya que sus claves antiguas en texto plano no se migran por seguridad.
  3. Tener presente que las 52 tablas secundarias del antiguo CDAV (gases, equipos, facturación) son ignoradas porque el sistema actual está enfocado en CRM, contactos, motos y campañas de llamadas.

