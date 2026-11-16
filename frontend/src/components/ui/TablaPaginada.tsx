import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import type { ApiError } from "../../services/apiClient";
import type { Paginado } from "../../services/esquemas";
import { formatearNumero } from "../../utils/formatters";
import { AvisoError } from "./Aviso";
import { Boton } from "./Boton";
import { EstadoVacio } from "./EstadoVacio";

export interface Columna<T> {
  clave: string;
  titulo: string;
  celda: (fila: T) => ReactNode;
  ordenable?: string;
  clase?: string;
}

interface TablaPaginadaProps<T> {
  titulo: string;
  columnas: Columna<T>[];
  datos: Paginado<T> | undefined;
  cargando: boolean;
  error: ApiError | null;
  claveFila: (fila: T) => string;
  pagina: number;
  alCambiarPagina: (pagina: number) => void;
  orden?: string;
  alOrdenar?: (orden: string) => void;
  vacio?: ReactNode;
}

/** Tabla con page[number]/page[size], orden y estados de carga, error y vacío. */
export function TablaPaginada<T>({
  titulo,
  columnas,
  datos,
  cargando,
  error,
  claveFila,
  pagina,
  alCambiarPagina,
  orden,
  alOrdenar,
  vacio,
}: TablaPaginadaProps<T>) {
  if (error) return <AvisoError error={error} />;
  if (cargando && !datos) {
    return (
      <div role="status" className="flex items-center justify-center gap-2 p-8">
        <Loader2 aria-hidden="true" className="giro" /> Cargando {titulo.toLowerCase()}…
      </div>
    );
  }
  if (!datos || datos.data.length === 0) {
    return <>{vacio ?? <EstadoVacio titulo={`No hay ${titulo.toLowerCase()} para mostrar`} />}</>;
  }
  const { number, total, total_pages: totalPaginas } = datos.meta.page;

  const indicadorOrden = (campo: string): "ascending" | "descending" | "none" => {
    if (orden === campo) return "ascending";
    if (orden === `-${campo}`) return "descending";
    return "none";
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-x-auto" tabIndex={0} role="region" aria-label={`Tabla de ${titulo.toLowerCase()}`}>
        <table className="tabla" aria-busy={cargando}>
          <caption className="sr-only">
            {titulo}: página {number} de {totalPaginas}
          </caption>
          <thead>
            <tr>
              {columnas.map((columna) => (
                <th
                  key={columna.clave}
                  scope="col"
                  className={columna.clase}
                  aria-sort={columna.ordenable ? indicadorOrden(columna.ordenable) : undefined}
                >
                  {columna.ordenable && alOrdenar ? (
                    <button
                      type="button"
                      className="inline-flex min-h-6 items-center gap-1 font-semibold underline-offset-2 hover:underline"
                      onClick={() =>
                        alOrdenar(orden === columna.ordenable ? `-${columna.ordenable}` : (columna.ordenable as string))
                      }
                    >
                      {columna.titulo}
                      <span aria-hidden="true">
                        {indicadorOrden(columna.ordenable) === "ascending"
                          ? "▲"
                          : indicadorOrden(columna.ordenable) === "descending"
                            ? "▼"
                            : "↕"}
                      </span>
                    </button>
                  ) : (
                    columna.titulo
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {datos.data.map((fila) => (
              <tr key={claveFila(fila)}>
                {columnas.map((columna) => (
                  <td key={columna.clave} className={columna.clase}>
                    {columna.celda(fila)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <nav aria-label={`Paginación de ${titulo.toLowerCase()}`} className="flex flex-wrap items-center justify-between gap-2">
        <p className="texto-secundario text-sm" aria-live="polite">
          {formatearNumero(total)} registros · página {number} de {formatearNumero(totalPaginas)}
        </p>
        <div className="flex gap-2">
          <Boton
            variante="secundario"
            onClick={() => alCambiarPagina(pagina - 1)}
            disabled={number <= 1 || cargando}
            icono={<ChevronLeft aria-hidden="true" size={18} />}
          >
            Anterior
          </Boton>
          <Boton
            variante="secundario"
            onClick={() => alCambiarPagina(pagina + 1)}
            disabled={number >= totalPaginas || cargando}
            icono={<ChevronRight aria-hidden="true" size={18} />}
          >
            Siguiente
          </Boton>
        </div>
      </nav>
    </div>
  );
}
