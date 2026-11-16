import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";

import { tokenStore } from "./tokenStore";

export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
  request_id?: string;
  errors?: Record<string, string[]>;
}

/** Error normalizado al formato RFC 7807 para toda la aplicación. */
export class ApiError extends Error {
  readonly problema: ProblemDetail;

  constructor(problema: ProblemDetail) {
    super(problema.detail);
    this.name = "ApiError";
    this.problema = problema;
  }

  get status(): number {
    return this.problema.status;
  }

  erroresDeCampo(): Record<string, string> {
    const salida: Record<string, string> = {};
    for (const [campo, mensajes] of Object.entries(this.problema.errors ?? {})) {
      salida[campo] = Array.isArray(mensajes) ? mensajes.join(" ") : String(mensajes);
    }
    return salida;
  }
}

const METODOS_IDEMPOTENTES = new Set(["post", "put", "patch"]);

export function nuevoId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    const buffer = new Uint8Array(16);
    crypto.getRandomValues(buffer);
    buffer[6] = ((buffer[6] ?? 0) & 0x0f) | 0x40;
    buffer[8] = ((buffer[8] ?? 0) & 0x3f) | 0x80;
    const hex = Array.from(buffer, (b) => b.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function normalizarError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (axios.isAxiosError(error)) {
    const datos = error.response?.data as Partial<ProblemDetail> | undefined;
    const status = error.response?.status ?? 0;
    return new ApiError({
      type: datos?.type ?? (status ? `/problemas/${status}` : "/problemas/red"),
      title: datos?.title ?? (status ? "Error" : "Sin conexión"),
      status,
      detail:
        typeof datos?.detail === "string"
          ? datos.detail
          : status
            ? "Ocurrió un error inesperado."
            : "No fue posible comunicarse con el servidor. Verifique que el backend esté en ejecución.",
      instance: datos?.instance,
      request_id: datos?.request_id ?? error.response?.headers?.["x-request-id"],
      errors: datos?.errors,
    });
  }
  return new ApiError({ type: "/problemas/cliente", title: "Error", status: 0, detail: String(error) });
}

type ReintentoConfig = InternalAxiosRequestConfig & { _reintento?: boolean };

interface EnEspera {
  resolver: (token: string) => void;
  rechazar: (error: unknown) => void;
}

export interface OpcionesCliente {
  baseURL?: string;
  alExpirarSesion?: () => void;
}

/**
 * Cliente HTTP centralizado:
 * withCredentials + XSRF, Authorization desde tokenStore, X-Request-ID e Idempotency-Key,
 * refresco silencioso con cola (failedQueue), cancelación sin error y errores RFC 7807.
 */
export function crearCliente({ baseURL = "/api/v1", alExpirarSesion }: OpcionesCliente = {}): AxiosInstance {
  const cliente = axios.create({
    baseURL,
    withCredentials: true,
    xsrfCookieName: "XSRF-TOKEN",
    xsrfHeaderName: "X-XSRF-TOKEN",
    timeout: 30000,
    headers: { Accept: "application/json" },
  });

  let refrescando = false;
  let cola: EnEspera[] = [];

  const vaciarCola = (error: unknown, token: string | null): void => {
    for (const espera of cola) {
      if (token) espera.resolver(token);
      else espera.rechazar(error);
    }
    cola = [];
  };

  cliente.interceptors.request.use((config) => {
    const token = tokenStore.get();
    if (token && !config.headers.Authorization) config.headers.Authorization = `Bearer ${token}`;
    config.headers["X-Request-ID"] = nuevoId();
    if (METODOS_IDEMPOTENTES.has((config.method ?? "get").toLowerCase()) && !config.headers["Idempotency-Key"]) {
      config.headers["Idempotency-Key"] = nuevoId();
    }
    return config;
  });

  cliente.interceptors.response.use(
    (respuesta) => respuesta,
    async (error: AxiosError) => {
      if (axios.isCancel(error)) return Promise.reject(error);
      const original = error.config as ReintentoConfig | undefined;
      const esAuth = Boolean(
        original?.url && (original.url.includes("/auth/login") || original.url.includes("/auth/refresh")),
      );
      if (error.response?.status === 401 && original && !original._reintento && !esAuth) {
        if (refrescando) {
          return new Promise<string>((resolver, rechazar) => cola.push({ resolver, rechazar })).then((token) => {
            original.headers.Authorization = `Bearer ${token}`;
            return cliente(original);
          });
        }
        original._reintento = true;
        refrescando = true;
        try {
          const token = await refrescarSesion(cliente);
          vaciarCola(null, token);
          original.headers.Authorization = `Bearer ${token}`;
          return await cliente(original);
        } catch (errorRefresco) {
          vaciarCola(errorRefresco, null);
          tokenStore.clear();
          alExpirarSesion?.();
          return Promise.reject(normalizarError(error));
        } finally {
          refrescando = false;
        }
      }
      return Promise.reject(normalizarError(error));
    },
  );

  return cliente;
}

export interface RespuestaAcceso {
  access: string;
  expira_en: number;
}

/** Pide la cookie CSRF si falta y renueva el token de acceso con la cookie HttpOnly de refresco. */
export async function refrescarSesion(cliente: AxiosInstance): Promise<string> {
  await asegurarCsrf(cliente);
  const { data } = await cliente.post<RespuestaAcceso>("/auth/refresh");
  tokenStore.set(data.access);
  return data.access;
}

export async function asegurarCsrf(cliente: AxiosInstance): Promise<void> {
  if (!document.cookie.split("; ").some((c) => c.startsWith("XSRF-TOKEN="))) {
    await cliente.get("/auth/csrf");
  }
}

export function esCancelacion(error: unknown): boolean {
  return axios.isCancel(error);
}

let manejadorExpiracion: (() => void) | undefined;

export function alExpirarSesion(manejador: () => void): void {
  manejadorExpiracion = manejador;
}

export const apiClient = crearCliente({ alExpirarSesion: () => manejadorExpiracion?.() });
