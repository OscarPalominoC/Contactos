import { describe, expect, it } from "vitest";

// Vitest corre con `css: false` (los imports de CSS llegan vacíos): se lee el archivo con fs de Node.
// Vitest se ejecuta desde frontend/, así que la ruta es relativa a esa carpeta.
declare function require(modulo: "node:fs"): { readFileSync: (ruta: string, codificacion: "utf-8") => string };
const { readFileSync } = require("node:fs");
const css = readFileSync("src/styles/index.css", "utf-8");

describe("hoja de estilos glassmorphism", () => {
  it("declara -webkit-backdrop-filter ANTES de backdrop-filter (el minificador conserva la última y Chrome solo entiende la estándar)", () => {
    expect(css).not.toMatch(/\n\s*backdrop-filter:[^;]+;\s*\n\s*-webkit-backdrop-filter:/);
    expect(css.match(/-webkit-backdrop-filter:[^;]+;\s*\n\s*backdrop-filter:/g)?.length ?? 0).toBeGreaterThanOrEqual(5);
  });

  it("los títulos de primer nivel llevan 1px de separación entre letras", () => {
    expect(css).toMatch(/h1,\s*\n?\s*\.title-l1\s*\{[^}]*letter-spacing:\s*1px/);
  });
});
