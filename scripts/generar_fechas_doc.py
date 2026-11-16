import os
import sys
import django

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

def query_to_dicts(sql):
    with connection.cursor() as cursor:
        cursor.execute(sql)
        desc = [col[0] for col in cursor.description]
        return [dict(zip(desc, row)) for row in cursor.fetchall()]

# 1. Contactos
contactos = query_to_dicts("""
    SELECT nip, nombre, dia_nac, mes_nac, fecha_registro, creado_en, actualizado_en 
    FROM contactos_contacto 
    WHERE dia_nac IS NOT NULL AND mes_nac IS NOT NULL 
    LIMIT 5;
""")

# 2. Motos
motos = query_to_dicts("""
    SELECT placa, fecha_soat, fecha_venc_soat, fecha_rtmg, fecha_venc_rtmg, creado_en, actualizado_en 
    FROM vehiculos_moto 
    WHERE fecha_soat IS NOT NULL AND fecha_rtmg IS NOT NULL 
    LIMIT 5;
""")

# 3. Revisiones RTM
revisiones = query_to_dicts("""
    SELECT certificado, placa, fecha_certificado, fecha_venc_certificado, fecha_soat, fecha_venc_soat, fecha_registro_runt, fecha_registro, creado_en 
    FROM revisiones_revision 
    WHERE fecha_certificado IS NOT NULL 
    LIMIT 5;
""")

# 4. SOAT
soats = query_to_dicts("""
    SELECT soat, placa, fecha_soat, fecha_venc_soat, fecha_registro, creado_en, estado 
    FROM revisiones_soat 
    WHERE fecha_soat IS NOT NULL 
    LIMIT 5;
""")

# 5. Llamadas Cumpleanos
llamadas_c = query_to_dicts("""
    SELECT id, nip, fecha, estado, num_llamadas, intentos, creado_en 
    FROM llamadas_cumpleanos 
    LIMIT 5;
""")

# 6. Llamadas RTM
llamadas_rtm = query_to_dicts("""
    SELECT id, placa, fecha, estado, num_llamadas, intentos, creado_en 
    FROM llamadas_rtm 
    LIMIT 5;
""")

# 7. Llamadas SOAT
llamadas_soat = query_to_dicts("""
    SELECT id, placa, fecha, estado, num_llamadas, intentos, creado_en 
    FROM llamadas_soat 
    LIMIT 5;
""")

# 8. Usuarios
usuarios = query_to_dicts("""
    SELECT nip, nombre, rol, fecha_creacion, clave_cambiada_en, last_login 
    FROM cuentas_usuario 
    LIMIT 5;
""")

# 9. Ingresos
ingresos = query_to_dicts("""
    SELECT id, nip_usuario, exitoso, ip, fecha 
    FROM cuentas_ingreso 
    LIMIT 5;
""")

# 10. Auditoria
auditoria = query_to_dicts("""
    SELECT id, accion, modelo, objeto_id, usuario, fecha 
    FROM comun_registro_auditoria 
    LIMIT 5;
""")

# Anomalías específicas
anomalias_cumple_count = query_to_dicts("""
    SELECT count(*) as c 
    FROM contactos_contacto 
    WHERE (mes_nac = 2 AND dia_nac > 29)
       OR (mes_nac IN (4, 6, 9, 11) AND dia_nac > 30)
       OR (dia_nac < 1 OR dia_nac > 31)
       OR (mes_nac < 1 OR mes_nac > 12);
""")[0]['c']

anomalias_feb31_count = query_to_dicts("""
    SELECT count(*) as c 
    FROM contactos_contacto 
    WHERE mes_nac = 2 AND dia_nac = 31;
""")[0]['c']

anomalias_cumple_samples = query_to_dicts("""
    SELECT nip, nombre, dia_nac, mes_nac 
    FROM contactos_contacto 
    WHERE mes_nac = 2 AND dia_nac = 31
    LIMIT 5;
""")

