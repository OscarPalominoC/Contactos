import { AlertTriangle, Ban, CheckCircle2, Copy, HelpCircle, Phone, PhoneMissed, PhoneOff } from "lucide-react";

import type { EstadoDocumento, EstadoLlamada } from "../../services/esquemas";

const DOCUMENTO: Record<EstadoDocumento, { clase: string; texto: string; Icono: typeof CheckCircle2 }> = {
  VIGENTE: { clase: "insignia-exito", texto: "Vigente", Icono: CheckCircle2 },
  VENCIDO: { clase: "insignia-alerta", texto: "Vencido", Icono: AlertTriangle },
  DUPLICADO: { clase: "insignia-aviso", texto: "Duplicado", Icono: Copy },
  ANULADO: { clase: "insignia-info", texto: "Anulado", Icono: Ban },
  NO: { clase: "insignia-info", texto: "No (legado)", Icono: HelpCircle },
};

/** Estado de RTM/SOAT: color + icono + texto (WCAG 1.4.1). */
export function InsigniaDocumento({ estado }: { estado: EstadoDocumento }) {
  const { clase, texto, Icono } = DOCUMENTO[estado];
  return (
    <span className={`insignia ${clase}`}>
      <Icono aria-hidden="true" size={14} />
      {texto}
    </span>
  );
}

const LLAMADA: Record<EstadoLlamada, { clase: string; Icono: typeof Phone }> = {
  realizada: { clase: "insignia-exito", Icono: Phone },
  no_realizada: { clase: "insignia-alerta", Icono: PhoneOff },
  realizada_sin_exito: { clase: "insignia-aviso", Icono: PhoneMissed },
  ocupada: { clase: "insignia-aviso", Icono: PhoneMissed },
  sin_estado: { clase: "insignia-info", Icono: HelpCircle },
};

export const NOMBRES_ESTADO_LLAMADA: Record<EstadoLlamada, string> = {
  realizada: "Realizada",
  no_realizada: "No realizada",
  realizada_sin_exito: "Realizada sin éxito",
  ocupada: "Ocupada",
  sin_estado: "Sin estado",
};

export function InsigniaLlamada({ estado }: { estado: EstadoLlamada }) {
  const { clase, Icono } = LLAMADA[estado];
  return (
    <span className={`insignia ${clase}`}>
      <Icono aria-hidden="true" size={14} />
      {NOMBRES_ESTADO_LLAMADA[estado]}
    </span>
  );
}

export function InsigniaContacto({ estado }: { estado: "habilitado" | "inhabilitado" }) {
  return estado === "habilitado" ? (
    <span className="insignia insignia-exito">
      <CheckCircle2 aria-hidden="true" size={14} />
      Habilitado
    </span>
  ) : (
    <span className="insignia insignia-alerta">
      <Ban aria-hidden="true" size={14} />
      Inhabilitado
    </span>
  );
}
