import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useUi } from "../app/uiStore";
import { AppLayout } from "../layouts/Layouts";
import { primerNombre } from "../utils/formatters";
import { renderizar, YO_ADMIN } from "./utilidades";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock("../services/apiClient", async (original) => ({
  ...(await original<typeof import("../services/apiClient")>()),
  apiClient: api,
}));
const sesion = vi.hoisted(() => ({
  cerrar: vi.fn(async () => undefined),
  recargar: vi.fn(async () => null),
  cambiarClave: vi.fn(async () => null),
  nombre: "OSCAR EDUARDO PALOMINO CARDENAS",
}));
vi.mock("../app/sesion", () => ({
  useSesion: () => ({
    usuario: { ...YO_ADMIN, nombre: sesion.nombre, permisos: ["contactos.view_contacto"] },
    estado: "autenticado",
    cerrar: sesion.cerrar,
    recargar: sesion.recargar,
    cambiarClave: sesion.cambiarClave,
    puede: (p: string) => p === "contactos.view_contacto",
  }),
}));

function conLayout() {
  return renderizar(
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<p>Contenido</p>} />
        <Route path="/contactos" element={<p>Contactos</p>} />
      </Route>
    </Routes>,
  );
}

beforeEach(() => {
  for (const f of [...Object.values(api), sesion.cerrar, sesion.recargar, sesion.cambiarClave]) f.mockReset();
  useUi.setState({ tema: "claro", menuAbierto: false });
});

describe("primerNombre", () => {
  it("toma la primera palabra con mayúscula inicial", () => {
    expect(primerNombre("OSCAR EDUARDO PALOMINO CARDENAS")).toBe("Oscar");
    expect(primerNombre("  ángela  maría ")).toBe("Ángela");
    expect(primerNombre("")).toBe("");
    expect(primerNombre(undefined)).toBe("");
  });
});

describe("Navbar", () => {
  it("el logo solo dice CHECK MOTOS", () => {
    conLayout();
    const banner = screen.getByRole("banner");
    expect(banner).toHaveTextContent("CHECK MOTOS");
    expect(banner).not.toHaveTextContent("Barrancabermeja");
    expect(banner).not.toHaveTextContent("CDA");
  });

  it("tema y cierre de sesión son solo iconos con nombre accesible", async () => {
    conLayout();
    const tema = screen.getByRole("button", { name: "Activar modo oscuro" });
    const salir = screen.getByRole("button", { name: "Cerrar sesión" });
    expect(tema.textContent).toBe("");
    expect(salir.textContent).toBe("");
    expect(tema).toHaveAttribute("title", "Activar modo oscuro");
    await userEvent.click(salir);
    expect(sesion.cerrar).toHaveBeenCalledOnce();
  });

  it("muestra solo el primer nombre y despliega opciones de cuenta", async () => {
    conLayout();
    const boton = screen.getByRole("button", { name: /Oscar/ });
    expect(boton).toHaveTextContent(/^Oscar$/);
    expect(boton).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "true");
    const panel = document.getElementById(boton.getAttribute("aria-controls") ?? "") as HTMLElement;
    expect(within(panel).getByText("OSCAR EDUARDO PALOMINO CARDENAS")).toBeInTheDocument();
    expect(within(panel).getByRole("button", { name: "Cambiar nombre" })).toHaveFocus();
    expect(within(panel).getByRole("button", { name: "Actualizar contraseña" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(boton).toHaveFocus();
    await userEvent.click(boton);
    await userEvent.click(screen.getByText("Contenido"));
    expect(boton).toHaveAttribute("aria-expanded", "false");
  });

  it("cambia el nombre con PATCH /auth/yo y recarga la sesión", async () => {
    api.patch.mockResolvedValue({ data: { ...YO_ADMIN, nombre: "OSCAR PALOMINO" } });
    conLayout();
    await userEvent.click(screen.getByRole("button", { name: /Oscar/ }));
    await userEvent.click(screen.getByRole("button", { name: "Cambiar nombre" }));
    const dialogo = screen.getByRole("dialog", { name: "Cambiar nombre" });
    const campo = within(dialogo).getByLabelText(/Nombre completo/);
    expect(campo).toHaveValue("OSCAR EDUARDO PALOMINO CARDENAS");
    await userEvent.clear(campo);
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    expect(within(dialogo).getByText(/mínimo 3 letras/)).toBeInTheDocument();
    expect(api.patch).not.toHaveBeenCalled();
    await userEvent.type(campo, "Oscar Palomino");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/auth/yo", { nombre: "Oscar Palomino" }, expect.anything()));
    await waitFor(() => expect(sesion.recargar).toHaveBeenCalled());
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Cambiar nombre" })).toBeNull());
  });

  it("abre el formulario de cambio de contraseña con la regla de 5 caracteres", async () => {
    conLayout();
    await userEvent.click(screen.getByRole("button", { name: /Oscar/ }));
    await userEvent.click(screen.getByRole("button", { name: "Actualizar contraseña" }));
    const dialogo = screen.getByRole("dialog", { name: "Actualizar contraseña" });
    expect(within(dialogo).getByRole("list", { name: "Requisitos de la nueva clave" })).toHaveTextContent("Al menos 5 caracteres");
    await userEvent.type(within(dialogo).getByLabelText(/Clave actual/), "vieja");
    await userEvent.type(within(dialogo).getByLabelText(/^Nueva clave/), "oscar");
    await userEvent.type(within(dialogo).getByLabelText(/Confirmar nueva clave/), "oscar");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Cambiar clave" }));
    await waitFor(() => expect(sesion.cambiarClave).toHaveBeenCalledWith("vieja", "oscar"));
  });

  it("la navegación usa aria-current y no repite Mi cuenta", () => {
    conLayout();
    const nav = screen.getByRole("navigation", { name: "Principal" });
    expect(within(nav).getByRole("link", { name: "Tablero" })).toHaveAttribute("aria-current", "page");
    expect(nav).not.toHaveTextContent("Mi cuenta");
  });

  it("al cargar no roba el foco (el primer Tab llega al enlace de salto); al navegar lo lleva al contenido", async () => {
    conLayout();
    expect(document.getElementById("contenido")).not.toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("link", { name: "Saltar al contenido principal" })).toHaveFocus();
    await userEvent.click(screen.getByRole("link", { name: "Contactos" }));
    await waitFor(() => expect(document.getElementById("contenido")).toHaveFocus());
  });

  it("en pantallas angostas la marca queda como texto para lectores y el logo no se repite", () => {
    conLayout();
    const marca = screen.getByText("CHECK MOTOS");
    expect(marca.className).toContain("marca-texto");
  });
});
