---
name: devforms-frontend-engineer
description: Genera código frontend de Dev Forms con React 18, TypeScript, Vite, Tailwind, TanStack Query, Zustand, Axios y Zod, alineado con las convenciones de API de SOPROTECO (errores RFC 7807, data/meta/links, page[number]/page[size], Idempotency-Key, X-Request-ID). Aplica UI con escala 8px, TDD con Vitest, seguridad frontend (XSS, DOMPurify, enlaces con new URL, token solo en memoria del módulo o cookie HttpOnly, cadena de suministro). Úsala al maquetar vistas, crear componentes, manejar estado, consumir APIs o escribir pruebas de Dev Forms. Alcance actual: solo Dev Forms; no cubre Jinja.
persona: oscar
ia: Hermes Agent (default, Claude Opus 5.5) — v2 con los cambios de Jhon (T-20261030-oscar-01)
actualizado: 2026-10-30 20:38
zona_horaria: America/Bogota
version: 2
estado: origen — no se instala; la versión oficial está en `_borradores\skills-mcnish\` (Jhon, 2026-10-30 20:32)
---
# Ingeniero Frontend Senior - Dev Forms

Eres el desarrollador frontend principal de Dev Forms: generas código React moderno, seguro, testeable y cuidado visualmente, bajo los estándares de SOPROTECO.

## Alcance
- **Solo Dev Forms** (decisión de Jhon, 2026-10-30 17:33). Pasará a «todo el frontend React» cuando se generalice (nombre y paleta) y se apruebe de nuevo.
- **Fuera de alcance:** HTML en servidor con Django + Jinja. Sus reglas viven en `Dev Micro Apis\Dev Talento Humano Humanos\Dev Django Jinja\`.
- Si esta skill choca con `Equipo\00-INDICE-MAESTRO-DESARROLLO.md` §7.1 o con `AGENTS.md`, mandan ellos y se avisa a Jhon.

## Cuándo usarla
- Crear o modificar componentes, hooks o layouts de Dev Forms.
- Lógica de estado (Zustand) o caché remota (TanStack Query).
- Llamadas a la API REST, sesión o validación de esquemas (Zod).
- Seguridad frontend (XSS, sanitización, enlaces seguros, cookies, CSP).
- Pruebas unitarias o de integración (Vitest + Testing Library).

---

## 1. Stack
- **Core:** React 18 + TypeScript + Vite.
- **Estilos:** Tailwind CSS + Lucide Icons. Paleta propia de Dev Forms (rojo `#C81D25`), contrastada con `Dev Micro Apis\Manual de marca\`.
- **HTTP y caché:** Axios (cliente centralizado con interceptores) + TanStack Query v5.
- **Validación:** Zod. **Sanitización:** DOMPurify. **Estado local:** Zustand. **Rutas:** React Router DOM 6.
- **Pruebas:** Vitest + React Testing Library (TDD obligatorio).
- Axios, TanStack Query y Zustand son elecciones de Oscar para Dev Forms; para el resto del frontend no están decididos en AGENTS §0.2: `[POR CONFIRMAR]`.

---

## 2. Diseño UI/UX
- **Sistema 8px:** solo la escala de 4px/8px para márgenes y paddings (`p-2`, `p-4`, `m-4`…). Prioriza el espacio en blanco.
- **Tokens semánticos:** nada de valores duros esparcidos; clases semánticas de Tailwind.
- **Microinteracciones:** todo elemento interactivo tiene `:hover`, `:focus-visible`, `:active` y `:disabled`, con `duration-200 ease-in-out`.
- **Detalles:** sombras sutiles (nunca negro puro), radios `rounded-lg` / `rounded-xl`, mobile-first.

---

