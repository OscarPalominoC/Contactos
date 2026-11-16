import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { hoyBogota, MESES } from "../../utils/formatters";

/** Fechas como 'AAAA-MM-DD' manipuladas en UTC para que la zona horaria no corra el día. */
interface Partes {
  ano: number;
  mes: number; // 0 a 11
  dia: number;
}

const ANO_MINIMO = 1990;
const ANO_MAXIMO = 2100;
const DIAS_SEMANA = [
  { corto: "lu", largo: "lunes" },
  { corto: "ma", largo: "martes" },
  { corto: "mi", largo: "miércoles" },
  { corto: "ju", largo: "jueves" },
  { corto: "vi", largo: "viernes" },
  { corto: "sá", largo: "sábado" },
  { corto: "do", largo: "domingo" },
] as const;
const formatoLargo = new Intl.DateTimeFormat("es-CO", { timeZone: "UTC", day: "numeric", month: "long", year: "numeric" });

const dos = (n: number) => String(n).padStart(2, "0");
const aIso = ({ ano, mes, dia }: Partes) => `${ano}-${dos(mes + 1)}-${dos(dia)}`;
const diasDelMes = (ano: number, mes: number) => new Date(Date.UTC(ano, mes + 1, 0)).getUTCDate();

/** 'AAAA-MM-DD' válida y existente en el calendario, dentro de 1990-2100; si no, null. */
export function leerFechaIso(valor: string | null | undefined): Partes | null {
  const coincidencia = /^(\d{4})-(\d{2})-(\d{2})$/.exec(valor ?? "");
  if (!coincidencia) return null;
  const [ano, mes, dia] = [Number(coincidencia[1]), Number(coincidencia[2]) - 1, Number(coincidencia[3])];
  if (ano < ANO_MINIMO || ano > ANO_MAXIMO || mes < 0 || mes > 11 || dia < 1 || dia > diasDelMes(ano, mes)) return null;
  return { ano, mes, dia };
}

function desdeUtc(fecha: Date): Partes {
  return { ano: fecha.getUTCFullYear(), mes: fecha.getUTCMonth(), dia: fecha.getUTCDate() };
}

function sumarDias(p: Partes, dias: number): Partes {
  return desdeUtc(new Date(Date.UTC(p.ano, p.mes, p.dia + dias)));
}

function sumarMeses(p: Partes, meses: number): Partes {
  const destino = new Date(Date.UTC(p.ano, p.mes + meses, 1));
  const ano = destino.getUTCFullYear();
  const mes = destino.getUTCMonth();
  return { ano, mes, dia: Math.min(p.dia, diasDelMes(ano, mes)) };
}

/** Lunes = 0 … domingo = 6. */
const diaSemana = (p: Partes) => (new Date(Date.UTC(p.ano, p.mes, p.dia)).getUTCDay() + 6) % 7;

export function formatearFechaLarga(valor: string): string {
  const p = leerFechaIso(valor);
  return p ? formatoLargo.format(new Date(Date.UTC(p.ano, p.mes, p.dia))) : "";
}

interface CampoFechaProps {
  etiqueta: string;
  /** 'AAAA-MM-DD' o '' (sin fecha). */
  valor: string;
  alCambiar: (valor: string) => void;
  min?: string;
  max?: string;
  error?: string;
  ayuda?: string;
  obligatorio?: boolean;
  disabled?: boolean;
  /** Fecha de referencia para «Hoy» (por defecto, la fecha de Bogotá). */
  hoy?: string;
}

/**
 * Selector de fecha accesible con calendario en popover de vidrio.
 * Solo permite elegir días que existen (no hay entrada de texto libre), dentro de `min`/`max`.
 * Teclado: flechas (día/semana), Inicio/Fin (semana), RePág/AvPág (mes), Enter/Espacio (elegir), Escape (cerrar).
 */
