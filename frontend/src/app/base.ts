/**
 * La app se publica bajo un subpath (vite `base`, p. ej. oscarpalomino.dev/contactos/).
 * Las rutas del router y los archivos de `public/` deben resolverse bajo ese subpath;
 * una ruta absoluta como "/login" o "/favicon.svg" saldría de la aplicación.
 */
const BASE_VITE: string = import.meta.env?.BASE_URL ?? "/";

export function basenameRouter(base: string | undefined = BASE_VITE): string {
  const limpio = (base ?? "/").replace(/\/+$/, "");
  return limpio || "/";
}

export function rutaPublica(archivo: string, base: string = BASE_VITE): string {
  const prefijo = base.endsWith("/") ? base : `${base}/`;
  return `${prefijo}${archivo.replace(/^\/+/, "")}`;
}
