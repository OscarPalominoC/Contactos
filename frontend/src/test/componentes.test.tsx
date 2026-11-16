import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { Aviso, AvisoError } from "../components/ui/Aviso";
import { Boton } from "../components/ui/Boton";
import { CampoAreaTexto, CampoSeleccion, CampoTexto } from "../components/ui/Campos";
import { Confirmacion, Dialogo } from "../components/ui/Dialogo";
import { EstadoVacio } from "../components/ui/EstadoVacio";
import { InsigniaContacto, InsigniaDocumento, InsigniaLlamada } from "../components/ui/Insignias";
import { Detalles, EncabezadoPagina, Tarjeta } from "../components/ui/Pagina";
import { TablaPaginada } from "../components/ui/TablaPaginada";
import { ApiError } from "../services/apiClient";
import { evaluarClave, nivelFortaleza } from "../features/auth/PaginaCambioClave";
import { erroresZod, nulo } from "../features/formulario";
import { formularioContactoSchema, cuerpoContacto } from "../features/contactos/esquemas";
import { paginado, renderizar } from "./utilidades";

describe("Boton", () => {
  it("se deshabilita y anuncia carga para evitar doble envío", async () => {
    const clic = vi.fn();
    const { rerender } = renderizar(<Boton onClick={clic}>Guardar</Boton>);
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));
    expect(clic).toHaveBeenCalledOnce();
    rerender(
      <Boton onClick={clic} cargando textoCargando="Guardando…">
        Guardar
      </Boton>,
    );
    const boton = screen.getByRole("button", { name: "Guardando…" });
    expect(boton).toBeDisabled();
    expect(boton).toHaveAttribute("aria-busy", "true");
    await userEvent.click(boton);
    expect(clic).toHaveBeenCalledOnce();
  });
});

describe("Campos", () => {
  it("vincula etiqueta, error y ayuda con aria-describedby", () => {
    renderizar(
      <>
        <CampoTexto etiqueta="Correo" error="Correo inválido." obligatorio />
        <CampoTexto etiqueta="Placa" ayuda="Ejemplo ABC12D" />
        <CampoSeleccion etiqueta="Estado" opciones={[{ valor: "a", texto: "A" }]} vacio="Todos" error="Elija uno" />
        <CampoAreaTexto etiqueta="Observación" ayuda="Opcional" />
      </>,
    );
    const correo = screen.getByLabelText(/Correo/);
    expect(correo).toHaveAttribute("aria-invalid", "true");
    expect(correo).toBeRequired();
    expect(correo).toHaveAccessibleDescription(/Correo inválido/);
    expect(screen.getByLabelText("Placa")).toHaveAccessibleDescription("Ejemplo ABC12D");
    expect(screen.getByLabelText("Estado")).toHaveAccessibleDescription(/Elija uno/);
    expect(screen.getByLabelText("Observación")).toHaveAccessibleDescription("Opcional");
  });
});

