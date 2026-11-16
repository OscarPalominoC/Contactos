import { describe, expect, it } from "vitest";

import {
  cumpleanos,
  enmascararDocumento,
  formatearCop,
  formatearDocumento,
  formatearFecha,
  formatearFechaHora,
  formatearNumero,
  formatearTelefono,
  hoyBogota,
  nombreMes,
  normalizarPlaca,
  sumarDias,
} from "../utils/formatters";

describe("formateadores", () => {
  it("formatea fechas ISO como dd/mm/aaaa", () => {
    expect(formatearFecha("2027-03-15")).toBe("15/03/2027");
    expect(formatearFecha("2026-11-06T10:00:00Z")).toBe("06/11/2026");
  });

  it("devuelve guion largo para fechas vacías o inválidas", () => {
    expect(formatearFecha(null)).toBe("—");
    expect(formatearFecha("")).toBe("—");
    expect(formatearFecha("basura")).toBe("—");
    expect(formatearFechaHora(undefined)).toBe("—");
    expect(formatearFechaHora("no-es-fecha")).toBe("—");
  });

  it("muestra la hora en zona de Bogotá", () => {
    // 2026-11-07 15:30 UTC = 10:30 a. m. en Bogotá (UTC-5)
    const texto = formatearFechaHora("2026-11-07T15:30:00Z");
    expect(texto).toContain("07/11/2026");
    expect(texto).toMatch(/10:30/);
  });

  it("formatea moneda y números", () => {
    expect(formatearCop(67000).replace(/\s/g, " ")).toContain("67.000");
    expect(formatearCop(null)).toBe("—");
    expect(formatearNumero(220992)).toBe("220.992");
    expect(formatearNumero(undefined)).toBe("—");
  });

  it("formatea y enmascara documentos", () => {
    expect(formatearDocumento("1096223757")).toBe("1.096.223.757");
    expect(formatearDocumento("ABC-12")).toBe("ABC-12");
    expect(formatearDocumento(null)).toBe("—");
    expect(enmascararDocumento("1096223757")).toBe("****3757");
    expect(enmascararDocumento("123")).toBe("****");
    expect(enmascararDocumento("")).toBe("—");
  });

  it("formatea teléfonos colombianos", () => {
    expect(formatearTelefono("3001234567")).toBe("300 123 4567");
    expect(formatearTelefono("6221663")).toBe("622 1663");
    expect(formatearTelefono("+57 300 123")).toBe("+57 300 123");
    expect(formatearTelefono("")).toBe("—");
  });

  it("normaliza placas", () => {
    expect(normalizarPlaca(" abc-12d ")).toBe("ABC12D");
    expect(normalizarPlaca("xyz 98e")).toBe("XYZ98E");
  });

  it("resuelve meses y cumpleaños", () => {
    expect(nombreMes(5)).toBe("Mayo");
    expect(nombreMes(0)).toBe("—");
    expect(nombreMes(13)).toBe("—");
    expect(nombreMes(null)).toBe("—");
    expect(cumpleanos(15, 5)).toBe("15 de mayo");
    expect(cumpleanos(null, 5)).toBe("Mayo");
    expect(cumpleanos(null, null)).toBe("—");
  });

  it("calcula la fecha de Bogotá y suma días", () => {
    // 2026-01-01 03:00 UTC sigue siendo 31/12/2025 en Bogotá
    expect(hoyBogota(new Date("2026-01-01T03:00:00Z"))).toBe("2025-12-31");
    expect(sumarDias("2026-11-14", 30)).toBe("2026-12-14");
    expect(sumarDias("2026-12-31", 1)).toBe("2027-01-01");
  });

  it("no altera el dato de origen", () => {
    const original = "2027-03-15";
    formatearFecha(original);
    expect(original).toBe("2027-03-15");
  });
});