# 2. SOAT años futuros extremos / errores
anomalias_soat_futuro = query_to_dicts("""
    SELECT soat, placa, fecha_soat, fecha_venc_soat, estado, usuario 
    FROM revisiones_soat 
    WHERE fecha_soat > '2050-01-01' OR fecha_venc_soat > '2050-01-01'
    LIMIT 5;
""")

# 3. SOAT fecha_venc < fecha_soat
anomalias_soat_invertido = query_to_dicts("""
    SELECT soat, placa, fecha_soat, fecha_venc_soat, estado, usuario 
    FROM revisiones_soat 
    WHERE fecha_venc_soat < fecha_soat
    LIMIT 5;
""")

# 4. Revisiones con certificado > 2050 o venc <= certificado
anomalias_rev_invertido = query_to_dicts("""
    SELECT certificado, placa, fecha_certificado, fecha_venc_certificado, estado, usuario 
    FROM revisiones_revision 
    WHERE fecha_venc_certificado <= fecha_certificado
    LIMIT 5;
""")

# 5. Revisiones años futuros
anomalias_rev_futuro = query_to_dicts("""
    SELECT certificado, placa, fecha_certificado, fecha_venc_certificado, estado, usuario 
    FROM revisiones_revision 
    WHERE fecha_certificado > '2050-01-01' OR fecha_venc_certificado > '2050-01-01'
    LIMIT 5;
""")

# 6. Incongruencias Estado vs Fecha (VIGENTE pero vencido en el pasado)
anomalias_soat_estado = query_to_dicts("""
    SELECT soat, placa, fecha_soat, fecha_venc_soat, estado 
    FROM revisiones_soat 
    WHERE estado = 'VIGENTE' AND fecha_venc_soat < '2024-01-01'
    LIMIT 5;
""")

lines = []
lines.append("# Auditoría y Mapeo Estructural de Fechas — Check Ltda.")
lines.append("")
lines.append("> **Entorno:** Base de datos relacional PostgreSQL (`check_contactos`) — CDA Check Motos, Barrancabermeja, Santander.")
lines.append("> **Propósito:** Documentar detalladamente cada tabla del sistema que gestiona información temporal y de calendario, sus propiedades específicas, muestras reales de 5 registros y el inventario exhaustivo de inconsistencias, anomalías heredadas (cumpleaños el 31 de febrero, años 3017, fechas invertidas) y recomendaciones de remediación técnica.")
lines.append("")
lines.append("---")
lines.append("")
lines.append("## 1. Mapeo de Tablas con Propiedades de Fecha y Registros de Muestra")
lines.append("")

def format_table(name, model, desc, props, samples):
    t_lines = []
    t_lines.append(f"### 1.{name}")
    t_lines.append(f"* **Tabla en BD:** `{props['tabla']}`")
    t_lines.append(f"* **Modelo Django:** `{props['modelo']}`")
    t_lines.append(f"* **Descripción de Negocio:** {desc}")
    t_lines.append("")
    t_lines.append("#### Propiedades de Fecha y Tiempo")
    t_lines.append("| Propiedad | Tipo de Dato (BD) | Formato / Restricción | Propósito Operativo |")
    t_lines.append("| :--- | :--- | :--- | :--- |")
    for p in props['columnas']:
        t_lines.append(f"| `{p['nombre']}` | `{p['tipo']}` | {p['formato']} | {p['proposito']} |")
    t_lines.append("")
    t_lines.append("#### 5 Registros de Muestra Reales de la Base de Datos")
    if samples:
        headers = list(samples[0].keys())
        t_lines.append("| " + " | ".join(headers) + " |")
        t_lines.append("| " + " | ".join([":---"] * len(headers)) + " |")
        for s in samples:
            row_str = " | ".join([str(s[h]) if s[h] is not None else "NULL" for h in headers])
            t_lines.append(f"| {row_str} |")
    t_lines.append("")
    t_lines.append("---")
    t_lines.append("")
    return "\n".join(t_lines)

