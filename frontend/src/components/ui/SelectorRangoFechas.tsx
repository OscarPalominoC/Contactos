import { X } from "lucide-react";

import { CampoFecha } from "./CampoFecha";

export interface RangoFechas {
  desde: string;
  hasta: string;
}

interface SelectorRangoFechasProps extends RangoFechas {
  alCambiar: (rango: RangoFechas) => void;
  leyenda?: string;
  etiquetaDesde?: string;
  etiquetaHasta?: string;
}

/** Dos calendarios enlazados: «Desde» nunca puede ser posterior a «Hasta» (cada uno acota al otro). */
export function SelectorRangoFechas({
  desde,
  hasta,
  alCambiar,
  leyenda = "Rango de fechas",
  etiquetaDesde = "Desde",
  etiquetaHasta = "Hasta",
}: SelectorRangoFechasProps) {
  return (
    <fieldset className="col-span-full flex flex-col gap-2 md:col-span-2">
      <legend className="sr-only">{leyenda}</legend>
      <div className="grid grid-cols-1 items-end gap-4 sm:grid-cols-[1fr_1fr_auto]">
        <CampoFecha etiqueta={etiquetaDesde} valor={desde} max={hasta || undefined} alCambiar={(v) => alCambiar({ desde: v, hasta })} />
        <CampoFecha etiqueta={etiquetaHasta} valor={hasta} min={desde || undefined} alCambiar={(v) => alCambiar({ desde, hasta: v })} />
        {(desde || hasta) && (
          <button type="button" className="btn btn-texto" onClick={() => alCambiar({ desde: "", hasta: "" })}>
            <X aria-hidden="true" size={18} />
            <span>Limpiar fechas</span>
          </button>
        )}
      </div>
    </fieldset>
  );
}
