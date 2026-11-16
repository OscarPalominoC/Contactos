import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PaginaLlamadas } from "../features/llamadas/PaginaLlamadas";
import { hoyBogota } from "../utils/formatters";
import { CONTACTO, paginado, renderizar, YO_ADMIN } from "./utilidades";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock("../services/apiClient", async (original) => ({
  ...(await original<typeof import("../services/apiClient")>()),
  apiClient: api,
}));
vi.mock("../app/sesion", () => ({
  useSesion: () => ({ usuario: YO_ADMIN, estado: "autenticado", puede: (p: string) => YO_ADMIN.permisos.includes(p) }),
}));

const AUD = { creado_en: null, actualizado_en: null, creado_por: "", actualizado_por: "" };
const BASE = { estado: "no_realizada", estado_nombre: "No realizada", observacion: "", usuario: "", num_llamadas: 1, intentos: "", ...AUD };
const PLACA = { id: "ABC12D.2026-11-08", fecha: "2026-11-08", placa: "ABC12D", motivo_llamada: "rtmyg", ...BASE };
const CUMPLE = { id: 7, fecha: "2026-11-07T10:00:00-05:00", nip: CONTACTO.nip, motivo_llamada: "cumpleanos", ...BASE };
const POR_LLAMAR = {
  placa: "ABC12D",
  fecha: "2026-11-20",
  propietario_nip: CONTACTO.nip,
  propietario_nombre: "CLIENTE DE PRUEBA",
  celular: "3000000000",
  llamada_id: null,
  estado: "sin_llamar",
  num_llamadas: 0,
  observacion: "",
};
const RECURSO = { cumpleanos: "/llamadas-cumpleanos", rtm: "/llamadas-rtm", soat: "/llamadas-soat" } as const;

beforeEach(() => {
  for (const f of Object.values(api)) f.mockReset();
  api.get.mockImplementation(async (ruta: string) => {
    if (ruta.endsWith("/por-llamar")) return { data: paginado([POR_LLAMAR]) };
    if (ruta.startsWith("/llamadas-cumpleanos")) return { data: paginado([CUMPLE]) };
    if (ruta.startsWith("/contactos")) return { data: paginado([CONTACTO]) };
    return { data: paginado([PLACA]) };
  });
});

/** Parámetros de la última petición GET a `ruta`. */
function ultimosParametros(ruta: string): Record<string, unknown> {
  const llamadas = api.get.mock.calls.filter(([r]) => r === ruta);
  return (llamadas.at(-1)?.[1] as { params: Record<string, unknown> }).params;
}

async function elegirHoy(etiqueta: RegExp) {
  await userEvent.click(screen.getByRole("button", { name: etiqueta }));
  await userEvent.keyboard("{Enter}");
}

async function abrirHistorial() {
  await userEvent.click(await screen.findByRole("button", { name: "Historial de llamadas" }));
}

