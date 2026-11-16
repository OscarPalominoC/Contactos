---
persona: oscar
ia: Claude Code (Claude Opus 5.5)
actualizado: 2026-11-14 17:45
zona_horaria: America/Bogota
estado: BORRADOR — sujeto a validación de Jurídica
---
# Política de tratamiento de datos personales — Check Contactos

> **BORRADOR SUJETO A VALIDACIÓN DE JURÍDICA.** Este documento describe las medidas técnicas del sistema. No es criterio legal aprobado: la base legal, los plazos de retención y los procedimientos ante el titular están marcados `[POR CONFIRMAR]` y no deben usarse hasta que Jurídica los defina.

## 1. Responsable

Check Ltda. (CDA Check Motos), NIT 900.225.272-8, Barrancabermeja, Santander. Datos de contacto del responsable del tratamiento: `[POR CONFIRMAR]`.

## 2. Datos tratados

| Titular | Datos | Origen |
|---|---|---|
| Clientes | Documento, nombre, teléfono, celular, día y mes de nacimiento, dirección, correo, placas, fechas de RTM y SOAT, historial de llamadas | Sistema legado importado el 2026-11-14 y registros nuevos |
| Empleados | Documento (usuario), nombre, rol, registro de ingresos (fecha, IP, resultado) | Cuentas del sistema |

## 3. Finalidades

1. Recordar al cliente el vencimiento de la RTM y del SOAT.
2. Fidelización: saludo de cumpleaños.
3. Control de acceso y auditoría del sistema.

Base legal (Ley 1581 de 2012 y Decreto 1377 de 2013) y existencia de la autorización previa del titular: `[POR CONFIRMAR]` con Jurídica.

## 4. Retención

`[POR CONFIRMAR]`. No se definen plazos en este borrador. Mientras Jurídica decide:

- Los contactos **inhabilitados** (1 862 al importar) se conservan, pero no aparecen en la lista de cumpleaños del día.
- Si deben anonimizarse o suprimirse está `[POR CONFIRMAR]`.

## 5. Derechos del titular

Consultar, actualizar, rectificar, suprimir y revocar la autorización. Procedimiento, canal y plazos de respuesta: `[POR CONFIRMAR]`.

Cobertura técnica disponible hoy:

- **Consulta:** la ficha 360 reúne todos los datos de un contacto.
- **Actualización y rectificación:** edición del contacto, que queda auditada.
- **Supresión y revocación:** el contacto se inhabilita. La supresión física y la anonimización no están implementadas hasta que Jurídica defina el procedimiento.

## 6. Medidas de seguridad implementadas

| Medida | Detalle |
|---|---|
| Acceso | Usuario y clave personales con hash Argon2id; cambio obligatorio de la clave temporal; bloqueo tras 5 intentos fallidos |
| Sesión | Token de acceso de 5 minutos solo en memoria; refresco en cookie HttpOnly con rotación; cierre por inactividad a los 30 minutos con aviso previo |
| Mínimo privilegio | Roles administrador, ingeniero, técnico y usuario con permisos por recurso, verificados en el servidor (la matriz está pendiente de confirmar con la empresa) |
| Sin exportación | No existen exportaciones, descargas ni impresión de listados (RN-12) |
| Auditoría | Toda creación, edición o anulación queda registrada con usuario, fecha y código de petición; los ingresos quedan en el registro de ingresos |
| Registros (logs) | Se enmascaran correos y números largos (cédulas y teléfonos) |
| Transporte | Uso local en el equipo de la empresa. Si el sistema se publica en red, HTTPS es obligatorio (HSTS y cookies `Secure` ya están configurados para entornos distintos de local) |
| Respaldo | Copia diaria con `pg_dump`, guardando las 14 más recientes. Cifrado del respaldo: `[POR CONFIRMAR]` |

## 7. Incidentes

Procedimiento de reporte de incidentes de seguridad a la Superintendencia de Industria y Comercio: `[POR CONFIRMAR]`.
