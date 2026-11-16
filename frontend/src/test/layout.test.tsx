import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { crearQueryClient, rutas } from "../app/App";
import { aplicarTema, useUi } from "../app/uiStore";
import { AppLayout, AuthLayout } from "../layouts/Layouts";
import { ApiError } from "../services/apiClient";
import { renderizar, YO_ADMIN } from "./utilidades";

const sesion = vi.hoisted(() => ({ cerrar: vi.fn(async () => undefined), permisos: [] as string[] }));
vi.mock("../app/sesion", () => ({
  useSesion: () => ({
    usuario: { ...YO_ADMIN, permisos: sesion.permisos },
    estado: "autenticado",
    cerrar: sesion.cerrar,
    puede: (p: string) => sesion.permisos.includes(p),
  }),
  ProveedorSesion: ({ children }: { children: React.ReactNode }) => children,
}));

function conLayout(ruta = "/") {
  return renderizar(
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<p>Contenido del tablero</p>} />
        <Route path="/contactos" element={<p>Contenido de contactos</p>} />
      </Route>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<p>Formulario</p>} />
      </Route>
    </Routes>,
    { ruta },
  );
}

describe("AppLayout", () => {
  beforeEach(() => {
    sesion.cerrar.mockClear();
    sesion.permisos = ["contactos.view_contacto"];
    useUi.setState({ tema: "claro", menuAbierto: false });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllEnvs();
  });

  it("muestra solo los enlaces permitidos, enlace de salto y nombre del usuario", () => {
    conLayout();
    const nav = screen.getByRole("navigation", { name: "Principal" });
    expect(nav).toHaveTextContent("Tablero");
    expect(nav).toHaveTextContent("Contactos");
    expect(nav).not.toHaveTextContent("Mi cuenta");
    expect(nav).not.toHaveTextContent("Usuarios");
    expect(nav).not.toHaveTextContent("SOAT");
    expect(screen.getByRole("link", { name: "Saltar al contenido principal" })).toHaveAttribute("href", "#contenido");
    expect(screen.getByRole("button", { name: /Administrador/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Tablero" })).toHaveAttribute("aria-current", "page");
  });

  it("alterna el tema y el menú, y cierra sesión", async () => {
    conLayout();
    await userEvent.click(screen.getByRole("button", { name: "Activar modo oscuro" }));
    expect(document.documentElement).toHaveClass("dark");
    expect(useUi.getState().tema).toBe("oscuro");
    await userEvent.click(screen.getByRole("button", { name: "Activar modo claro" }));
    expect(document.documentElement).not.toHaveClass("dark");

    const menu = screen.getByRole("button", { name: "Menú" });
    expect(menu).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(menu);
    expect(menu).toHaveAttribute("aria-expanded", "true");
    await userEvent.click(screen.getByRole("link", { name: "Contactos" }));
    expect(await screen.findByText("Contenido de contactos")).toBeInTheDocument();
    expect(useUi.getState().menuAbierto).toBe(false);

    await userEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));
    expect(sesion.cerrar).toHaveBeenCalledOnce();
  });

  it("sin VITE_INACTIVIDAD_MINUTOS no cierra sesión tras 31 min", () => {
    vi.useFakeTimers();
    conLayout();
    act(() => {
      vi.advanceTimersByTime(31 * 60 * 1000);
    });
    expect(sesion.cerrar).not.toHaveBeenCalled();
    expect(screen.queryByText(/por inactividad/)).not.toBeInTheDocument();
  });

  it("con VITE_INACTIVIDAD_MINUTOS=1 avisa y cierra", () => {
    vi.stubEnv("VITE_INACTIVIDAD_MINUTOS", "1");
    vi.useFakeTimers();
    conLayout();
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.getByText("Su sesión se cerrará en 1 minuto por inactividad.")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(60 * 1000);
    });
    expect(sesion.cerrar).toHaveBeenCalledOnce();
  });

  it("avisa antes de cerrar por inactividad y permite prorrogar", async () => {
    vi.stubEnv("VITE_INACTIVIDAD_MINUTOS", "30");
    vi.useFakeTimers();
    conLayout();
    act(() => {
      vi.advanceTimersByTime(29 * 60 * 1000 + 1);
    });
    expect(screen.getByText("Su sesión se cerrará en 1 minuto por inactividad.")).toBeInTheDocument();
    act(() => {
      screen.getByRole("button", { name: "Seguir conectado" }).click();
    });
    expect(screen.queryByText(/por inactividad/)).not.toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(30 * 60 * 1000 + 1);
    });
    expect(sesion.cerrar).toHaveBeenCalledOnce();
  });

  it("AuthLayout renderiza el contenido", () => {
    conLayout("/login");
    expect(screen.getByText("Formulario")).toBeInTheDocument();
  });
});

describe("uiStore y configuración", () => {
  it("guarda el tema en localStorage y aplica la clase", () => {
    useUi.setState({ tema: "claro" });
    useUi.getState().alternarTema();
    expect(localStorage.getItem("tema")).toBe("oscuro");
    aplicarTema("claro");
    expect(document.documentElement).not.toHaveClass("dark");
    useUi.getState().alternarMenu();
    expect(useUi.getState().menuAbierto).toBe(true);
    useUi.getState().cerrarMenu();
    expect(useUi.getState().menuAbierto).toBe(false);
  });

  it("el QueryClient reintenta solo errores de red o del servidor", () => {
    const cliente = crearQueryClient();
    const reintentar = cliente.getDefaultOptions().queries?.retry as (n: number, e: unknown) => boolean;
    const error = (status: number) => new ApiError({ type: "x", title: "t", status, detail: "d" });
    expect(reintentar(0, error(503))).toBe(true);
    expect(reintentar(0, error(0))).toBe(true);
    expect(reintentar(0, error(404))).toBe(false);
    expect(reintentar(2, error(503))).toBe(false);
  });

  it("las rutas cubren todas las pantallas del plan bajo un único proveedor de sesión", () => {
    expect(rutas).toHaveLength(1);
    const caminos: string[] = [];
    const recorrer = (lista: typeof rutas) =>
      lista.forEach((r) => {
        if (r.path) caminos.push(r.path);
        if (r.children) recorrer(r.children);
      });
    recorrer(rutas);
    for (const camino of [
      "/login",
      "/cambiar-clave",
      "/",
      "/contactos",
      "/contactos/:nip",
      "/motos",
      "/motos/:placa",
      "/revisiones",
      "/soat",
      "/llamadas",
      "/catalogos",
      "/usuarios",
      "/mi-cuenta",
    ]) {
      expect(caminos).toContain(camino);
    }
    expect(caminos.some((c) => /export|descarg|imprim|csv|xlsx|pdf/i.test(c))).toBe(false);
  });
});

describe("App", () => {
  it("monta el router con el proveedor de consultas", async () => {
    window.history.pushState({}, "", "/login");
    const { App } = await import("../app/App");
    const { render } = await import("@testing-library/react");
    render(<App />);
    await waitFor(() => expect(document.querySelector("#contenido")).not.toBeNull());
  });
});
