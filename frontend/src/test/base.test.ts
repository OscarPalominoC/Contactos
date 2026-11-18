import { describe, expect, it } from "vitest";

import { basenameRouter, rutaPublica } from "../app/base";

describe("rutas bajo un subpath (/contactos/)", () => {
  it("el router usa el subpath como basename", () => {
    expect(basenameRouter("/contactos/")).toBe("/contactos");
  });

  it("en la raíz el basename es /", () => {
    expect(basenameRouter("/")).toBe("/");
    expect(basenameRouter(undefined)).toBe("/");
  });

  it("los archivos de public/ se resuelven bajo el subpath", () => {
    expect(rutaPublica("favicon.svg", "/contactos/")).toBe("/contactos/favicon.svg");
    expect(rutaPublica("/logo-check.png", "/contactos")).toBe("/contactos/logo-check.png");
    expect(rutaPublica("favicon.svg", "/")).toBe("/favicon.svg");
  });

  it("por defecto toma el BASE_URL de Vite", () => {
    expect(rutaPublica("favicon.svg")).toBe(`${import.meta.env.BASE_URL}favicon.svg`);
  });
});
