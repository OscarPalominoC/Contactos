import { LogOut, Menu, Moon, Sun, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useSesion } from "../app/sesion";
import { useUi } from "../app/uiStore";
import { Aviso } from "../components/ui/Aviso";
import { Boton } from "../components/ui/Boton";
import { MenuUsuario } from "./MenuUsuario";

interface Enlace {
  a: string;
  texto: string;
  permiso?: string;
}

const ENLACES: Enlace[] = [
  { a: "/", texto: "Tablero" },
  { a: "/contactos", texto: "Contactos", permiso: "contactos.view_contacto" },
  { a: "/motos", texto: "Motos", permiso: "vehiculos.view_moto" },
  { a: "/revisiones", texto: "Revisiones RTM", permiso: "revisiones.view_revision" },
  { a: "/soat", texto: "SOAT", permiso: "revisiones.view_soat" },
  { a: "/llamadas", texto: "Llamadas", permiso: "llamadas.view_llamadartm" },
  { a: "/catalogos", texto: "Marcas y líneas", permiso: "vehiculos.view_marca" },
  { a: "/usuarios", texto: "Usuarios", permiso: "cuentas.view_usuario" },
];

const AVISO_MS = 60 * 1000;
const INTERVALO_MIN_ACTIVIDAD_MS = 5 * 1000;

/** Minutos de inactividad configurados; 0 (por defecto) desactiva el cierre automático. */
function inactividadMs(): number {
  const minutos = Number(import.meta.env.VITE_INACTIVIDAD_MINUTOS ?? 0);
  return Number.isFinite(minutos) && minutos > 0 ? minutos * 60_000 : 0;
}

/** Cierra la sesión por inactividad avisando 60 s antes, con opción de prorrogar (WCAG 2.2.1). Desactivado por defecto. */
function useInactividad(alExpirar: () => void) {
  const [aviso, setAviso] = useState(false);
  const temporizadores = useRef<number[]>([]);
  const reiniciar = useRef<() => void>(() => undefined);
  // Referencia al callback: así el efecto no se vuelve a montar en cada render y los temporizadores no se reinician.
  const expirar = useRef(alExpirar);
  expirar.current = alExpirar;

  useEffect(() => {
    const total = inactividadMs();
    if (total === 0) return;
    const limpiar = () => temporizadores.current.forEach((t) => window.clearTimeout(t));
    let ultimoReinicio = Date.now();
    reiniciar.current = () => {
      limpiar();
      setAviso(false);
      ultimoReinicio = Date.now();
      temporizadores.current = [
        window.setTimeout(() => setAviso(true), Math.max(total - AVISO_MS, 0)),
        window.setTimeout(() => expirar.current(), total),
      ];
    };
    reiniciar.current();
    const actividad = (evento: Event) => {
      if (document.querySelector("[data-aviso-inactividad]")) return;
      // Eventos continuos (rueda, desplazamiento, ratón) se limitan para no reprogramar temporizadores sin parar.
      const continuo = evento.type === "wheel" || evento.type === "scroll" || evento.type === "mousemove";
      if (continuo && Date.now() - ultimoReinicio < INTERVALO_MIN_ACTIVIDAD_MS) return;
      reiniciar.current();
    };
    const eventos = ["keydown", "pointerdown", "wheel", "scroll", "mousemove"] as const;
    eventos.forEach((e) => window.addEventListener(e, actividad, { passive: true, capture: e === "scroll" }));
    return () => {
      limpiar();
      eventos.forEach((e) => window.removeEventListener(e, actividad, { capture: e === "scroll" }));
    };
  }, []);

  return { aviso, prorrogar: () => reiniciar.current() };
}

