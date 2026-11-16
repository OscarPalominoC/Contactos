---
persona: oscar
ia: Claude Code (Claude Opus 5.5)
actualizado: 2026-11-14 17:45
zona_horaria: America/Bogota
---
# Manual de uso — Check Contactos

## Primer ingreso

1. Abra <http://localhost:5173>.
2. Escriba su **usuario** (su número de documento) y la **clave temporal** que le entregaron en persona.
3. El sistema le pide cambiar la clave antes de mostrar cualquier pantalla. La nueva clave:
   - tiene al menos 5 caracteres (puede incluir su nombre o su documento);
   - no puede ser la temporal ni una de sus 3 claves anteriores.
4. Si se equivoca 5 veces seguidas, la cuenta se bloquea durante 1 hora. Un administrador puede desbloquearla reiniciando su clave.
5. Por seguridad, la sesión se cierra tras 30 minutos sin actividad. Un minuto antes aparece un aviso con el botón **Seguir conectado**.

## Pantallas

| Pantalla | Para qué sirve |
|---|---|
| **Tablero** | RTM y SOAT que vencen en los próximos 30 días, cumpleaños de hoy, llamadas del día y contactos nuevos del mes. Cada indicador lleva al listado filtrado. |
| **Contactos** | **Solo búsqueda:** al entrar no se lista nada. Escriba al menos 3 caracteres del nombre o del documento; estado, mes de cumpleaños y **canal de contacto** afinan la búsqueda. La tabla no muestra la cédula: **clic en el nombre** abre la ficha (motos, RTM, SOAT y llamadas del cliente, con el documento). **Editar** y **Nuevo contacto** siguen en su lugar. Los contactos no se borran: se inhabilitan. |
| **Motos** | **Solo búsqueda** por placa (mínimo 3 caracteres). **Clic en la placa** abre el vehículo con su historial; el **propietario** aparece por nombre y lleva a su ficha. **Nueva moto** y **Editar** siguen en su lugar. La línea se elige después de la marca. |
| **Revisiones RTM** | **Solo búsqueda** por placa o número de certificado (mínimo 3 caracteres), o por rango de vencimiento (así llega el enlace del tablero). La tabla muestra placa (enlace al vehículo), vigencia, vencimiento, estado y propietario (enlace a su ficha); el número de certificado se ve al editar. **Registrar revisión** (si deja vacío el vencimiento, se calcula a un año), editar, marcar como duplicada o anular. |
| **SOAT** | Igual que RTM: búsqueda por placa, número de póliza o rango de vencimiento. La tabla muestra placa, vigencia, vencimiento, estado y propietario, sin el número de póliza. **Registrar SOAT** con su aseguradora, editar, marcar como duplicada o anular. |
| **Llamadas** | Pestañas Cumpleaños, RTM y SOAT (flechas ← → del teclado). **Pendientes de RTM y SOAT** se calculan desde los **vencimientos** del rango **Vence desde / Vence hasta** (por defecto, hoy y los 30 días siguientes): aparecen las motos cuyo documento más reciente vence en ese rango y que aún no tienen una llamada realizada para esa fecha. Si la moto ya renovó, no aparece; solo se listan clientes habilitados que autorizan el canal. **Registrar llamada** en la fila deja lista la placa y la fecha; si ya hubo un intento sin éxito, la fila ofrece **Nuevo intento** y queda al final. La placa lleva al vehículo y el propietario a su ficha. En **Cumpleaños**, pendientes muestra solo **Cumpleaños del periodo**, que se puede ordenar por nombre, cumpleaños o celular. **Historial** es la bitácora de llamadas registradas, con rango **Desde / Hasta** y estado. |
| **Marcas y líneas** | Catálogos (administrador e ingeniero). Una marca o línea en uso no se puede eliminar. |
| **Usuarios** | Solo el administrador: crear cuentas, cambiar el rol, desactivar y reiniciar claves. La clave temporal se muestra **una sola vez**. |
| **Barra superior** | A la derecha: la luna o el sol cambia entre modo oscuro y claro; **su primer nombre** abre las opciones **Cambiar nombre** y **Actualizar contraseña**; la puerta cierra la sesión. En pantallas angostas, el botón de tres líneas muestra el menú. |

## Calendario y fechas

- Las fechas se eligen en un calendario: clic en el campo o **Enter**. Flechas mueven el día, **Inicio/Fin** la semana, **RePág/AvPág** el mes; los selectores de mes y año saltan directo. **Escape** cierra. Solo se pueden elegir días que existen.
- En **Desde / Hasta**, el calendario no deja elegir un «Desde» posterior al «Hasta». **Limpiar fechas** quita el filtro.
- Fechas heredadas del sistema anterior que no se pudieron reparar (por ejemplo, año 3196) se muestran como **—**. Un cumpleaños imposible (como el 31 de febrero) se muestra como **— (Fecha inválida)**.

## Preferencias de contacto

En el formulario del contacto, **Preferencias de contacto** tiene una casilla por canal (Cumpleaños, SOAT, RTM) y **Seleccionar todos los canales**, que marca o desmarca los tres a la vez. Los contactos con cumpleaños imposible llegan con Cumpleaños desactivado: al abrirlos, el formulario lo avisa; corrija la fecha y vuelva a marcar Cumpleaños.

**Fecha de cumpleaños:** se elige en un calendario de enero a diciembre con los días de la semana del año en curso. Solo se guardan el día y el mes, por eso no hay selector de año. Las flechas del calendario (o RePág/AvPág) cambian de mes; **Limpiar** deja el contacto sin cumpleaños. El 29 de febrero siempre aparece, aunque el año en curso no sea bisiesto.

**Llamadas de cumpleaños:** la tarjeta **Cumpleaños del periodo** lista a quienes cumplen años entre **Cumpleaños desde** y **Cumpleaños hasta** (por defecto, hoy). Funciona aunque el periodo cruce el fin de año. El nombre de cada cliente es un enlace a su ficha. La bitácora de cumpleaños también muestra el nombre con enlace, en lugar de la cédula.

## Estados

- **RTM y SOAT:**
  - **Vigente** y **Vencido** se calculan solos con la fecha de vencimiento.
  - **Duplicado** y **Anulado** los marca un usuario.
  - **No (legado)** son 9 registros antiguos cuyo significado está por confirmar.
- **Llamadas:** Realizada, No realizada, Realizada sin éxito, Ocupada y Sin estado (este último solo aparece en datos antiguos).

## Errores

Si algo falla, el aviso rojo muestra un **código de soporte**. Cópielo y envíelo al administrador: con él se ubica el error exacto en los registros.

## Lo que el sistema no hace

No exporta, descarga ni imprime listados. Es una decisión deliberada para proteger los datos de los clientes.
