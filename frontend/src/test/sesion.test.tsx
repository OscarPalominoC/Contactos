import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RutaCambioClave, RutaProtegida } from "../app/RutaProtegida";
import { useSesion } from "../app/sesion";
import { PaginaCambioClave } from "../features/auth/PaginaCambioClave";
import { PaginaLogin } from "../features/auth/PaginaLogin";
import { PaginaMiCuenta } from "../features/auth/PaginaMiCuenta";
import { ApiError } from "../services/apiClient";
import { tokenStore } from "../services/tokenStore";
import { renderizarConSesion, YO_ADMIN } from "./utilidades";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));

vi.mock("../services/apiClient", async (original) => {
  const real = await original<typeof import("../services/apiClient")>();
  return {
    ...real,
    apiClient: api,
    asegurarCsrf: vi.fn(async () => undefined),
    refrescarSesion: vi.fn(async () => {
      const { data } = await api.post("/auth/refresh");
      tokenStore.set(data.access);
      return data.access as string;
    }),
  };
});

function error401() {
  return new ApiError({ type: "/problemas/credenciales-invalidas", title: "No autenticado", status: 401, detail: "Credenciales inválidas.", request_id: "rid-1" });
}

function Rutas() {
  return (
    <Routes>
      <Route path="/login" element={<PaginaLogin />} />
      <Route
        path="/cambiar-clave"
        element={
          <RutaCambioClave>
            <PaginaCambioClave />
          </RutaCambioClave>
        }
      />
      <Route
        path="/"
        element={
          <RutaProtegida>
            <p>Inicio protegido</p>
          </RutaProtegida>
        }
      />
      <Route
        path="/usuarios"
        element={
          <RutaProtegida permiso="permiso.inexistente">
            <p>Usuarios</p>
          </RutaProtegida>
        }
      />
      <Route
        path="/mi-cuenta"
        element={
          <RutaProtegida>
            <PaginaMiCuenta />
          </RutaProtegida>
        }
      />
    </Routes>
  );
}

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  tokenStore.clear();
});

