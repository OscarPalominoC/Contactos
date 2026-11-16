import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PaginaContactos } from "../features/contactos/PaginaContactos";
import { PaginaLlamadas } from "../features/llamadas/PaginaLlamadas";
import { PaginaMotos } from "../features/motos/PaginaMotos";
import { PaginaRevisiones } from "../features/revisiones/PaginaRevisiones";
import { PaginaSoat } from "../features/soat/PaginaSoat";
import { hoyBogota, sumarDias } from "../utils/formatters";
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
const PROPIETARIO = { propietario_nip: CONTACTO.nip, propietario_nombre: "CLIENTE DE PRUEBA" };
const MOTO = {
  placa: "ABC12D",
  marca: "HONDA",
  modelo: "2024",
  linea: "XR 190L",
  nip_contacto: CONTACTO.nip,
  nombre_contacto: "CLIENTE DE PRUEBA",
  nro_soat: "",
  fecha_soat: null,
  fecha_venc_soat: null,
  nro_certificado: "",
  fecha_rtmg: null,
  fecha_venc_rtmg: null,
  ...AUD,
};
const REVISION = {
  certificado: "CERT-001",
  placa: "ABC12D",
  ...PROPIETARIO,
  soat: "",
  fecha_soat: null,
  fecha_venc_soat: null,
  fecha_certificado: "2026-11-06",
  fecha_venc_certificado: "2027-11-06",
  nro_autodeclaracion_runt: "",
  nro_solicitud_runt: "",
  nro_certificado_runt: "",
  fecha_registro_runt: null,
  estado: "VIGENTE",
  estado_actual: "VIGENTE",
  usuario: "OPERADOR",
  fecha_registro: null,
  ...AUD,
};
const SOAT = {
  soat: "12345-MUNDIAL",
  placa: "ABC12D",
  ...PROPIETARIO,
  aseguradora: "MUNDIAL",
  fecha_soat: "2026-11-07",
  fecha_venc_soat: "2027-11-07",
  estado: "VIGENTE",
  estado_actual: "VIGENTE",
  usuario: "OPERADOR",
  fecha_registro: null,
  ...AUD,
};
const POR_LLAMAR = {
  placa: "ABC12D",
  fecha: "2026-11-20",
  ...PROPIETARIO,
  celular: "3000000000",
  llamada_id: null,
  estado: "sin_llamar",
  num_llamadas: 0,
  observacion: "",
};
const LLAMADA_PLACA = {
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
};

const DATOS: Record<string, unknown> = {
  "/contactos": paginado([CONTACTO]),
  "/motos": paginado([MOTO]),
  "/revisiones": paginado([REVISION]),
  "/soats": paginado([SOAT]),
  "/llamadas-rtm/por-llamar": paginado([POR_LLAMAR]),
  "/llamadas-soat/por-llamar": paginado([POR_LLAMAR]),
  "/llamadas-rtm": paginado([LLAMADA_PLACA]),
  "/llamadas-soat": paginado([LLAMADA_PLACA]),
  "/llamadas-cumpleanos": paginado([]),
};

beforeEach(() => {
  for (const f of Object.values(api)) f.mockReset();
  api.get.mockImplementation(async (ruta: string) => ({ data: DATOS[ruta] ?? paginado([]) }));
});

const rutasPedidas = () => api.get.mock.calls.map(([r]) => r as string);
function ultimosParametros(ruta: string): Record<string, unknown> {
  const llamadas = api.get.mock.calls.filter(([r]) => r === ruta);
  return (llamadas.at(-1)?.[1] as { params: Record<string, unknown> }).params;
}

