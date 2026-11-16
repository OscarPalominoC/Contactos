import { AlertTriangle } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { CampoCumpleanos } from "../../components/ui/CampoCumpleanos";
import { CampoSeleccion, CampoTexto } from "../../components/ui/Campos";
import { contactoSchema, type Contacto } from "../../services/esquemas";
import { useGuardar } from "../../utils/consultas";
import { esCumpleanosValido, nombreMes } from "../../utils/formatters";
import { DialogoFormulario, useFormulario } from "../formulario";
import { cuerpoContacto, formularioContactoSchema, type FormularioContacto } from "./esquemas";

const VACIO: FormularioContacto = {
  nip: "",
  nombre: "",
  telefono: "",
  celular: "",
  correo: "",
  direccion: "",
  dia_nac: "",
  mes_nac: "",
  estado: "habilitado",
  contactar_cumpleanos: true,
  contactar_soat: true,
  contactar_rtm: true,
};

type Canal = "contactar_cumpleanos" | "contactar_soat" | "contactar_rtm";
export const CANALES: { campo: Canal; texto: string }[] = [
  { campo: "contactar_cumpleanos", texto: "Cumpleaños" },
  { campo: "contactar_soat", texto: "SOAT" },
  { campo: "contactar_rtm", texto: "RTM" },
];

/** Un cumpleaños imposible del legado (p. ej. 31 de febrero) se descarta del formulario y se avisa. */
function desdeContacto(c: Contacto): { valores: FormularioContacto; invalido: string | null } {
  const tieneFecha = c.dia_nac != null && c.mes_nac != null;
  const invalido = tieneFecha && !esCumpleanosValido(c.dia_nac, c.mes_nac) ? `${c.dia_nac} de ${nombreMes(c.mes_nac).toLowerCase()}` : null;
  return {
    invalido,
    valores: {
      nip: c.nip,
      nombre: c.nombre,
      telefono: c.telefono,
      celular: c.celular,
      correo: c.correo,
      direccion: c.direccion,
      dia_nac: !invalido && c.dia_nac ? String(c.dia_nac) : "",
      mes_nac: !invalido && c.mes_nac ? String(c.mes_nac) : "",
      estado: c.estado,
      contactar_cumpleanos: invalido ? false : c.contactar_cumpleanos,
      contactar_soat: c.contactar_soat,
      contactar_rtm: c.contactar_rtm,
    },
  };
}

