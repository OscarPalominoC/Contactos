import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PaginaDetalleMoto } from "../features/motos/PaginaMotos";
import { PaginaRevisiones } from "../features/revisiones/PaginaRevisiones";
import { cumpleanos, esCumpleanosValido, formatearFecha, formatearFechaHora } from "../utils/formatters";
import { CONTACTO, paginado, renderizar, YO_ADMIN } from "./utilidades";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock("../services/apiClient", async (original) => ({
  ...(await original<typeof import("../services/apiClient")>()),
  apiClient: api,
}));
vi.mock("../app/sesion", () => ({
  useSesion: () => ({ usuario: YO_ADMIN, estado: "autenticado", puede: (p: string) => YO_ADMIN.permisos.includes(p) }),
}));

describe("formatearFecha con datos del legado", () => {
  it("oculta años fuera de 1990-2100", () => {
    expect(formatearFecha("3196-05-01")).toBe("—");
    expect(formatearFecha("0227-02-14")).toBe("—");
    expect(formatearFecha("1899-12-30")).toBe("—");
    expect(formatearFecha("2101-01-01")).toBe("—");
    expect(formatearFechaHora("3017-07-21T10:00:00Z")).toBe("—");
  });

  it("marca días inexistentes como fecha inválida", () => {
    expect(formatearFecha("2026-02-31")).toBe("— (Fecha inválida)");
    expect(formatearFecha("2026-04-31")).toBe("— (Fecha inválida)");
    expect(formatearFecha("2025-02-29")).toBe("— (Fecha inválida)");
  });

  it("formatea normalmente las fechas válidas (dd/mm/aaaa)", () => {
    expect(formatearFecha("1990-01-01")).toBe("01/01/1990");
    expect(formatearFecha("2100-12-31")).toBe("31/12/2100");
    expect(formatearFecha("2024-02-29")).toBe("29/02/2024");
    expect(formatearFechaHora("2026-11-14T15:00:00Z")).toMatch(/^14\/11\/2026/);
  });
});

describe("cumpleanos con datos del legado", () => {
  it("el 31 de febrero y otras combinaciones imposibles se marcan inválidas", () => {
    expect(cumpleanos(31, 2)).toBe("— (Fecha inválida)");
    expect(cumpleanos(31, 4)).toBe("— (Fecha inválida)");
    expect(cumpleanos(29, 2)).toBe("29 de febrero");
    expect(esCumpleanosValido(31, 2)).toBe(false);
    expect(esCumpleanosValido(29, 2)).toBe(true);
    expect(esCumpleanosValido(5, 13)).toBe(false);
    expect(esCumpleanosValido(null, 2)).toBe(false);
  });
});

const AUD = { creado_en: null, actualizado_en: null, creado_por: "", actualizado_por: "" };
const REVISION_CORRUPTA = {
  certificado: "CERT-RARO",
  placa: "LZB56D",
  soat: "",
  fecha_soat: null,
  fecha_venc_soat: null,
  fecha_certificado: "3196-05-01",
  fecha_venc_certificado: "2012-05-01",
  nro_autodeclaracion_runt: "",
  nro_solicitud_runt: "",
  nro_certificado_runt: "",
  fecha_registro_runt: null,
  estado: "VENCIDO",
  estado_actual: "VENCIDO",
  usuario: "",
  fecha_registro: null,
  ...AUD,
};
const MOTO = {
  placa: "LZB56D",
  marca: "HONDA",
  modelo: "2010",
  linea: "",
  nip_contacto: CONTACTO.nip,
  nro_soat: "",
  fecha_soat: null,
  fecha_venc_soat: "3196-01-01",
  nro_certificado: "",
  fecha_rtmg: null,
  fecha_venc_rtmg: "2027-03-15",
  propietario: null,
  ...AUD,
};

beforeEach(() => {
  for (const f of Object.values(api)) f.mockReset();
  api.get.mockImplementation(async (ruta: string) => {
    if (ruta === "/motos/LZB56D") return { data: MOTO };
    if (ruta.startsWith("/revisiones")) return { data: paginado([REVISION_CORRUPTA]) };
    return { data: paginado([]) };
  });
});

describe("vistas con fechas corruptas del legado", () => {
  it("revisiones muestran '—' en lugar del año 3196", async () => {
    renderizar(<PaginaRevisiones />);
    await userEvent.type(screen.getByLabelText("Buscar por placa o certificado"), "LZB");
    const fila = (await screen.findByRole("link", { name: "LZB56D" })).closest("tr") as HTMLElement;
    expect(fila).not.toHaveTextContent("3196");
    expect(within(fila).getAllByRole("cell")[1]).toHaveTextContent("—");
    expect(within(fila).getByText("01/05/2012")).toBeInTheDocument();
  });

  it("el detalle de la moto muestra '—' en un vencimiento insalvable", async () => {
    renderizar(
      <Routes>
        <Route path="/motos/:placa" element={<PaginaDetalleMoto />} />
      </Routes>,
      { ruta: "/motos/LZB56D" },
    );
    expect(await screen.findByText("15/03/2027")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("3196");
  });
});
