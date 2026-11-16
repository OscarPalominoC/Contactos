import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PaginaContactos } from "../features/contactos/PaginaContactos";
import { contactoSchema } from "../services/esquemas";
import { CONTACTO, paginado, renderizar, YO_ADMIN } from "./utilidades";

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock("../services/apiClient", async (original) => ({
  ...(await original<typeof import("../services/apiClient")>()),
  apiClient: api,
}));
vi.mock("../app/sesion", () => ({
  useSesion: () => ({ usuario: YO_ADMIN, estado: "autenticado", puede: (p: string) => YO_ADMIN.permisos.includes(p) }),
}));

const SIN_SOAT = { ...CONTACTO, nip: "2000000002", nombre: "SIN SOAT", contactar_soat: false };
const FEBRERO_31 = { ...CONTACTO, nip: "3000000003", nombre: "FEBRERO TREINTA", dia_nac: 31, mes_nac: 2, contactar_cumpleanos: false };

beforeEach(() => {
  for (const f of Object.values(api)) f.mockReset();
  api.get.mockResolvedValue({ data: paginado([CONTACTO, SIN_SOAT, FEBRERO_31]) });
  api.patch.mockImplementation(async (_ruta: string, cuerpo: Record<string, unknown>) => ({ data: { ...CONTACTO, ...cuerpo } }));
  api.post.mockImplementation(async (_ruta: string, cuerpo: Record<string, unknown>) => ({ data: { ...CONTACTO, ...cuerpo } }));
});

function ultimoCuerpo(metodo: typeof api.patch): Record<string, unknown> {
  return metodo.mock.calls.at(-1)?.[1] as Record<string, unknown>;
}

/** La página de contactos es solo de búsqueda: se escribe un texto para que aparezcan resultados. */
async function renderizarConBusqueda() {
  renderizar(<PaginaContactos />);
  await userEvent.type(screen.getByLabelText("Buscar por documento o nombre"), "cliente");
}

async function editar(nombre: string) {
  await userEvent.click(await screen.findByRole("button", { name: `Editar ${nombre}` }));
  return screen.getByRole("dialog", { name: "Editar contacto" });
}

describe("Esquema de contacto", () => {
  it("exige los tres campos de consentimiento", () => {
    expect(contactoSchema.safeParse(CONTACTO).success).toBe(true);
    const sinCampo: Record<string, unknown> = { ...CONTACTO };
    delete sinCampo.contactar_soat;
    expect(contactoSchema.safeParse(sinCampo).success).toBe(false);
  });
});