describe("Llamadas: historial con rango de fechas", () => {
  it.each(["cumpleanos", "rtm", "soat"] as const)("en %s el historial filtra por rango y estado", async (pestana) => {
    renderizar(<PaginaLlamadas />, { ruta: `/llamadas?pestana=${pestana}` });
    const ruta = RECURSO[pestana];
    await abrirHistorial();
    await waitFor(() => expect(api.get.mock.calls.some(([r]) => r === ruta)).toBe(true));
    expect(ultimosParametros(ruta)["filter[pendiente]"]).toBeUndefined();
    const hoy = hoyBogota();
    expect(screen.getByRole("group", { name: "Rango de fechas" })).toBeInTheDocument();
    await elegirHoy(/^Desde/);
    await waitFor(() => expect(ultimosParametros(ruta)).toMatchObject({ "filter[desde]": hoy }));
    await elegirHoy(/^Hasta/);
    await waitFor(() => expect(ultimosParametros(ruta)).toMatchObject({ "filter[desde]": hoy, "filter[hasta]": hoy }));
    await userEvent.selectOptions(screen.getByLabelText("Estado"), "ocupada");
    await waitFor(() => expect(ultimosParametros(ruta)["filter[estado]"]).toBe("ocupada"));
    await userEvent.click(screen.getByRole("button", { name: "Limpiar fechas" }));
    await waitFor(() => expect(ultimosParametros(ruta)["filter[desde]"]).toBeUndefined());
    expect(ultimosParametros(ruta)["filter[hasta]"]).toBeUndefined();
  });

  it("el rango de una pestaña no se mezcla con otra", async () => {
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=rtm" });
    await abrirHistorial();
    await elegirHoy(/^Desde/);
    await waitFor(() => expect(ultimosParametros("/llamadas-rtm")["filter[desde]"]).toBe(hoyBogota()));
    await userEvent.click(screen.getByRole("tab", { name: "SOAT" }));
    await waitFor(() => expect(api.get.mock.calls.some(([r]) => r === "/llamadas-soat")).toBe(true));
    expect(ultimosParametros("/llamadas-soat")["filter[desde]"]).toBeUndefined();
  });

  it("solo consulta la lista de la pestaña y vista activas", async () => {
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=rtm" });
    await screen.findByRole("link", { name: "ABC12D" });
    const rutas = api.get.mock.calls.map(([r]) => r as string);
    expect(rutas).toContain("/llamadas-rtm/por-llamar");
    expect(rutas).not.toContain("/llamadas-cumpleanos");
    expect(rutas).not.toContain("/llamadas-soat");
    expect(rutas).not.toContain("/llamadas-rtm");
  });

  it("muestra '—' en la fecha objetivo cuando el servidor la marca como insalvable", async () => {
    api.get.mockImplementation(async (ruta: string) =>
      ruta === "/llamadas-rtm" ? { data: paginado([{ ...PLACA, fecha: null }]) } : { data: paginado([]) },
    );
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=rtm" });
    await abrirHistorial();
    const fila = (await screen.findByRole("link", { name: "ABC12D" })).closest("tr") as HTMLElement;
    expect(within(fila).getAllByRole("cell")[0]).toHaveTextContent("—");
  });

  it("en pendientes conserva el total del servidor para paginar", async () => {
    api.get.mockImplementation(async (ruta: string) =>
      ruta === "/llamadas-rtm/por-llamar" ? { data: paginado([POR_LLAMAR], 60) } : { data: paginado([]) },
    );
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=rtm" });
    expect(await screen.findByText(/60 registros · página 1 de 3/)).toBeInTheDocument();
  });
});

describe("Llamadas: registro", () => {
  it("la fecha objetivo de una llamada por placa se elige con el calendario", async () => {
    api.post.mockResolvedValue({ data: PLACA });
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=soat" });
    await userEvent.click(await screen.findByRole("button", { name: "Registrar llamada" }));
    const dialogo = screen.getByRole("dialog", { name: "Registrar llamada de SOAT" });
    await userEvent.type(within(dialogo).getByLabelText(/^Placa/), "abc12d");
    expect(within(dialogo).getByRole("button", { name: /Fecha objetivo/ })).toBeInTheDocument();
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith("/llamadas-soat", expect.objectContaining({ placa: "ABC12D", fecha: hoyBogota() }), expect.anything()),
    );
  });

  it("muestra el error del servidor en la placa al registrar", async () => {
    const { ApiError } = await import("../services/apiClient");
    api.post.mockRejectedValueOnce(
      new ApiError({ type: "x", title: "Datos inválidos", status: 422, detail: "Revise.", errors: { placa: ["No existe una moto con esa placa."] } }),
    );
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=rtm" });
    await userEvent.click(await screen.findByRole("button", { name: "Registrar llamada" }));
    const dialogo = screen.getByRole("dialog", { name: "Registrar llamada de RTM" });
    await userEvent.type(within(dialogo).getByLabelText(/^Placa/), "zzz99z");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    expect(await within(dialogo).findByText("No existe una moto con esa placa.")).toBeInTheDocument();
  });

  it("el error de la placa no queda pegado al volver a abrir el diálogo", async () => {
    const { ApiError } = await import("../services/apiClient");
    api.post.mockRejectedValueOnce(
      new ApiError({ type: "x", title: "Datos inválidos", status: 422, detail: "Revise.", errors: { placa: ["No existe una moto con esa placa."] } }),
    );
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=rtm" });
    await userEvent.click(await screen.findByRole("button", { name: "Registrar llamada" }));
    let dialogo = screen.getByRole("dialog", { name: "Registrar llamada de RTM" });
    await userEvent.type(within(dialogo).getByLabelText(/^Placa/), "zzz99z");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await within(dialogo).findByText("No existe una moto con esa placa.");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Cancelar" }));
    await userEvent.click(screen.getByRole("button", { name: "Registrar llamada" }));
    dialogo = screen.getByRole("dialog", { name: "Registrar llamada de RTM" });
    expect(within(dialogo).queryByText("No existe una moto con esa placa.")).toBeNull();
  });
});

