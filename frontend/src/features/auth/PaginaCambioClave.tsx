import { Check, KeyRound, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { useSesion } from "../../app/sesion";
import { Aviso, AvisoError } from "../../components/ui/Aviso";
import { Boton } from "../../components/ui/Boton";
import { CampoTexto } from "../../components/ui/Campos";
import { normalizarError, type ApiError } from "../../services/apiClient";
import { useTitulo } from "../../utils/hooks";

export interface Regla {
  texto: string;
  cumple: boolean;
}

export const LONGITUD_MINIMA_CLAVE = 5;

/**
 * Reglas de la nueva clave, visibles antes de escribirla. El servidor valida de nuevo.
 * Política de desarrollo local: solo longitud mínima; puede incluir nombre o documento.
 */
export function evaluarClave(clave: string, confirmacion: string): Regla[] {
  return [
    { texto: `Al menos ${LONGITUD_MINIMA_CLAVE} caracteres`, cumple: clave.length >= LONGITUD_MINIMA_CLAVE },
    { texto: "La confirmación coincide", cumple: clave.length > 0 && clave === confirmacion },
  ];
}

export function nivelFortaleza(clave: string): { valor: number; texto: string } {
  let puntos = 0;
  if (clave.length >= 12) puntos++;
  if (clave.length >= 16) puntos++;
  if (/[a-z]/.test(clave) && /[A-Z]/.test(clave)) puntos++;
  if (/\d/.test(clave)) puntos++;
  if (/[^a-zA-Z0-9]/.test(clave)) puntos++;
  const textos = ["Muy débil", "Débil", "Aceptable", "Buena", "Fuerte", "Muy fuerte"];
  return { valor: puntos, texto: textos[puntos] ?? "Muy débil" };
}

export function FormularioCambioClave({ obligatorio = false }: { obligatorio?: boolean }) {
  const { cambiarClave } = useSesion();
  const navegar = useNavigate();
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [errorCampo, setErrorCampo] = useState<string | undefined>();
  const [exito, setExito] = useState(false);
  const [enviando, setEnviando] = useState(false);

  const reglas = evaluarClave(nueva, confirmacion);
  const fortaleza = nivelFortaleza(nueva);
  const valida = reglas.every((r) => r.cumple) && actual.length > 0;

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault();
    if (!valida) return;
    setEnviando(true);
    setError(null);
    setErrorCampo(undefined);
    try {
      await cambiarClave(actual, nueva);
      setExito(true);
      setActual("");
      setNueva("");
      setConfirmacion("");
      if (obligatorio) navegar("/", { replace: true });
    } catch (e) {
      const apiError = normalizarError(e);
      setError(apiError);
      setErrorCampo(apiError.erroresDeCampo().clave_nueva);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
      {exito && <Aviso tipo="exito">Su clave se cambió correctamente.</Aviso>}
      <AvisoError error={error} />
      <CampoTexto
        etiqueta={obligatorio ? "Clave temporal" : "Clave actual"}
        type="password"
        autoComplete="current-password"
        value={actual}
        onChange={(e) => setActual(e.target.value)}
        obligatorio
      />
      <CampoTexto
        etiqueta="Nueva clave"
        type="password"
        autoComplete="new-password"
        value={nueva}
        onChange={(e) => setNueva(e.target.value)}
        error={errorCampo}
        obligatorio
      />
      <div>
        <div className="flex items-center justify-between text-sm">
          <span>Fortaleza</span>
          <span className="font-semibold">{nueva ? fortaleza.texto : "—"}</span>
        </div>
        <meter min={0} max={5} low={2} high={4} optimum={5} value={fortaleza.valor} className="h-2 w-full" aria-label="Fortaleza de la nueva clave">
          {fortaleza.texto}
        </meter>
      </div>
      <CampoTexto
        etiqueta="Confirmar nueva clave"
        type="password"
        autoComplete="new-password"
        value={confirmacion}
        onChange={(e) => setConfirmacion(e.target.value)}
        obligatorio
      />
      <ul aria-label="Requisitos de la nueva clave" className="flex flex-col gap-1 text-sm">
        {reglas.map((regla) => (
          <li key={regla.texto} className="flex items-center gap-2">
            {regla.cumple ? (
              <Check aria-hidden="true" size={16} className="text-emerald-700 dark:text-emerald-400" />
            ) : (
              <X aria-hidden="true" size={16} className="text-[#a3161d] dark:text-[#ff8a8f]" />
            )}
            <span>
              {regla.texto}
              <span className="sr-only">{regla.cumple ? ": cumple" : ": pendiente"}</span>
            </span>
          </li>
        ))}
      </ul>
      <Boton type="submit" cargando={enviando} disabled={!valida} icono={<KeyRound aria-hidden="true" size={18} />}>
        Cambiar clave
      </Boton>
    </form>
  );
}

export function PaginaCambioClave() {
  useTitulo("Cambiar clave temporal");
  const { usuario, cerrar } = useSesion();
  return (
    <div className="glass-card w-full max-w-md p-6 lg:p-8">
      <h1 className="text-2xl uppercase">Cambie su clave</h1>
      <p className="texto-secundario mt-2 mb-6 text-sm">
        Hola, {usuario?.nombre}. Por seguridad debe reemplazar la clave temporal que le entregaron antes de continuar.
      </p>
      <FormularioCambioClave obligatorio />
      <Boton variante="texto" className="mt-4 w-full" onClick={() => void cerrar()}>
        Cerrar sesión
      </Boton>
    </div>
  );
}
