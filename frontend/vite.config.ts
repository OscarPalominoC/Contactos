/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  base: "/contactos/", // Crucial para que los assets carguen bajo oscarpalomino.dev/contactos/
  plugins: [react(), tailwindcss()],
  server: {
    host: "0.0.0.0", // Permite recibir tráfico desde fuera del contenedor
    port: 5177,      // Coincide con el puerto mapeado en Docker
    strictPort: true,
    proxy: {
      "/api": { target: "http://backend:8004", changeOrigin: false }, // En docker se usa el nombre del servicio
    },
    allowedHosts: ['oscarpalomino.dev', 'www.oscarpalomino.dev'],
    hmr: {
      host: 'oscarpalomino.dev',
      clientPort: 443,
      protocol: 'wss',
      path: 'contactos/@vite/'
    }
  },
  build: {
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          datos: ["@tanstack/react-query", "axios", "zod", "zustand"],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
    restoreMocks: true,
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/main.tsx", "src/test/**", "src/**/*.d.ts", "src/vite-env.d.ts"],
      thresholds: { lines: 85, functions: 85, statements: 85, branches: 80 },
    },
  },
});