describe("Llamadas: cumpleaños por periodo y nombre con enlace a la ficha", () => {
  it("la lista de cumpleaños solo trae contactos que autorizan el canal", async () => {
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=cumpleanos" });
    await screen.findByRole("region", { name: "Cumpleaños del periodo" });
    await waitFor(() =>
      expect(ultimosParametros("/contactos")).toMatchObject({ "filter[contactar_cumpleanos]": "true", "filter[estado]": "habilitado" }),
    );
  });

  it("la lista de cumpleaños usa fecha inicial y final (hoy por defecto) y no muestra la cédula", async () => {
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=cumpleanos" });
    const tarjeta = await screen.findByRole("region", { name: "Cumpleaños del periodo" });
    const hoy = hoyBogota();
    await waitFor(() => expect(ultimosParametros("/contactos")).toMatchObject({ "filter[cumple_desde]": hoy, "filter[cumple_hasta]": hoy }));
    expect(within(tarjeta).getByRole("group", { name: "Periodo de cumpleaños" })).toBeInTheDocument();
    expect(within(tarjeta).getByRole("button", { name: /^Cumpleaños desde/ })).toBeInTheDocument();
    expect(within(tarjeta).getByRole("button", { name: /^Cumpleaños hasta/ })).toBeInTheDocument();
    expect(within(tarjeta).queryByRole("columnheader", { name: "Documento" })).toBeNull();
    expect(within(tarjeta).queryByText(/1\.000\.000\.001|1000000001/)).toBeNull();
    const enlace = await within(tarjeta).findByRole("link", { name: "CLIENTE DE PRUEBA" });
    expect(enlace).toHaveAttribute("href", `/contactos/${CONTACTO.nip}`);
    expect(within(tarjeta).getByText("15 de mayo")).toBeInTheDocument();
  });

  it("al limpiar el periodo vuelve a consultar los cumpleaños de hoy", async () => {
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=cumpleanos" });
    const tarjeta = await screen.findByRole("region", { name: "Cumpleaños del periodo" });
    await userEvent.click(within(tarjeta).getByRole("button", { name: "Limpiar fechas" }));
    const hoy = hoyBogota();
    await waitFor(() => expect(ultimosParametros("/contactos")).toMatchObject({ "filter[cumple_desde]": hoy, "filter[cumple_hasta]": hoy }));
  });

  it("el historial de cumpleaños muestra el nombre como enlace y no la cédula", async () => {
    api.get.mockImplementation(async (ruta: string) =>
      ruta.startsWith("/llamadas-cumpleanos") ? { data: paginado([{ ...CUMPLE, nombre: "CLIENTE DE PRUEBA" }]) } : { data: paginado([]) },
    );
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=cumpleanos" });
    await abrirHistorial();
    const tabla = await screen.findByRole("table", { name: /Llamadas de cumpleaños/ });
    const enlace = await within(tabla).findByRole("link", { name: "CLIENTE DE PRUEBA" });
    expect(enlace).toHaveAttribute("href", `/contactos/${CONTACTO.nip}`);
    expect(within(tabla).queryByText(/1\.000\.000\.001|1000000001/)).toBeNull();
  });

  it("si el contacto de la llamada ya no existe lo indica sin enlace", async () => {
    api.get.mockImplementation(async (ruta: string) =>
      ruta.startsWith("/llamadas-cumpleanos") ? { data: paginado([{ ...CUMPLE, nombre: null }]) } : { data: paginado([]) },
    );
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=cumpleanos" });
    await abrirHistorial();
    const tabla = await screen.findByRole("table", { name: /Llamadas de cumpleaños/ });
    expect(await within(tabla).findByText("Contacto no registrado")).toBeInTheDocument();
    expect(within(tabla).queryByRole("link")).toBeNull();
  });
});
