/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Minutos de inactividad antes de cerrar la sesión; 0 o ausente la desactiva. */
  readonly VITE_INACTIVIDAD_MINUTOS?: string;
}
