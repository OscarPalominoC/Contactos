import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

declare const process: { env: Record<string, string | undefined> };

/**
 * Auditoría WCAG 2.1 AA con axe-core contra la aplicación real (backend + datos importados).
 * Requiere: backend en 127.0.0.1:8000, frontend en localhost:5173 y las variables
 * E2E_NIP / E2E_CLAVE de una cuenta sin clave temporal (scripts/e2e.ps1 la crea y la borra).
 */
const NIP = process.env.E2E_NIP ?? "";
const CLAVE = process.env.E2E_CLAVE ?? "";
const ETIQUETAS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function auditar(page: Page, nombre: string) {
  const resultado = await new AxeBuilder({ page: page as never }).withTags(ETIQUETAS).analyze();
  const resumen = resultado.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} nodos — ${v.help}`);
  expect(resumen, `Violaciones WCAG en ${nombre}`).toEqual([]);
}

/**
 * Navega dentro de la SPA sin recargar: cada recarga llama a /auth/refresh, limitado a 10/min,
 * y una ráfaga de recargas cerraría la sesión por el límite (no por accesibilidad).
 */
async function navegar(page: Page, ruta: string) {
  await page.evaluate((r) => {
    window.history.pushState({}, "", r);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, ruta);
}

async function ingresar(page: Page) {
  await page.goto("/login");
  await page.getByLabel(/Usuario/).fill(NIP);
  await page.getByLabel(/Contraseña/).fill(CLAVE);
  await page.getByRole("button", { name: "Ingresar" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Tablero" })).toBeVisible();
}

const PANTALLAS: { ruta: string; titulo: RegExp }[] = [
  { ruta: "/", titulo: /Tablero/ },
  { ruta: "/contactos", titulo: /Contactos/ },
  { ruta: "/motos", titulo: /Motos/ },
  { ruta: "/revisiones", titulo: /Revisiones RTM/ },
  { ruta: "/soat", titulo: /SOAT/ },
  { ruta: "/llamadas?pestana=cumpleanos", titulo: /Llamadas/ },
  { ruta: "/catalogos", titulo: /Marcas y líneas/ },
  { ruta: "/usuarios", titulo: /Usuarios/ },
  { ruta: "/mi-cuenta", titulo: /Mi cuenta/ },
];

test.describe("Accesibilidad WCAG 2.1 AA", () => {
  test("login sin violaciones", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("button", { name: "Ingresar" })).toBeVisible();
    await expect(page).toHaveTitle("Iniciar sesión · Check Contactos");
    await auditar(page, "login");
  });

  for (const tema of ["claro", "oscuro"] as const) {
    test(`pantallas en modo ${tema}`, async ({ page }) => {
      await page.addInitScript((t) => localStorage.setItem("tema", t), tema);
      await ingresar(page);
      for (const { ruta, titulo } of PANTALLAS) {
        await navegar(page, ruta);
        await expect(page.getByRole("heading", { level: 1, name: titulo })).toBeVisible();
        await page.waitForLoadState("networkidle");
        await expect(page.getByRole("status").filter({ hasText: /Cargando/ })).toHaveCount(0);
        await auditar(page, `${ruta} (${tema})`);
      }
    });
  }

  test("ficha 360 y diálogo de formulario", async ({ page }) => {
    await ingresar(page);
    await navegar(page, "/contactos");
    // Contactos es solo de búsqueda: se busca y se entra a la ficha por el nombre.
    await page.getByLabel("Buscar por documento o nombre").fill("mar");
    const primerNombre = page.getByRole("table").getByRole("link").first();
    await expect(primerNombre).toBeVisible();
    await auditar(page, "resultados de búsqueda de contactos");
    await primerNombre.click();
    await expect(page.getByRole("heading", { name: "Datos del contacto" })).toBeVisible();
    await auditar(page, "ficha 360");
    await navegar(page, "/contactos");
    await page.getByRole("button", { name: "Nuevo contacto" }).click();
    await expect(page.getByRole("dialog", { name: "Nuevo contacto" })).toBeVisible();
    await auditar(page, "diálogo nuevo contacto");
    await page.getByRole("button", { name: /Fecha de cumpleaños/ }).click();
    await expect(page.getByRole("dialog", { name: "Calendario: Fecha de cumpleaños" })).toBeVisible();
    await auditar(page, "calendario de cumpleaños");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: "Calendario: Fecha de cumpleaños" })).toHaveCount(0);
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Nuevo contacto" })).toBeFocused();
  });

  for (const tema of ["claro", "oscuro"] as const) {
    test(`barra superior y menú de usuario en modo ${tema}`, async ({ page }) => {
      await page.addInitScript((t) => localStorage.setItem("tema", t), tema);
      await ingresar(page);
      const banner = page.getByRole("banner");
      await expect(banner).not.toContainText("Barrancabermeja");
      await expect(banner.getByRole("button", { name: /Activar modo/ })).toHaveText("");
      await expect(banner.getByRole("button", { name: "Cerrar sesión" })).toHaveText("");
      const usuario = banner.getByRole("button", { name: /^Cuenta/ });
      await usuario.click();
      await expect(page.getByRole("button", { name: "Cambiar nombre" })).toBeFocused();
      await auditar(page, `menú de usuario (${tema})`);
      await page.keyboard.press("Escape");
      await expect(usuario).toBeFocused();
      for (const opcion of ["Cambiar nombre", "Actualizar contraseña"]) {
        await usuario.click();
        await page.getByRole("button", { name: opcion }).click();
        await expect(page.getByRole("dialog", { name: opcion })).toBeVisible();
        await auditar(page, `diálogo ${opcion} (${tema})`);
        await page.keyboard.press("Escape");
        await expect(page.getByRole("dialog")).toHaveCount(0);
      }
    });
  }

  test("navegación por teclado: enlace de salto y foco visible", async ({ page }) => {
    await ingresar(page);
    await page.keyboard.press("Tab");
    const salto = page.getByRole("link", { name: "Saltar al contenido principal" });
    await expect(salto).toBeFocused();
    await expect(salto).toBeInViewport();
    await page.keyboard.press("Enter");
    await expect(page.locator("#contenido")).toBeFocused();
  });

  test("reflujo a 320 px sin desplazamiento horizontal", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await ingresar(page);
    for (const ruta of ["/", "/contactos", "/llamadas"]) {
      await navegar(page, ruta);
      await page.waitForLoadState("networkidle");
      await expect(page.getByRole("button", { name: "Menú" })).toBeVisible();
      const desborde = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(desborde, `desborde horizontal en ${ruta}`).toBeLessThanOrEqual(0);
    }
  });
});
