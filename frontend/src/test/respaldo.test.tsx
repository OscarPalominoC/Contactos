import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TarjetaRespaldo } from "../features/tablero/TarjetaRespaldo";
import * as recursos from "../services/recursos";

vi.mock("../services/recursos");

function renderizar() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TarjetaRespaldo />
    </QueryClientProvider>,
  );
}

describe("TarjetaRespaldo", () => {
  const estadoBase = {
    es_servidor_local: true,
    ruta_configurada: "F:\\Check\\respaldos",
    ejecutando: false,
    ultimo_respaldo: {
      archivo: "check_contactos-15-11-2026.sql",
      tamano_bytes: 18031564,
      tamano_formateado: "17.2 MB",
      creado_en: "2026-11-15T14:30:00-05:00",
    },
    total_respaldos: 3,
    ultimo_resultado: "Listo para respaldar",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("en dispositivo remoto NO muestra ningún botón ni tarjeta en el DOM", async () => {
    vi.mocked(recursos.obtener).mockImplementation((url: string) => {
      if (url === "/respaldos/es-servidor") {
        return Promise.resolve({ es_servidor: false });
      }
      return Promise.resolve(estadoBase);
    });

    const { container } = renderizar();

    // Esperar a que se procese la consulta
    await new Promise((r) => setTimeout(r, 50));

    expect(screen.queryByRole("heading", { name: /copia de seguridad/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /copia|respaldo/i })).not.toBeInTheDocument();
    expect(container.firstChild).toBeNull();
  });

  it("en el servidor local muestra la tarjeta completa, campo de ruta y botón .sql", async () => {
    vi.mocked(recursos.obtener).mockImplementation((url: string) => {
      if (url === "/respaldos/es-servidor") {
        return Promise.resolve({ es_servidor: true });
      }
      return Promise.resolve(estadoBase);
    });

    renderizar();

    expect(await screen.findByText("check_contactos-15-11-2026.sql")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /copia de seguridad de la base de datos/i })).toBeInTheDocument();
    expect(screen.getByText("Conectado en el servidor")).toBeInTheDocument();
    expect(screen.getByText(/17.2 MB/)).toBeInTheDocument();
    expect(await screen.findByDisplayValue("F:\\Check\\respaldos")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /validar ruta/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /guardar ruta/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /generar copia de seguridad en servidor \(\.sql\)/i })).toBeInTheDocument();
  });

  it("permite validar la ruta en el servidor local", async () => {
    const user = userEvent.setup();
    vi.mocked(recursos.obtener).mockImplementation((url: string) => {
      if (url === "/respaldos/es-servidor") {
        return Promise.resolve({ es_servidor: true });
      }
      return Promise.resolve(estadoBase);
    });
    vi.mocked(recursos.crear).mockResolvedValueOnce({
      valida: true,
      ruta: "D:\\NuevosRespaldos",
      mensaje: "Ruta válida y con permisos de escritura.",
    });

    renderizar();

    const input = await screen.findByDisplayValue("F:\\Check\\respaldos");
    await user.clear(input);
    await user.type(input, "D:\\NuevosRespaldos");

    const botonValidar = screen.getByRole("button", { name: /validar ruta/i });
    await user.click(botonValidar);

    expect(recursos.crear).toHaveBeenCalledWith(
      "/respaldos/validar-ruta",
      expect.anything(),
      { ruta: "D:\\NuevosRespaldos" },
    );
    expect(await screen.findByText("Ruta válida y con permisos de escritura.")).toBeInTheDocument();
  });

  it("permite guardar la nueva ruta en el servidor local", async () => {
    const user = userEvent.setup();
    vi.mocked(recursos.obtener).mockImplementation((url: string) => {
      if (url === "/respaldos/es-servidor") {
        return Promise.resolve({ es_servidor: true });
      }
      return Promise.resolve(estadoBase);
    });
    vi.mocked(recursos.crear).mockResolvedValueOnce({
      ruta_configurada: "D:\\NuevosRespaldos",
      mensaje: "Ruta configurada con éxito.",
    });

    renderizar();

    const input = await screen.findByDisplayValue("F:\\Check\\respaldos");
    await user.clear(input);
    await user.type(input, "D:\\NuevosRespaldos");

    const botonGuardar = screen.getByRole("button", { name: /guardar ruta/i });
    await user.click(botonGuardar);

    expect(recursos.crear).toHaveBeenCalledWith(
      "/respaldos/configurar-ruta",
      expect.anything(),
      { ruta: "D:\\NuevosRespaldos" },
    );
    expect(await screen.findByText("Ruta guardada correctamente en el servidor.")).toBeInTheDocument();
  });

  it("ejecuta el respaldo .sql por consola en el servidor al hacer clic en el botón", async () => {
    const user = userEvent.setup();
    vi.mocked(recursos.obtener).mockImplementation((url: string) => {
      if (url === "/respaldos/es-servidor") {
        return Promise.resolve({ es_servidor: true });
      }
      return Promise.resolve(estadoBase);
    });
    vi.mocked(recursos.crear).mockResolvedValueOnce({
      mensaje: "Copia de seguridad iniciada por consola en el servidor.",
      ruta_destino: "F:\\Check\\respaldos",
      iniciado_en: "2026-11-15T13:00:00-05:00",
    });

    renderizar();

    const botonEjecutar = await screen.findByRole("button", { name: /generar copia de seguridad en servidor \(\.sql\)/i });
    await user.click(botonEjecutar);

    expect(recursos.crear).toHaveBeenCalledWith(
      "/respaldos/ejecutar",
      expect.anything(),
      {},
    );
    expect(await screen.findByText("Copia de seguridad iniciada por consola en el servidor.")).toBeInTheDocument();
  });
});
