import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { createBrowserRouter, Navigate, Outlet, RouterProvider, type RouteObject } from "react-router-dom";

import { PaginaCatalogos } from "../features/catalogos/PaginaCatalogos";
import { PaginaContactos } from "../features/contactos/PaginaContactos";
import { PaginaFichaContacto } from "../features/contactos/PaginaFichaContacto";
import { PaginaCambioClave } from "../features/auth/PaginaCambioClave";
import { PaginaLogin } from "../features/auth/PaginaLogin";
import { PaginaMiCuenta } from "../features/auth/PaginaMiCuenta";
import { PaginaLlamadas } from "../features/llamadas/PaginaLlamadas";
import { PaginaDetalleMoto, PaginaMotos } from "../features/motos/PaginaMotos";
import { PaginaRevisiones } from "../features/revisiones/PaginaRevisiones";
import { PaginaSoat } from "../features/soat/PaginaSoat";
import { PaginaTablero } from "../features/tablero/PaginaTablero";
import { PaginaUsuarios } from "../features/usuarios/PaginaUsuarios";
import { AppLayout, AuthLayout } from "../layouts/Layouts";
import type { ApiError } from "../services/apiClient";
import { RutaCambioClave, RutaProtegida } from "./RutaProtegida";
import { ProveedorSesion } from "./sesion";

export function crearQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        retry: (intentos, error) => {
          const estado = (error as ApiError).status;
          return intentos < 2 && (estado === 0 || estado >= 500);
        },
      },
      mutations: { retry: false },
    },
  });
}

const protegida = (elemento: ReactNode, permiso?: string) => <RutaProtegida permiso={permiso}>{elemento}</RutaProtegida>;

/** Raíz única: un solo proveedor de sesión para todas las rutas. */
function Raiz() {
  return (
    <ProveedorSesion>
      <Outlet />
    </ProveedorSesion>
  );
}

const hijas: RouteObject[] = [
  {
    element: <AuthLayout />,
    children: [
      { path: "/login", element: <PaginaLogin /> },
      {
        path: "/cambiar-clave",
        element: (
          <RutaCambioClave>
            <PaginaCambioClave />
          </RutaCambioClave>
        ),
      },
    ],
  },
  {
    element: protegida(<AppLayout />),
    children: [
      { path: "/", element: <PaginaTablero /> },
      { path: "/contactos", element: protegida(<PaginaContactos />, "contactos.view_contacto") },
      { path: "/contactos/:nip", element: protegida(<PaginaFichaContacto />, "contactos.view_contacto") },
      { path: "/motos", element: protegida(<PaginaMotos />, "vehiculos.view_moto") },
      { path: "/motos/:placa", element: protegida(<PaginaDetalleMoto />, "vehiculos.view_moto") },
      { path: "/revisiones", element: protegida(<PaginaRevisiones />, "revisiones.view_revision") },
      { path: "/soat", element: protegida(<PaginaSoat />, "revisiones.view_soat") },
      { path: "/llamadas", element: protegida(<PaginaLlamadas />, "llamadas.view_llamadartm") },
      { path: "/catalogos", element: protegida(<PaginaCatalogos />, "vehiculos.view_marca") },
      { path: "/usuarios", element: protegida(<PaginaUsuarios />, "cuentas.view_usuario") },
      { path: "/mi-cuenta", element: <PaginaMiCuenta /> },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
];

export const rutas: RouteObject[] = [{ element: <Raiz />, children: hijas }];

const router = createBrowserRouter(rutas);

export function App({ queryClient = crearQueryClient() }: { queryClient?: QueryClient }) {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
