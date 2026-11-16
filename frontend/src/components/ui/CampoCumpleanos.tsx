import { Cake, ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { cumpleanos, diasDelMesCumpleanos, hoyBogota, MESES } from "../../utils/formatters";

const DIAS_SEMANA = [
  { corto: "lu", largo: "lunes" },
  { corto: "ma", largo: "martes" },
  { corto: "mi", largo: "miércoles" },
  { corto: "ju", largo: "jueves" },
  { corto: "vi", largo: "viernes" },
  { corto: "sá", largo: "sábado" },
  { corto: "do", largo: "domingo" },
] as const;

interface DiaMes {
  mes: number; // 1 a 12
  dia: number;
}

/** Todos los días de enero 1 a diciembre 31, con el 29 de febrero siempre presente (nadie pierde su cumpleaños). */
const DIAS_DEL_ANO: DiaMes[] = Array.from({ length: 12 }, (_, i) =>
  Array.from({ length: diasDelMesCumpleanos(i + 1) }, (_, d) => ({ mes: i + 1, dia: d + 1 })),
).flat();
const indice = (p: DiaMes) => DIAS_DEL_ANO.findIndex((d) => d.mes === p.mes && d.dia === p.dia);
const enRango = (i: number) => DIAS_DEL_ANO[Math.min(Math.max(i, 0), DIAS_DEL_ANO.length - 1)] as DiaMes;

/** Columna del primer día del mes (lunes = 0) según el calendario de `ano`. */
const columnaInicial = (ano: number, mes: number) => (new Date(Date.UTC(ano, mes - 1, 1)).getUTCDay() + 6) % 7;

interface CampoCumpleanosProps {
  etiqueta: string;
  dia: number | null;
  mes: number | null;
  alCambiar: (dia: number | null, mes: number | null) => void;
  error?: string;
  ayuda?: string;
  /** Año cuyo calendario da la disposición de los días de la semana (por defecto, el actual en Bogotá). */
  ano?: number;
}

/**
 * Selector de cumpleaños (día y mes, sin año): calendario de enero a diciembre con los días de la semana
 * del año actual. No se elige año porque no se almacena.
 * Teclado: flechas (día/semana), Inicio/Fin (semana), RePág/AvPág (mes), Enter/Espacio (elegir), Escape (cerrar).
 */
export function CampoCumpleanos({ etiqueta, dia, mes, alCambiar, error, ayuda, ano }: CampoCumpleanosProps) {
  const id = useId();
  const idEtiqueta = `${id}-etiqueta`;
  const idValor = `${id}-valor`;
  const raiz = useRef<HTMLDivElement>(null);
  const disparador = useRef<HTMLButtonElement>(null);
  const cuadricula = useRef<HTMLTableElement>(null);
  const [abierto, setAbierto] = useState(false);
  const [enfoque, setEnfoque] = useState<DiaMes>({ mes: 1, dia: 1 });
  const [debeEnfocar, setDebeEnfocar] = useState(false);

  const hoy = hoyBogota();
  const anoCalendario = ano ?? Number(hoy.slice(0, 4));
  const seleccion = dia && mes && indice({ dia, mes }) >= 0 ? { dia, mes } : null;
  const clave = (p: DiaMes) => `${p.mes}-${p.dia}`;

  const cerrar = useCallback((devolverFoco: boolean) => {
    setAbierto(false);
    if (devolverFoco) disparador.current?.focus();
  }, []);

  const abrir = () => {
    setEnfoque(seleccion ?? { mes: Number(hoy.slice(5, 7)), dia: Number(hoy.slice(8, 10)) });
    setAbierto(true);
    setDebeEnfocar(true);
  };

  useEffect(() => {
    if (!abierto || !debeEnfocar) return;
    cuadricula.current?.querySelector<HTMLButtonElement>(`[data-dia="${clave(enfoque)}"]`)?.focus();
    setDebeEnfocar(false);
  }, [abierto, debeEnfocar, enfoque]);

  useEffect(() => {
    if (!abierto) return;
    const alPulsar = (evento: MouseEvent) => {
      if (raiz.current && !raiz.current.contains(evento.target as Node)) cerrar(false);
    };
    document.addEventListener("mousedown", alPulsar);
    return () => document.removeEventListener("mousedown", alPulsar);
  }, [abierto, cerrar]);

  const elegir = (valor: DiaMes | null) => {
    alCambiar(valor?.dia ?? null, valor?.mes ?? null);
    cerrar(true);
  };

  const mover = (destino: DiaMes) => {
    setEnfoque(destino);
    setDebeEnfocar(true);
  };

  const cambiarMes = (delta: number) => {
    const nuevoMes = Math.min(Math.max(enfoque.mes + delta, 1), 12);
    mover({ mes: nuevoMes, dia: Math.min(enfoque.dia, diasDelMesCumpleanos(nuevoMes)) });
  };

  const teclado = (evento: KeyboardEvent<HTMLTableElement>) => {
    const i = indice(enfoque);
    const columna = (columnaInicial(anoCalendario, enfoque.mes) + enfoque.dia - 1) % 7;
    const acciones: Record<string, () => void> = {
      ArrowLeft: () => mover(enRango(i - 1)),
      ArrowRight: () => mover(enRango(i + 1)),
      ArrowUp: () => mover(enRango(i - 7)),
      ArrowDown: () => mover(enRango(i + 7)),
      Home: () => mover(enRango(i - Math.min(columna, enfoque.dia - 1))),
      End: () => mover(enRango(i + Math.min(6 - columna, diasDelMesCumpleanos(enfoque.mes) - enfoque.dia))),
      PageUp: () => cambiarMes(-1),
      PageDown: () => cambiarMes(1),
    };
    const accion = acciones[evento.key];
    if (!accion) return;
    evento.preventDefault();
    accion();
  };

  const nombreMes = MESES[enfoque.mes - 1] ?? "";
  const totalDias = diasDelMesCumpleanos(enfoque.mes);
  const celdas: (DiaMes | null)[] = [
    ...Array.from({ length: columnaInicial(anoCalendario, enfoque.mes) }, () => null),
    ...Array.from({ length: totalDias }, (_, i) => ({ mes: enfoque.mes, dia: i + 1 })),
  ];
  while (celdas.length % 7 !== 0) celdas.push(null);
  const semanas = Array.from({ length: celdas.length / 7 }, (_, i) => celdas.slice(i * 7, i * 7 + 7));
  const esHoy = (p: DiaMes) => p.mes === Number(hoy.slice(5, 7)) && p.dia === Number(hoy.slice(8, 10));
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
        onClick={() => (abierto ? cerrar(true) : abrir())}
      >
        <span id={idValor} className={seleccion ? "" : "texto-secundario"}>
          {seleccion ? cumpleanos(seleccion.dia, seleccion.mes) : "Seleccione día y mes"}
        </span>
        <Cake aria-hidden="true" size={18} className="shrink-0" />
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
          <div className="mb-2 flex items-center justify-between gap-1">
            <button type="button" className="calendario-nav" aria-label="Mes anterior" disabled={enfoque.mes === 1} onClick={() => cambiarMes(-1)}>
              <ChevronLeft aria-hidden="true" size={18} />
            </button>
            <p className="font-heading text-sm font-bold" aria-live="polite">
              {nombreMes}
            </p>
            <button type="button" className="calendario-nav" aria-label="Mes siguiente" disabled={enfoque.mes === 12} onClick={() => cambiarMes(1)}>
              <ChevronRight aria-hidden="true" size={18} />
            </button>
          </div>

          <table ref={cuadricula} role="grid" aria-label={nombreMes} className="w-full border-collapse" onKeyDown={teclado}>
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
                  {semana.map((celda, j) =>
                    celda ? (
                      <td key={j} role="gridcell" className="p-0 text-center">
                        <button
                          type="button"
                          data-dia={clave(celda)}
                          className="calendario-dia"
                          aria-label={cumpleanos(celda.dia, celda.mes)}
                          aria-pressed={seleccion !== null && clave(seleccion) === clave(celda)}
                          aria-current={esHoy(celda) ? "date" : undefined}
                          tabIndex={clave(enfoque) === clave(celda) ? 0 : -1}
                          onClick={() => elegir(celda)}
                        >
                          {celda.dia}
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

          <div className="mt-2 flex justify-start">
            <button type="button" className="btn btn-texto" onClick={() => elegir(null)}>
              Limpiar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
