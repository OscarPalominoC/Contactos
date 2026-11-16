import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { CampoCumpleanos } from "../components/ui/CampoCumpleanos";

function Controlado({ inicial = { dia: null, mes: null }, ano = 2026, alCambiar = vi.fn() }: {
  inicial?: { dia: number | null; mes: number | null };
  ano?: number;
  alCambiar?: (dia: number | null, mes: number | null) => void;
}) {
  const [v, setV] = useState(inicial);
  return (
    <CampoCumpleanos
      etiqueta="Fecha de cumpleaños"
      dia={v.dia}
      mes={v.mes}
      ano={ano}
      alCambiar={(dia, mes) => {
        alCambiar(dia, mes);
        setV({ dia, mes });
      }}
    />
  );
}

/** Columna (0 = lunes … 6 = domingo) del día con ese nombre accesible. */
function columna(nombre: string): number {
  const celda = screen.getByRole("button", { name: nombre }).closest("td") as HTMLTableCellElement;
  return celda.cellIndex;
}

describe("CampoCumpleanos", () => {
  it("muestra día y mes sin año y no ofrece listas desplegables", async () => {
    render(<Controlado inicial={{ dia: 15, mes: 5 }} />);
    const disparador = screen.getByRole("button", { name: /Fecha de cumpleaños/ });
    expect(disparador).toHaveTextContent("15 de mayo");
    await userEvent.click(disparador);
    const calendario = screen.getByRole("dialog", { name: "Calendario: Fecha de cumpleaños" });
    expect(within(calendario).queryByRole("combobox")).toBeNull();
    expect(within(calendario).queryByText(/2026/)).toBeNull();
    expect(within(calendario).getByRole("grid", { name: "Mayo" })).toBeInTheDocument();
    expect(within(calendario).getByRole("button", { name: "15 de mayo" })).toHaveFocus();
  });

  it("sin valor indica que se elija día y mes y abre en el mes actual", async () => {
    render(<Controlado />);
    expect(screen.getByRole("button", { name: /Fecha de cumpleaños/ })).toHaveTextContent("Seleccione día y mes");
  });

  it("los días de la semana coinciden con el año actual", async () => {
    render(<Controlado inicial={{ dia: 1, mes: 1 }} ano={2026} />);
    await userEvent.click(screen.getByRole("button", { name: /Fecha de cumpleaños/ }));
    expect(columna("1 de enero")).toBe(3); // 1-ene-2026 es jueves
    await userEvent.click(screen.getByRole("button", { name: "Mes siguiente" }));
    expect(columna("1 de febrero")).toBe(6); // 1-feb-2026 es domingo
  });

  it("va solo de enero a diciembre", async () => {
    render(<Controlado inicial={{ dia: 10, mes: 1 }} />);
    await userEvent.click(screen.getByRole("button", { name: /Fecha de cumpleaños/ }));
    expect(screen.getByRole("button", { name: "Mes anterior" })).toBeDisabled();
    for (let i = 0; i < 11; i++) await userEvent.click(screen.getByRole("button", { name: "Mes siguiente" }));
    expect(screen.getByRole("grid", { name: "Diciembre" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mes siguiente" })).toBeDisabled();
  });

  it("el teclado no sale del año: tras el 31 de diciembre se queda en el 31", async () => {
    render(<Controlado inicial={{ dia: 31, mes: 12 }} />);
    await userEvent.click(screen.getByRole("button", { name: /Fecha de cumpleaños/ }));
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("button", { name: "31 de diciembre" })).toHaveFocus();
    await userEvent.keyboard("{PageUp}");
    expect(screen.getByRole("button", { name: "30 de noviembre" })).toHaveFocus();
  });

  it("ofrece el 29 de febrero aunque el año actual no sea bisiesto", async () => {
    render(<Controlado inicial={{ dia: 1, mes: 2 }} ano={2026} />);
    await userEvent.click(screen.getByRole("button", { name: /Fecha de cumpleaños/ }));
    expect(columna("28 de febrero")).toBe(5);
    expect(columna("29 de febrero")).toBe(6);
  });

  it("en año bisiesto el 29 de febrero cae en su día real", async () => {
    render(<Controlado inicial={{ dia: 1, mes: 2 }} ano={2028} />);
    await userEvent.click(screen.getByRole("button", { name: /Fecha de cumpleaños/ }));
    expect(columna("29 de febrero")).toBe(1); // 29-feb-2028 es martes
  });

  it("elegir un día entrega día y mes y cierra; Limpiar los quita", async () => {
    const alCambiar = vi.fn();
    render(<Controlado inicial={{ dia: 15, mes: 5 }} alCambiar={alCambiar} />);
    const disparador = screen.getByRole("button", { name: /Fecha de cumpleaños/ });
    await userEvent.click(disparador);
    await userEvent.click(screen.getByRole("button", { name: "Mes siguiente" }));
    await userEvent.click(screen.getByRole("button", { name: "3 de junio" }));
    expect(alCambiar).toHaveBeenLastCalledWith(3, 6);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(disparador).toHaveFocus();
    expect(disparador).toHaveTextContent("3 de junio");
    await userEvent.click(disparador);
    await userEvent.click(screen.getByRole("button", { name: "Limpiar" }));
    expect(alCambiar).toHaveBeenLastCalledWith(null, null);
    expect(disparador).toHaveTextContent("Seleccione día y mes");
  });

  it("Escape cierra y devuelve el foco", async () => {
    render(<Controlado inicial={{ dia: 15, mes: 5 }} />);
    const disparador = screen.getByRole("button", { name: /Fecha de cumpleaños/ });
    await userEvent.click(disparador);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(disparador).toHaveFocus();
  });
});