/** Casilla maestra + una casilla por canal. La maestra queda «indeterminada» si solo algunos están marcados. */
function PreferenciasContacto({
  valores,
  bloqueados,
  alCambiar,
}: {
  valores: Record<Canal, boolean>;
  bloqueados: Partial<Record<Canal, string>>;
  alCambiar: (cambios: Partial<Record<Canal, boolean>>) => void;
}) {
  const idAyuda = useId();
  const maestro = useRef<HTMLInputElement>(null);
  const disponibles = CANALES.filter((c) => !bloqueados[c.campo]);
  const marcados = disponibles.filter((c) => valores[c.campo]).length;
  const todos = disponibles.length > 0 && marcados === disponibles.length;
  const algunos = marcados > 0 && !todos;

  useEffect(() => {
    if (maestro.current) maestro.current.indeterminate = algunos;
  }, [algunos]);

  return (
    <fieldset className="glass-subtle col-span-full rounded-xl p-3" aria-describedby={idAyuda}>
      <legend className="px-1 text-sm font-semibold">Preferencias de contacto</legend>
      <p id={idAyuda} className="texto-secundario mb-2 text-xs">
        Canales por los que el cliente autoriza ser llamado.
      </p>
      <label className="casilla font-semibold">
        <input
          ref={maestro}
          type="checkbox"
          checked={todos}
          aria-checked={algunos ? "mixed" : todos}
          disabled={disponibles.length === 0}
          onChange={() => alCambiar(Object.fromEntries(disponibles.map((c) => [c.campo, !todos])))}
        />
        Seleccionar todos los canales
      </label>
      <div className="grid grid-cols-1 gap-1 pl-6 sm:grid-cols-3">
        {CANALES.map((c) => (
          <label key={c.campo} className="casilla" title={bloqueados[c.campo]}>
            <input
              type="checkbox"
              checked={valores[c.campo]}
              disabled={Boolean(bloqueados[c.campo])}
              onChange={(e) => alCambiar({ [c.campo]: e.target.checked })}
            />
            {c.texto}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/** `contacto`: undefined = cerrado, null = nuevo, objeto = edición. */
export function FormularioContactoDialogo({ contacto, alCerrar }: { contacto: Contacto | null | undefined; alCerrar: () => void }) {
  const edicion = Boolean(contacto);
  const { valores, setValores, errores, cambiar, validar, erroresServidor } = useFormulario<FormularioContacto>(VACIO);
  const [cumpleInvalido, setCumpleInvalido] = useState<string | null>(null);
  const guardar = useGuardar("contactos", contactoSchema, {
    id: contacto?.nip,
    invalidar: ["ficha", "tablero"],
    alExito: alCerrar,
  });
  const { reset } = guardar;

  useEffect(() => {
    if (contacto !== undefined) {
      const inicial = contacto ? desdeContacto(contacto) : { valores: VACIO, invalido: null };
      setValores(inicial.valores);
      setCumpleInvalido(inicial.invalido);
      reset();
    }
  }, [contacto, setValores, reset]);

  const enviar = () => {
    const datos = validar(formularioContactoSchema);
    if (!datos) return;
    guardar.mutate(cuerpoContacto(datos, edicion), { onError: erroresServidor });
  };

  const cumpleCompleto = valores.dia_nac !== "" && valores.mes_nac !== "";
  // Sin fecha válida no hay a quién felicitar: el canal se bloquea hasta rectificar la fecha.
  const bloqueoCumple = cumpleInvalido && !cumpleCompleto ? "Corrija primero la fecha de cumpleaños." : undefined;

  return (
    <DialogoFormulario
      abierto={contacto !== undefined}
      titulo={edicion ? "Editar contacto" : "Nuevo contacto"}
      alCerrar={alCerrar}
      alEnviar={enviar}
      enviando={guardar.isPending}
      error={guardar.error}
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <CampoTexto
          etiqueta="Documento"
          value={valores.nip}
          onChange={cambiar("nip")}
          error={errores.nip}
          disabled={edicion}
          ayuda={edicion ? "El documento no se puede cambiar." : undefined}
          obligatorio
        />
        <CampoTexto etiqueta="Nombre completo" autoComplete="name" value={valores.nombre} onChange={cambiar("nombre")} error={errores.nombre} obligatorio />
        <CampoTexto etiqueta="Celular" type="tel" autoComplete="tel" value={valores.celular} onChange={cambiar("celular")} error={errores.celular} />
        <CampoTexto etiqueta="Teléfono fijo" type="tel" autoComplete="tel" value={valores.telefono} onChange={cambiar("telefono")} error={errores.telefono} />
        <CampoTexto etiqueta="Correo" type="email" autoComplete="email" value={valores.correo} onChange={cambiar("correo")} error={errores.correo} />
        <CampoTexto
          etiqueta="Dirección"
          autoComplete="street-address"
          value={valores.direccion}
          onChange={cambiar("direccion")}
          error={errores.direccion}
        />
        {cumpleInvalido && (
          <div role="alert" className="insignia-aviso col-span-full flex items-start gap-2 rounded-lg border p-3 text-sm">
            <AlertTriangle aria-hidden="true" size={18} className="mt-0.5 shrink-0" />
            <span>
              El cumpleaños registrado ({cumpleInvalido}) no existe en el calendario. Se guardará sin cumpleaños y sin llamadas de
              cumpleaños, salvo que lo rectifique abajo.
            </span>
          </div>
        )}
        <CampoCumpleanos
          etiqueta="Fecha de cumpleaños"
          dia={valores.dia_nac ? Number(valores.dia_nac) : null}
          mes={valores.mes_nac ? Number(valores.mes_nac) : null}
          alCambiar={(dia, mes) => setValores((v) => ({ ...v, dia_nac: dia ? String(dia) : "", mes_nac: mes ? String(mes) : "" }))}
          error={errores.dia_nac ?? errores.mes_nac}
          ayuda="Solo día y mes; el año no se guarda."
        />
        <CampoSeleccion
          etiqueta="Estado"
          value={valores.estado}
          onChange={cambiar("estado")}
          error={errores.estado}
          opciones={[
            { valor: "habilitado", texto: "Habilitado" },
            { valor: "inhabilitado", texto: "Inhabilitado (no se le llama)" },
          ]}
        />
        <PreferenciasContacto
          valores={valores}
          bloqueados={{ contactar_cumpleanos: bloqueoCumple }}
          alCambiar={(cambios) => setValores((v) => ({ ...v, ...cambios }))}
        />
      </div>
    </DialogoFormulario>
  );
}