export function AppLayout() {
  const { cerrar, puede } = useSesion();
  const { tema, alternarTema, menuAbierto, alternarMenu, cerrarMenu } = useUi();
  const ubicacion = useLocation();
  const principal = useRef<HTMLElement>(null);
  const { aviso, prorrogar } = useInactividad(() => void cerrar());

  // Al navegar, el foco pasa al contenido (anuncia el cambio de página). En la carga inicial no se mueve,
  // para que el primer Tab llegue al enlace «Saltar al contenido principal» (WCAG 2.4.1).
  const primeraCarga = useRef(true);
  useEffect(() => {
    cerrarMenu();
    if (primeraCarga.current) {
      primeraCarga.current = false;
      return;
    }
    principal.current?.focus();
  }, [ubicacion.pathname, cerrarMenu]);

  const enlaces = ENLACES.filter((enlace) => !enlace.permiso || puede(enlace.permiso));

  return (
    <div className="relative flex min-h-screen flex-col">
      {/* Fondo ambiental decorativo: orbes fluidos en colores Check Ltda. que potencian el efecto Glassmorphism */}
      <div className="liquid-ambient-bg" aria-hidden="true">
        <div className="liquid-orb liquid-orb-red" />
        <div className="liquid-orb liquid-orb-blue" />
        <div className="liquid-orb liquid-orb-yellow" />
      </div>

      <a href="#contenido" className="salto-contenido">
        Saltar al contenido principal
      </a>

      {/* Barra superior de vidrio: marca, navegación en texto (sin cajas) y acciones con icono */}
      <header className="glass-navbar sticky top-0 z-30 w-full">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-2 px-3 sm:gap-4 sm:px-6 lg:px-8">
          <div className="flex shrink-0 items-center gap-2.5">
            <img src="/logo-check.png" alt="" width={36} height={36} className="h-9 w-9 object-contain" />
            {/* En móvil solo se ve el logo; el nombre sigue disponible para lectores de pantalla */}
            <span className="marca-texto font-heading text-lg font-extrabold tracking-wide text-marca-rojo">CHECK MOTOS</span>
          </div>

          <nav
            id="menu-principal"
            aria-label="Principal"
            className={`nav-principal glass-popover ${menuAbierto ? "nav-abierta" : ""}`}
          >
            <ul className="flex flex-col xl:h-16 xl:flex-row xl:items-stretch xl:justify-center xl:gap-1">
              {enlaces.map(({ a, texto }) => (
                <li key={a} className="xl:flex">
                  <NavLink to={a} end={a === "/"} className="enlace-nav">
                    {texto}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          <div className="ml-auto flex shrink-0 items-center gap-1 xl:ml-0">
            <button
              type="button"
              className="btn-icono"
              onClick={alternarTema}
              aria-label={tema === "claro" ? "Activar modo oscuro" : "Activar modo claro"}
              title={tema === "claro" ? "Activar modo oscuro" : "Activar modo claro"}
            >
              {tema === "claro" ? <Moon aria-hidden="true" size={20} /> : <Sun aria-hidden="true" size={20} />}
            </button>
            <MenuUsuario />
            <button type="button" className="btn-icono" onClick={() => void cerrar()} aria-label="Cerrar sesión" title="Cerrar sesión">
              <LogOut aria-hidden="true" size={20} />
            </button>
            <button
              type="button"
              className="btn-icono boton-menu"
              onClick={alternarMenu}
              aria-expanded={menuAbierto}
              aria-controls="menu-principal"
              aria-label="Menú"
              title="Menú"
            >
              {menuAbierto ? <X aria-hidden="true" size={22} /> : <Menu aria-hidden="true" size={22} />}
            </button>
          </div>
        </div>
      </header>

      {/* Contenido principal */}
      <main id="contenido" ref={principal} tabIndex={-1} className="relative z-10 flex-1 p-4 lg:p-8 max-w-7xl mx-auto w-full outline-none">
        {aviso && (
          <div data-aviso-inactividad className="mb-4">
            <Aviso tipo="info">
              <p>Su sesión se cerrará en 1 minuto por inactividad.</p>
              <Boton variante="azul" className="mt-2" onClick={prorrogar}>
                Seguir conectado
              </Boton>
            </Aviso>
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}

export function AuthLayout() {
  return (
    <div className="relative flex min-h-screen items-center justify-center p-4">
      <div className="liquid-ambient-bg" aria-hidden="true">
        <div className="liquid-orb liquid-orb-red" />
        <div className="liquid-orb liquid-orb-blue" />
        <div className="liquid-orb liquid-orb-yellow" />
      </div>
      <main id="contenido" className="relative z-10 w-full max-w-md">
        <Outlet />
      </main>
    </div>
  );
}
