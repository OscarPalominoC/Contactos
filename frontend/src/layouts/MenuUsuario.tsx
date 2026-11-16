import { ChevronDown, KeyRound, UserPen } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { useSesion } from "../app/sesion";
import { CampoTexto } from "../components/ui/Campos";
import { Dialogo } from "../components/ui/Dialogo";
import { FormularioCambioClave } from "../features/auth/PaginaCambioClave";
import { DialogoFormulario } from "../features/formulario";
import { nuevoId, normalizarError, type ApiError } from "../services/apiClient";
import { yoSchema } from "../services/esquemas";
import { actualizar } from "../services/recursos";
import { primerNombre } from "../utils/formatters";

function DialogoNombre({ abierto, alCerrar }: { abierto: boolean; alCerrar: () => void }) {
  const { usuario, recargar } = useSesion();
  const [nombre, setNombre] = useState("");
  const [errorCampo, setErrorCampo] = useState<string | undefined>();
  const [error, setError] = useState<ApiError | null>(null);
  const [enviando, setEnviando] = useState(false);
  const clave = useRef(nuevoId());

  useEffect(() => {
    if (abierto) {
      setNombre(usuario?.nombre ?? "");
      setErrorCampo(undefined);
      setError(null);
      clave.current = nuevoId();
    }
  }, [abierto, usuario?.nombre]);

  const enviar = async () => {
    const limpio = nombre.trim().replace(/\s+/g, " ");
    if (limpio.length < 3) {
      setErrorCampo("Escriba su nombre (mínimo 3 letras).");
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      await actualizar("/auth/yo", yoSchema, { nombre: limpio }, clave.current);
      await recargar();
      alCerrar();
    } catch (e) {
      const apiError = normalizarError(e);
      setError(apiError);
      setErrorCampo(apiError.erroresDeCampo().nombre);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <DialogoFormulario abierto={abierto} titulo="Cambiar nombre" alCerrar={alCerrar} alEnviar={() => void enviar()} enviando={enviando} error={error}>
      <CampoTexto
        etiqueta="Nombre completo"
        autoComplete="name"
        value={nombre}
        onChange={(e) => setNombre(e.target.value)}
        error={errorCampo}
        ayuda="En la barra superior se muestra solo el primer nombre."
        obligatorio
      />
    </DialogoFormulario>
  );
}

/**
 * Botón con el primer nombre que despliega las opciones de la cuenta (patrón disclosure:
 * aria-expanded + aria-controls). Escape o clic fuera lo cierran y el foco vuelve al botón.
 */
export function MenuUsuario() {
  const { usuario } = useSesion();
  const idPanel = useId();
  const raiz = useRef<HTMLDivElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const primeraOpcion = useRef<HTMLButtonElement>(null);
  const [abierto, setAbierto] = useState(false);
  const [dialogo, setDialogo] = useState<"nombre" | "clave" | null>(null);

  useEffect(() => {
    if (!abierto) return;
    primeraOpcion.current?.focus();
    const alPulsar = (evento: MouseEvent) => {
      if (raiz.current && !raiz.current.contains(evento.target as Node)) setAbierto(false);
    };
    document.addEventListener("mousedown", alPulsar);
    return () => document.removeEventListener("mousedown", alPulsar);
  }, [abierto]);

  const elegir = (opcion: "nombre" | "clave") => {
    setAbierto(false);
    setDialogo(opcion);
  };

  return (
    <div
      ref={raiz}
      className="relative"
      onKeyDown={(e) => {
        if (e.key === "Escape" && abierto) {
          e.preventDefault();
          setAbierto(false);
          boton.current?.focus();
        }
      }}
    >
      <button
        ref={boton}
        type="button"
        className="boton-usuario"
        aria-expanded={abierto}
        aria-controls={idPanel}
        onClick={() => setAbierto((a) => !a)}
      >
        <span>{primerNombre(usuario?.nombre)}</span>
        <ChevronDown aria-hidden="true" size={16} className={`transition-transform ${abierto ? "rotate-180" : ""}`} />
      </button>

      <div id={idPanel} hidden={!abierto} className="glass-popover menu-usuario absolute right-0 top-full z-50 mt-2 p-2">
        <div className="border-b border-[var(--glass-border)] px-3 pb-2 pt-1">
          <p className="text-sm font-semibold">{usuario?.nombre}</p>
          <p className="texto-secundario text-xs capitalize">{usuario?.rol}</p>
        </div>
        <ul className="mt-1 flex flex-col">
          <li>
            <button ref={primeraOpcion} type="button" className="opcion-menu" onClick={() => elegir("nombre")}>
              <UserPen aria-hidden="true" size={18} />
              Cambiar nombre
            </button>
          </li>
          <li>
            <button type="button" className="opcion-menu" onClick={() => elegir("clave")}>
              <KeyRound aria-hidden="true" size={18} />
              Actualizar contraseña
            </button>
          </li>
        </ul>
      </div>

      <DialogoNombre abierto={dialogo === "nombre"} alCerrar={() => setDialogo(null)} />
      <Dialogo abierto={dialogo === "clave"} titulo="Actualizar contraseña" alCerrar={() => setDialogo(null)}>
        <FormularioCambioClave />
      </Dialogo>
    </div>
  );
}
