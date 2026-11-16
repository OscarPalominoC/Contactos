import { useMutation, useQuery, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import type { z } from "zod";

import type { ApiError } from "../services/apiClient";
import { nuevoId } from "../services/apiClient";
import { actualizar, crear, obtenerLista, parametrosLista, type Parametros } from "../services/recursos";

/** Lista paginada de un recurso con filtros y orden; cancela peticiones obsoletas con AbortSignal. */
export function useLista<T extends z.ZodTypeAny>(
  recurso: string,
  esquema: T,
  filtros: Parametros,
  tamano = 25,
  /** `habilitada: false` no consulta (p. ej. hasta que el usuario escriba una búsqueda). */
  { habilitada = true }: { habilitada?: boolean } = {},
) {
  const [pagina, setPagina] = useState(1);
  const [orden, setOrden] = useState<string | undefined>(undefined);
  const consulta = useQuery({
    queryKey: [recurso, "lista", { pagina, tamano, filtros, orden }],
    queryFn: ({ signal }) => obtenerLista(`/${recurso}`, esquema, parametrosLista(pagina, tamano, filtros, orden), signal),
    placeholderData: keepPreviousData,
    enabled: habilitada,
  });
  // Funciones estables: las páginas las usan como dependencia de efectos que reinician la página al
  // cambiar filtros. Si cambiaran en cada render, el efecto se dispararía siempre y devolvería a la página 1.
  const reiniciarPagina = useCallback(() => setPagina(1), []);
  const cambiarOrden = useCallback((nuevo: string) => {
    setOrden(nuevo);
    setPagina(1);
  }, []);
  return {
    ...consulta,
    error: consulta.error as ApiError | null,
    pagina,
    setPagina,
    orden,
    setOrden: cambiarOrden,
    reiniciarPagina,
  };
}

/**
 * Guardado con Idempotency-Key estable por intento de envío: un reintento del mismo envío
 * reutiliza la clave; tras el éxito se genera una nueva.
 */
export function useGuardar<T extends z.ZodTypeAny>(
  recurso: string,
  esquema: T,
  opciones: { id?: string; invalidar?: string[]; alExito?: (dato: z.infer<T>) => void } = {},
) {
  const queryClient = useQueryClient();
  const clave = useRef(nuevoId());
  const mutacion = useMutation<z.infer<T>, ApiError, Record<string, unknown>>({
    mutationFn: (cuerpo) =>
      opciones.id
        ? actualizar(`/${recurso}/${encodeURIComponent(opciones.id)}`, esquema, cuerpo, clave.current)
        : crear(`/${recurso}`, esquema, cuerpo, clave.current),
    onSuccess: async (dato) => {
      clave.current = nuevoId();
      await Promise.all(
        [recurso, ...(opciones.invalidar ?? [])].map((r) => queryClient.invalidateQueries({ queryKey: [r] })),
      );
      opciones.alExito?.(dato);
    },
  });
  return mutacion;
}

/** Acción POST sobre un elemento (anular, intentos, reiniciar-clave). */
export function useAccion<T extends z.ZodTypeAny>(
  recurso: string,
  accion: string,
  esquema: T,
  opciones: { invalidar?: string[]; alExito?: (dato: z.infer<T>) => void } = {},
) {
  const queryClient = useQueryClient();
  const clave = useRef(nuevoId());
  return useMutation<z.infer<T>, ApiError, { id: string; cuerpo?: Record<string, unknown> }>({
    mutationFn: ({ id, cuerpo }) =>
      crear(`/${recurso}/${encodeURIComponent(id)}/${accion}`, esquema, cuerpo ?? {}, clave.current),
    onSuccess: async (dato) => {
      clave.current = nuevoId();
      await Promise.all(
        [recurso, ...(opciones.invalidar ?? [])].map((r) => queryClient.invalidateQueries({ queryKey: [r] })),
      );
      opciones.alExito?.(dato);
    },
  });
}
