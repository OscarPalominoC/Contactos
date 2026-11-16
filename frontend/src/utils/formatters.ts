/** Formateadores puros: no alteran el dato de origen. Zona horaria America/Bogota. */

const ZONA = "America/Bogota";

const formatoFecha = new Intl.DateTimeFormat("es-CO", { timeZone: "UTC", day: "2-digit", month: "2-digit", year: "numeric" });
const formatoFechaHora = new Intl.DateTimeFormat("es-CO", {
  timeZone: ZONA,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: true,
});
const formatoCop = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
const formatoNumero = new Intl.NumberFormat("es-CO");

export const MESES = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
] as const;

/** Rango plausible de fechas de negocio: fuera de él son errores de digitación del legado (3017, 0227, 1899). */
export const ANO_MINIMO = 1990;
export const ANO_MAXIMO = 2100;
export const FECHA_INVALIDA = "— (Fecha inválida)";

const fueraDeRango = (ano: number) => ano < ANO_MINIMO || ano > ANO_MAXIMO;

/** 'AAAA-MM-DD' → 'dd/mm/aaaa'. Vacío, insalvable o fuera de 1990-2100 → '—'; día inexistente → '— (Fecha inválida)'. */
export function formatearFecha(valor: string | null | undefined): string {
  if (!valor) return "—";
  const partes = /^(\d{4})-(\d{2})-(\d{2})/.exec(valor);
  if (!partes) return "—";
  const [ano, mes, dia] = [Number(partes[1]), Number(partes[2]), Number(partes[3])];
  if (fueraDeRango(ano)) return "—";
  const fecha = new Date(Date.UTC(ano, mes - 1, dia));
  if (fecha.getUTCMonth() !== mes - 1 || fecha.getUTCDate() !== dia) return FECHA_INVALIDA;
  return formatoFecha.format(fecha);
}

/** ISO con zona → 'dd/mm/aaaa, hh:mm a. m.' en hora de Bogotá. Fuera de 1990-2100 → '—'. */
export function formatearFechaHora(valor: string | null | undefined): string {
  if (!valor) return "—";
  const fecha = new Date(valor);
  return Number.isNaN(fecha.getTime()) || fueraDeRango(fecha.getUTCFullYear()) ? "—" : formatoFechaHora.format(fecha);
}

export function formatearCop(valor: number | null | undefined): string {
  return valor == null ? "—" : formatoCop.format(valor);
}

export function formatearNumero(valor: number | null | undefined): string {
  return valor == null ? "—" : formatoNumero.format(valor);
}

/** Cédula con separadores de miles si es numérica: 1096223757 → 1.096.223.757. */
export function formatearDocumento(valor: string | null | undefined): string {
  if (!valor) return "—";
  return /^\d+$/.test(valor) ? formatoNumero.format(Number(valor)) : valor;
}

/** Enmascara el documento dejando los últimos 4 dígitos (para vistas con menos privilegio). */
export function enmascararDocumento(valor: string | null | undefined): string {
  if (!valor) return "—";
  return valor.length <= 4 ? "****" : `****${valor.slice(-4)}`;
}

/** Celular colombiano: 3001234567 → 300 123 4567. */
export function formatearTelefono(valor: string | null | undefined): string {
  if (!valor) return "—";
  const digitos = valor.replace(/\D/g, "");
  if (digitos.length === 10) return `${digitos.slice(0, 3)} ${digitos.slice(3, 6)} ${digitos.slice(6)}`;
  if (digitos.length === 7) return `${digitos.slice(0, 3)} ${digitos.slice(3)}`;
  return valor;
}

/** Primer nombre con mayúscula inicial: «OSCAR EDUARDO PALOMINO» → «Oscar». */
export function primerNombre(nombre: string | null | undefined): string {
  const palabra = (nombre ?? "").trim().split(/\s+/)[0] ?? "";
  return palabra ? palabra.charAt(0).toLocaleUpperCase("es-CO") + palabra.slice(1).toLocaleLowerCase("es-CO") : "";
}

export function normalizarPlaca(valor: string): string {
  return valor.replace(/[\s-]+/g, "").toUpperCase();
}

export function nombreMes(numero: number | null | undefined): string {
  if (!numero || numero < 1 || numero > 12) return "—";
  return MESES[numero - 1] ?? "—";
}

/** Días que tiene un mes para un cumpleaños (febrero admite 29). */
export function diasDelMesCumpleanos(mes: number): number {
  return new Date(Date.UTC(2000, mes, 0)).getUTCDate();
}

/** Día y mes existen en el calendario (el 31 de febrero del legado no). */
export function esCumpleanosValido(dia: number | null | undefined, mes: number | null | undefined): boolean {
  if (!dia || !mes || mes < 1 || mes > 12) return false;
  return dia >= 1 && dia <= diasDelMesCumpleanos(mes);
}

export function cumpleanos(dia: number | null | undefined, mes: number | null | undefined): string {
  if (!dia || !mes) return mes ? nombreMes(mes) : "—";
  if (!esCumpleanosValido(dia, mes)) return FECHA_INVALIDA;
  return `${dia} de ${nombreMes(mes).toLowerCase()}`;
}

/** Fecha local de Bogotá en formato AAAA-MM-DD (para valores por defecto de formularios). */
export function hoyBogota(ahora: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: ZONA, year: "numeric", month: "2-digit", day: "2-digit" }).format(
    ahora,
  );
}

export function sumarDias(fechaIso: string, dias: number): string {
  const fecha = new Date(`${fechaIso}T00:00:00Z`);
  fecha.setUTCDate(fecha.getUTCDate() + dias);
  return fecha.toISOString().slice(0, 10);
}