describe("Avisos e insignias", () => {
  it("usa role alert para errores e incluye el código de soporte", () => {
    const error = new ApiError({ type: "x", title: "t", status: 500, detail: "Falló", request_id: "rid-123" });
    renderizar(
      <>
        <AvisoError error={error} />
        <AvisoError error={null} />
        <Aviso tipo="exito">Listo</Aviso>
      </>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Falló");
    expect(screen.getByRole("alert")).toHaveTextContent("rid-123");
    expect(screen.getByRole("status")).toHaveTextContent("Listo");
  });

  it("muestra estados con texto además de color", () => {
    renderizar(
      <>
        <InsigniaDocumento estado="VENCIDO" />
        <InsigniaDocumento estado="NO" />
        <InsigniaLlamada estado="no_realizada" />
        <InsigniaContacto estado="inhabilitado" />
        <InsigniaContacto estado="habilitado" />
      </>,
    );
    for (const texto of ["Vencido", "No (legado)", "No realizada", "Inhabilitado", "Habilitado"]) {
      expect(screen.getByText(texto)).toBeInTheDocument();
    }
  });

  it("estado vacío, encabezado, tarjeta y detalles", () => {
    renderizar(
      <>
        <EncabezadoPagina titulo="Contactos" descripcion="Clientes" acciones={<button>Nuevo</button>} />
        <Tarjeta titulo="Datos">
          <Detalles items={[{ termino: "Celular", valor: "300" }]} />
        </Tarjeta>
        <EstadoVacio titulo="Sin datos" descripcion="Nada aún" accion={<span>ícono</span>} />
      </>,
    );
    expect(screen.getByRole("heading", { level: 1, name: "Contactos" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Datos" })).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Sin datos");
  });
});

describe("Dialogo", () => {
  function Prueba() {
    const [abierto, setAbierto] = useState(false);
    return (
      <>
        <button onClick={() => setAbierto(true)}>Abrir</button>
        <Dialogo abierto={abierto} titulo="Editar" alCerrar={() => setAbierto(false)} pie={<span>pie</span>}>
          <input aria-label="Nombre" />
        </Dialogo>
      </>
    );
  }

  it("abre con título accesible, cierra con Esc y devuelve el foco", async () => {
    renderizar(<Prueba />);
    const abrir = screen.getByRole("button", { name: "Abrir" });
    await userEvent.click(abrir);
    const dialogo = screen.getByRole("dialog", { name: "Editar" });
    expect(dialogo).toHaveAttribute("open");
    act(() => {
      dialogo.dispatchEvent(new Event("cancel", { cancelable: true }));
    });
    await waitFor(() => expect(dialogo).not.toHaveAttribute("open"));
    expect(abrir).toHaveFocus();
  });

  it("confirmación con botón de cancelar y confirmar", async () => {
    const confirmar = vi.fn();
    const cerrar = vi.fn();
    renderizar(
      <Confirmacion abierto titulo="Anular" mensaje="¿Seguro?" textoConfirmar="Anular" alConfirmar={confirmar} alCerrar={cerrar} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Anular" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(confirmar).toHaveBeenCalledOnce();
    expect(cerrar).toHaveBeenCalledOnce();
  });
});

describe("TablaPaginada", () => {
  const columnas = [
    { clave: "n", titulo: "Nombre", celda: (f: { n: string }) => f.n, ordenable: "nombre" },
    { clave: "x", titulo: "Otra", celda: () => "x" },
  ];

  it("muestra carga, vacío y error", () => {
    const base = { titulo: "Contactos", columnas, claveFila: (f: { n: string }) => f.n, pagina: 1, alCambiarPagina: vi.fn() };
    const { rerender } = renderizar(<TablaPaginada {...base} datos={undefined} cargando error={null} />);
    expect(screen.getByRole("status")).toHaveTextContent("Cargando contactos");
    rerender(<TablaPaginada {...base} datos={paginado([])} cargando={false} error={null} />);
    expect(screen.getByRole("status")).toHaveTextContent("No hay contactos para mostrar");
    rerender(
      <TablaPaginada
        {...base}
        datos={undefined}
        cargando={false}
        error={new ApiError({ type: "x", title: "t", status: 500, detail: "Error del servidor" })}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Error del servidor");
  });

  it("pagina y ordena", async () => {
    const alCambiarPagina = vi.fn();
    const alOrdenar = vi.fn();
    const datos = { ...paginado([{ n: "ANA" }, { n: "LUIS" }], 60), meta: { page: { number: 2, size: 25, total: 60, total_pages: 3 } } };
    const { rerender } = renderizar(
      <TablaPaginada
        titulo="Contactos"
        columnas={columnas}
        datos={datos}
        cargando={false}
        error={null}
        claveFila={(f) => f.n}
        pagina={2}
        alCambiarPagina={alCambiarPagina}
        orden="nombre"
        alOrdenar={alOrdenar}
      />,
    );
    expect(screen.getByRole("columnheader", { name: /Nombre/ })).toHaveAttribute("aria-sort", "ascending");
    expect(screen.getByText(/60 registros · página 2 de 3/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Siguiente" }));
    await userEvent.click(screen.getByRole("button", { name: "Anterior" }));
    expect(alCambiarPagina).toHaveBeenNthCalledWith(1, 3);
    expect(alCambiarPagina).toHaveBeenNthCalledWith(2, 1);
    await userEvent.click(screen.getByRole("button", { name: /Nombre/ }));
    expect(alOrdenar).toHaveBeenCalledWith("-nombre");
    rerender(
      <TablaPaginada
        titulo="Contactos"
        columnas={columnas}
        datos={datos}
        cargando={false}
        error={null}
        claveFila={(f) => f.n}
        pagina={2}
        alCambiarPagina={alCambiarPagina}
        orden="-nombre"
        alOrdenar={alOrdenar}
      />,
    );
    expect(screen.getByRole("columnheader", { name: /Nombre/ })).toHaveAttribute("aria-sort", "descending");
    await userEvent.click(screen.getByRole("button", { name: /Nombre/ }));
    expect(alOrdenar).toHaveBeenLastCalledWith("nombre");
  });
});

describe("Reglas de la nueva clave", () => {
  it("solo exige 5 caracteres y que la confirmación coincida (puede incluir nombre o documento)", () => {
    expect(evaluarClave("abcd", "").map((r) => r.cumple)).toEqual([false, false]);
    expect(evaluarClave("perez", "perez").every((r) => r.cumple)).toBe(true);
    expect(evaluarClave("900001", "900001").every((r) => r.cumple)).toBe(true);
    expect(evaluarClave("Moto1", "Moto2")[1]?.cumple).toBe(false);
    expect(evaluarClave("Moto1", "")[0]?.texto).toBe("Al menos 5 caracteres");
  });

  it("califica la fortaleza", () => {
    expect(nivelFortaleza("").texto).toBe("Muy débil");
    expect(nivelFortaleza("Moto-Roja-2026-Larga!").valor).toBe(5);
  });
});

describe("Esquemas de formulario", () => {
  it("normaliza y valida el contacto", () => {
    const valido = formularioContactoSchema.parse({
      nip: " 1 234 567 ",
      nombre: "Ana",
      telefono: "",
      celular: "300 123 4567",
      correo: "",
      direccion: "",
      dia_nac: "15",
      mes_nac: "5",
      estado: "habilitado",
      contactar_cumpleanos: true,
      contactar_soat: true,
      contactar_rtm: false,
    });
    expect(valido.nip).toBe("1234567");
    expect(cuerpoContacto(valido, false)).toMatchObject({ nip: "1234567", dia_nac: 15, mes_nac: 5, contactar_rtm: false });
    const febrero = formularioContactoSchema.safeParse({ ...valido, dia_nac: "31", mes_nac: "2" });
    expect(febrero.success).toBe(false);
    expect(cuerpoContacto({ ...valido, dia_nac: "", mes_nac: "" }, true)).not.toHaveProperty("nip");
    const invalido = formularioContactoSchema.safeParse({ ...valido, correo: "no", dia_nac: "40", nombre: "a" });
    expect(invalido.success).toBe(false);
    if (!invalido.success) {
      expect(Object.keys(erroresZod(invalido.error)).sort()).toEqual(["correo", "dia_nac", "nombre"]);
    }
  });

  it("convierte vacío en null", () => {
    expect(nulo("")).toBeNull();
    expect(nulo("2026-01-01")).toBe("2026-01-01");
  });
});
