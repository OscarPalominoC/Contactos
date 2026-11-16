import { defineConfig, devices } from "@playwright/test";

declare const process: { env: Record<string, string | undefined> };

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_URL ?? "http://localhost:5173",
    locale: "es-CO",
    timezoneId: "America/Bogota",
    trace: "off",
  },
  // E2E_CANAL=chromium usa el Chromium completo en modo headless (si no está descargado el headless_shell).
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], ...(process.env.E2E_CANAL ? { channel: process.env.E2E_CANAL } : {}) } }],
});
