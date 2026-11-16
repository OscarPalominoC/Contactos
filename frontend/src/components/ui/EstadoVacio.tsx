import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

/** Estado vacío estándar para toda lista o bloque sin datos. */
export function EstadoVacio({ titulo, descripcion, accion }: { titulo: string; descripcion?: string; accion?: ReactNode }) {
  return (
    <div role="status" className="flex flex-col items-center gap-2 px-4 py-8 text-center">
      <Inbox aria-hidden="true" size={40} strokeWidth={1.5} className="texto-secundario" />
      <p className="font-semibold">{titulo}</p>
      {descripcion && <p className="texto-secundario text-sm">{descripcion}</p>}
      {accion}
    </div>
  );
}
