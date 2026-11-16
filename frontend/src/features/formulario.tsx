import { useState, type FormEvent } from "react";
import { z } from "zod";

import { AvisoError } from "../components/ui/Aviso";
import { Boton } from "../components/ui/Boton";
import { Dialogo } from "../components/ui/Dialogo";
import type { ApiError } from "../services/apiClient";

/** Convierte los issues de Zod en un mapa campo → mensaje. */
export function erroresZod(error: z.ZodError): Record<string, string> {
  const salida: Record<string, string> = {};
  for (const issue of error.issues) {
    const campo = String(issue.path[0] ?? "general");
    salida[campo] ??= issue.message;
  }
  return salida;
}

/** Estado común de un formulario: valores, errores de campo (Zod y del servidor 422). */
export function useFormulario<T extends Record<string, string | boolean>>(inicial: T) {
  const [valores, setValores] = useState<T>(inicial);
  const [errores, setErrores] = useState<Record<string, string>>({});
  const cambiar = (campo: keyof T) => (evento: { target: { value: string } }) =>
    setValores((previo) => ({ ...previo, [campo]: evento.target.value }));
  const validar = <S extends z.ZodTypeAny>(esquema: S): z.infer<S> | null => {
    const resultado = esquema.safeParse(valores);
    if (!resultado.success) {
      setErrores(erroresZod(resultado.error));
      return null;
    }
    setErrores({});
    return resultado.data;
  };
  const erroresServidor = (error: ApiError) => setErrores(error.erroresDeCampo());
  return { valores, setValores, errores, cambiar, validar, erroresServidor };
}

/** Diálogo de formulario con envío protegido contra doble clic. */
export function DialogoFormulario({
  abierto,
  titulo,
  alCerrar,
  alEnviar,
  enviando,
  error,
  textoEnviar = "Guardar",
  children,
}: {
  abierto: boolean;
  titulo: string;
  alCerrar: () => void;
  alEnviar: () => void;
  enviando: boolean;
  error: ApiError | null;
  textoEnviar?: string;
  children: React.ReactNode;
}) {
  const enviar = (evento: FormEvent) => {
    evento.preventDefault();
    if (!enviando) alEnviar();
  };
  const idFormulario = `form-${titulo.replace(/\s+/g, "-").toLowerCase()}`;
  return (
    <Dialogo
      abierto={abierto}
      titulo={titulo}
      alCerrar={alCerrar}
      pie={
        <>
          <Boton variante="secundario" onClick={alCerrar} disabled={enviando}>
            Cancelar
          </Boton>
          <Boton type="submit" form={idFormulario} cargando={enviando} textoCargando="Guardando…">
            {textoEnviar}
          </Boton>
        </>
      }
    >
      <form id={idFormulario} onSubmit={enviar} noValidate className="flex flex-col gap-4">
        <AvisoError error={error && error.status !== 422 ? error : null} />
        {error?.status === 422 && Object.keys(error.problema.errors ?? {}).length === 0 && <AvisoError error={error} />}
        {children}
      </form>
    </Dialogo>
  );
}

export const textoOpcional = z.string().trim().max(255);
export const fechaOpcional = z
  .string()
  .trim()
  .refine((v) => v === "" || /^\d{4}-\d{2}-\d{2}$/.test(v), "Use el formato AAAA-MM-DD.");

/** '' → null para enviar fechas vacías a la API. */
export function nulo(valor: string): string | null {
  return valor === "" ? null : valor;
}