describe("sesión y rutas protegidas", () => {
  it("sin sesión redirige al login", async () => {
    api.post.mockRejectedValueOnce(error401());
    renderizarConSesion(<Rutas />, { ruta: "/" });
    expect(await screen.findByRole("heading", { name: "Check Contactos" })).toBeInTheDocument();
    expect(screen.queryByText("Inicio protegido")).not.toBeInTheDocument();
  });

  it("recupera la sesión con la cookie de refresco al abrir", async () => {
    api.post.mockResolvedValueOnce({ data: { access: "t1", expira_en: 300 } });
    api.get.mockResolvedValueOnce({ data: YO_ADMIN });
    renderizarConSesion(<Rutas />, { ruta: "/" });
    expect(await screen.findByText("Inicio protegido")).toBeInTheDocument();
  });

  it("sin el permiso requerido vuelve al inicio", async () => {
    api.post.mockResolvedValueOnce({ data: { access: "t1", expira_en: 300 } });
    api.get.mockResolvedValueOnce({ data: YO_ADMIN });
    renderizarConSesion(<Rutas />, { ruta: "/usuarios" });
    expect(await screen.findByText("Inicio protegido")).toBeInTheDocument();
  });

  it("valida el formulario de login antes de enviar", async () => {
    api.post.mockRejectedValueOnce(error401());
    renderizarConSesion(<Rutas />, { ruta: "/login" });
    await userEvent.click(await screen.findByRole("button", { name: "Ingresar" }));
    expect(screen.getByText("Escriba su usuario (documento).")).toBeInTheDocument();
    expect(screen.getByText("Escriba su contraseña.")).toBeInTheDocument();
    expect(api.post).toHaveBeenCalledTimes(1);
  });

  it("muestra el error genérico y limpia la contraseña si las credenciales fallan", async () => {
    api.post.mockRejectedValueOnce(error401()).mockRejectedValueOnce(error401());
    renderizarConSesion(<Rutas />, { ruta: "/login" });
    await userEvent.type(await screen.findByLabelText(/Usuario/), "900001");
    await userEvent.type(screen.getByLabelText(/Contraseña/), "mala");
    await userEvent.click(screen.getByRole("button", { name: "Ingresar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Credenciales inválidas.");
    expect(screen.getByLabelText(/Contraseña/)).toHaveValue("");
  });

  it("con clave temporal obliga a cambiarla y luego entra", async () => {
    const temporal = { ...YO_ADMIN, debe_cambiar_clave: true };
    api.post
      .mockRejectedValueOnce(error401())
      .mockResolvedValueOnce({ data: { access: "t1", expira_en: 300 } })
      .mockResolvedValueOnce({ data: { access: "t2", expira_en: 300 } });
    api.get.mockResolvedValueOnce({ data: temporal }).mockResolvedValueOnce({ data: YO_ADMIN });
    renderizarConSesion(<Rutas />, { ruta: "/login" });

    await userEvent.type(await screen.findByLabelText(/Usuario/), "900001");
    await userEvent.type(screen.getByLabelText(/Contraseña/), "Temporal-0001");
    await userEvent.click(screen.getByRole("button", { name: "Ingresar" }));
    expect(await screen.findByRole("heading", { name: "Cambie su clave" })).toBeInTheDocument();
    expect(tokenStore.get()).toBe("t1");

    const boton = screen.getByRole("button", { name: "Cambiar clave" });
    expect(boton).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/Clave temporal/), "Temporal-0001");
    await userEvent.type(screen.getByLabelText(/^Nueva clave/), "Moto-Roja-2026!");
    await userEvent.type(screen.getByLabelText(/Confirmar nueva clave/), "Moto-Roja-2026!");
    expect(boton).toBeEnabled();
    await userEvent.click(boton);
    expect(await screen.findByText("Inicio protegido")).toBeInTheDocument();
    expect(api.post).toHaveBeenLastCalledWith("/auth/cambio-clave", { clave_actual: "Temporal-0001", clave_nueva: "Moto-Roja-2026!" });
    expect(tokenStore.get()).toBe("t2");
  });

  it("muestra el error del servidor en el campo de la nueva clave", async () => {
    api.post
      .mockResolvedValueOnce({ data: { access: "t1", expira_en: 300 } })
      .mockRejectedValueOnce(
        new ApiError({
          type: "/problemas/datos-invalidos",
          title: "Datos inválidos",
          status: 422,
          detail: "Revise los campos marcados.",
          errors: { clave_nueva: ["Esta contraseña es demasiado común."] },
        }),
      );
    api.get.mockResolvedValueOnce({ data: YO_ADMIN });
    renderizarConSesion(<Rutas />, { ruta: "/mi-cuenta" });
    await userEvent.type(await screen.findByLabelText(/Clave actual/), "Actual-Clave-1");
    await userEvent.type(screen.getByLabelText(/^Nueva clave/), "Moto-Roja-2026!");
    await userEvent.type(screen.getByLabelText(/Confirmar nueva clave/), "Moto-Roja-2026!");
    await userEvent.click(screen.getByRole("button", { name: "Cambiar clave" }));
    expect(await screen.findByText("Esta contraseña es demasiado común.")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Nueva clave/)).toHaveAttribute("aria-invalid", "true");
  });

  it("la página de cambio de clave sin clave temporal manda al inicio", async () => {
    api.post.mockResolvedValueOnce({ data: { access: "t1", expira_en: 300 } });
    api.get.mockResolvedValueOnce({ data: YO_ADMIN });
    renderizarConSesion(<Rutas />, { ruta: "/cambiar-clave" });
    expect(await screen.findByText("Inicio protegido")).toBeInTheDocument();
  });

  it("cerrar sesión limpia el token", async () => {
    api.post.mockResolvedValueOnce({ data: { access: "t1", expira_en: 300 } }).mockResolvedValueOnce({ data: {} });
    api.get.mockResolvedValueOnce({ data: YO_ADMIN });
    function Salir() {
      const { cerrar, estado } = useSesion();
      return (
        <>
          <p>estado:{estado}</p>
          <button onClick={() => void cerrar()}>Salir</button>
        </>
      );
    }
    renderizarConSesion(<Salir />);
    await screen.findByText("estado:autenticado");
    await userEvent.click(screen.getByRole("button", { name: "Salir" }));
    await waitFor(() => expect(screen.getByText("estado:anonimo")).toBeInTheDocument());
    expect(tokenStore.get()).toBeNull();
    expect(api.post).toHaveBeenLastCalledWith("/auth/logout");
  });
});
