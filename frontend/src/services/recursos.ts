import type { z } from "zod";

import { ApiError, apiClient, normalizarError } from "./apiClient";
import { sobrePaginado, type Paginado } from "./esquemas";

export type Parametros = Record<string, string | number | undefined | null>;

/** Convierte { page: 1, size: 25, filtros: {estado: 'x'} } en page[number], page[size] y filter[...]. */
export function parametrosLista(pagina: number, tamano: number, filtros: Parametros = {}, orden?: string): Parametros {
  const salida: Parametros = { "page[number]": pagina, "page[size]": tamano };
  for (const [clave, valor] of Object.entries(filtros)) {
    if (valor !== undefined && valor !== null && valor !== "") salida[`filter[${clave}]`] = valor;
  }
  if (orden) salida.sort = orden;
  return salida;
}

/** Toda falla (HTTP, red o respuesta con forma inesperada) llega a la interfaz como ApiError. */
async function seguro<R>(operacion: () => Promise<R>): Promise<R> {
  try {
    return await operacion();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error && typeof error === "object" && "issues" in error) {
      throw new ApiError({
        type: "/problemas/respuesta-inesperada",
        title: "Respuesta inesperada",
        status: 0,
        detail: "El servidor respondió con datos que la aplicación no reconoce.",
      });
    }
    throw normalizarError(error);
  }
}

export async function obtenerLista<T extends z.ZodTypeAny>(
  ruta: string,
  esquema: T,
  params: Parametros,
  signal?: AbortSignal,
): Promise<Paginado<z.infer<T>>> {
  return seguro(async () => {
    const { data } = await apiClient.get(ruta, { params, signal });
    return sobrePaginado(esquema).parse(data) as Paginado<z.infer<T>>;
  });
}

export async function obtener<T extends z.ZodTypeAny>(ruta: string, esquema: T, signal?: AbortSignal): Promise<z.infer<T>> {
  return seguro(async () => {
    const { data } = await apiClient.get(ruta, { signal });
    return esquema.parse(data);
  });
}

export async function crear<T extends z.ZodTypeAny>(
  ruta: string,
  esquema: T,
  cuerpo: unknown,
  claveIdempotencia?: string,
): Promise<z.infer<T>> {
  return seguro(async () => {
    const { data } = await apiClient.post(ruta, cuerpo, {
      headers: claveIdempotencia ? { "Idempotency-Key": claveIdempotencia } : undefined,
    });
    return esquema.parse(data);
  });
}

export async function actualizar<T extends z.ZodTypeAny>(
  ruta: string,
  esquema: T,
  cuerpo: unknown,
  claveIdempotencia?: string,
): Promise<z.infer<T>> {
  return seguro(async () => {
    const { data } = await apiClient.patch(ruta, cuerpo, {
      headers: claveIdempotencia ? { "Idempotency-Key": claveIdempotencia } : undefined,
    });
    return esquema.parse(data);
  });
}

export async function eliminar(ruta: string): Promise<void> {
  await seguro(() => apiClient.delete(ruta));
}

export function ruta(base: string, id: string): string {
  return `${base}/${encodeURIComponent(id)}`;
}
