import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { alExpirarSesion, apiClient, asegurarCsrf, esSesionExpirada, refrescarSesion } from "../services/apiClient";
import { accesoSchema, yoSchema, type Yo } from "../services/esquemas";
import { tokenStore } from "../services/tokenStore";

const REINTENTO_ARRANQUE_MS = 15 * 1000;
const RENOVACION_MIN_MS = 60 * 1000;

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
  const ultimaRenovacion = useRef(0);

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
    let enCurso = false;
    let resuelto = false;

    const reintento = setInterval(() => void intentar(), REINTENTO_ARRANQUE_MS);
    const detener = () => {
      clearInterval(reintento);
      window.removeEventListener("focus", intentar);
      window.removeEventListener("online", intentar);
      document.removeEventListener("visibilitychange", alVolverVisible);
    };

    // Al abrir la aplicación se intenta recuperar la sesión con la cookie HttpOnly de refresco.
    // Solo un 401/403 significa sesión vencida; con red caída o 5xx se sigue en "cargando" y se reintenta.
    async function intentar(): Promise<void> {
      if (!activo || resuelto || enCurso) return;
      enCurso = true;
      try {
        await refrescarSesion(apiClient);
        ultimaRenovacion.current = Date.now();
        const yo = await cargarYo();
        if (!activo) return;
        resuelto = true;
        detener();
        setUsuario(yo);
        setEstado("autenticado");
      } catch (error) {
        if (activo && esSesionExpirada(error)) {
          resuelto = true;
          detener();
          limpiar();
        }
      } finally {
        enCurso = false;
      }
    }
    function alVolverVisible(): void {
      if (document.visibilityState === "visible") void intentar();
    }

    void intentar();
    window.addEventListener("focus", intentar);
    window.addEventListener("online", intentar);
    document.addEventListener("visibilitychange", alVolverVisible);
    return () => {
      activo = false;
      detener();
    };
  }, [limpiar]);

  // Mantenimiento proactivo de la sesión: renueva el token silenciosamente cada 4 min (antes de que venza
  // el access token de 5 min) y al reactivar la pestaña, evitando cierres de sesión inesperados.
  useEffect(() => {
    if (estado !== "autenticado") return;

    const renovarSilencioso = async () => {
      // focus y visibilitychange suelen dispararse juntos: se omite si hubo una renovación hace menos de 60 s.
      if (Date.now() - ultimaRenovacion.current < RENOVACION_MIN_MS) return;
      try {
        await refrescarSesion(apiClient);
        ultimaRenovacion.current = Date.now();
      } catch (error) {
        // Red caída o 5xx: se conserva la sesión y se reintenta luego; solo 401/403 la cierra.
        if (esSesionExpirada(error)) limpiar();
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
  }, [estado, limpiar]);

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