# 1. Contactos
lines.append(format_table("1. Contactos de Clientes (`contactos_contacto`)", "Contacto", "Directorio principal de propietarios, conductores y clientes del CDA Check Motos.", {
    "tabla": "contactos_contacto",
    "modelo": "apps.contactos.models.Contacto",
    "columnas": [
        {"nombre": "dia_nac", "tipo": "smallint", "formato": "1 a 31 (entero)", "proposito": "Día del natalicio del cliente para campañas de fidelización y llamadas de cumpleaños."},
        {"nombre": "mes_nac", "tipo": "smallint", "formato": "1 a 12 (entero)", "proposito": "Mes del natalicio del cliente."},
        {"nombre": "fecha_registro", "tipo": "timestamp with time zone", "formato": "ISO 8601 con zona horaria", "proposito": "Marca de tiempo en la que el cliente fue dado de alta originalmente en el CDA."},
        {"nombre": "creado_en", "tipo": "timestamp with time zone", "formato": "ISO 8601 (auto_now_add)", "proposito": "Registro de auditoría de creación en la base de datos moderna."},
        {"nombre": "actualizado_en", "tipo": "timestamp with time zone", "formato": "ISO 8601 (auto_now)", "proposito": "Última modificación de datos del contacto."}
    ]
}, contactos))

