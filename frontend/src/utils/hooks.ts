import { useEffect, useState } from "react";

/** Retrasa un valor (búsquedas) para no consultar en cada tecla. */
export function useRetardo<T>(valor: T, milisegundos = 350): T {
  const [retrasado, setRetrasado] = useState(valor);
  useEffect(() => {
    const temporizador = setTimeout(() => setRetrasado(valor), milisegundos);
    return () => clearTimeout(temporizador);
  }, [valor, milisegundos]);
  return retrasado;
}

/** Cambia el <title> del documento por vista (WCAG 2.4.2). */
export function useTitulo(titulo: string): void {
  useEffect(() => {
    document.title = `${titulo} · Check Contactos`;
  }, [titulo]);
}

/** Mínimo de caracteres para lanzar una búsqueda en los listados. */
export const MINIMO_BUSQUEDA = 3;
