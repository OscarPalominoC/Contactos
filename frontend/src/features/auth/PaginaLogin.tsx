import { LogIn } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { useSesion } from "../../app/sesion";
import { AvisoError } from "../../components/ui/Aviso";
import { Boton } from "../../components/ui/Boton";
import { CampoTexto } from "../../components/ui/Campos";
import { normalizarError, type ApiError } from "../../services/apiClient";
import { useTitulo } from "../../utils/hooks";

const loginSchema = z.object({
  nip: z.string().trim().min(1, "Escriba su usuario (documento)."),
  password: z.string().min(1, "Escriba su contraseña."),
});

export function PaginaLogin() {
  useTitulo("Iniciar sesión");
  const { iniciar, estado, usuario } = useSesion();
  const navegar = useNavigate();
  const ubicacion = useLocation();
  const [nip, setNip] = useState("");
  const [password, setPassword] = useState("");
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [error, setError] = useState<ApiError | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (estado === "autenticado" && usuario) {
    return <Navigate to={usuario.debe_cambiar_clave ? "/cambiar-clave" : "/"} replace />;
  }

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault();
    const resultado = loginSchema.safeParse({ nip, password });
    if (!resultado.success) {
      setErrores(Object.fromEntries(resultado.error.issues.map((i) => [String(i.path[0]), i.message])));
      return;
    }
    setErrores({});
    setError(null);
    setEnviando(true);
    try {
      const yo = await iniciar(resultado.data.nip, resultado.data.password);
      const destino = (ubicacion.state as { desde?: string } | null)?.desde ?? "/";
      navegar(yo.debe_cambiar_clave ? "/cambiar-clave" : destino, { replace: true });
    } catch (e) {
      setError(normalizarError(e));
      setPassword("");
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="glass-card w-full max-w-md p-6 lg:p-8">
      <div className="mb-6 flex items-center gap-3">
        <img src="/favicon.svg" alt="" width={48} height={48} />
        <div>
          <h1 className="text-2xl uppercase">Check Contactos</h1>
          <p className="texto-secundario text-sm">CDA Check Motos</p>
        </div>
      </div>
      <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
        <AvisoError error={error} />
        <CampoTexto
          etiqueta="Usuario (documento)"
          name="nip"
          autoComplete="username"
          inputMode="text"
          value={nip}
          onChange={(e) => setNip(e.target.value)}
          error={errores.nip}
          obligatorio
        />
        <CampoTexto
          etiqueta="Contraseña"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errores.password}
          obligatorio
        />
        <Boton type="submit" cargando={enviando} textoCargando="Ingresando…" icono={<LogIn aria-hidden="true" size={18} />}>
          Ingresar
        </Boton>
      </form>
      <p className="texto-secundario mt-6 text-xs">
        Aviso de privacidad: este sistema trata datos personales de clientes de CDA Check Motos únicamente para
        recordatorios de vencimiento de RTM y SOAT y para fidelización. El acceso queda registrado. Después de 5
        intentos fallidos la cuenta se bloquea durante 1 hora.
      </p>
    </div>
  );
}