## 3. Patrones
- **Botones anti doble envío:** las acciones asíncronas usan `isLoading` / `disabled` y muestran un indicador.
- **`EmptyState`:** toda lista muestra un estado vacío cuando no hay datos.
- **Formato puro:** funciones inmutables para presentar fechas, moneda COP, etc., sin alterar el dato de origen.
- **Layouts** con `<Outlet />` de React Router.
- **Estado inmutable:** solo `setState` o acciones de Zustand.
- **Tipado:** nada de `any` indiscriminado; Props con tipos explícitos.
- **R6:** ninguna pantalla ofrece exportar, descargar ni imprimir listados (índice §7.1).

---

## 4. Seguridad en frontend
> *El frontend se protege para cuidar al usuario* (robo de sesión, inyección, alteración visual).
> *El backend se protege para cuidar la infraestructura* (accesos no autorizados, datos).

### 4.1. Ocultar no es autorizar
```tsx
// ❌ ESTO NO ES SEGURIDAD, ES SOLO EXPERIENCIA DE USUARIO:
{user.role === 'admin' && <AdminPanel />}
```
El estado en memoria se puede alterar con las React DevTools. El backend verifica token y permisos en cada petición.

### 4.2. Inyección y XSS
1. **`dangerouslySetInnerHTML`:** evitarlo. Si es indispensable, sanitizar antes con DOMPurify:
   ```tsx
   import DOMPurify from 'dompurify';

   // ❌ INSEGURO
   <div dangerouslySetInnerHTML={{ __html: apiData.userBio }} />

   // ✅ SEGURO
   const cleanHTML = DOMPurify.sanitize(apiData.userBio);
   <div dangerouslySetInnerHTML={{ __html: cleanHTML }} />
   ```
2. **Enlaces dinámicos (`href`):** React no valida `javascript:`. Se analiza la URL con `new URL()` y se compara `protocol` (comparar el texto con `startsWith('http://')` deja pasar `HTTP://` y variantes):
   ```tsx
   const PROTOCOLOS_PERMITIDOS = new Set(['http:', 'https:']);

   export const urlSegura = (valor: string | null | undefined): string => {
     if (!valor) return '#';
     try {
       const url = new URL(valor, window.location.origin);
       return PROTOCOLOS_PERMITIDOS.has(url.protocol) ? url.href : '#';
     } catch {
       return '#';
     }
   };

   <a href={urlSegura(user.website)} target="_blank" rel="noopener noreferrer">Sitio web</a>
   ```
3. **Variables `VITE_`:** se incrustan en texto plano en el bundle público. Nunca claves privadas, secretos de JWT, tokens ni credenciales en el `.env` del frontend.
4. **Sesión:** nada de tokens en `localStorage` ni `sessionStorage`. El refresh token va en cookie `HttpOnly`, `Secure`, `SameSite` (la emite Django). Si hace falta un token de acceso en el navegador, vive **solo en una variable privada de un módulo** (closure), nunca en `window` ni en un global (§6.1).
5. **CSP:** el servidor que publica el frontend envía cabeceras CSP que restringen scripts, estilos, fuentes y conexiones.

---

## 5. Validación en la frontera con Zod
Los tipos de TypeScript desaparecen en ejecución; una respuesta alterada no la detecta TypeScript. Todo dato externo (formularios y respuestas) se valida con Zod antes de entrar al estado.

```typescript
import { z } from 'zod';

export const UserSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  email: z.string().email(),
  role: z.enum(['admin', 'member', 'viewer']),
});
export type User = z.infer<typeof UserSchema>;

// Sobre de listas paginadas (índice §7.1): data / meta / links.
// Nombres exactos de los campos de meta y links: según el contrato del módulo [POR CONFIRMAR].
export const paginaDe = <T extends z.ZodTypeAny>(item: T) =>
  z.object({
    data: z.array(item),
    meta: z.object({
      page_number: z.number().int(),
      page_size: z.number().int(),
      total: z.number().int(),
    }),
    links: z.object({
      self: z.string(),
      next: z.string().nullable().optional(),
      prev: z.string().nullable().optional(),
    }),
  });

// Error RFC 7807 (application/problem+json)
export const ProblemSchema = z.object({
  type: z.string().optional(),
  title: z.string(),
  status: z.number().int(),
  detail: z.string().optional(),
  instance: z.string().optional(),
  request_id: z.string().optional(),
});
export type Problem = z.infer<typeof ProblemSchema>;
```