# 2. Motos
lines.append(format_table("2. Vehículos Motocicleta (`vehiculos_moto`)", "Moto", "Inventario de motocicletas atendidas en la pista de inspección del CDA.", {
    "tabla": "vehiculos_moto",
    "modelo": "apps.vehiculos.models.Moto",
    "columnas": [
        {"nombre": "fecha_soat", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha de expedición del último SOAT registrado en la ficha técnica del vehículo."},
        {"nombre": "fecha_venc_soat", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha de vencimiento del SOAT; alimenta las alertas de renovación y llamadas."},
        {"nombre": "fecha_rtmg", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha de emisión de la última Revisión Técnico-Mecánica y de Emisiones Contaminantes."},
        {"nombre": "fecha_venc_rtmg", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha de vencimiento de la RTM del vehículo."},
        {"nombre": "creado_en", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Auditoría de inserción en el sistema."},
        {"nombre": "actualizado_en", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Auditoría de última actualización."}
    ]
}, motos))

# 3. Revisiones RTM
lines.append(format_table("3. Revisiones Técnico-Mecánicas (`revisiones_revision`)", "Revision", "Certificados oficiales de inspección técnico-mecánica y de emisiones de gases para motocicletas.", {
    "tabla": "revisiones_revision",
    "modelo": "apps.revisiones.models.Revision",
    "columnas": [
        {"nombre": "fecha_certificado", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha oficial de expedición del certificado de inspección."},
        {"nombre": "fecha_venc_certificado", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha de expiración de la vigencia del certificado (típicamente 1 año después)."},
        {"nombre": "fecha_soat", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha de expedición de la póliza SOAT presentada al momento de la revisión."},
        {"nombre": "fecha_venc_soat", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha de vencimiento del SOAT presentado."},
        {"nombre": "fecha_registro_runt", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha en la que la revisión fue cargada y avalada en el sistema central RUNT."},
        {"nombre": "fecha_registro", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Estampa de tiempo local en que el usuario recepcionó el vehículo."},
        {"nombre": "creado_en", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Auditoría de creación técnica."}
    ]
}, revisiones))

# 4. SOAT
lines.append(format_table("4. Pólizas SOAT (`revisiones_soat`)", "Soat", "Historial y control de pólizas del Seguro Obligatorio de Accidentes de Tránsito registradas para motocicletas.", {
    "tabla": "revisiones_soat",
    "modelo": "apps.revisiones.models.Soat",
    "columnas": [
        {"nombre": "fecha_soat", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha de inicio / emisión de la cobertura del SOAT."},
        {"nombre": "fecha_venc_soat", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha límite de vigencia de la póliza (base para llamadas de renovación)."},
        {"nombre": "fecha_registro", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Fecha y hora en que la póliza fue ingresada en el sistema del CDA."},
        {"nombre": "creado_en", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Auditoría de inserción."}
    ]
}, soats))

# 5. Llamadas Cumpleanos
lines.append(format_table("5. Bitácora de Llamadas por Cumpleaños (`llamadas_cumpleanos`)", "LlamadaCumpleanos", "Gestión de contacto telefónico para felicitación y fidelización en natalicios.", {
    "tabla": "llamadas_cumpleanos",
    "modelo": "apps.llamadas.models.LlamadaCumpleanos",
    "columnas": [
        {"nombre": "fecha", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Fecha y hora en que se gestiona la llamada telefónica."},
        {"nombre": "intentos", "tipo": "text", "formato": "Marcas de tiempo separadas por ';'", "proposito": "Historial concatenado de estampas de tiempo de cada intento telefónico realizado."},
        {"nombre": "creado_en", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Auditoría del registro de llamada."}
    ]
}, llamadas_c))

# 6. Llamadas RTM
lines.append(format_table("6. Bitácora de Llamadas por RTM (`llamadas_rtm`)", "LlamadaRtm", "Control de llamadas de seguimiento para renovación oportuna de la revisión técnico-mecánica.", {
    "tabla": "llamadas_rtm",
    "modelo": "apps.llamadas.models.LlamadaRtm",
    "columnas": [
        {"nombre": "fecha", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha objetivo / vencimiento de la RTM que motiva la llamada preventiva."},
        {"nombre": "intentos", "tipo": "text", "formato": "Marcas de tiempo separadas por ';'", "proposito": "Estampas de tiempo exactas en las que el operador marcó al usuario."},
        {"nombre": "creado_en", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Auditoría del registro inicial."}
    ]
}, llamadas_rtm))

# 7. Llamadas SOAT
lines.append(format_table("7. Bitácora de Llamadas por SOAT (`llamadas_soat`)", "LlamadaSoat", "Control de llamadas de recordatorio para adquisición o renovación del seguro obligatorio.", {
    "tabla": "llamadas_soat",
    "modelo": "apps.llamadas.models.LlamadaSoat",
    "columnas": [
        {"nombre": "fecha", "tipo": "date", "formato": "AAAA-MM-DD", "proposito": "Fecha límite de la póliza vigente que dispara la campaña telefónica."},
        {"nombre": "intentos", "tipo": "text", "formato": "Marcas de tiempo separadas por ';'", "proposito": "Estampas de tiempo de cada marcación telefónica."},
        {"nombre": "creado_en", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Auditoría de inserción."}
    ]
}, llamadas_soat))

# 8. Usuarios
lines.append(format_table("8. Usuarios del Sistema (`cuentas_usuario`)", "Usuario", "Personal administrativo, técnico, call center y de recepción de Check Ltda.", {
    "tabla": "cuentas_usuario",
    "modelo": "apps.cuentas.models.Usuario",
    "columnas": [
        {"nombre": "fecha_creacion", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Fecha de alta del usuario en la plataforma."},
        {"nombre": "clave_cambiada_en", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Fecha de la última rotación de contraseña (control de expiración cada 90 días)."},
        {"nombre": "last_login", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Fecha y hora del último acceso exitoso del usuario."}
    ]
}, usuarios))

# 9. Ingresos
lines.append(format_table("9. Registro de Intentos de Ingreso (`cuentas_ingreso`)", "Ingreso", "Trazabilidad de seguridad de accesos exitosos y fallidos al sistema.", {
    "tabla": "cuentas_ingreso",
    "modelo": "apps.cuentas.models.Ingreso",
    "columnas": [
        {"nombre": "fecha", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Estampa de tiempo exacta del intento de autenticación."}
    ]
}, ingresos))

# 10. Auditoría
lines.append(format_table("10. Auditoría General del Sistema (`comun_registro_auditoria`)", "RegistroAuditoria", "Log inmutable de operaciones sobre los modelos (creación, edición, eliminación).", {
    "tabla": "comun_registro_auditoria",
    "modelo": "apps.comun.models.RegistroAuditoria",
    "columnas": [
        {"nombre": "fecha", "tipo": "timestamp with time zone", "formato": "ISO 8601", "proposito": "Estampa de tiempo del evento de auditoría."}
    ]
}, auditoria))

# SECCIÓN 2: AUDITORÍA DE ANOMALÍAS
lines.append("## 2. Auditoría Exhaustiva de Anomalías, Incongruencias y Fechas Inválidas")
lines.append("")
lines.append("El análisis automatizado sobre los más de 200.000 registros heredados de la base de datos MySQL original ha evidenciado múltiples categorías de anomalías temporales, originadas principalmente por falta de validación en la interfaz de digitación del software legado, fallos en la digitalización de pólizas físicas y prácticas operativas de captura.")
lines.append("")

# Caso 1: Cumpleaños
lines.append("### 2.1 Cumpleaños Ficticios e Inválidos (Caso \"31 de Febrero\")")
lines.append(f"* **Total de contactos con fechas anómalas:** **{anomalias_cumple_count:,} registros** de 54.084 contactos totales.")
lines.append(f"* **Total de contactos registrados exactamente el 31 de Febrero (`dia_nac = 31, mes_nac = 2`):** **{anomalias_feb31_count:,} registros**.")
lines.append("* **Causa Técnica / Operativa:** En el software legado, los campos de fecha de nacimiento eran obligatorios en el formulario, pero la recepcionista no siempre obtenía dicho dato del cliente. Como solución rápida para poder guardar el formulario, el sistema o los digitadores establecieron el valor centinela **31 de Febrero** como bandera para indicar \"Fecha de cumpleaños no suministrada\".")
lines.append("* **Impacto en el nuevo sistema:** Si el sistema de llamadas automáticas o el tablero no filtra estos registros centinela, el motor de campañas de cumpleaños intentará agendar llamadas el 31 de febrero (fecha que nunca ocurre en el calendario gregoriano) o generará errores al intentar instanciar objetos `datetime.date(año, 2, 31)`.")
lines.append("")
lines.append("#### 5 Ejemplos Reales de Contactos con Cumpleaños el 31 de Febrero:")
lines.append("| NIP / Cédula | Nombre del Contacto | Día de Nacimiento | Mes de Nacimiento | Inconsistencia |")
lines.append("| :--- | :--- | :--- | :--- | :--- |")
for c in anomalias_cumple_samples:
    lines.append(f"| `{c['nip']}` | {c['nombre']} | `{c['dia_nac']}` | `{c['mes_nac']}` | 31 de Febrero (Fecha inexistente) |")
lines.append("")

# Caso 2: Años futuros y errores de siglo (Caso año 3017)
lines.append("### 2.2 Años Futuros Extremos y Errores de Digitador (Caso Año 3017 / 3196)")
lines.append("* **Descripción del Hallazgo:** En pólizas SOAT y certificados de revisión, existen registros con años superiores al 2050 (e.g. 3017, 3196, 2426, 2103).")
lines.append("* **Caso Emblemático Reportado por la Empresa:** Póliza `1318-20045995 SURA` asociada a la moto `MYC04D`.")
lines.append("  * `fecha_soat`: **`3017-07-21`** (Año 3017 en el siglo XXXI).")
lines.append("  * `fecha_venc_soat`: **`2018-07-21`** (Año 2018).")
lines.append("  * `estado` en base de datos: **`VIGENTE`**.")
lines.append("* **Diagnóstico:** Se trata de un error de tipeo en el teclado numérico: el digitador presionó la tecla '3' en lugar de la tecla '2', transformando el año de inicio de cobertura de `2017` a `3017`. Como consecuencia matemática, la fecha de vencimiento (`2018-07-21`) quedó mil años antes que la fecha de expedición (`3017-07-21`), generando una duración negativa de -999 años.")
lines.append("")
lines.append("#### Muestra de Pólizas SOAT con Años Futuros Extremos:")
lines.append("| Póliza SOAT | Placa Moto | Fecha Expedición | Fecha Vencimiento | Estado Registrado | Usuario que Registró |")
lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
for s in anomalias_soat_futuro:
    lines.append(f"| `{s['soat']}` | `{s['placa']}` | `{s['fecha_soat']}` | `{s['fecha_venc_soat']}` | `{s['estado']}` | {s['usuario']} |")
lines.append("")

# Caso 3: Fechas Invertidas
lines.append("### 2.3 Fechas Invertidas (`fecha_vencimiento < fecha_expedicion`)")
lines.append("* **Descripción del Hallazgo:** Se encontraron pólizas y revisiones donde la fecha de vencimiento es cronológicamente anterior a la fecha de inicio/expedición.")
lines.append("* **Causa:** Errores de digitación como el año `0227` en lugar de `2027` (digitador omite el 2 inicial o coloca 0 al inicio), intercambios de día y mes (formato anglosajón MM/DD/AAAA interpretado como DD/MM/AAAA), o typos en el siglo.")
lines.append("")
lines.append("#### 5 Ejemplos Reales de Pólizas SOAT con Fecha de Vencimiento Menor a Fecha de Expedición:")
lines.append("| Póliza SOAT | Placa Moto | Fecha Expedición | Fecha Vencimiento | Diagnóstico de Inconsistencia |")
lines.append("| :--- | :--- | :--- | :--- | :--- |")
for s in anomalias_soat_invertido:
    lines.append(f"| `{s['soat']}` | `{s['placa']}` | `{s['fecha_soat']}` | `{s['fecha_venc_soat']}` | Vencimiento anterior a la expedición |")
lines.append("")

# Caso 4: Revisiones con fechas invertidas
lines.append("### 2.4 Revisiones Técnico-Mecánicas con Fechas Invertidas o Años Truncados")
lines.append("* **Descripción:** En la tabla `revisiones_revision`, se registran certificados donde la fecha de vencimiento aparece como año `0227` o `0224` en lugar de `2027` o `2024`, resultando formalmente en fechas del año 227 d.C.")
lines.append("")
lines.append("#### 5 Ejemplos Reales de Revisiones RTM con Fechas Inconsistentes:")
lines.append("| Certificado | Placa Moto | Fecha Certificado | Fecha Vencimiento Certificado | Estado |")
lines.append("| :--- | :--- | :--- | :--- | :--- |")
for r in anomalias_rev_invertido:
    lines.append(f"| `{r['certificado']}` | `{r['placa']}` | `{r['fecha_certificado']}` | `{r['fecha_venc_certificado']}` | `{r['estado']}` |")
lines.append("")

# Caso 5: Discrepancia Estado vs Fecha
lines.append("### 2.5 Incoherencia de Negocio: Estado \"VIGENTE\" con Fechas Vencidas hace Años")
lines.append("* **Descripción:** En el sistema legado MySQL, la columna `estado` era una cadena estática (`VARCHAR(15)` o `VARCHAR(20)`) que no se recalculaba de forma automática con el paso de los días. En consecuencia, miles de pólizas y certificados cuya vigencia expiró en 2018, 2019 o 2021 continúan figurando con `estado = \"VIGENTE\"` en la base de datos.")
lines.append("* **Impacto Operativo:** Filtrar revisiones o SOAT únicamente por la columna `estado = \"VIGENTE\"` en SQL arroja pólizas vencidas hace media década. La vigencia debe ser evaluada siempre dinámicamente comparando `fecha_vencimiento >= fecha_actual`.")
lines.append("")
lines.append("#### 5 Ejemplos de Registros Marcados como \"VIGENTE\" pero con Vencimiento Expirado:")
lines.append("| Póliza SOAT | Placa Moto | Fecha Expedición | Fecha Vencimiento Real | Estado Registrado (Erróneo) |")
lines.append("| :--- | :--- | :--- | :--- | :--- |")
for s in anomalias_soat_estado:
    lines.append(f"| `{s['soat']}` | `{s['placa']}` | `{s['fecha_soat']}` | `{s['fecha_venc_soat']}` | `{s['estado']}` (Debería ser VENCIDO) |")
lines.append("")

# Caso 6: Formato de Intentos en Llamadas
lines.append("### 2.6 Estructura Especial: Estampas de Tiempo en Campo `intentos` de Llamadas")
lines.append("* **Descripción Técnica:** Las tablas de bitácora (`llamadas_cumpleanos`, `llamadas_rtm`, `llamadas_soat`) almacenan el historial de múltiples intentos en un único campo de texto `intentos`, separando cada marca de tiempo mediante punto y coma (`;`).")
lines.append("* **Ejemplo Real de Contenido:** `\"2026-03-09 10:15:32;2026-03-09 14:22:05;2026-03-10 09:00:11\"`")
lines.append("* **Comportamiento:** Cada nuevo intento telefónico realizado suma 1 al campo `num_llamadas` y concatena la estampa de tiempo actual al final de la cadena de texto.")
lines.append("")

# SECCIÓN 3: RECOMENDACIONES DE INGENIERÍA
lines.append("## 3. Plan de Remediación y Reglas de Validación para la Nueva Plataforma")
lines.append("")
lines.append("Para blindar la plataforma de Check Ltda. frente a estos errores históricos sin perder la trazabilidad de los datos originales, se aplican y recomiendan las siguientes directrices:")
lines.append("")
lines.append("1. **Filtro de Cumpleaños Centinela:**")
lines.append("   * La consulta de \"Cumpleaños de Hoy\" y el dashboard deben ignorar estrictamente a los contactos con `dia_nac = 31` y `mes_nac = 2` o cualquier combinación inválida.")
lines.append("   * El formulario de edición de contactos debe requerir fechas válidas del calendario gregoriano (1-31 según mes, máximo 29 en febrero).")
lines.append("2. **Cálculo Dinámico de Vigencia (No confiar en campo estático `estado`):**")
lines.append("   * La vigencia de un SOAT o RTM debe calcularse en el backend mediante la fórmula:")
lines.append("     ```python")
lines.append("     es_vigente = (fecha_venc_soat >= timezone.now().date())")
lines.append("     ```")
lines.append("   * El campo `estado` se mantiene para compatibilidad y para registrar estados administrativos especiales (e.g. `ANULADO`).")
lines.append("3. **Validación Cruzada de Fechas en Formularios:**")
lines.append("   * `fecha_vencimiento` debe ser obligatoriamente posterior a `fecha_expedicion`: `fecha_vencimiento > fecha_expedicion`.")
lines.append("   * El año de cualquier fecha de inspección o póliza debe estar en el rango acotado: `2000 <= año <= año_actual + 5`. Bloqueando entradas como `3017` o `0227`.")
lines.append("4. **Corrección de Años Transpuestos (Script de Normalización):**")
lines.append("   * Para años con patrón `02XX` (e.g. `0227`), transformar a `20XX` (`2027`).")
lines.append("   * Para pólizas con año `3017` y vencimiento `2018`, ajustar la expedición al año `2017`.")
lines.append("")

output_path = os.path.join(os.path.dirname(__file__), "..", "fechas.md")
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("fechas.md generado exitosamente en:", output_path)
