import axios, { type InternalAxiosRequestConfig } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, crearCliente, esCancelacion, esSesionExpirada, normalizarError, nuevoId, refrescarSesion } from "../services/apiClient";
import { tokenStore } from "../services/tokenStore";

interface Llamada {
  url: string;
  method: string;
  headers: Record<string, string>;
  data?: unknown;
}

/** Adaptador falso que registra las peticiones y responde según una cola de respuestas. */
function adaptador(respuestas: ((llamada: Llamada) => { status: number; data?: unknown })[]) {
  const llamadas: Llamada[] = [];
  let indice = 0;
  const adapter = async (config: InternalAxiosRequestConfig) => {
    const llamada: Llamada = {
      url: String(config.url),
      method: String(config.method),
      headers: Object.fromEntries(Object.entries((config.headers ?? {}) as Record<string, string>)),
      data: config.data,
    };
    llamadas.push(llamada);
    const respuesta = (respuestas[Math.min(indice++, respuestas.length - 1)] ?? (() => ({ status: 200, data: undefined as unknown })))(llamada);
    const base = { config, headers: { "x-request-id": "rid-1" }, statusText: "", data: respuesta.data ?? {} };
    if (respuesta.status >= 400) {
      const error = new axios.AxiosError("fallo", String(respuesta.status), config as never, null, {
        ...base,
        status: respuesta.status,
      } as never);
      throw error;
    }
    return { ...base, status: respuesta.status };
  };
  return { adapter, llamadas };
}