describe("Contactos: preferencias de contacto", () => {
  it("filtra la lista por canal autorizado o no autorizado", async () => {
    await renderizarConBusqueda();
    await screen.findByText("SIN SOAT");
    const filtro = screen.getByLabelText("Canal de contacto");
    await userEvent.selectOptions(filtro, "contactar_soat:false");
    await waitFor(() =>
      expect(api.get).toHaveBeenLastCalledWith("/contactos", expect.objectContaining({ params: expect.objectContaining({ "filter[contactar_soat]": "false" }) })),
    );
    await userEvent.selectOptions(filtro, "contactar_rtm:true");
    await waitFor(() => {
      const params = (api.get.mock.calls.at(-1)?.[1] as { params: Record<string, unknown> }).params;
      expect(params["filter[contactar_rtm]"]).toBe("true");
      expect(params["filter[contactar_soat]"]).toBeUndefined();
    });
  });

  it("muestra insignias con texto e icono de los canales autorizados por cliente", async () => {
    await renderizarConBusqueda();
    const fila = (await screen.findByText("SIN SOAT")).closest("tr") as HTMLElement;
    const canales = within(fila).getByRole("list", { name: "Canales autorizados" });
    const items = within(canales).getAllByRole("listitem");
    expect(items.map((i) => i.textContent)).toEqual(["Cumpleaños: autorizado", "SOAT: no autorizado", "RTM: autorizado"]);
  });

  it("el checkbox maestro alterna los tres canales a la vez", async () => {
    await renderizarConBusqueda();
    const dialogo = await editar("CLIENTE DE PRUEBA");
    const grupo = within(dialogo).getByRole("group", { name: "Preferencias de contacto" });
    const maestro = within(grupo).getByRole("checkbox", { name: "Seleccionar todos los canales" });
    const individuales = ["Cumpleaños", "SOAT", "RTM"].map((n) => within(grupo).getByRole("checkbox", { name: n }));
    expect(maestro).toBeChecked();
    individuales.forEach((c) => expect(c).toBeChecked());

    await userEvent.click(maestro);
    individuales.forEach((c) => expect(c).not.toBeChecked());
    expect(maestro).not.toBeChecked();

    await userEvent.click(individuales[1] as HTMLElement);
    expect(maestro).not.toBeChecked();
    expect((maestro as HTMLInputElement).indeterminate).toBe(true);

    await userEvent.click(maestro);
    individuales.forEach((c) => expect(c).toBeChecked());
    expect((maestro as HTMLInputElement).indeterminate).toBe(false);

    await userEvent.click(individuales[2] as HTMLElement);
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    expect(ultimoCuerpo(api.patch)).toMatchObject({ contactar_cumpleanos: true, contactar_soat: true, contactar_rtm: false });
  });

  it("un contacto nuevo acepta los tres canales por defecto", async () => {
    await renderizarConBusqueda();
    await userEvent.click(await screen.findByRole("button", { name: "Nuevo contacto" }));
    const dialogo = screen.getByRole("dialog", { name: "Nuevo contacto" });
    expect(within(dialogo).getByRole("checkbox", { name: "Seleccionar todos los canales" })).toBeChecked();
    await userEvent.type(within(dialogo).getByLabelText(/Documento/), "7654321");
    await userEvent.type(within(dialogo).getByLabelText(/Nombre completo/), "Nueva Persona");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.post).toHaveBeenCalled());
    expect(ultimoCuerpo(api.post)).toMatchObject({ contactar_cumpleanos: true, contactar_soat: true, contactar_rtm: true });
  });

  it("la fecha de cumpleaños se elige con un calendario de día y mes, sin listas desplegables", async () => {
    await renderizarConBusqueda();
    const dialogo = await editar("CLIENTE DE PRUEBA");
    expect(within(dialogo).queryByLabelText("Día de nacimiento")).toBeNull();
    expect(within(dialogo).queryByLabelText("Mes de nacimiento")).toBeNull();
    const campo = within(dialogo).getByRole("button", { name: /Fecha de cumpleaños/ });
    expect(campo).toHaveTextContent("15 de mayo");
    await userEvent.click(campo);
    await userEvent.click(within(dialogo).getByRole("button", { name: "Mes siguiente" }));
    await userEvent.click(within(dialogo).getByRole("button", { name: "20 de junio" }));
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    expect(ultimoCuerpo(api.patch)).toMatchObject({ dia_nac: 20, mes_nac: 6 });
  });

  it("alerta un cumpleaños inexistente (31 de febrero) y permite rectificarlo y reactivar el canal", async () => {
    await renderizarConBusqueda();
    const dialogo = await editar("FEBRERO TREINTA");
    expect(within(dialogo).getByRole("alert")).toHaveTextContent(/31 de febrero/);
    const campo = within(dialogo).getByRole("button", { name: /Fecha de cumpleaños/ });
    expect(campo).toHaveTextContent("Seleccione día y mes");
    const cumple = within(dialogo).getByRole("checkbox", { name: "Cumpleaños" });
    expect(cumple).not.toBeChecked();
    expect(cumple).toBeDisabled();

    await userEvent.click(campo);
    while (!within(dialogo).queryByRole("grid", { name: "Febrero" })) {
      const anterior = within(dialogo).getByRole("button", { name: "Mes anterior" });
      const siguiente = within(dialogo).getByRole("button", { name: "Mes siguiente" });
      const actual = within(dialogo).getByRole("grid").getAttribute("aria-label");
      await userEvent.click(actual === "Enero" ? siguiente : anterior);
    }
    await userEvent.click(within(dialogo).getByRole("button", { name: "28 de febrero" }));
    expect(cumple).toBeEnabled();
    await userEvent.click(cumple);
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    expect(ultimoCuerpo(api.patch)).toMatchObject({ dia_nac: 28, mes_nac: 2, contactar_cumpleanos: true });
  });

  it("guardar sin rectificar envía el cumpleaños vacío y el canal apagado", async () => {
    await renderizarConBusqueda();
    const dialogo = await editar("FEBRERO TREINTA");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    expect(ultimoCuerpo(api.patch)).toMatchObject({ dia_nac: null, mes_nac: null, contactar_cumpleanos: false });
  });

  it("combina el filtro de canal con la búsqueda y el mes", async () => {
    await renderizarConBusqueda();
    await screen.findByText("SIN SOAT");
    await userEvent.selectOptions(screen.getByLabelText("Canal de contacto"), "contactar_cumpleanos:true");
    await userEvent.selectOptions(screen.getByLabelText("Mes de cumpleaños"), "2");
    await userEvent.type(screen.getByLabelText("Buscar por documento o nombre"), "ana");
    await waitFor(() =>
      expect(api.get).toHaveBeenLastCalledWith(
        "/contactos",
        expect.objectContaining({ params: expect.objectContaining({ "filter[contactar_cumpleanos]": "true", "filter[mes_nac]": "2", "filter[q]": "clienteana" }) }),
      ),
    );
  });

  it("limpiar el cumpleaños quita día y mes juntos", async () => {
    await renderizarConBusqueda();
    const dialogo = await editar("CLIENTE DE PRUEBA");
    await userEvent.click(within(dialogo).getByRole("button", { name: /Fecha de cumpleaños/ }));
    await userEvent.click(within(dialogo).getByRole("button", { name: "Limpiar" }));
    await userEvent.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await waitFor(() => expect(api.patch).toHaveBeenCalled());
    expect(ultimoCuerpo(api.patch)).toMatchObject({ dia_nac: null, mes_nac: null });
  });
});
