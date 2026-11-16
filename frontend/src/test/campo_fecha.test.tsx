import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { CampoFecha } from "../components/ui/CampoFecha";
import { SelectorRangoFechas } from "../components/ui/SelectorRangoFechas";
import { renderizar } from "./utilidades";

function abrir(nombre: RegExp) {
  return userEvent.click(screen.getByRole("button", { name: nombre }));
}

describe("CampoFecha", () => {
  it("muestra la fecha formateada en español y un texto guía cuando está vacía", () => {
    const { rerender } = renderizar(<CampoFecha etiqueta="Fecha" valor="2026-11-14" alCambiar={() => {}} />);
    expect(screen.getByRole("button", { name: /Fecha/ })).toHaveTextContent("14 de noviembre de 2026");
    rerender(<CampoFecha etiqueta="Fecha" valor="" alCambiar={() => {}} />);
    expect(screen.getByRole("button", { name: /Fecha/ })).toHaveTextContent("Seleccione una fecha");
  });

  it("al hacer clic abre el calendario con la cuadrícula del mes", async () => {
    renderizar(<CampoFecha etiqueta="Fecha" valor="2026-02-10" alCambiar={() => {}} />);
    await abrir(/Fecha/);
    const dialogo = screen.getByRole("dialog", { name: /Fecha/ });
    const cuadricula = within(dialogo).getByRole("grid");
    // Febrero de 2026 tiene 28 días: nunca se ofrece el 29, 30 ni 31.
    expect(within(cuadricula).getAllByRole("gridcell").filter((c) => c.querySelector("button"))).toHaveLength(28);
    expect(within(cuadricula).queryByRole("button", { name: /31 de febrero/ })).toBeNull();
    expect(within(cuadricula).getByRole("button", { name: "10 de febrero de 2026" })).toHaveAttribute("aria-pressed", "true");
  });

  it("navega meses y permite elegir mes y año directamente", async () => {
    renderizar(<CampoFecha etiqueta="Fecha" valor="2026-01-15" alCambiar={() => {}} />);
    await abrir(/Fecha/);
    await userEvent.click(screen.getByRole("button", { name: "Mes anterior" }));
    expect(screen.getByLabelText("Mes")).toHaveValue("11");
    expect(screen.getByLabelText("Año")).toHaveValue("2025");
    await userEvent.click(screen.getByRole("button", { name: "Mes siguiente" }));
    await userEvent.click(screen.getByRole("button", { name: "Mes siguiente" }));
    expect(screen.getByLabelText("Mes")).toHaveValue("1");
    await userEvent.selectOptions(screen.getByLabelText("Año"), "2030");
    await userEvent.selectOptions(screen.getByLabelText("Mes"), "6");
    expect(screen.getByRole("button", { name: "1 de julio de 2030" })).toBeInTheDocument();
  });

  it("seleccionar un día dispara onChange en formato AAAA-MM-DD y cierra", async () => {
    const alCambiar = vi.fn();
    renderizar(<CampoFecha etiqueta="Fecha" valor="2026-11-14" alCambiar={alCambiar} />);
    await abrir(/Fecha/);
    await userEvent.click(screen.getByRole("button", { name: "3 de noviembre de 2026" }));
    expect(alCambiar).toHaveBeenCalledWith("2026-11-03");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("se cierra con Escape devolviendo el foco y también con clic fuera", async () => {
    renderizar(
      <>
        <CampoFecha etiqueta="Fecha" valor="2026-11-14" alCambiar={() => {}} />
        <p>Afuera</p>
      </>,
    );
    const disparador = screen.getByRole("button", { name: /Fecha/ });
    await userEvent.click(disparador);
    expect(screen.getByRole("button", { name: "14 de noviembre de 2026" })).toHaveFocus();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(disparador).toHaveFocus();
    await userEvent.click(disparador);
    await userEvent.click(screen.getByText("Afuera"));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("se opera con flechas, Inicio/Fin, RePág/AvPág y Enter", async () => {
    const alCambiar = vi.fn();
    renderizar(<CampoFecha etiqueta="Fecha" valor="2026-11-14" alCambiar={alCambiar} />);
    await abrir(/Fecha/);
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("button", { name: "15 de noviembre de 2026" })).toHaveFocus();
    await userEvent.keyboard("{ArrowDown}");
    expect(screen.getByRole("button", { name: "22 de noviembre de 2026" })).toHaveFocus();
    await userEvent.keyboard("{ArrowUp}{ArrowLeft}");
    expect(screen.getByRole("button", { name: "14 de noviembre de 2026" })).toHaveFocus();
    await userEvent.keyboard("{Home}");
    expect(screen.getByRole("button", { name: "9 de noviembre de 2026" })).toHaveFocus();
    await userEvent.keyboard("{End}");
    expect(screen.getByRole("button", { name: "15 de noviembre de 2026" })).toHaveFocus();
    await userEvent.keyboard("{PageDown}");
    expect(screen.getByRole("button", { name: "15 de diciembre de 2026" })).toHaveFocus();
    await userEvent.keyboard("{PageUp}{PageUp}");
    expect(screen.getByRole("button", { name: "15 de octubre de 2026" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(alCambiar).toHaveBeenCalledWith("2026-10-15");
  });

  it("respeta mínimo y máximo, y permite limpiar o elegir hoy", async () => {
    const alCambiar = vi.fn();
    renderizar(<CampoFecha etiqueta="Fecha" valor="2026-11-14" min="2026-11-10" max="2026-11-20" alCambiar={alCambiar} />);
    await abrir(/Fecha/);
    expect(screen.getByRole("button", { name: "9 de noviembre de 2026" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "21 de noviembre de 2026" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "9 de noviembre de 2026" }));
    expect(alCambiar).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Limpiar" }));
    expect(alCambiar).toHaveBeenCalledWith("");
  });

  it("botón Hoy selecciona la fecha de Bogotá", async () => {
    const alCambiar = vi.fn();
    renderizar(<CampoFecha etiqueta="Fecha" valor="" alCambiar={alCambiar} hoy="2026-11-14" />);
    await abrir(/Fecha/);
    await userEvent.click(screen.getByRole("button", { name: "Hoy" }));
    expect(alCambiar).toHaveBeenCalledWith("2026-11-14");
  });

  it("asocia error y ayuda al disparador y cumple área táctil mínima", () => {
    renderizar(<CampoFecha etiqueta="Fecha" valor="" alCambiar={() => {}} error="Elija una fecha." ayuda="Opcional" obligatorio />);
    const boton = screen.getByRole("button", { name: /Fecha/ });
    expect(boton).toHaveAccessibleDescription(/Elija una fecha/);
    expect(boton).toHaveAttribute("aria-invalid", "true");
    expect(boton.className).toContain("min-h-[44px]");
  });
});

describe("SelectorRangoFechas", () => {
  function Prueba({ alCambiar }: { alCambiar: (r: { desde: string; hasta: string }) => void }) {
    const [rango, setRango] = useState({ desde: "2026-11-10", hasta: "2026-11-20" });
    return (
      <SelectorRangoFechas
        desde={rango.desde}
        hasta={rango.hasta}
        alCambiar={(r) => {
          setRango(r);
          alCambiar(r);
        }}
      />
    );
  }

  it("no permite un 'Desde' posterior a 'Hasta' ni viceversa", async () => {
    renderizar(<Prueba alCambiar={() => {}} />);
    expect(screen.getByRole("group", { name: "Rango de fechas" })).toBeInTheDocument();
    await abrir(/^Desde/);
    expect(screen.getByRole("button", { name: "21 de noviembre de 2026" })).toBeDisabled();
    await userEvent.keyboard("{Escape}");
    await abrir(/^Hasta/);
    expect(screen.getByRole("button", { name: "9 de noviembre de 2026" })).toBeDisabled();
  });

  it("cambia cada extremo y limpia el filtro", async () => {
    const alCambiar = vi.fn();
    renderizar(<Prueba alCambiar={alCambiar} />);
    await abrir(/^Desde/);
    await userEvent.click(screen.getByRole("button", { name: "12 de noviembre de 2026" }));
    expect(alCambiar).toHaveBeenLastCalledWith({ desde: "2026-11-12", hasta: "2026-11-20" });
    await abrir(/^Hasta/);
    await userEvent.click(screen.getByRole("button", { name: "18 de noviembre de 2026" }));
    expect(alCambiar).toHaveBeenLastCalledWith({ desde: "2026-11-12", hasta: "2026-11-18" });
    await userEvent.click(screen.getByRole("button", { name: "Limpiar fechas" }));
    expect(alCambiar).toHaveBeenLastCalledWith({ desde: "", hasta: "" });
    expect(screen.queryByRole("button", { name: "Limpiar fechas" })).toBeNull();
  });
});