describe("Listados solo de búsqueda", () => {
  it("contactos: no carga la lista al entrar; al buscar muestra el nombre con enlace y sin cédula", async () => {
    renderizar(<PaginaContactos />);
    expect(await screen.findByText("Busque un contacto")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nuevo contacto" })).toBeInTheDocument();
    expect(rutasPedidas()).not.toContain("/contactos");

    await userEvent.type(screen.getByLabelText("Buscar por documento o nombre"), "cl");
    expect(rutasPedidas()).not.toContain("/contactos");
    await userEvent.type(screen.getByLabelText("Buscar por documento o nombre"), "i");
    const enlace = await screen.findByRole("link", { name: "CLIENTE DE PRUEBA" });
    expect(enlace).toHaveAttribute("href", `/contactos/${CONTACTO.nip}`);
    expect(ultimosParametros("/contactos")["filter[q]"]).toBe("cli");
    const tabla = screen.getByRole("table");
    expect(within(tabla).queryByRole("columnheader", { name: /Documento/ })).toBeNull();
    expect(within(tabla).queryByText(/1\.000\.000\.001|1000000001/)).toBeNull();
    expect(within(tabla).getByRole("button", { name: "Editar CLIENTE DE PRUEBA" })).toBeInTheDocument();
    expect(within(tabla).queryByRole("link", { name: /Ver ficha/ })).toBeNull();
  });

  it("motos: busca por placa; la placa lleva al vehículo y el propietario (nombre) a su ficha", async () => {
    renderizar(<PaginaMotos />);
    expect(await screen.findByText("Busque una moto")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nueva moto" })).toBeInTheDocument();
    expect(rutasPedidas()).not.toContain("/motos");
    await userEvent.type(screen.getByLabelText("Buscar por placa"), "abc");
    expect(await screen.findByRole("link", { name: "ABC12D" })).toHaveAttribute("href", "/motos/ABC12D");
    expect(screen.getByRole("link", { name: "CLIENTE DE PRUEBA" })).toHaveAttribute("href", `/contactos/${CONTACTO.nip}`);
    expect(screen.queryByText(/1\.000\.000\.001|1000000001/)).toBeNull();
    expect(screen.getByRole("button", { name: "Editar moto ABC12D" })).toBeInTheDocument();
  });

  it.each([
    ["revisiones", PaginaRevisiones, "/revisiones", "Busque una revisión", "Buscar por placa o certificado", "CERT-001", "2026-11-06", "2027-11-06"],
    ["SOAT", PaginaSoat, "/soats", "Busque un SOAT", "Buscar por placa o póliza", "12345-MUNDIAL", "2026-11-07", "2027-11-07"],
  ] as const)("%s: busca; no muestra el número, sí placa, vigencia, vencimiento, estado y propietario", async (_n, Pagina, ruta, aviso, etiqueta, numero, desde, hasta) => {
    renderizar(<Pagina />);
    expect(await screen.findByText(aviso)).toBeInTheDocument();
    expect(rutasPedidas()).not.toContain(ruta);
    await userEvent.type(screen.getByLabelText(etiqueta), "abc");
    const placa = await screen.findByRole("link", { name: "ABC12D" });
    expect(placa).toHaveAttribute("href", "/motos/ABC12D");
    expect(ultimosParametros(ruta)["filter[q]"]).toBe("abc");
    const tabla = screen.getByRole("table");
    expect(within(tabla).queryByText(numero)).toBeNull();
    expect(within(tabla).getByRole("link", { name: "CLIENTE DE PRUEBA" })).toHaveAttribute("href", `/contactos/${CONTACTO.nip}`);
    const [a, m, d] = desde.split("-");
    const [a2, m2, d2] = hasta.split("-");
    expect(within(tabla).getByText(`${d}/${m}/${a}`)).toBeInTheDocument();
    expect(within(tabla).getByText(`${d2}/${m2}/${a2}`)).toBeInTheDocument();
    expect(within(tabla).getByRole("columnheader", { name: /Vigencia/ })).toBeInTheDocument();
    expect(within(tabla).getByRole("columnheader", { name: /Vencimiento/ })).toBeInTheDocument();
    expect(within(tabla).getByText("Vigente")).toBeInTheDocument();
  });

  it("revisiones: el rango de vencimiento del tablero cuenta como búsqueda", async () => {
    renderizar(<PaginaRevisiones />, { ruta: "/revisiones?estado=VIGENTE&vence_desde=2026-11-14&vence_hasta=2026-12-14" });
    expect(await screen.findByRole("link", { name: "ABC12D" })).toBeInTheDocument();
    expect(ultimosParametros("/revisiones")).toMatchObject({ "filter[vence_desde]": "2026-11-14", "filter[estado]": "VIGENTE" });
  });
});

describe("Llamadas por vencimiento", () => {
  it.each(["rtm", "soat"] as const)("%s: pendientes salen de los vencimientos (hoy a 30 días) con enlaces y botón de llamar", async (pestana) => {
    api.post.mockResolvedValue({ data: LLAMADA_PLACA });
    renderizar(<PaginaLlamadas />, { ruta: `/llamadas?pestana=${pestana}` });
    const ruta = `/llamadas-${pestana}/por-llamar`;
    const placa = await screen.findByRole("link", { name: "ABC12D" });
    expect(placa).toHaveAttribute("href", "/motos/ABC12D");
    const hoy = hoyBogota();
    expect(ultimosParametros(ruta)).toMatchObject({ "filter[desde]": hoy, "filter[hasta]": sumarDias(hoy, 30) });
    expect(rutasPedidas()).not.toContain(`/llamadas-${pestana}`);
    expect(screen.getByRole("link", { name: "CLIENTE DE PRUEBA" })).toHaveAttribute("href", `/contactos/${CONTACTO.nip}`);
    expect(screen.getByText("Sin llamar")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Registrar llamada a ABC12D" }));
    const dialogo = screen.getByRole("dialog", { name: /Registrar llamada de/ });
    expect(within(dialogo).getByLabelText(/^Placa/)).toHaveValue("ABC12D");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenCalledWith(`/llamadas-${pestana}`, expect.objectContaining({ placa: "ABC12D", fecha: "2026-11-20" }), expect.anything()),
    );
  });

  it("un vencimiento con intento previo ofrece Nuevo intento sobre su llamada", async () => {
    DATOS["/llamadas-rtm/por-llamar"] = paginado([{ ...POR_LLAMAR, llamada_id: "ABC12D.2026-11-20", estado: "ocupada", num_llamadas: 2 }]);
    api.post.mockResolvedValue({ data: LLAMADA_PLACA });
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=rtm" });
    await userEvent.click(await screen.findByRole("button", { name: "Nuevo intento para ABC12D" }));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Registrar intento" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/llamadas-rtm/ABC12D.2026-11-20/intentos", expect.anything(), expect.anything()));
    DATOS["/llamadas-rtm/por-llamar"] = paginado([POR_LLAMAR]);
  });

  it("al limpiar el rango vuelve a hoy + 30 días", async () => {
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=rtm" });
    await screen.findByRole("link", { name: "ABC12D" });
    await userEvent.click(screen.getByRole("button", { name: "Limpiar fechas" }));
    const hoy = hoyBogota();
    await waitFor(() => expect(ultimosParametros("/llamadas-rtm/por-llamar")).toMatchObject({ "filter[desde]": hoy, "filter[hasta]": sumarDias(hoy, 30) }));
  });

  it("el historial muestra la placa como enlace al vehículo", async () => {
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=soat" });
    await userEvent.click(await screen.findByRole("button", { name: "Historial de llamadas" }));
    await waitFor(() => expect(rutasPedidas()).toContain("/llamadas-soat"));
    const tabla = await screen.findByRole("table", { name: /Llamadas de SOAT/ });
    expect(await within(tabla).findByRole("link", { name: "ABC12D" })).toHaveAttribute("href", "/motos/ABC12D");
  });
});

