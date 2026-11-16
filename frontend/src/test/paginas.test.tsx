import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PaginaCatalogos } from "../features/catalogos/PaginaCatalogos";
import { PaginaContactos } from "../features/contactos/PaginaContactos";
import { PaginaFichaContacto } from "../features/contactos/PaginaFichaContacto";
import { PaginaLlamadas } from "../features/llamadas/PaginaLlamadas";
import { PaginaDetalleMoto, PaginaMotos } from "../features/motos/PaginaMotos";
import { PaginaRevisiones } from "../features/revisiones/PaginaRevisiones";
import { PaginaSoat } from "../features/soat/PaginaSoat";
import { PaginaTablero } from "../features/tablero/PaginaTablero";
import { PaginaUsuarios } from "../features/usuarios/PaginaUsuarios";
import { ApiError } from "../services/apiClient";
import { CONTACTO, paginado, renderizar, YO_ADMIN } from "./utilidades";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock("../services/apiClient", async (original) => ({
  ...(await original<typeof import("../services/apiClient")>()),
  apiClient: api,
}));
vi.mock("../app/sesion", () => ({
  useSesion: () => ({
    usuario: YO_ADMIN,
    estado: "autenticado",
    puede: (permiso: string) => YO_ADMIN.permisos.includes(permiso),
  }),
}));

const AUD = { creado_en: null, actualizado_en: null, creado_por: "", actualizado_por: "" };
const MOTO = {
  placa: "ABC12D",
  marca: "HONDA",
  modelo: "2024",
  linea: "XR 190L",
  nip_contacto: CONTACTO.nip,
  nro_soat: "",
  fecha_soat: null,
  fecha_venc_soat: null,
  nro_certificado: "",
  fecha_rtmg: null,
  fecha_venc_rtmg: "2027-03-15",
  ...AUD,
};
const REVISION = {
  certificado: "CERT-001",
  placa: "ABC12D",
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
  aseguradora: "MUNDIAL",
  fecha_soat: "2026-11-07",
  fecha_venc_soat: "2027-11-07",
  estado: "VIGENTE",
  estado_actual: "VIGENTE",
  usuario: "OPERADOR",
  fecha_registro: null,
  ...AUD,
};
const LLAMADA_BASE = {
  motivo_llamada: "rtmyg",
  estado: "no_realizada",
  estado_nombre: "No realizada",
  observacion: "NO CONTESTA\nMENSAJE WHATSAPP",
  usuario: "OPERADOR",
  num_llamadas: 2,
  intentos: "",
  ...AUD,
};
const LLAMADA_PLACA = { id: "ABC12D.2026-11-08", fecha: "2026-11-08", placa: "ABC12D", ...LLAMADA_BASE };
const LLAMADA_CUMPLE = { id: 7, fecha: "2026-11-07T00:00:00-05:00", nip: CONTACTO.nip, ...LLAMADA_BASE, motivo_llamada: "cumpleanos" };
/** Vencimiento por llamar con un intento previo (su llamada es LLAMADA_PLACA). */
const POR_LLAMAR = {
  placa: "ABC12D",
  fecha: "2026-11-08",
  propietario_nip: CONTACTO.nip,
  propietario_nombre: "CLIENTE DE PRUEBA",
  celular: "3000000000",
  llamada_id: "ABC12D.2026-11-08",
  estado: "no_realizada",
  num_llamadas: 2,
  observacion: "NO CONTESTA\nMENSAJE WHATSAPP",
};
const USUARIO = {
  nip: "900002",
  nombre: "OPERADOR DE PRUEBA",
  rol: "usuario",
  is_active: true,
  debe_cambiar_clave: true,
  last_login: null,
  clave_cambiada_en: null,
};

/** Respuestas GET por prefijo de ruta. */
function responderGet(mapa: Record<string, unknown>) {
  api.get.mockImplementation(async (ruta: string) => {
    const clave = Object.keys(mapa)
      .sort((a, b) => b.length - a.length)
      .find((k) => ruta.startsWith(k));
    if (clave === undefined) throw new ApiError({ type: "x", title: "t", status: 404, detail: `Sin mock para ${ruta}` });
    return { data: mapa[clave] };
  });
}

