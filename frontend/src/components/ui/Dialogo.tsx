import { X } from "lucide-react";
import { useEffect, useId, useRef, type ReactNode } from "react";

import { Boton } from "./Boton";

interface DialogoProps {
  abierto: boolean;
  titulo: string;
  alCerrar: () => void;
  children: ReactNode;
  pie?: ReactNode;
}

/**
 * Diálogo modal nativo (<dialog>): captura el foco mientras está abierto, se cierra con Esc
 * y devuelve el foco al elemento que lo abrió.
 */
export function Dialogo({ abierto, titulo, alCerrar, children, pie }: DialogoProps) {
  const referencia = useRef<HTMLDialogElement>(null);
  const disparador = useRef<Element | null>(null);
  const idTitulo = useId();

  useEffect(() => {
    const dialogo = referencia.current;
    if (!dialogo) return;
    if (abierto && !dialogo.open) {
      disparador.current = document.activeElement;
      if (typeof dialogo.showModal === "function") dialogo.showModal();
      else dialogo.setAttribute("open", "");
    } else if (!abierto && dialogo.open) {
      if (typeof dialogo.close === "function") dialogo.close();
      else dialogo.removeAttribute("open");
      if (disparador.current instanceof HTMLElement) disparador.current.focus();
    }
  }, [abierto]);

  return (
    <dialog
      ref={referencia}
      aria-labelledby={idTitulo}
      onCancel={(evento) => {
        evento.preventDefault();
        alCerrar();
      }}
      className="glass-card m-auto w-[min(40rem,calc(100vw-2rem))] p-0 text-[var(--text-main)] backdrop:bg-black/50"
    >
      {abierto && (
        <div className="flex max-h-[85vh] flex-col">
          <header className="flex items-center justify-between gap-4 border-b border-[var(--glass-border)] p-4">
            <h2 id={idTitulo} className="text-lg font-bold">
              {titulo}
            </h2>
            <Boton variante="texto" onClick={alCerrar} aria-label="Cerrar diálogo" icono={<X aria-hidden="true" size={20} />}>
              <span className="sr-only">Cerrar</span>
            </Boton>
          </header>
          <div className="overflow-y-auto p-4">{children}</div>
          {pie && <footer className="flex flex-wrap justify-end gap-2 border-t border-[var(--glass-border)] p-4">{pie}</footer>}
        </div>
      )}
    </dialog>
  );
}

/** Paso de confirmación previo a acciones irreversibles (WCAG 3.3.4). */
export function Confirmacion({
  abierto,
  titulo,
  mensaje,
  textoConfirmar,
  cargando,
  alConfirmar,
  alCerrar,
}: {
  abierto: boolean;
  titulo: string;
  mensaje: ReactNode;
  textoConfirmar: string;
  cargando?: boolean;
  alConfirmar: () => void;
  alCerrar: () => void;
}) {
  return (
    <Dialogo
      abierto={abierto}
      titulo={titulo}
      alCerrar={alCerrar}
      pie={
        <>
          <Boton variante="secundario" onClick={alCerrar} disabled={cargando}>
            Cancelar
          </Boton>
          <Boton variante="peligro" onClick={alConfirmar} cargando={cargando}>
            {textoConfirmar}
          </Boton>
        </>
      }
    >
      <div className="text-sm">{mensaje}</div>
    </Dialogo>
  );
}
