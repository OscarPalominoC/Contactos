import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useSesion } from "./sesion";

function Cargando() {
  return (
    <div role="status" className="flex min-h-screen items-center justify-center gap-2">
      <Loader2 aria-hidden="true" className="giro" /> Verificando sesión…
    </div>
  );
}

/**
 * Rutas protegidas. Es experiencia de usuario: la autorización real la hace el backend en cada petición.
 */
export function RutaProtegida({ children, permiso }: { children: ReactNode; permiso?: string }) {
  const { estado, usuario, puede } = useSesion();
  const ubicacion = useLocation();
  if (estado === "cargando") return <Cargando />;
  if (estado === "anonimo" || !usuario) return <Navigate to="/login" replace state={{ desde: ubicacion.pathname }} />;
  if (usuario.debe_cambiar_clave) return <Navigate to="/cambiar-clave" replace />;
  if (permiso && !puede(permiso)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function RutaCambioClave({ children }: { children: ReactNode }) {
  const { estado, usuario } = useSesion();
  if (estado === "cargando") return <Cargando />;
  if (!usuario) return <Navigate to="/login" replace />;
  if (!usuario.debe_cambiar_clave) return <Navigate to="/" replace />;
  return <>{children}</>;
}