export function CampoFecha({ etiqueta, valor, alCambiar, min, max, error, ayuda, obligatorio, disabled, hoy }: CampoFechaProps) {
  const id = useId();
  const idEtiqueta = `${id}-etiqueta`;
  const idValor = `${id}-valor`;
  const raiz = useRef<HTMLDivElement>(null);
  const disparador = useRef<HTMLButtonElement>(null);
  const cuadricula = useRef<HTMLTableElement>(null);
  const [abierto, setAbierto] = useState(false);
  const [enfoque, setEnfoque] = useState<Partes | null>(null);
  const [debeEnfocar, setDebeEnfocar] = useState(false);

  const isoHoy = hoy ?? hoyBogota();
  const minimo = min && leerFechaIso(min) ? min : `${ANO_MINIMO}-01-01`;
  const maximo = max && leerFechaIso(max) ? max : `${ANO_MAXIMO}-12-31`;
  const seleccion = leerFechaIso(valor);
  const fueraDeRango = (p: Partes) => aIso(p) < minimo || aIso(p) > maximo;
  const acotar = (p: Partes): Partes => {
    const iso = aIso(p);
    if (iso < minimo) return leerFechaIso(minimo) as Partes;
    if (iso > maximo) return leerFechaIso(maximo) as Partes;
    return p;
  };

  const cerrar = useCallback((devolverFoco: boolean) => {
    setAbierto(false);
    if (devolverFoco) disparador.current?.focus();
  }, []);

  const abrir = () => {
    setEnfoque(acotar(seleccion ?? leerFechaIso(isoHoy) ?? { ano: 2026, mes: 0, dia: 1 }));
    setAbierto(true);
    setDebeEnfocar(true);
  };

  // Lleva el foco al día activo cuando se abre o cuando el teclado lo mueve.
  useEffect(() => {
    if (!abierto || !debeEnfocar || !enfoque) return;
    cuadricula.current?.querySelector<HTMLButtonElement>(`[data-fecha="${aIso(enfoque)}"]`)?.focus();
    setDebeEnfocar(false);
  }, [abierto, debeEnfocar, enfoque]);

  // Clic fuera cierra sin robar el foco.
  useEffect(() => {
    if (!abierto) return;
    const alPulsar = (evento: MouseEvent) => {
      if (raiz.current && !raiz.current.contains(evento.target as Node)) cerrar(false);
    };
    document.addEventListener("mousedown", alPulsar);
    return () => document.removeEventListener("mousedown", alPulsar);
  }, [abierto, cerrar]);

  const elegir = (iso: string) => {
    alCambiar(iso);
    cerrar(true);
  };

  const mover = (destino: Partes) => {
    setEnfoque(acotar(destino));
    setDebeEnfocar(true);
  };

  const teclado = (evento: KeyboardEvent<HTMLTableElement>) => {
    if (!enfoque) return;
    const acciones: Record<string, () => Partes> = {
      ArrowLeft: () => sumarDias(enfoque, -1),
      ArrowRight: () => sumarDias(enfoque, 1),
      ArrowUp: () => sumarDias(enfoque, -7),
      ArrowDown: () => sumarDias(enfoque, 7),
      Home: () => sumarDias(enfoque, -diaSemana(enfoque)),
      End: () => sumarDias(enfoque, 6 - diaSemana(enfoque)),
      PageUp: () => sumarMeses(enfoque, evento.shiftKey ? -12 : -1),
      PageDown: () => sumarMeses(enfoque, evento.shiftKey ? 12 : 1),
    };
    const accion = acciones[evento.key];
    if (!accion) return;
    evento.preventDefault();
    mover(accion());
  };

  const vista = enfoque ?? seleccion ?? (leerFechaIso(isoHoy) as Partes);
  const anoMin = Number(minimo.slice(0, 4));
  const anoMax = Number(maximo.slice(0, 4));
  const anos = Array.from({ length: anoMax - anoMin + 1 }, (_, i) => anoMin + i);
  const primerDia = diaSemana({ ...vista, dia: 1 });
  const totalDias = diasDelMes(vista.ano, vista.mes);
  const celdas: (Partes | null)[] = [
    ...Array.from({ length: primerDia }, () => null),
    ...Array.from({ length: totalDias }, (_, i) => ({ ano: vista.ano, mes: vista.mes, dia: i + 1 })),
  ];
  while (celdas.length % 7 !== 0) celdas.push(null);
  const semanas = Array.from({ length: celdas.length / 7 }, (_, i) => celdas.slice(i * 7, i * 7 + 7));
  const puedeAnterior = aIso({ ano: vista.ano, mes: vista.mes, dia: 1 }) > minimo;
  const puedeSiguiente = aIso({ ano: vista.ano, mes: vista.mes, dia: totalDias }) < maximo;
  const descripcion = [ayuda && !error ? `${id}-ayuda` : null, error ? `${id}-error` : null].filter(Boolean).join(" ") || undefined;

  return (
    <div
      ref={raiz}
      className="relative flex w-full flex-col gap-1"
      onKeyDown={(e) => {
        if (e.key === "Escape" && abierto) {
          e.stopPropagation();
          e.preventDefault();
          cerrar(true);
        }
      }}
    >
      <span id={idEtiqueta} className="text-sm font-medium">
        {etiqueta}
        {obligatorio && (
          <span aria-hidden="true" className="text-marca-rojo">
            {" "}
            *
          </span>
        )}
        {obligatorio && <span className="sr-only"> (obligatorio)</span>}
      </span>
      <button
        ref={disparador}
        type="button"
        className="glass-input campo-fecha-disparador flex min-h-[44px] items-center justify-between gap-2 text-left"
        aria-labelledby={`${idEtiqueta} ${idValor}`}
        aria-describedby={descripcion}
        aria-invalid={Boolean(error)}
        aria-haspopup="dialog"
        aria-expanded={abierto}
        disabled={disabled}
        onClick={() => (abierto ? cerrar(true) : abrir())}
      >
        <span id={idValor} className={seleccion ? "" : "texto-secundario"}>
          {seleccion ? formatearFechaLarga(valor) : "Seleccione una fecha"}
        </span>
        <CalendarDays aria-hidden="true" size={18} className="shrink-0" />
      </button>
      {ayuda && !error && (
        <p id={`${id}-ayuda`} className="texto-secundario text-xs">
          {ayuda}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="flex items-center gap-1 text-xs font-semibold text-[#a3161d] dark:text-[#ff8a8f]">
          <span aria-hidden="true">⚠</span> {error}
        </p>
      )}

      {abierto && (
        <div role="dialog" aria-label={`Calendario: ${etiqueta}`} className="glass-popover calendario absolute top-full left-0 z-50 mt-2 p-3">
          <div className="mb-2 flex items-center gap-1">
            <button
              type="button"
              className="calendario-nav"
              aria-label="Mes anterior"
              disabled={!puedeAnterior}
              onClick={() => mover(sumarMeses(vista, -1))}
            >
              <ChevronLeft aria-hidden="true" size={18} />
            </button>
            <select
              aria-label="Mes"
              className="glass-input calendario-select"
              value={vista.mes}
              onChange={(e) => setEnfoque(acotar({ ...vista, mes: Number(e.target.value), dia: Math.min(vista.dia, diasDelMes(vista.ano, Number(e.target.value))) }))}
            >
              {MESES.map((nombre, i) => (
                <option key={nombre} value={i}>
                  {nombre}
                </option>
              ))}
            </select>
            <select
              aria-label="Año"
              className="glass-input calendario-select"
              value={vista.ano}
              onChange={(e) => setEnfoque(acotar({ ...vista, ano: Number(e.target.value), dia: Math.min(vista.dia, diasDelMes(Number(e.target.value), vista.mes)) }))}
            >
              {anos.map((ano) => (
                <option key={ano} value={ano}>
                  {ano}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="calendario-nav"
              aria-label="Mes siguiente"
              disabled={!puedeSiguiente}
              onClick={() => mover(sumarMeses(vista, 1))}
            >
              <ChevronRight aria-hidden="true" size={18} />
            </button>
          </div>

          <table ref={cuadricula} role="grid" aria-label={`${MESES[vista.mes]} de ${vista.ano}`} className="w-full border-collapse" onKeyDown={teclado}>
            <thead>
              <tr>
                {DIAS_SEMANA.map((d) => (
                  <th key={d.corto} scope="col" abbr={d.largo} className="texto-secundario pb-1 text-center text-xs font-semibold uppercase">
                    {d.corto}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {semanas.map((semana, i) => (
                <tr key={i}>
                  {semana.map((dia, j) =>
                    dia ? (
                      <td key={j} role="gridcell" className="p-0 text-center">
                        <button
                          type="button"
                          data-fecha={aIso(dia)}
                          className="calendario-dia"
                          aria-label={formatearFechaLarga(aIso(dia))}
                          aria-pressed={valor === aIso(dia)}
                          aria-current={aIso(dia) === isoHoy ? "date" : undefined}
                          tabIndex={enfoque && aIso(enfoque) === aIso(dia) ? 0 : -1}
                          disabled={fueraDeRango(dia)}
                          onClick={() => elegir(aIso(dia))}
                        >
                          {dia.dia}
                        </button>
                      </td>
                    ) : (
                      <td key={j} role="gridcell" aria-hidden="true" />
                    ),
                  )}
                </tr>
              ))}
            </tbody>
          </table>

          <div className="mt-2 flex justify-between gap-2">
            <button type="button" className="btn btn-texto" onClick={() => elegir("")}>
              Limpiar
            </button>
            <button
              type="button"
              className="btn btn-secundario"
              disabled={!leerFechaIso(isoHoy) || fueraDeRango(leerFechaIso(isoHoy) as Partes)}
              onClick={() => elegir(isoHoy)}
            >
              Hoy
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
