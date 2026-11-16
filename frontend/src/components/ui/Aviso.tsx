import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import type { ReactNode } from "react";

import type { ApiError } from "../../services/apiClient";

type Tipo = "exito" | "error" | "info" | "advertencia";

const ICONOS = { exito: CheckCircle2, error: AlertTriangle, info: Info, advertencia: AlertTriangle } as const;
const CLASES = {
  exito: "insignia-exito",
  error: "insignia-alerta",
  info: "insignia-info",
  advertencia: "insignia-aviso",
} as const;

/** Mensaje de estado anunciado por lectores de pantalla (role=status / role=alert). */
export function Aviso({ tipo = "info", children }: { tipo?: Tipo; children: ReactNode }) {
  const Icono = ICONOS[tipo];
  return (
    <div
      role={tipo === "error" ? "alert" : "status"}
      className={`${CLASES[tipo]} flex items-start gap-2 rounded-lg border p-3 text-sm`}
    >
      <Icono aria-hidden="true" size={18} className="mt-0.5 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

/** Muestra un ApiError con su request_id para soporte. */
export function AvisoError({ error }: { error: ApiError | Error | null | undefined }) {
  if (!error) return null;
  const detalle = (error as ApiError).problema?.detail ?? error.message ?? "Ocurrió un error inesperado.";
  const requestId = (error as ApiError).problema?.request_id;
  return (
    <Aviso tipo="error">
      <p className="font-semibold">{detalle}</p>
      {requestId && (
        <p className="mt-1 text-xs">
          Código de soporte: <code>{requestId}</code>
        </p>
      )}
    </Aviso>
  );
}
