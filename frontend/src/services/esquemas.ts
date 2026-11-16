import { z } from "zod";

/** Esquemas de las respuestas de la API: se validan en la frontera. */

export function sobrePaginado<T extends z.ZodTypeAny>(item: T) {
  return z.object({
    data: z.array(item),
    meta: z.object({
      page: z.object({ number: z.number(), size: z.number(), total: z.number(), total_pages: z.number() }),
    }),
    links: z.record(z.string(), z.string().nullable()),
  });
}

export type Paginado<T> = {
  data: T[];
  meta: { page: { number: number; size: number; total: number; total_pages: number } };
  links: Record<string, string | null>;
};

const texto = z.string();
const textoNulo = z.string().nullable();

export const auditoria = {
  creado_en: textoNulo,
  actualizado_en: textoNulo,
  creado_por: texto,
  actualizado_por: texto,
};

export const ROLES = ["administrador", "ingeniero", "tecnico", "usuario"] as const;
export type Rol = (typeof ROLES)[number];

export const yoSchema = z.object({
  nip: texto,
  nombre: texto,
  rol: z.enum(ROLES),
  debe_cambiar_clave: z.boolean(),
  permisos: z.array(texto),
});
export type Yo = z.infer<typeof yoSchema>;

export const accesoSchema = z.object({ access: texto, expira_en: z.number() });

export const contactoSchema = z.object({
  nip: texto,
  nombre: texto,
  telefono: texto,
  celular: texto,
  dia_nac: z.number().nullable(),
  mes_nac: z.number().nullable(),
  mes_nac_nombre: textoNulo,
  direccion: texto,
  correo: texto,
  estado: z.enum(["habilitado", "inhabilitado"]),
  usuario: texto,
  fecha_registro: textoNulo,
  cumple_confir: z.boolean(),
  contactar_cumpleanos: z.boolean(),
  contactar_soat: z.boolean(),
  contactar_rtm: z.boolean(),
  ...auditoria,
});
export type Contacto = z.infer<typeof contactoSchema>;

export const motoSchema = z.object({
  placa: texto,
  marca: texto,
  modelo: texto,
  linea: texto,
  nip_contacto: texto,
  nombre_contacto: z.string().nullable().optional(),
  nro_soat: texto,
  fecha_soat: textoNulo,
  fecha_venc_soat: textoNulo,
  nro_certificado: texto,
  fecha_rtmg: textoNulo,
  fecha_venc_rtmg: textoNulo,
  propietario: z.object({ nip: texto, nombre: texto, celular: texto }).nullable().optional(),
  ...auditoria,
});
export type Moto = z.infer<typeof motoSchema>;

export const marcaSchema = z.object({ codigo: texto, nombre: texto });
export type Marca = z.infer<typeof marcaSchema>;

export const lineaSchema = z.object({ linea: texto, marca: texto, marca_nombre: z.string().nullable() });
export type Linea = z.infer<typeof lineaSchema>;

/** Titular de la moto (null si la moto o el contacto no existen en el legado). */
const propietario = { propietario_nip: z.string().nullable().optional(), propietario_nombre: z.string().nullable().optional() };

export const ESTADOS_DOCUMENTO = ["VIGENTE", "VENCIDO", "DUPLICADO", "ANULADO", "NO"] as const;
export type EstadoDocumento = (typeof ESTADOS_DOCUMENTO)[number];

export const revisionSchema = z.object({
  certificado: texto,
  placa: texto,
  ...propietario,
  soat: texto,
  fecha_soat: textoNulo,
  fecha_venc_soat: textoNulo,
  fecha_certificado: textoNulo,
  fecha_venc_certificado: textoNulo,
  nro_autodeclaracion_runt: texto,
  nro_solicitud_runt: texto,
  nro_certificado_runt: texto,
  fecha_registro_runt: textoNulo,
  estado: z.enum(ESTADOS_DOCUMENTO),
  estado_actual: z.enum(ESTADOS_DOCUMENTO),
  usuario: texto,
  fecha_registro: textoNulo,
  ...auditoria,
});
export type Revision = z.infer<typeof revisionSchema>;

export const soatSchema = z.object({
  soat: texto,
  placa: z.string().nullable(),
  ...propietario,
  aseguradora: texto,
  fecha_soat: textoNulo,
  fecha_venc_soat: textoNulo,
  estado: z.enum(ESTADOS_DOCUMENTO),
  estado_actual: z.enum(ESTADOS_DOCUMENTO),
  usuario: texto,
  fecha_registro: textoNulo,
  ...auditoria,
});
export type Soat = z.infer<typeof soatSchema>;

