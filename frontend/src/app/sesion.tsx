import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { alExpirarSesion, apiClient, asegurarCsrf, refrescarSesion } from "../services/apiClient";
import { accesoSchema, yoSchema, type Yo } from "../services/esquemas";
import { tokenStore } from "../services/tokenStore";

export type EstadoSesion = "cargando" | "anonimo" | "autenticado";

interface ValorSesion {
  estado: EstadoSesion;
  usuario: Yo | null;
  iniciar: (nip: string, password: string) => Promise<Yo>;
  cerrar: () => Promise<void>;
  cambiarClave: (actual: string, nueva: string) => Promise<Yo>;
  recargar: () => Promise<Yo | null>;
  puede: (permiso: string) => boolean;
}

const ContextoSesion = createContext<ValorSesion | null>(null);

async function cargarYo(): Promise<Yo> {
  const { data } = await apiClient.get("/auth/yo");
  return yoSchema.parse(data);
}

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [estado, setEstado] = useState<EstadoSesion>("cargando");
  const [usuario, setUsuario] = useState<Yo | null>(null);
  const queryClient = useQueryClient();

  const limpiar = useCallback(() => {
    tokenStore.clear();
    setUsuario(null);
    setEstado("anonimo");
    queryClient.clear();
  }, [queryClient]);

  const recargar = useCallback(async (): Promise<Yo | null> => {
    try {
      const yo = await cargarYo();
      setUsuario(yo);
      setEstado("autenticado");
      return yo;
    } catch {
      limpiar();
      return null;
    }
  }, [limpiar]);

  useEffect(() => {
    alExpirarSesion(limpiar);
    let activo = true;
    // Al abrir la aplicación se intenta recuperar la sesión con la cookie HttpOnly de refresco.
    refrescarSesion(apiClient)
      .then(() => (activo ? recargar() : null))
      .catch(() => activo && limpiar());
    return () => {
      activo = false;
    };
  }, [limpiar, recargar]);

  // Mantenimiento proactivo de la sesión: renueva el token silenciosamente cada 4 min (antes de que venza
  // el access token de 5 min) y al reactivar la pestaña, evitando cierres de sesión inesperados.
  useEffect(() => {
    if (estado !== "autenticado") return;

    const renovarSilencioso = async () => {
      try {
        await refrescarSesion(apiClient);
      } catch {
        // En caso de fallo definitivo el cliente HTTP limpiará la sesión
      }
    };

    const intervalo = setInterval(renovarSilencioso, 4 * 60 * 1000);
    const alCambiarVisibilidad = () => {
      if (document.visibilityState === "visible") {
        void renovarSilencioso();
      }
    };

    document.addEventListener("visibilitychange", alCambiarVisibilidad);
    window.addEventListener("focus", renovarSilencioso);

    return () => {
      clearInterval(intervalo);
      document.removeEventListener("visibilitychange", alCambiarVisibilidad);
      window.removeEventListener("focus", renovarSilencioso);
    };
  }, [estado]);

  const iniciar = useCallback(async (nip: string, password: string): Promise<Yo> => {
    await asegurarCsrf(apiClient);
    const { data } = await apiClient.post("/auth/login", { nip, password });
    tokenStore.set(accesoSchema.parse(data).access);
    const yo = await cargarYo();
    setUsuario(yo);
    setEstado("autenticado");
    return yo;
  }, []);

  const cerrar = useCallback(async (): Promise<void> => {
    try {
      await asegurarCsrf(apiClient);
      await apiClient.post("/auth/logout");
    } finally {
      limpiar();
    }
  }, [limpiar]);

  const cambiarClave = useCallback(async (actual: string, nueva: string): Promise<Yo> => {
    const { data } = await apiClient.post("/auth/cambio-clave", { clave_actual: actual, clave_nueva: nueva });
    tokenStore.set(accesoSchema.parse(data).access);
    const yo = await cargarYo();
    setUsuario(yo);
    return yo;
  }, []);

  const puede = useCallback((permiso: string) => usuario?.permisos.includes(permiso) ?? false, [usuario]);

  const valor = useMemo(
    () => ({ estado, usuario, iniciar, cerrar, cambiarClave, recargar, puede }),
    [estado, usuario, iniciar, cerrar, cambiarClave, recargar, puede],
  );
  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>;
}

export function useSesion(): ValorSesion {
  const valor = useContext(ContextoSesion);
  if (!valor) throw new Error("useSesion debe usarse dentro de ProveedorSesion");
  return valor;
}
