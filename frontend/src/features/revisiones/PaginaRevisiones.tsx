import { Ban, Pencil, Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { z } from "zod";

import { useSesion } from "../../app/sesion";
import { Boton } from "../../components/ui/Boton";
import { CampoSeleccion, CampoTexto } from "../../components/ui/Campos";
import { Confirmacion } from "../../components/ui/Dialogo";
import { EnlaceContacto, EnlacePlaca } from "../../components/ui/Enlaces";
import { EstadoVacio } from "../../components/ui/EstadoVacio";
import { InsigniaDocumento } from "../../components/ui/Insignias";
import { EncabezadoPagina, Tarjeta } from "../../components/ui/Pagina";
import { TablaPaginada, type Columna } from "../../components/ui/TablaPaginada";
import { revisionSchema, type Revision } from "../../services/esquemas";
import { useAccion, useGuardar, useLista } from "../../utils/consultas";
import { formatearFecha, hoyBogota, normalizarPlaca } from "../../utils/formatters";
import { MINIMO_BUSQUEDA, useRetardo, useTitulo } from "../../utils/hooks";
import { DialogoFormulario, fechaOpcional, nulo, useFormulario } from "../formulario";

export const OPCIONES_ESTADO_FILTRO = [
  { valor: "VIGENTE", texto: "Vigente" },
  { valor: "VENCIDO", texto: "Vencido" },
  { valor: "DUPLICADO", texto: "Duplicado" },
  { valor: "ANULADO", texto: "Anulado" },
];

export const OPCIONES_ESTADO_EDITABLE = [
  { valor: "VIGENTE", texto: "Vigente (se calcula con el vencimiento)" },
  { valor: "DUPLICADO", texto: "Duplicado" },
];

const formularioRevisionSchema = z.object({
  certificado: z.string().trim().min(1, "Escriba el número de certificado."),
  placa: z
    .string()
    .transform(normalizarPlaca)
    .pipe(z.string().regex(/^[A-Z0-9]{5,6}$/, "Escriba una placa válida, por ejemplo ABC12D.")),
  fecha_certificado: fechaOpcional.refine((v) => v !== "", "Indique la fecha del certificado."),
  fecha_venc_certificado: fechaOpcional,
  nro_certificado_runt: z.string().trim(),
  nro_solicitud_runt: z.string().trim(),
  nro_autodeclaracion_runt: z.string().trim(),
  estado: z.enum(["VIGENTE", "DUPLICADO"]),
});
type Valores = z.input<typeof formularioRevisionSchema>;

function FormularioRevision({ revision, alCerrar }: { revision: Revision | null | undefined; alCerrar: () => void }) {
  const edicion = Boolean(revision);
  const vacio: Valores = {
    certificado: "",
    placa: "",
    fecha_certificado: hoyBogota(),
    fecha_venc_certificado: "",
    nro_certificado_runt: "",
    nro_solicitud_runt: "",
    nro_autodeclaracion_runt: "",
    estado: "VIGENTE",
  };
  const { valores, setValores, errores, cambiar, validar, erroresServidor } = useFormulario<Valores>(vacio);
  const guardar = useGuardar("revisiones", revisionSchema, {
    id: revision?.certificado,
    invalidar: ["tablero", "ficha"],
    alExito: alCerrar,
  });
  const { reset } = guardar;

  useEffect(() => {
    if (revision === undefined) return;
    reset();
    setValores(
      revision
        ? {
            certificado: revision.certificado,
            placa: revision.placa,
            fecha_certificado: revision.fecha_certificado ?? "",
            fecha_venc_certificado: revision.fecha_venc_certificado ?? "",
            nro_certificado_runt: revision.nro_certificado_runt,
            nro_solicitud_runt: revision.nro_solicitud_runt,
            nro_autodeclaracion_runt: revision.nro_autodeclaracion_runt,
            estado: revision.estado === "DUPLICADO" ? "DUPLICADO" : "VIGENTE",
          }
        : { ...vacio, fecha_certificado: hoyBogota() },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revision, setValores, reset]);

  const enviar = () => {
    const datos = validar(formularioRevisionSchema);
    if (!datos) return;
    const cuerpo: Record<string, unknown> = {
      fecha_certificado: datos.fecha_certificado,
      fecha_venc_certificado: nulo(datos.fecha_venc_certificado),
      nro_certificado_runt: datos.nro_certificado_runt,
      nro_solicitud_runt: datos.nro_solicitud_runt,
      nro_autodeclaracion_runt: datos.nro_autodeclaracion_runt,
      estado: datos.estado,
    };
    if (!edicion) Object.assign(cuerpo, { certificado: datos.certificado, placa: datos.placa });
    guardar.mutate(cuerpo, { onError: erroresServidor });
  };

  return (
    <DialogoFormulario
      abierto={revision !== undefined}
      titulo={edicion ? `Editar revisión ${revision?.certificado}` : "Registrar revisión RTM"}
      alCerrar={alCerrar}
      alEnviar={enviar}
      enviando={guardar.isPending}
      error={guardar.error}
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <CampoTexto etiqueta="Número de certificado" value={valores.certificado} onChange={cambiar("certificado")} error={errores.certificado} disabled={edicion} obligatorio />
        <CampoTexto etiqueta="Placa" value={valores.placa} onChange={cambiar("placa")} error={errores.placa} disabled={edicion} obligatorio />
        <CampoTexto etiqueta="Fecha del certificado" type="date" value={valores.fecha_certificado} onChange={cambiar("fecha_certificado")} error={errores.fecha_certificado} obligatorio />
        <CampoTexto
          etiqueta="Fecha de vencimiento"
          type="date"
          value={valores.fecha_venc_certificado}
          onChange={cambiar("fecha_venc_certificado")}
          error={errores.fecha_venc_certificado}
          ayuda="Si la deja vacía se calcula a un año."
        />
        <CampoTexto etiqueta="Certificado RUNT" value={valores.nro_certificado_runt} onChange={cambiar("nro_certificado_runt")} error={errores.nro_certificado_runt} />
        <CampoTexto etiqueta="Solicitud RUNT" value={valores.nro_solicitud_runt} onChange={cambiar("nro_solicitud_runt")} error={errores.nro_solicitud_runt} />
        <CampoTexto
          etiqueta="Autodeclaración RUNT"
          value={valores.nro_autodeclaracion_runt}
          onChange={cambiar("nro_autodeclaracion_runt")}
          error={errores.nro_autodeclaracion_runt}
        />
        <CampoSeleccion etiqueta="Estado" value={valores.estado} onChange={cambiar("estado")} error={errores.estado} opciones={OPCIONES_ESTADO_EDITABLE} />
      </div>
    </DialogoFormulario>
  );
}

/** Filtros iniciales tomados de la URL (enlaces del tablero). */
export function useFiltrosUrl() {
  const [params] = useSearchParams();
  return {
    estado: params.get("estado") ?? "",
    desde: params.get("vence_desde") ?? "",
    hasta: params.get("vence_hasta") ?? "",
  };
}

export function PaginaRevisiones() {
  useTitulo("Revisiones RTM");
  const { puede } = useSesion();
  const inicial = useFiltrosUrl();
  const [busqueda, setBusqueda] = useState("");
  const [estado, setEstado] = useState(inicial.estado);
  const [desde, setDesde] = useState(inicial.desde);
  const [hasta, setHasta] = useState(inicial.hasta);
  const [editando, setEditando] = useState<Revision | null | undefined>(undefined);
  const [anulando, setAnulando] = useState<Revision | null>(null);
  const q = useRetardo(busqueda).trim();
  // Solo búsqueda: placa o certificado, o un rango de vencimiento (como el que llega desde el tablero).
  const buscando = q.length >= MINIMO_BUSQUEDA || Boolean(desde || hasta);
  const lista = useLista("revisiones", revisionSchema, { q, estado, vence_desde: desde, vence_hasta: hasta }, 25, { habilitada: buscando });
  const { reiniciarPagina } = lista;
  useEffect(() => reiniciarPagina(), [q, estado, desde, hasta, reiniciarPagina]);
  const anular = useAccion("revisiones", "anular", revisionSchema, { invalidar: ["tablero", "ficha"], alExito: () => setAnulando(null) });

  const columnas: Columna<Revision>[] = [
    { clave: "placa", titulo: "Placa", celda: (r) => <EnlacePlaca placa={r.placa} /> },
    { clave: "fecha", titulo: "Vigencia", celda: (r) => formatearFecha(r.fecha_certificado), ordenable: "fecha_certificado" },
    { clave: "vence", titulo: "Vencimiento", celda: (r) => formatearFecha(r.fecha_venc_certificado), ordenable: "fecha_venc_certificado" },
    { clave: "estado", titulo: "Estado", celda: (r) => <InsigniaDocumento estado={r.estado_actual} /> },
    { clave: "propietario", titulo: "Propietario", celda: (r) => <EnlaceContacto nip={r.propietario_nip} nombre={r.propietario_nombre} /> },
    {
      clave: "acciones",
      titulo: "Acciones",
      celda: (r) =>
        puede("revisiones.change_revision") && r.estado !== "ANULADO" ? (
          <div className="flex flex-wrap gap-1">
            <Boton
              variante="texto"
              onClick={() => setEditando(r)}
              aria-label={`Editar revisión de ${r.placa} que vence el ${formatearFecha(r.fecha_venc_certificado)}`}
              icono={<Pencil aria-hidden="true" size={18} />}
            >
              Editar
            </Boton>
            <Boton
              variante="texto"
              onClick={() => setAnulando(r)}
              aria-label={`Anular revisión de ${r.placa} que vence el ${formatearFecha(r.fecha_venc_certificado)}`}
              icono={<Ban aria-hidden="true" size={18} />}
            >
              Anular
            </Boton>
          </div>
        ) : (
          "—"
        ),
    },
  ];

  return (
    <>
      <EncabezadoPagina
        titulo="Revisiones RTM"
        descripcion="Revisiones técnico-mecánicas y de gases."
        acciones={
          puede("revisiones.add_revision") && (
            <Boton onClick={() => setEditando(null)} icono={<Plus aria-hidden="true" size={18} />}>
              Registrar revisión
            </Boton>
          )
        }
      />
      <Tarjeta>
        <div role="search" className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <CampoTexto
            etiqueta="Buscar por placa o certificado"
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            ayuda={`Al menos ${MINIMO_BUSQUEDA} caracteres.`}
          />
          <CampoSeleccion etiqueta="Estado" value={estado} onChange={(e) => setEstado(e.target.value)} vacio="Todos" opciones={OPCIONES_ESTADO_FILTRO} />
          <CampoTexto etiqueta="Vence desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
          <CampoTexto etiqueta="Vence hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        </div>
        {!buscando ? (
          <EstadoVacio
            titulo="Busque una revisión"
            descripcion="Escriba la placa o el número de certificado, o elija un rango de vencimiento. Para ver el vehículo, haga clic en la placa."
            accion={<Search aria-hidden="true" className="texto-secundario" />}
          />
        ) : (
          <TablaPaginada
            titulo="Revisiones"
            columnas={columnas}
            datos={lista.data}
            cargando={lista.isFetching}
            error={lista.error}
            claveFila={(r) => r.certificado}
            pagina={lista.pagina}
            alCambiarPagina={lista.setPagina}
            orden={lista.orden}
            alOrdenar={lista.setOrden}
          />
        )}
      </Tarjeta>
      <FormularioRevision revision={editando} alCerrar={() => setEditando(undefined)} />
      <Confirmacion
        abierto={anulando !== null}
        titulo="Anular revisión"
        mensaje={
          <p>
            ¿Anular la revisión <strong>{anulando?.certificado}</strong> de la placa <strong>{anulando?.placa}</strong>? El registro
            se conserva marcado como anulado.
          </p>
        }
        textoConfirmar="Anular"
        cargando={anular.isPending}
        alConfirmar={() => anulando && anular.mutate({ id: anulando.certificado })}
        alCerrar={() => setAnulando(null)}
      />
    </>
  );
}
