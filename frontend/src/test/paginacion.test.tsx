import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PaginaContactos } from "../features/contactos/PaginaContactos";
import { PaginaLlamadas } from "../features/llamadas/PaginaLlamadas";
import { PaginaMotos } from "../features/motos/PaginaMotos";
import { PaginaRevisiones } from "../features/revisiones/PaginaRevisiones";
import { PaginaSoat } from "../features/soat/PaginaSoat";
import { CONTACTO, renderizar, YO_ADMIN } from "./utilidades";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock("../services/apiClient", async (original) => ({
  ...(await original<typeof import("../services/apiClient")>()),
  apiClient: api,
}));
vi.mock("../app/sesion", () => ({
  useSesion: () => ({ usuario: YO_ADMIN, estado: "autenticado", puede: (p: string) => YO_ADMIN.permisos.includes(p) }),
}));

const AUD = { creado_en: null, actualizado_en: null, creado_por: "", actualizado_por: "" };
const PROPIETARIO = { propietario_nip: CONTACTO.nip, propietario_nombre: "CLIENTE DE PRUEBA" };
const FILAS: Record<string, unknown> = {
  "/contactos": CONTACTO,
  "/motos": {
    placa: "ABC12D",
    marca: "HONDA",
    modelo: "2024",
    linea: "",
    nip_contacto: CONTACTO.nip,
    nombre_contacto: "CLIENTE DE PRUEBA",
    nro_soat: "",
    fecha_soat: null,
    fecha_venc_soat: null,
    nro_certificado: "",
    fecha_rtmg: null,
    fecha_venc_rtmg: null,
    ...AUD,
  },
  "/revisiones": {
    certificado: "C1",
    placa: "ABC12D",
    ...PROPIETARIO,
    soat: "",
    fecha_soat: null,
    fecha_venc_soat: null,
    fecha_certificado: "2026-01-01",
    fecha_venc_certificado: "2027-01-01",
    nro_autodeclaracion_runt: "",
    nro_solicitud_runt: "",
    nro_certificado_runt: "",
    fecha_registro_runt: null,
    estado: "VIGENTE",
    estado_actual: "VIGENTE",
    usuario: "",
    fecha_registro: null,
    ...AUD,
  },
  "/soats": {
    soat: "1-SURA",
    placa: "ABC12D",
    ...PROPIETARIO,
    aseguradora: "SURA",
    fecha_soat: "2026-01-01",
    fecha_venc_soat: "2027-01-01",
    estado: "VIGENTE",
    estado_actual: "VIGENTE",
    usuario: "",
    fecha_registro: null,
    ...AUD,
  },
  "/llamadas-rtm/por-llamar": {
    placa: "ABC12D",
    fecha: "2026-11-20",
    ...PROPIETARIO,
    celular: "3000000000",
    llamada_id: null,
    estado: "sin_llamar",
    num_llamadas: 0,
    observacion: "",
  },
  "/llamadas-rtm": {
    id: "ABC12D.2026-11-08",
    fecha: "2026-11-08",
    placa: "ABC12D",
    motivo_llamada: "rtmyg",
    estado: "realizada",
    estado_nombre: "Realizada",
    observacion: "",
    usuario: "",
    num_llamadas: 1,
    intentos: "",
    ...AUD,
  },
};

/** Respuesta paginada de 3 páginas que devuelve la página pedida (como el servidor real). */
beforeEach(() => {
  for (const f of Object.values(api)) f.mockReset();
  api.get.mockImplementation(async (ruta: string, config: { params: Record<string, unknown> }) => {
    const numero = Number(config.params["page[number]"] ?? 1);
    return {
      data: {
        data: [FILAS[ruta]],
        meta: { page: { number: numero, size: 25, total: 60, total_pages: 3 } },
        links: { self: null, next: null, prev: null, first: null, last: null },
      },
    };
  });
});

function paginaPedida(ruta: string): unknown {
  const llamadas = api.get.mock.calls.filter(([r]) => r === ruta);
  return (llamadas.at(-1)?.[1] as { params: Record<string, unknown> }).params["page[number]"];
}

/** Avanza a la página 2 y comprueba que se queda ahí (no vuelve sola a la 1). */
async function avanzarYComprobar(ruta: string) {
  expect(await screen.findByText(/60 registros · página 1 de 3/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Siguiente" }));
  expect(await screen.findByText(/60 registros · página 2 de 3/)).toBeInTheDocument();
  await new Promise((r) => setTimeout(r, 400));
  expect(paginaPedida(ruta)).toBe(2);
  expect(screen.getByText(/60 registros · página 2 de 3/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Siguiente" }));
  expect(await screen.findByText(/60 registros · página 3 de 3/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Anterior" }));
  expect(await screen.findByText(/60 registros · página 2 de 3/)).toBeInTheDocument();
}

const casos: [string, () => ReactElement, string, string | null, string][] = [
  ["Contactos", () => <PaginaContactos />, "/contactos", "Buscar por documento o nombre", "/contactos"],
  ["Motos", () => <PaginaMotos />, "/motos", "Buscar por placa", "/motos"],
  ["Revisiones RTM", () => <PaginaRevisiones />, "/revisiones", "Buscar por placa o certificado", "/revisiones"],
  ["SOAT", () => <PaginaSoat />, "/soats", "Buscar por placa o póliza", "/soat"],
  ["Llamadas RTM pendientes", () => <PaginaLlamadas />, "/llamadas-rtm/por-llamar", null, "/llamadas?pestana=rtm"],
  ["Cumpleaños del periodo", () => <PaginaLlamadas />, "/contactos", null, "/llamadas?pestana=cumpleanos"],
];

describe("Paginación", () => {
  it.each(casos)("%s avanza y retrocede de página", async (_nombre, pagina, ruta, busqueda, url) => {
    renderizar(pagina(), { ruta: url });
    if (busqueda) await userEvent.type(screen.getByLabelText(busqueda), "abc");
    await avanzarYComprobar(ruta);
  });

  it("historial de llamadas avanza de página", async () => {
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=rtm" });
    await userEvent.click(await screen.findByRole("button", { name: "Historial de llamadas" }));
    await waitFor(() => expect(api.get.mock.calls.some(([r]) => r === "/llamadas-rtm")).toBe(true));
    await avanzarYComprobar("/llamadas-rtm");
  });

  it("cambiar la búsqueda vuelve a la página 1", async () => {
    renderizar(<PaginaContactos />);
    const campo = screen.getByLabelText("Buscar por documento o nombre");
    await userEvent.type(campo, "abc");
    await avanzarYComprobar("/contactos");
    await userEvent.type(campo, "d");
    await waitFor(() => expect(paginaPedida("/contactos")).toBe(1));
    expect(within(screen.getByRole("navigation", { name: /Paginación/ })).getByText(/página 1 de 3/)).toBeInTheDocument();
  });
});
