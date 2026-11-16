import type { ReactNode } from "react";

/** Encabezado de página: h1 único por vista con acciones opcionales. */
export function EncabezadoPagina({ titulo, descripcion, acciones }: { titulo: string; descripcion?: string; acciones?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl uppercase lg:text-3xl">{titulo}</h1>
        {descripcion && <p className="texto-secundario mt-1">{descripcion}</p>}
      </div>
      {acciones && <div className="flex flex-wrap gap-2">{acciones}</div>}
    </div>
  );
}

export function Tarjeta({ children, className = "", titulo }: { children: ReactNode; className?: string; titulo?: string }) {
  return (
    <section className={`glass-card p-4 lg:p-6 ${className}`} aria-label={titulo}>
      {titulo && <h2 className="mb-4 text-lg font-bold">{titulo}</h2>}
      {children}
    </section>
  );
}

/** Lista de definición para fichas de detalle. */
export function Detalles({ items }: { items: { termino: string; valor: ReactNode }[] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map(({ termino, valor }) => (
        <div key={termino}>
          <dt className="texto-secundario text-xs font-semibold uppercase">{termino}</dt>
          <dd className="mt-0.5 break-words">{valor}</dd>
        </div>
      ))}
    </dl>
  );
}