export const ESTADOS_LLAMADA = ["realizada", "no_realizada", "realizada_sin_exito", "ocupada", "sin_estado"] as const;
export type EstadoLlamada = (typeof ESTADOS_LLAMADA)[number];

const llamadaBase = {
  motivo_llamada: texto,
  estado: z.enum(ESTADOS_LLAMADA),
  estado_nombre: texto,
  observacion: texto,
  usuario: texto,
  num_llamadas: z.number(),
  intentos: texto,
  ...auditoria,
};

export const llamadaCumpleanosSchema = z.object({ id: z.number(), fecha: texto, nip: texto, nombre: z.string().nullable().optional(), ...llamadaBase });
export type LlamadaCumpleanos = z.infer<typeof llamadaCumpleanosSchema>;

export const llamadaPlacaSchema = z.object({ id: texto, fecha: textoNulo, placa: texto, ...llamadaBase });
export type LlamadaPlaca = z.infer<typeof llamadaPlacaSchema>;

export const fichaSchema = z.object({
  contacto: contactoSchema,
  motos: z.array(motoSchema),
  revisiones: z.array(revisionSchema),
  soats: z.array(soatSchema),
  llamadas_cumpleanos: z.array(llamadaCumpleanosSchema),
  llamadas_rtm: z.array(llamadaPlacaSchema),
  llamadas_soat: z.array(llamadaPlacaSchema),
});
export type Ficha = z.infer<typeof fichaSchema>;

export const tableroSchema = z.object({
  dias_horizonte: z.number(),
  rtm_por_vencer: z.number(),
  soat_por_vencer: z.number(),
  llamadas_hoy: z.object({ cumpleanos: z.number(), rtm: z.number(), soat: z.number() }),
  cumpleanos_hoy: z.number(),
  contactos_nuevos_mes: z.number(),
});
export type Tablero = z.infer<typeof tableroSchema>;

export const usuarioSchema = z.object({
  nip: texto,
  nombre: texto,
  rol: z.enum(ROLES),
  is_active: z.boolean(),
  debe_cambiar_clave: z.boolean(),
  last_login: textoNulo,
  clave_cambiada_en: textoNulo,
  clave_temporal: z.string().optional(),
});
export type Usuario = z.infer<typeof usuarioSchema>;

/** Vencimiento de RTM o SOAT por llamar (calculado en el servidor desde los documentos). */
export const porLlamarSchema = z.object({
  placa: texto,
  fecha: texto,
  propietario_nip: texto,
  propietario_nombre: texto,
  celular: texto,
  llamada_id: z.string().nullable(),
  estado: z.enum([...ESTADOS_LLAMADA, "sin_llamar"]),
  num_llamadas: z.number(),
  observacion: texto,
});
export type PorLlamar = z.infer<typeof porLlamarSchema>;

export const esServidorSchema = z.object({
  es_servidor: z.boolean(),
});
export type EsServidor = z.infer<typeof esServidorSchema>;

export const respaldoUltimoSchema = z.object({
  archivo: z.string(),
  tamano_bytes: z.number(),
  tamano_formateado: z.string(),
  creado_en: z.string(),
});
export type RespaldoUltimo = z.infer<typeof respaldoUltimoSchema>;

export const respaldoEstadoSchema = z.object({
  es_servidor_local: z.boolean(),
  ruta_configurada: z.string(),
  ejecutando: z.boolean(),
  ultimo_respaldo: respaldoUltimoSchema.nullable().optional(),
  total_respaldos: z.number(),
  ultimo_resultado: z.string().nullable().optional(),
});
export type RespaldoEstado = z.infer<typeof respaldoEstadoSchema>;

export const rutaValidacionResponseSchema = z.object({
  valida: z.boolean(),
  ruta: z.string(),
  mensaje: z.string(),
});
export type RutaValidacionResponse = z.infer<typeof rutaValidacionResponseSchema>;

export const rutaConfigResponseSchema = z.object({
  ruta_configurada: z.string(),
  mensaje: z.string(),
});
export type RutaConfigResponse = z.infer<typeof rutaConfigResponseSchema>;

export const respaldoEjecucionResponseSchema = z.object({
  mensaje: z.string(),
  ruta_destino: z.string(),
  iniciado_en: z.string(),
});
export type RespaldoEjecucionResponse = z.infer<typeof respaldoEjecucionResponseSchema>;
