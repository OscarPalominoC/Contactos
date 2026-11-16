import { z } from "zod";

import { esCumpleanosValido } from "../../utils/formatters";

/** Validación de formularios de contactos (separada del JSX). */
export const formularioContactoSchema = z.object({
  nip: z
    .string()
    .trim()
    .transform((v) => v.replace(/\s+/g, "").toUpperCase())
    .pipe(z.string().regex(/^[0-9A-Z-]{3,30}$/, "Use solo números, letras y guiones (3 a 30).")),
  nombre: z
    .string()
    .trim()
    .min(3, "Escriba el nombre completo."),
  telefono: z.string().trim().max(100),
  celular: z
    .string()
    .trim()
    .refine((v) => v === "" || /^[\d\s+()-]{7,20}$/.test(v), "Escriba un teléfono válido, por ejemplo 300 123 4567."),
  correo: z
    .string()
    .trim()
    .refine((v) => v === "" || /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v), "Escriba un correo válido, por ejemplo nombre@dominio.com."),
  direccion: z.string().trim().max(255),
  dia_nac: z
    .string()
    .refine((v) => v === "" || (Number(v) >= 1 && Number(v) <= 31), "El día debe estar entre 1 y 31."),
  mes_nac: z.string(),
  estado: z.enum(["habilitado", "inhabilitado"]),
  contactar_cumpleanos: z.boolean(),
  contactar_soat: z.boolean(),
  contactar_rtm: z.boolean(),
}).superRefine((datos, ctx) => {
  if (datos.dia_nac !== "" && datos.mes_nac !== "" && !esCumpleanosValido(Number(datos.dia_nac), Number(datos.mes_nac))) {
    ctx.addIssue({ code: "custom", path: ["dia_nac"], message: "Ese día no existe en el mes elegido." });
  }
});

export type FormularioContacto = z.input<typeof formularioContactoSchema>;

export function cuerpoContacto(datos: z.output<typeof formularioContactoSchema>, edicion: boolean): Record<string, unknown> {
  const cuerpo: Record<string, unknown> = {
    nombre: datos.nombre,
    telefono: datos.telefono,
    celular: datos.celular,
    correo: datos.correo,
    direccion: datos.direccion,
    dia_nac: datos.dia_nac === "" ? null : Number(datos.dia_nac),
    mes_nac: datos.mes_nac === "" ? null : Number(datos.mes_nac),
    estado: datos.estado,
    contactar_cumpleanos: datos.contactar_cumpleanos,
    contactar_soat: datos.contactar_soat,
    contactar_rtm: datos.contactar_rtm,
  };
  if (!edicion) cuerpo.nip = datos.nip;
  return cuerpo;
}
