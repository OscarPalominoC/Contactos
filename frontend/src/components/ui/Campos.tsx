import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

interface Comunes {
  etiqueta: string;
  error?: string;
  ayuda?: string;
  obligatorio?: boolean;
}

function Envoltorio({
  id,
  etiqueta,
  error,
  ayuda,
  obligatorio,
  children,
}: Comunes & { id: string; children: ReactNode }) {
  return (
    <div className="flex w-full flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium">
        {etiqueta}
        {obligatorio && (
          <span aria-hidden="true" className="text-marca-rojo">
            {" "}
            *
          </span>
        )}
        {obligatorio && <span className="sr-only"> (obligatorio)</span>}
      </label>
      {children}
      {ayuda && !error && (
        <p id={`${id}-ayuda`} className="texto-secundario text-xs">
          {ayuda}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="flex items-center gap-1 text-xs font-semibold text-[#a3161d] dark:text-[#ff8a8f]">
          <span aria-hidden="true">⚠</span> {error}
        </p>
      )}
    </div>
  );
}

function descripciones(id: string, error?: string, ayuda?: string): string | undefined {
  return [ayuda && !error ? `${id}-ayuda` : null, error ? `${id}-error` : null].filter(Boolean).join(" ") || undefined;
}

export function CampoTexto({ etiqueta, error, ayuda, obligatorio, ...props }: Comunes & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <Envoltorio id={id} etiqueta={etiqueta} error={error} ayuda={ayuda} obligatorio={obligatorio}>
      <input
        id={id}
        className="glass-input"
        aria-invalid={Boolean(error)}
        aria-describedby={descripciones(id, error, ayuda)}
        required={obligatorio}
        {...props}
      />
    </Envoltorio>
  );
}

export function CampoSeleccion({
  etiqueta,
  error,
  ayuda,
  obligatorio,
  opciones,
  vacio,
  ...props
}: Comunes &
  SelectHTMLAttributes<HTMLSelectElement> & { opciones: readonly { valor: string; texto: string }[]; vacio?: string }) {
  const id = useId();
  return (
    <Envoltorio id={id} etiqueta={etiqueta} error={error} ayuda={ayuda} obligatorio={obligatorio}>
      <select
        id={id}
        className="glass-input"
        aria-invalid={Boolean(error)}
        aria-describedby={descripciones(id, error, ayuda)}
        required={obligatorio}
        {...props}
      >
        {vacio !== undefined && <option value="">{vacio}</option>}
        {opciones.map((opcion) => (
          <option key={opcion.valor} value={opcion.valor}>
            {opcion.texto}
          </option>
        ))}
      </select>
    </Envoltorio>
  );
}

export function CampoAreaTexto({
  etiqueta,
  error,
  ayuda,
  obligatorio,
  ...props
}: Comunes & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId();
  return (
    <Envoltorio id={id} etiqueta={etiqueta} error={error} ayuda={ayuda} obligatorio={obligatorio}>
      <textarea
        id={id}
        className="glass-input min-h-24"
        aria-invalid={Boolean(error)}
        aria-describedby={descripciones(id, error, ayuda)}
        required={obligatorio}
        {...props}
      />
    </Envoltorio>
  );
}