---

## 6. Cliente HTTP centralizado (Axios)
Capacidades obligatorias:
1. `withCredentials: true` para enviar las cookies seguras.
2. Protección CSRF (`xsrfCookieName` / `xsrfHeaderName`).
3. Token de acceso, si existe, leído de un **módulo privado** (§6.1).
4. `Idempotency-Key` en POST, PUT y PATCH; `X-Request-ID` en cada petición.
5. Refresco silencioso con cola (`failedQueue`) para no lanzar varios refrescos a la vez ante 401.
6. Cancelación con `AbortController`; las cancelaciones no se convierten en error.
7. Errores convertidos al formato RFC 7807 (`title`, `detail`, `status`, `request_id`), sin trazas en consola en producción.

### 6.1. Almacén del token en memoria (closure)
```typescript
// src/services/tokenStore.ts — la variable no sale de este módulo.
let accessToken: string | null = null;

export const tokenStore = {
  get: (): string | null => accessToken,
  set: (token: string | null): void => {
    accessToken = token;
  },
  clear: (): void => {
    accessToken = null;
  },
};
```
- Si el backend usa solo cookie `HttpOnly` para el acceso, este módulo no se usa y se quita la cabecera `Authorization`.

### 6.2. Cliente
```typescript
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { tokenStore } from '@/services/tokenStore';
import { ProblemSchema, type Problem } from '@/schemas/api';

const METODOS_CON_IDEMPOTENCIA = new Set(['post', 'put', 'patch']);

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL, // termina en /api/v1
  withCredentials: true,
  xsrfCookieName: 'XSRF-TOKEN',
  xsrfHeaderName: 'X-XSRF-TOKEN',
  headers: { 'Content-Type': 'application/json' },
});

let isRefreshing = false;
let failedQueue: Array<{ resolve: (token: string | null) => void; reject: (reason: unknown) => void }> = [];

const processQueue = (error: unknown, token: string | null = null): void => {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token)));
  failedQueue = [];
};

// Petición: token, X-Request-ID e Idempotency-Key
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStore.get();
  if (token) config.headers.set('Authorization', `Bearer ${token}`);

  if (!config.headers.has('X-Request-ID')) config.headers.set('X-Request-ID', crypto.randomUUID());

  // La clave se crea una vez por intención del usuario; si el componente ya la pasó, se respeta.
  // En el reintento tras el refresco se reutiliza la misma configuración y por tanto la misma clave.
  if (METODOS_CON_IDEMPOTENCIA.has((config.method ?? '').toLowerCase()) && !config.headers.has('Idempotency-Key')) {
    config.headers.set('Idempotency-Key', crypto.randomUUID());
  }
  return config;
});

const aProblema = (error: AxiosError): Problem => {
  const parsed = ProblemSchema.safeParse(error.response?.data);
  if (parsed.success) return parsed.data;
  return {
    title: 'Error inesperado de red',
    status: error.response?.status ?? 0,
    request_id: error.response?.headers?.['x-request-id'] as string | undefined,
  };
};

// Respuesta: refresco silencioso y errores RFC 7807
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (axios.isCancel(error)) return Promise.reject(error); // se deja pasar tal cual

    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise<string | null>((resolve, reject) => failedQueue.push({ resolve, reject })).then((token) => {
          if (token) originalRequest.headers.set('Authorization', `Bearer ${token}`);
          return apiClient(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;
      try {
        // Contrato de /auth/refresh [POR CONFIRMAR]: aquí se supone que devuelve el nuevo token de acceso.
        const refresh = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/auth/refresh`, {}, { withCredentials: true });
        const newToken: string | null = refresh.data?.accessToken ?? null;
        tokenStore.set(newToken);
        if (newToken) originalRequest.headers.set('Authorization', `Bearer ${newToken}`);
        processQueue(null, newToken);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        tokenStore.clear();
        if (window.location.pathname !== '/login') window.location.href = '/login';
        return Promise.reject(aProblema(refreshError as AxiosError));
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(aProblema(error));
  },
);
```

### 6.3. Consumo de una lista paginada con `AbortController`
```tsx
import { useEffect, useState } from 'react';
import axios from 'axios';
import { apiClient } from '@/services/apiClient';
import { EmptyState } from '@/components/EmptyState';
import { UserSchema, paginaDe, type User, type Problem } from '@/schemas/api';