describe("cliente HTTP", () => {
  beforeEach(() => {
    tokenStore.clear();
    document.cookie = "XSRF-TOKEN=token-csrf; path=/";
  });

  it("agrega X-Request-ID distinto en cada petición e Idempotency-Key solo en escrituras", async () => {
    const { adapter, llamadas } = adaptador([() => ({ status: 200 })]);
    const cliente = crearCliente({ baseURL: "/api/v1" });
    cliente.defaults.adapter = adapter;
    await cliente.get("/contactos");
    await cliente.post("/contactos", { nip: "1" });
    await cliente.patch("/contactos/1", { nombre: "X" });

    expect(llamadas[0]?.headers["X-Request-ID"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(llamadas[0]?.headers["X-Request-ID"]).not.toBe(llamadas[1]?.headers["X-Request-ID"]);
    expect(llamadas[0]?.headers["Idempotency-Key"]).toBeUndefined();
    expect(llamadas[1]?.headers["Idempotency-Key"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(llamadas[2]?.headers["Idempotency-Key"]).toBeDefined();
  });

  it("respeta una Idempotency-Key enviada por quien llama", async () => {
    const { adapter, llamadas } = adaptador([() => ({ status: 201 })]);
    const cliente = crearCliente();
    cliente.defaults.adapter = adapter;
    await cliente.post("/contactos", {}, { headers: { "Idempotency-Key": "clave-fija" } });
    expect(llamadas[0]?.headers["Idempotency-Key"]).toBe("clave-fija");
  });

  it("agrega el token de acceso desde el almacén en memoria", async () => {
    const { adapter, llamadas } = adaptador([() => ({ status: 200 })]);
    const cliente = crearCliente();
    cliente.defaults.adapter = adapter;
    tokenStore.set("token-abc");
    await cliente.get("/contactos");
    expect(llamadas[0]?.headers.Authorization).toBe("Bearer token-abc");
  });

  it("refresca una sola vez ante varios 401 simultáneos y reintenta en cola", async () => {
    let refrescos = 0;
    const adapter = async (config: InternalAxiosRequestConfig) => {
      const url = String(config.url);
      const headers = (config.headers ?? {}) as Record<string, string>;
      if (url === "/auth/refresh") {
        refrescos += 1;
        return { status: 200, data: { access: "token-nuevo", expira_en: 300 }, config, headers: {}, statusText: "" } as never;
      }
      if (headers.Authorization !== "Bearer token-nuevo") {
        throw new axios.AxiosError("401", "401", config as never, null, {
          status: 401,
          data: {},
          config,
          headers: {},
          statusText: "",
        } as never);
      }
      return { status: 200, data: { ok: url }, config, headers: {}, statusText: "" } as never;
    };
    const cliente = crearCliente();
    cliente.defaults.adapter = adapter;
    tokenStore.set("token-viejo");

    const resultados = await Promise.all([cliente.get("/contactos"), cliente.get("/motos"), cliente.get("/soats")]);
    expect(refrescos).toBe(1);
    expect(resultados.map((r) => r.data)).toEqual([{ ok: "/contactos" }, { ok: "/motos" }, { ok: "/soats" }]);
    expect(tokenStore.get()).toBe("token-nuevo");
  });

  it("si el refresco falla limpia el token y avisa que la sesión expiró", async () => {
    const alExpirarSesion = vi.fn();
    const adapter = async (config: InternalAxiosRequestConfig) => {
      throw new axios.AxiosError("401", "401", config as never, null, {
        status: 401,
        data: {},
        config,
        headers: {},
        statusText: "",
      } as never);
    };
    const cliente = crearCliente({ alExpirarSesion });
    cliente.defaults.adapter = adapter;
    tokenStore.set("token-viejo");
    await expect(cliente.get("/contactos")).rejects.toBeInstanceOf(ApiError);
    expect(tokenStore.get()).toBeNull();
    expect(alExpirarSesion).toHaveBeenCalledOnce();
  });

  it("dos refrescos concurrentes hacen un solo POST /auth/refresh", async () => {
    const { adapter, llamadas } = adaptador([() => ({ status: 200, data: { access: "t-unico", expira_en: 300 } })]);
    const cliente = crearCliente();
    cliente.defaults.adapter = adapter;
    const [a, b] = await Promise.all([refrescarSesion(cliente), refrescarSesion(cliente)]);
    expect(a).toBe("t-unico");
    expect(b).toBe("t-unico");
    expect(llamadas.filter((l) => l.url === "/auth/refresh")).toHaveLength(1);
  });

  it("no expira la sesión ante error de red en refresh", async () => {
    const alExpirarSesion = vi.fn();
    const adapter = async (config: InternalAxiosRequestConfig) => {
      if (String(config.url) === "/auth/refresh") throw new axios.AxiosError("sin red", "ERR_NETWORK", config as never);
      throw new axios.AxiosError("401", "401", config as never, null, { status: 401, data: {}, config, headers: {}, statusText: "" } as never);
    };
    const cliente = crearCliente({ alExpirarSesion });
    cliente.defaults.adapter = adapter;
    tokenStore.set("token-viejo");
    await expect(cliente.get("/contactos")).rejects.toBeInstanceOf(ApiError);
    expect(alExpirarSesion).not.toHaveBeenCalled();
    expect(tokenStore.get()).toBe("token-viejo");
  });

  it("no expira la sesión ante 5xx en refresh", async () => {
    const alExpirarSesion = vi.fn();
    const cliente = crearCliente({ alExpirarSesion });
    cliente.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
      const status = String(config.url) === "/auth/refresh" ? 503 : 401;
      throw new axios.AxiosError(String(status), String(status), config as never, null, { status, data: {}, config, headers: {}, statusText: "" } as never);
    };
    await expect(cliente.get("/contactos")).rejects.toBeInstanceOf(ApiError);
    expect(alExpirarSesion).not.toHaveBeenCalled();
  });

  it("expira la sesión con 401 en refresh", async () => {
    const alExpirarSesion = vi.fn();
    const { adapter } = adaptador([() => ({ status: 401 })]);
    const cliente = crearCliente({ alExpirarSesion });
    cliente.defaults.adapter = adapter;
    tokenStore.set("token-viejo");
    await expect(cliente.get("/contactos")).rejects.toBeInstanceOf(ApiError);
    expect(alExpirarSesion).toHaveBeenCalledOnce();
    expect(tokenStore.get()).toBeNull();
  });

  it("esSesionExpirada solo es verdadero para 401 y 403", () => {
    const err = (status: number) => new ApiError({ type: "x", title: "t", status, detail: "d" });
    expect(esSesionExpirada(err(401))).toBe(true);
    expect(esSesionExpirada(err(403))).toBe(true);
    expect(esSesionExpirada(err(0))).toBe(false);
    expect(esSesionExpirada(err(500))).toBe(false);
    expect(esSesionExpirada(new Error("x"))).toBe(false);
  });

  it("no intenta refrescar cuando el 401 viene del propio login", async () => {
    const { adapter, llamadas } = adaptador([() => ({ status: 401, data: { detail: "Credenciales inválidas." } })]);
    const cliente = crearCliente();
    cliente.defaults.adapter = adapter;
    await expect(cliente.post("/auth/login", {})).rejects.toBeInstanceOf(ApiError);
    expect(llamadas.filter((l) => l.url === "/auth/refresh")).toHaveLength(0);
  });

  it("sí intenta refrescar cuando el 401 viene de /auth/yo", async () => {
    let llamadoRefresh = false;
    const adapter = async (config: InternalAxiosRequestConfig) => {
      const url = String(config.url);
      if (url === "/auth/refresh") {
        llamadoRefresh = true;
        return { status: 200, data: { access: "token-renovado", expira_en: 300 }, config, headers: {}, statusText: "" } as never;
      }
      if (url === "/auth/yo") {
        if (!llamadoRefresh) {
          throw new axios.AxiosError("401", "401", config as never, null, {
            status: 401,
            data: {},
            config,
            headers: {},
            statusText: "",
          } as never);
        }
        return { status: 200, data: { nip: "900001", nombre: "Oscar" }, config, headers: {}, statusText: "" } as never;
      }
      return { status: 200, data: {}, config, headers: {}, statusText: "" } as never;
    };
    const cliente = crearCliente();
    cliente.defaults.adapter = adapter;
    tokenStore.set("token-inicial");
    const res = await cliente.get("/auth/yo");
    expect(llamadoRefresh).toBe(true);
    expect(res.data).toEqual({ nip: "900001", nombre: "Oscar" });
  });

  it("convierte las respuestas de error al formato RFC 7807", async () => {
    const problema = {
      type: "/problemas/datos-invalidos",
      title: "Datos inválidos",
      status: 422,
      detail: "Revise los campos marcados.",
      request_id: "rid-9",
      errors: { nombre: ["Escriba el nombre completo."], correo: ["Correo inválido."] },
    };
    const { adapter } = adaptador([() => ({ status: 422, data: problema })]);
    const cliente = crearCliente();
    cliente.defaults.adapter = adapter;
    const error = (await cliente.post("/contactos", {}).catch((e: unknown) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(422);
    expect(error.problema.request_id).toBe("rid-9");
    expect(error.erroresDeCampo()).toEqual({ nombre: "Escriba el nombre completo.", correo: "Correo inválido." });
  });

  it("las cancelaciones no se convierten en ApiError", async () => {
    const controlador = new AbortController();
    const adapter = async (config: InternalAxiosRequestConfig) => {
      controlador.abort();
      throw new axios.CanceledError("cancelado", undefined, config as never);
    };
    const cliente = crearCliente();
    cliente.defaults.adapter = adapter;
    const error = await cliente.get("/contactos", { signal: controlador.signal }).catch((e: unknown) => e);
    expect(esCancelacion(error)).toBe(true);
    expect(error).not.toBeInstanceOf(ApiError);
  });

  it("normaliza errores de red y de cliente", () => {
    const red = normalizarError(new axios.AxiosError("sin red", "ERR_NETWORK"));
    expect(red.status).toBe(0);
    expect(red.problema.detail).toContain("No fue posible comunicarse");
    const cualquiera = normalizarError(new Error("roto"));
    expect(cualquiera.problema.detail).toContain("roto");
    const mismo = new ApiError({ type: "x", title: "t", status: 400, detail: "d" });
    expect(normalizarError(mismo)).toBe(mismo);
  });

  it("envía credenciales y cabecera XSRF", () => {
    const cliente = crearCliente();
    expect(cliente.defaults.withCredentials).toBe(true);
    expect(cliente.defaults.xsrfHeaderName).toBe("X-XSRF-TOKEN");
    expect(cliente.defaults.xsrfCookieName).toBe("XSRF-TOKEN");
  });
});

describe("almacén de token", () => {
  it("guarda el token solo en memoria", () => {
    tokenStore.set("secreto");
    expect(tokenStore.get()).toBe("secreto");
    expect(localStorage.getItem("token")).toBeNull();
    expect(JSON.stringify(localStorage)).not.toContain("secreto");
    expect(JSON.stringify(sessionStorage)).not.toContain("secreto");
    tokenStore.clear();
    expect(tokenStore.get()).toBeNull();
  });
});

describe("nuevoId", () => {
  const patronUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

  it("genera un UUID v4 válido con crypto.randomUUID si está disponible", () => {
    const id = nuevoId();
    expect(id).toMatch(patronUuid);
  });

  it("genera un UUID v4 válido si crypto.randomUUID no es función (contexto no seguro / IP HTTP)", () => {
    const original = window.crypto;
    try {
      // Simular navegador en IP HTTP donde randomUUID es undefined
      Object.defineProperty(window, "crypto", {
        value: {
          getRandomValues: original.getRandomValues.bind(original),
          randomUUID: undefined,
        },
        configurable: true,
      });

      const id = nuevoId();
      expect(id).toMatch(patronUuid);
    } finally {
      Object.defineProperty(window, "crypto", {
        value: original,
        configurable: true,
      });
    }
  });

  it("genera un UUID v4 válido como fallback si crypto está completamente ausente", () => {
    const original = window.crypto;
    try {
      Object.defineProperty(window, "crypto", {
        value: undefined,
        configurable: true,
      });

      const id = nuevoId();
      expect(id).toMatch(patronUuid);
    } finally {
      Object.defineProperty(window, "crypto", {
        value: original,
        configurable: true,
      });
    }
  });
});
