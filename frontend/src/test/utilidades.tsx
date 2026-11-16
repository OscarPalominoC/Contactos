import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

import { ProveedorSesion } from "../app/sesion";

export function clientePruebas(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } });
}

/** Renderiza con QueryClient y router de memoria (sin proveedor de sesión). */
export function renderizar(ui: ReactElement, opciones: RenderOptions & { ruta?: string } = {}) {
  const { ruta = "/", ...resto } = opciones;
  const cliente = clientePruebas();
  const Envoltorio = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={cliente}>
      <MemoryRouter initialEntries={[ruta]}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  return { ...render(ui, { wrapper: Envoltorio, ...resto }), cliente };
}

/** Renderiza con proveedor de sesión (para pruebas de rutas protegidas y login). */
export function renderizarConSesion(ui: ReactElement, opciones: { ruta?: string } = {}) {
  const cliente = clientePruebas();
  const Envoltorio = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={cliente}>
      <MemoryRouter initialEntries={[opciones.ruta ?? "/"]}>
        <ProveedorSesion>{children}</ProveedorSesion>
      </MemoryRouter>
    </QueryClientProvider>
  );
  return { ...render(ui, { wrapper: Envoltorio }), cliente };
}

export const YO_ADMIN = {
  nip: "900001",
  nombre: "ADMINISTRADOR DE PRUEBA",
  rol: "administrador" as const,
  debe_cambiar_clave: false,
  permisos: [
    "contactos.view_contacto",
    "contactos.add_contacto",
    "contactos.change_contacto",
    "vehiculos.view_moto",
    "vehiculos.add_moto",
    "vehiculos.change_moto",
    "vehiculos.view_marca",
    "vehiculos.add_marca",
    "vehiculos.delete_marca",
    "vehiculos.view_linea",
    "vehiculos.add_linea",
    "vehiculos.delete_linea",
    "revisiones.view_revision",
    "revisiones.add_revision",
    "revisiones.change_revision",
    "revisiones.view_soat",
    "revisiones.add_soat",
    "revisiones.change_soat",
    "llamadas.view_llamadartm",
    "llamadas.add_llamadartm",
    "llamadas.change_llamadartm",
    "llamadas.view_llamadacumpleanos",
    "llamadas.add_llamadacumpleanos",
    "llamadas.change_llamadacumpleanos",
    "llamadas.view_llamadasoat",
    "llamadas.add_llamadasoat",
    "llamadas.change_llamadasoat",
    "cuentas.view_usuario",
  ],
};

export const CONTACTO = {
  nip: "1000000001",
  nombre: "CLIENTE DE PRUEBA",
  telefono: "",
  celular: "3000000000",
  dia_nac: 15,
  mes_nac: 5,
  mes_nac_nombre: "Mayo",
  direccion: "CRA 1 N 2-3",
  correo: "cliente@ejemplo.test",
  estado: "habilitado" as const,
  usuario: "OPERADOR",
  fecha_registro: "2026-11-06T13:56:15-05:00",
  cumple_confir: false,
  contactar_cumpleanos: true,
  contactar_soat: true,
  contactar_rtm: true,
  creado_en: null,
  actualizado_en: null,
  creado_por: "",
  actualizado_por: "",
};

export function paginado<T>(datos: T[], total = datos.length) {
  return {
    data: datos,
    meta: { page: { number: 1, size: 25, total, total_pages: Math.max(1, Math.ceil(total / 25)) } },
    links: { self: null, next: null, prev: null, first: null, last: null },
  };
}