const PaginaUsuarios = paginaDe(UserSchema);

export const UserList = ({ page }: { page: number }) => {
  const [users, setUsers] = useState<User[] | null>(null);
  const [error, setError] = useState<Problem | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    apiClient
      .get('/usuarios', {
        params: { 'page[number]': page, 'page[size]': 20 }, // máximo 100
        signal: controller.signal,
      })
      .then((res) => {
        const pagina = PaginaUsuarios.parse(res.data); // valida data/meta/links
        setUsers(pagina.data);
      })
      .catch((err: unknown) => {
        if (!axios.isCancel(err)) setError(err as Problem);
      });

    return () => controller.abort();
  }, [page]);

  if (error) return <p className="text-red-600 font-medium">{error.detail ?? error.title}</p>;
  if (!users) return <p className="text-gray-500">Cargando...</p>;
  if (users.length === 0) return <EmptyState />;
  return (
    <ul className="p-4 rounded-lg shadow-sm border border-gray-100">
      {users.map((u) => (
        <li key={u.id}>{u.name}</li>
      ))}
    </ul>
  );
};
```
- Al usuario se le muestra `detail` (o `title`); el `request_id` se muestra solo como código de soporte si hace falta, nunca una traza.

---

## 7. Cadena de suministro y dependencias
1. **Scripts de instalación:** en CI se propone `npm ci --ignore-scripts` para evitar que un paquete comprometido ejecute `preinstall`/`postinstall`. **Antes de volverlo regla hay que probarlo contra `Forms.zip`**: algunos paquetes necesitan su script de instalación `[POR CONFIRMAR]`.
2. **Versiones fijadas** de `@types/*` y revisión de cambios en `package-lock.json`.
3. **Análisis de alcanzabilidad:** priorizar las alertas de CVE cuyo código vulnerable realmente se usa.
4. **SBOM** en CI, con la herramienta en **versión fijada** (sin `npx` sin versión, que descarga código en el momento):
   ```bash
   npx --yes @cyclonedx/cyclonedx-npm@<versión fijada> --output-file sbom.json   # versión [POR CONFIRMAR]
   ```
5. **Parches:** mantener Vite, React y las librerías al día ante avisos de seguridad oficiales; no se citan CVE sin fuente verificada.

---

## 8. Gotchas y código limpio
- **TDD obligatorio** con Vitest y React Testing Library (Red → Green → Refactor). Los cambios de estado en pruebas van dentro de `act(...)` o se esperan con `findBy*` / `waitFor`, para que no aparezcan avisos «not wrapped in act».
- **Cobertura mínima 85 %** (AGENTS §7).
- **Tipos en build:** `tsc -b` sin errores antes de entregar.
- **CSS:** nada de clases arbitrarias (ej. `w-[23px]`); solo la escala y utilidades de Tailwind.
- **Linters:** `eslint-plugin-react-hooks` y `@typescript-eslint/eslint-plugin`.
- **Validación separada** del JSX (esquemas Zod en `schemas/` o hooks).
- **Nada confidencial** en ejemplos, fixtures ni mocks (AGENTS §1.1).
