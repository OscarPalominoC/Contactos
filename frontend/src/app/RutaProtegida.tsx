import { Loader2, RefreshCw, WifiOff } from "lucide-react";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { Boton } from "../components/ui/Boton";
import { useSesion } from "./sesion";

function Cargando() {
  const { sinConexion, reintentarConexion } = useSesion();
  if (sinConexion) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 p-4 text-center">
        <div role="alert" className="flex flex-col items-center gap-2">
          <WifiOff aria-hidden="true" />
          <p className="font-semibold">No se pudo conectar con el servidor.</p>
          <p className="text-sm opacity-80">Se seguirá intentando automáticamente cada pocos segundos.</p>
        </div>
        <Boton icono={<RefreshCw aria-hidden="true" size={18} />} onClick={reintentarConexion}>
          Reintentar
        </Boton>
      </div>
    );
  }
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
