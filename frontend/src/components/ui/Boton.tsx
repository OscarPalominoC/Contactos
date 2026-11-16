import { Loader2 } from "lucide-react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variante = "primario" | "secundario" | "azul" | "peligro" | "texto";

interface BotonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
  cargando?: boolean;
  icono?: ReactNode;
  textoCargando?: string;
}

/** Botón con protección anti doble envío: deshabilitado e indicador mientras `cargando`. */
export function Boton({
  variante = "primario",
  cargando = false,
  icono,
  textoCargando,
  children,
  disabled,
  type = "button",
  className = "",
  ...props
}: BotonProps) {
  return (
    <button
      type={type}
      className={`btn btn-${variante} ${className}`}
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      {...props}
    >
      {cargando ? <Loader2 aria-hidden="true" size={18} className="giro" /> : icono}
      <span>{cargando && textoCargando ? textoCargando : children}</span>
    </button>
  );
}