beforeEach(() => {
  for (const f of Object.values(api)) f.mockReset();
});

describe("Tablero", () => {
  it("muestra los indicadores con enlaces a los listados", async () => {
    responderGet({
      "/tablero": {
        dias_horizonte: 30,
        rtm_por_vencer: 12,
        soat_por_vencer: 7,
        llamadas_hoy: { cumpleanos: 1, rtm: 2, soat: 3 },
        cumpleanos_hoy: 4,
        contactos_nuevos_mes: 5,
      },
    });
    renderizar(<PaginaTablero />);
    expect(await screen.findByText("12")).toBeInTheDocument();
    expect(screen.getByText("Cumpleaños 1 · RTM 2 · SOAT 3")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /RTM por vencer/ })).toHaveAttribute("href", expect.stringContaining("/revisiones?vence_desde="));
    expect(document.title).toBe("Tablero · Check Contactos");
  });
});

describe("Contactos", () => {
  it("lista, filtra con filter[...] y crea un contacto con Idempotency-Key", async () => {
    responderGet({ "/contactos": paginado([CONTACTO]) });
    api.post.mockResolvedValueOnce({ data: { ...CONTACTO, nip: "7654321", nombre: "NUEVA PERSONA" } });
    renderizar(<PaginaContactos />);
    await userEvent.type(screen.getByLabelText("Buscar por documento o nombre"), "cliente");
    expect(await screen.findByText("CLIENTE DE PRUEBA")).toBeInTheDocument();
    expect(screen.getByText("15 de mayo")).toBeInTheDocument();
    expect(screen.getByText("300 000 0000")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Estado"), "inhabilitado");
    await waitFor(() =>
      expect(api.get).toHaveBeenLastCalledWith("/contactos", expect.objectContaining({ params: expect.objectContaining({ "filter[estado]": "inhabilitado" }) })),
    );

    await userEvent.click(screen.getByRole("button", { name: "Nuevo contacto" }));
    const dialogo = screen.getByRole("dialog", { name: "Nuevo contacto" });
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    expect(within(dialogo).getByText("Escriba el nombre completo.")).toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();

    await userEvent.type(within(dialogo).getByLabelText(/Documento/), "7654321");
    await userEvent.type(within(dialogo).getByLabelText(/Nombre completo/), "Nueva Persona");
    await userEvent.type(within(dialogo).getByLabelText("Correo"), "nueva@ejemplo.test");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledOnce());
    const [ruta, cuerpo, config] = api.post.mock.calls[0] as [string, Record<string, unknown>, { headers: Record<string, string> }];
    expect(ruta).toBe("/contactos");
    expect(cuerpo).toMatchObject({ nip: "7654321", nombre: "Nueva Persona", correo: "nueva@ejemplo.test" });
    expect(config.headers["Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("muestra los errores 422 del servidor en sus campos", async () => {
    responderGet({ "/contactos": paginado([CONTACTO]) });
    api.patch.mockRejectedValueOnce(
      new ApiError({ type: "/problemas/datos-invalidos", title: "Datos inválidos", status: 422, detail: "Revise los campos marcados.", errors: { correo: ["Correo rechazado por el servidor."] } }),
    );
    renderizar(<PaginaContactos />);
    await userEvent.type(screen.getByLabelText("Buscar por documento o nombre"), "cliente");
    await userEvent.click(await screen.findByRole("button", { name: "Editar CLIENTE DE PRUEBA" }));
    const dialogo = screen.getByRole("dialog", { name: "Editar contacto" });
    expect(within(dialogo).getByLabelText(/Documento/)).toBeDisabled();
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    expect(await within(dialogo).findByText("Correo rechazado por el servidor.")).toBeInTheDocument();
    expect(api.patch).toHaveBeenCalledWith(`/contactos/${CONTACTO.nip}`, expect.not.objectContaining({ nip: expect.anything() }), expect.anything());
  });

  it("muestra el estado vacío cuando no hay resultados", async () => {
    responderGet({ "/contactos": paginado([]) });
    renderizar(<PaginaContactos />);
    await userEvent.type(screen.getByLabelText("Buscar por documento o nombre"), "nadie");
    expect(await screen.findByText("No se encontraron contactos")).toBeInTheDocument();
  });

  it("ficha 360 con secciones vacías y observaciones como texto (sin HTML)", async () => {
    responderGet({
      [`/contactos/${CONTACTO.nip}/ficha`]: {
        contacto: CONTACTO,
        motos: [MOTO],
        revisiones: [REVISION],
        soats: [],
        llamadas_cumpleanos: [{ ...LLAMADA_CUMPLE, observacion: "<img src=x onerror=alert(1)>" }],
        llamadas_rtm: [LLAMADA_PLACA],
        llamadas_soat: [],
      },
    });
    renderizar(
      <Routes>
        <Route path="/contactos/:nip" element={<PaginaFichaContacto />} />
      </Routes>,
      { ruta: `/contactos/${CONTACTO.nip}` },
    );
    expect(await screen.findByRole("heading", { level: 1, name: "CLIENTE DE PRUEBA" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "ABC12D" })).toHaveAttribute("href", "/motos/ABC12D");
    expect(screen.getByText("Sin pólizas soat registradas")).toBeInTheDocument();
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(document.querySelector("img[src='x']")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Editar contacto" }));
    expect(screen.getByRole("dialog", { name: "Editar contacto" })).toBeInTheDocument();
  });

  it("ficha con error muestra el aviso", async () => {
    responderGet({});
    renderizar(
      <Routes>
        <Route path="/contactos/:nip" element={<PaginaFichaContacto />} />
      </Routes>,
      { ruta: "/contactos/no-existe" },
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("Sin mock");
  });
});

describe("Motos", () => {
  it("lista y crea una moto con marca y línea dependientes", async () => {
    responderGet({
      "/motos": paginado([MOTO]),
      "/marcas": paginado([{ codigo: "HO", nombre: "HONDA" }]),
      "/lineas": paginado([{ linea: "CB 125", marca: "HO", marca_nombre: "HONDA" }]),
    });
    api.post.mockResolvedValueOnce({ data: { ...MOTO, placa: "XYZ98E" } });
    renderizar(<PaginaMotos />);
    await userEvent.type(screen.getByLabelText("Buscar por placa"), "abc");
    expect(await screen.findByRole("link", { name: "ABC12D" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Nueva moto" }));
    const dialogo = screen.getByRole("dialog", { name: "Nueva moto" });
    expect(within(dialogo).getByLabelText("Línea")).toBeDisabled();
    await userEvent.type(within(dialogo).getByLabelText(/Placa/), "xyz-98e");
    await userEvent.type(within(dialogo).getByLabelText(/Documento del propietario/), CONTACTO.nip);
    await userEvent.selectOptions(within(dialogo).getByLabelText(/Marca/), await within(dialogo).findByRole("option", { name: "HONDA" }));
    await userEvent.selectOptions(within(dialogo).getByLabelText("Línea"), await within(dialogo).findByRole("option", { name: "CB 125" }));
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledOnce());
    expect(api.post.mock.calls[0]?.[1]).toMatchObject({ placa: "XYZ98E", marca: "HONDA", linea: "CB 125", fecha_venc_soat: null });
  });

  it("valida la placa y el modelo", async () => {
    responderGet({ "/motos": paginado([]), "/marcas": paginado([]) });
    renderizar(<PaginaMotos />);
    await userEvent.click(await screen.findByRole("button", { name: "Nueva moto" }));
    const dialogo = screen.getByRole("dialog", { name: "Nueva moto" });
    await userEvent.type(within(dialogo).getByLabelText(/Placa/), "A1");
    await userEvent.type(within(dialogo).getByLabelText(/Modelo/), "20");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    expect(within(dialogo).getByText(/La placa debe tener 5 o 6/)).toBeInTheDocument();
    expect(within(dialogo).getByText("El modelo es el año de 4 dígitos.")).toBeInTheDocument();
    expect(within(dialogo).getByText("Elija la marca.")).toBeInTheDocument();
  });

  it("detalle de moto con historial y edición", async () => {
    responderGet({
      "/motos/ABC12D": { ...MOTO, propietario: { nip: CONTACTO.nip, nombre: "CLIENTE DE PRUEBA", celular: "3000000000" } },
      "/revisiones": paginado([REVISION]),
      "/soats": paginado([SOAT]),
      "/llamadas-rtm": paginado([LLAMADA_PLACA]),
      "/marcas": paginado([{ codigo: "HO", nombre: "HONDA" }]),
      "/lineas": paginado([]),
    });
    renderizar(
      <Routes>
        <Route path="/motos/:placa" element={<PaginaDetalleMoto />} />
      </Routes>,
      { ruta: "/motos/ABC12D" },
    );
    expect(await screen.findByRole("heading", { level: 1, name: "Moto ABC12D" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "CLIENTE DE PRUEBA" })).toBeInTheDocument();
    expect(await screen.findByText("CERT-001")).toBeInTheDocument();
    expect(await screen.findByText("12345-MUNDIAL")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Editar moto" }));
    const dialogo = screen.getByRole("dialog", { name: "Editar moto ABC12D" });
    expect(within(dialogo).getByLabelText(/Placa/)).toBeDisabled();
    expect(within(dialogo).getByRole("option", { name: "XR 190L (del registro)" })).toBeInTheDocument();
  });
});

describe("Revisiones y SOAT", () => {
  it("registra una revisión y anula con confirmación", async () => {
    responderGet({ "/revisiones": paginado([REVISION]) });
    api.post
      .mockResolvedValueOnce({ data: { ...REVISION, certificado: "CERT-9" } })
      .mockResolvedValueOnce({ data: { ...REVISION, estado: "ANULADO", estado_actual: "ANULADO" } });
    renderizar(<PaginaRevisiones />, { ruta: "/revisiones?estado=VIGENTE&vence_desde=2026-11-14&vence_hasta=2026-12-14" });
    expect(await screen.findByRole("link", { name: "ABC12D" })).toBeInTheDocument();
    expect(screen.queryByText("CERT-001")).toBeNull();
    expect(screen.getByLabelText("Estado")).toHaveValue("VIGENTE");
    expect(api.get).toHaveBeenCalledWith(
      "/revisiones",
      expect.objectContaining({ params: expect.objectContaining({ "filter[vence_desde]": "2026-11-14", "filter[estado]": "VIGENTE" }) }),
    );

    await userEvent.click(screen.getByRole("button", { name: "Registrar revisión" }));
    const dialogo = screen.getByRole("dialog", { name: "Registrar revisión RTM" });
    await userEvent.type(within(dialogo).getByLabelText(/Número de certificado/), "CERT-9");
    await userEvent.type(within(dialogo).getByLabelText(/^Placa/), "abc12d");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
    expect(api.post.mock.calls[0]?.[1]).toMatchObject({ certificado: "CERT-9", placa: "ABC12D", fecha_venc_certificado: null });

    await userEvent.click(screen.getByRole("button", { name: "Anular revisión de ABC12D que vence el 06/11/2027" }));
    const confirmar = screen.getByRole("dialog", { name: "Anular revisión" });
    await userEvent.click(within(confirmar).getByRole("button", { name: "Anular" }));
    await waitFor(() => expect(api.post).toHaveBeenLastCalledWith("/revisiones/CERT-001/anular", {}, expect.anything()));
  });

  it("edita una revisión", async () => {
    responderGet({ "/revisiones": paginado([REVISION]) });
    api.patch.mockResolvedValueOnce({ data: REVISION });
    renderizar(<PaginaRevisiones />);
    await userEvent.type(screen.getByLabelText("Buscar por placa o certificado"), "abc");
    await userEvent.click(await screen.findByRole("button", { name: "Editar revisión de ABC12D que vence el 06/11/2027" }));
    const dialogo = screen.getByRole("dialog", { name: "Editar revisión CERT-001" });
    await userEvent.selectOptions(within(dialogo).getByLabelText("Estado"), "DUPLICADO");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/revisiones/CERT-001", expect.objectContaining({ estado: "DUPLICADO" }), expect.anything()));
  });

  it("registra, edita y anula un SOAT", async () => {
    responderGet({ "/soats": paginado([SOAT]) });
    api.post.mockResolvedValue({ data: SOAT });
    api.patch.mockResolvedValue({ data: SOAT });
    renderizar(<PaginaSoat />);
    await userEvent.type(screen.getByLabelText("Buscar por placa o póliza"), "abc");
    expect(await screen.findByRole("link", { name: "ABC12D" })).toBeInTheDocument();
    expect(screen.queryByText("12345-MUNDIAL")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Registrar SOAT" }));
    let dialogo = screen.getByRole("dialog", { name: "Registrar SOAT" });
    await userEvent.type(within(dialogo).getByLabelText(/Número de póliza/), "999");
    await userEvent.type(within(dialogo).getByLabelText(/^Placa/), "ABC12D");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/soats", expect.objectContaining({ numero: "999", aseguradora: "MUNDIAL", placa: "ABC12D" }), expect.anything()));

    await userEvent.click(await screen.findByRole("button", { name: "Editar SOAT de ABC12D que vence el 07/11/2027" }));
    dialogo = screen.getByRole("dialog", { name: "Editar SOAT 12345-MUNDIAL" });
    expect(within(dialogo).getByLabelText(/Número de póliza/)).toHaveValue("12345");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalledOnce());

    await userEvent.click(await screen.findByRole("button", { name: "Anular SOAT de ABC12D que vence el 07/11/2027" }));
    await userEvent.click(within(screen.getByRole("dialog", { name: "Anular SOAT" })).getByRole("button", { name: "Anular" }));
    await waitFor(() => expect(api.post).toHaveBeenLastCalledWith("/soats/12345-MUNDIAL/anular", {}, expect.anything()));
  });
});

describe("Llamadas", () => {
  it("cambia de pestaña con teclado, registra llamada e intento", async () => {
    responderGet({
      "/llamadas-rtm/por-llamar": paginado([POR_LLAMAR]),
      "/llamadas-soat/por-llamar": paginado([POR_LLAMAR]),
      "/llamadas-rtm": paginado([LLAMADA_PLACA]),
      "/llamadas-soat": paginado([{ ...LLAMADA_PLACA, motivo_llamada: "soat" }]),
      "/llamadas-cumpleanos": paginado([LLAMADA_CUMPLE]),
      "/contactos": paginado([CONTACTO]),
    });
    api.post.mockResolvedValue({ data: LLAMADA_PLACA });
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas" });
    expect(await screen.findByText("NO CONTESTA MENSAJE WHATSAPP", { normalizer: (t) => t.replace(/\s+/g, " ") })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "RTM" })).toHaveAttribute("aria-selected", "true");

    await userEvent.click(screen.getByRole("button", { name: "Nuevo intento para ABC12D" }));
    const intento = screen.getByRole("dialog", { name: "Nuevo intento: ABC12D" });
    await userEvent.selectOptions(within(intento).getByLabelText("Resultado"), "ocupada");
    await userEvent.click(within(intento).getByRole("button", { name: "Registrar intento" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/llamadas-rtm/ABC12D.2026-11-08/intentos", { estado: "ocupada", observacion: "" }, expect.anything()));

    screen.getByRole("tab", { name: "RTM" }).focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(await screen.findByRole("tab", { name: "SOAT", selected: true })).toHaveFocus();
    await userEvent.keyboard("{ArrowLeft}{ArrowLeft}");
    expect(await screen.findByRole("tab", { name: "Cumpleaños", selected: true })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Cumpleaños del periodo" })).toBeInTheDocument();

    await userEvent.click(await screen.findByRole("button", { name: "Registrar llamada a CLIENTE DE PRUEBA" }));
    const nueva = screen.getByRole("dialog", { name: "Registrar llamada de Cumpleaños" });
    expect(within(nueva).getByLabelText(/Documento del contacto/)).toHaveValue(CONTACTO.nip);
    await userEvent.type(within(nueva).getByLabelText("Observación"), "Felicitado");
    await userEvent.click(within(nueva).getByRole("button", { name: "Guardar" }));
    await waitFor(() =>
      expect(api.post).toHaveBeenLastCalledWith("/llamadas-cumpleanos", { nip: CONTACTO.nip, estado: "realizada", observacion: "Felicitado" }, expect.anything()),
    );
  });

  it("registra llamada por placa con fecha objetivo", async () => {
    responderGet({ "/llamadas-rtm": paginado([]), "/llamadas-cumpleanos": paginado([]) });
    api.post.mockResolvedValue({ data: LLAMADA_PLACA });
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=rtm" });
    await userEvent.click(await screen.findByRole("button", { name: "Registrar llamada" }));
    const nueva = screen.getByRole("dialog", { name: "Registrar llamada de RTM" });
    await userEvent.type(within(nueva).getByLabelText(/^Placa/), "abc 12d");
    await userEvent.click(within(nueva).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/llamadas-rtm", expect.objectContaining({ placa: "ABC12D", estado: "realizada" }), expect.anything()));
  });

  it("pendientes muestra los vencimientos por llamar en el orden del servidor; el historial, la bitácora", async () => {
    const sinIntentar = { ...POR_LLAMAR, placa: "NUEVA1", llamada_id: null, estado: "sin_llamar", num_llamadas: 0 };
    const intentada = { ...POR_LLAMAR, placa: "INTENT", llamada_id: "INTENT.2026-11-08", estado: "ocupada" };
    responderGet({
      "/llamadas-rtm/por-llamar": paginado([sinIntentar, intentada]),
      "/llamadas-rtm": paginado([{ ...LLAMADA_PLACA, id: "EXITO.2026-11-08", placa: "EXITO1", estado: "realizada", num_llamadas: 1 }]),
    });
    renderizar(<PaginaLlamadas />, { ruta: "/llamadas?pestana=rtm" });
    expect(await screen.findByRole("link", { name: "NUEVA1" })).toBeInTheDocument();
    const textos = screen.getAllByRole("row").map((f) => f.textContent ?? "");
    expect(textos.findIndex((t) => t.includes("NUEVA1"))).toBeLessThan(textos.findIndex((t) => t.includes("INTENT")));
    expect(screen.getByRole("button", { name: "Registrar llamada a NUEVA1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nuevo intento para INTENT" })).toBeInTheDocument();
    expect(screen.queryByText("EXITO1")).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "Historial de llamadas" }));
    expect(await screen.findByRole("link", { name: "EXITO1" })).toHaveAttribute("href", "/motos/EXITO1");
  });
});

describe("Catálogos", () => {
  it("crea y elimina marcas, y filtra líneas por marca", async () => {
    responderGet({
      "/marcas": paginado([{ codigo: "HO", nombre: "HONDA" }]),
      "/lineas": paginado([{ linea: "XR 190L", marca: "HO", marca_nombre: "HONDA" }]),
    });
    api.post.mockResolvedValue({ data: { codigo: "KT", nombre: "KTM" } });
    api.delete.mockRejectedValueOnce(new ApiError({ type: "/problemas/conflicto", title: "Conflicto", status: 409, detail: "La marca tiene líneas o motos asociadas." }));
    renderizar(<PaginaCatalogos />);
    await userEvent.click(await screen.findByRole("button", { name: "HONDA" }));
    expect(await screen.findByRole("heading", { name: "Líneas de HONDA" })).toBeInTheDocument();
    await waitFor(() =>
      expect(api.get).toHaveBeenCalledWith("/lineas", expect.objectContaining({ params: expect.objectContaining({ "filter[marca]": "HO" }) })),
    );

    await userEvent.click(screen.getByRole("button", { name: "Nueva marca" }));
    const dialogo = screen.getByRole("dialog", { name: "Nueva marca" });
    await userEvent.type(within(dialogo).getByLabelText(/Código/), "KT");
    await userEvent.type(within(dialogo).getByLabelText(/Nombre/), "KTM");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/marcas", { codigo: "KT", nombre: "KTM" }, expect.anything()));

    await userEvent.click(screen.getByRole("button", { name: "Eliminar marca HONDA" }));
    const confirmar = screen.getByRole("dialog", { name: "Eliminar marca" });
    await userEvent.click(within(confirmar).getByRole("button", { name: "Eliminar" }));
    expect(await within(confirmar).findByRole("alert")).toHaveTextContent("La marca tiene líneas o motos asociadas.");

    await userEvent.click(screen.getByRole("button", { name: "Nueva línea de HONDA" }));
    const linea = screen.getByRole("dialog", { name: "Nueva línea" });
    await userEvent.type(within(linea).getByLabelText(/Nombre de la línea/), "CB 125");
    await userEvent.click(within(linea).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.post).toHaveBeenLastCalledWith("/lineas", { linea: "CB 125", marca: "HO" }, expect.anything()));

    api.delete.mockResolvedValueOnce({});
    await userEvent.click(screen.getByRole("button", { name: "Eliminar línea XR 190L" }));
    await userEvent.click(within(screen.getByRole("dialog", { name: "Eliminar línea" })).getByRole("button", { name: "Eliminar" }));
    await waitFor(() => expect(api.delete).toHaveBeenLastCalledWith("/lineas/XR%20190L"));
  });
});

describe("Usuarios", () => {
  it("crea un usuario y muestra la clave temporal una sola vez", async () => {
    responderGet({ "/usuarios": paginado([USUARIO]) });
    api.post.mockResolvedValueOnce({ data: { ...USUARIO, nip: "600001", nombre: "NUEVO", clave_temporal: "Abc-Clave-Temp-16" } });
    renderizar(<PaginaUsuarios />);
    expect(await screen.findByText("OPERADOR DE PRUEBA")).toBeInTheDocument();
    expect(screen.getByText("Clave temporal")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Nuevo usuario" }));
    const dialogo = screen.getByRole("dialog", { name: "Nuevo usuario" });
    await userEvent.type(within(dialogo).getByLabelText(/Usuario \(documento\)/), "600001");
    await userEvent.type(within(dialogo).getByLabelText(/Nombre completo/), "Nuevo Empleado");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    const clave = await screen.findByRole("dialog", { name: "Clave temporal generada" });
    expect(within(clave).getByText("Abc-Clave-Temp-16")).toBeInTheDocument();
    await userEvent.click(within(clave).getByRole("button", { name: "Ya la anoté" }));
    await waitFor(() => expect(screen.queryByText("Abc-Clave-Temp-16")).not.toBeInTheDocument());
  });

  it("reinicia la clave, desactiva y edita", async () => {
    responderGet({ "/usuarios": paginado([USUARIO]) });
    api.post.mockResolvedValueOnce({ data: { ...USUARIO, clave_temporal: "Nueva-Temp-Clave-1" } });
    api.patch.mockResolvedValue({ data: { ...USUARIO, is_active: false } });
    renderizar(<PaginaUsuarios />);
    await userEvent.click(await screen.findByRole("button", { name: "Reiniciar clave de OPERADOR DE PRUEBA" }));
    await userEvent.click(within(screen.getByRole("dialog", { name: "Reiniciar clave" })).getByRole("button", { name: "Reiniciar clave" }));
    expect(await screen.findByText("Nueva-Temp-Clave-1")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ya la anoté" }));

    await userEvent.click(screen.getByRole("button", { name: "Desactivar a OPERADOR DE PRUEBA" }));
    await userEvent.click(within(screen.getByRole("dialog", { name: "Desactivar usuario" })).getByRole("button", { name: "Desactivar" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/usuarios/900002", { is_active: false }, expect.anything()));

    await userEvent.click(screen.getByRole("button", { name: "Editar OPERADOR DE PRUEBA" }));
    const dialogo = screen.getByRole("dialog", { name: "Editar usuario" });
    await userEvent.selectOptions(within(dialogo).getByLabelText("Rol"), "ingeniero");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.patch).toHaveBeenLastCalledWith("/usuarios/900002", { nombre: "OPERADOR DE PRUEBA", rol: "ingeniero" }, expect.anything()));
  });
});