describe("Cumpleaños", () => {
  it("pendientes solo consulta los cumpleaños del periodo (sin la bitácora)", async () => {
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=cumpleanos" });
    await screen.findByRole("region", { name: "Cumpleaños del periodo" });
    await waitFor(() => expect(rutasPedidas()).toContain("/contactos"));
    expect(rutasPedidas()).not.toContain("/llamadas-cumpleanos");
    expect(screen.queryByRole("region", { name: /Llamadas pendientes de Cumpleaños/ })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Historial de llamadas" }));
    await waitFor(() => expect(rutasPedidas()).toContain("/llamadas-cumpleanos"));
  });

  it.each([
    ["Nombre", "nombre"],
    ["Cumpleaños", "cumpleanos"],
    ["Celular", "celular"],
  ])("ordena por %s", async (columna, campo) => {
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=cumpleanos" });
    const tarjeta = await screen.findByRole("region", { name: "Cumpleaños del periodo" });
    await within(tarjeta).findByRole("link", { name: "CLIENTE DE PRUEBA" });
    const encabezado = within(tarjeta).getByRole("columnheader", { name: new RegExp(columna) });
    await userEvent.click(within(encabezado).getByRole("button"));
    await waitFor(() => expect(ultimosParametros("/contactos").sort).toBe(campo));
    await userEvent.click(within(encabezado).getByRole("button"));
    await waitFor(() => expect(ultimosParametros("/contactos").sort).toBe(`-${campo}`));
  });
});
