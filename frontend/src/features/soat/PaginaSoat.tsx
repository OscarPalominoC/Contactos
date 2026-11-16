import { Ban, Pencil, Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";
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
import { soatSchema, type Soat } from "../../services/esquemas";
import { useAccion, useGuardar, useLista } from "../../utils/consultas";
import { formatearFecha, hoyBogota, normalizarPlaca } from "../../utils/formatters";
import { MINIMO_BUSQUEDA, useRetardo, useTitulo } from "../../utils/hooks";
import { DialogoFormulario, fechaOpcional, nulo, useFormulario } from "../formulario";
import { OPCIONES_ESTADO_EDITABLE, OPCIONES_ESTADO_FILTRO, useFiltrosUrl } from "../revisiones/PaginaRevisiones";

const ASEGURADORAS = ["MUNDIAL", "SURA", "PREVISORA", "SEGUROS BOLIVAR", "SEGUROS DEL ESTADO", "AXA COLPATRIA", "MAPFRE", "LIBERTY", "HDI", "SOLIDARIA"];

const formularioSoatSchema = z.object({
  numero: z.string().trim().min(1, "Escriba el número de la póliza."),
  aseguradora: z.string().trim().min(2, "Escriba la aseguradora."),
  placa: z
    .string()
    .transform(normalizarPlaca)
    .pipe(z.string().regex(/^[A-Z0-9]{5,6}$/, "Escriba una placa válida, por ejemplo ABC12D.")),
  fecha_soat: fechaOpcional.refine((v) => v !== "", "Indique la fecha de expedición."),
  fecha_venc_soat: fechaOpcional,
  estado: z.enum(["VIGENTE", "DUPLICADO"]),
});
type Valores = z.input<typeof formularioSoatSchema>;

function FormularioSoat({ soat, alCerrar }: { soat: Soat | null | undefined; alCerrar: () => void }) {
  const edicion = Boolean(soat);
  const { valores, setValores, errores, cambiar, validar, erroresServidor } = useFormulario<Valores>({
    numero: "",
    aseguradora: "MUNDIAL",
    placa: "",
    fecha_soat: hoyBogota(),
    fecha_venc_soat: "",
    estado: "VIGENTE",
  });
  const guardar = useGuardar("soats", soatSchema, { id: soat?.soat, invalidar: ["tablero", "ficha"], alExito: alCerrar });
  const { reset } = guardar;

  useEffect(() => {
    if (soat === undefined) return;
    reset();
    const [numero = "", aseguradora = ""] = soat ? [soat.soat.slice(0, soat.soat.lastIndexOf("-")), soat.aseguradora] : [];
    setValores({
      numero: soat ? numero : "",
      aseguradora: soat ? aseguradora : "MUNDIAL",
      placa: soat?.placa ?? "",
      fecha_soat: soat ? (soat.fecha_soat ?? "") : hoyBogota(),
      fecha_venc_soat: soat?.fecha_venc_soat ?? "",
      estado: soat?.estado === "DUPLICADO" ? "DUPLICADO" : "VIGENTE",
    });
  }, [soat, setValores, reset]);

  const enviar = () => {
    const datos = validar(formularioSoatSchema);
    if (!datos) return;
    const cuerpo: Record<string, unknown> = {
      fecha_soat: datos.fecha_soat,
      fecha_venc_soat: nulo(datos.fecha_venc_soat),
      estado: datos.estado,
    };
    if (!edicion) Object.assign(cuerpo, { numero: datos.numero, aseguradora: datos.aseguradora, placa: datos.placa });
    guardar.mutate(cuerpo, { onError: erroresServidor });
  };

  return (
    <DialogoFormulario
      abierto={soat !== undefined}
      titulo={edicion ? `Editar SOAT ${soat?.soat}` : "Registrar SOAT"}
      alCerrar={alCerrar}
      alEnviar={enviar}
      enviando={guardar.isPending}
      error={guardar.error}
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <CampoTexto etiqueta="Número de póliza" value={valores.numero} onChange={cambiar("numero")} error={errores.numero} disabled={edicion} obligatorio />
        <CampoTexto
          etiqueta="Aseguradora"
          value={valores.aseguradora}
          onChange={cambiar("aseguradora")}
          error={errores.aseguradora}
          disabled={edicion}
          list="aseguradoras"
          obligatorio
        />
        <datalist id="aseguradoras">
          {ASEGURADORAS.map((a) => (
            <option key={a} value={a} />
          ))}
        </datalist>
        <CampoTexto etiqueta="Placa" value={valores.placa} onChange={cambiar("placa")} error={errores.placa} disabled={edicion} obligatorio />
        <CampoTexto etiqueta="Fecha de expedición" type="date" value={valores.fecha_soat} onChange={cambiar("fecha_soat")} error={errores.fecha_soat} obligatorio />
        <CampoTexto
          etiqueta="Fecha de vencimiento"
          type="date"
          value={valores.fecha_venc_soat}
          onChange={cambiar("fecha_venc_soat")}
          error={errores.fecha_venc_soat}
          ayuda="Si la deja vacía se calcula a un año."
        />
        <CampoSeleccion etiqueta="Estado" value={valores.estado} onChange={cambiar("estado")} error={errores.estado} opciones={OPCIONES_ESTADO_EDITABLE} />
      </div>
    </DialogoFormulario>
  );
}

export function PaginaSoat() {
  useTitulo("SOAT");
  const { puede } = useSesion();
  const inicial = useFiltrosUrl();
  const [busqueda, setBusqueda] = useState("");
  const [estado, setEstado] = useState(inicial.estado);
  const [desde, setDesde] = useState(inicial.desde);
  const [hasta, setHasta] = useState(inicial.hasta);
  const [editando, setEditando] = useState<Soat | null | undefined>(undefined);
  const [anulando, setAnulando] = useState<Soat | null>(null);
  const q = useRetardo(busqueda).trim();
  // Solo búsqueda: placa o póliza, o un rango de vencimiento (como el que llega desde el tablero).
  const buscando = q.length >= MINIMO_BUSQUEDA || Boolean(desde || hasta);
  const lista = useLista("soats", soatSchema, { q, estado, vence_desde: desde, vence_hasta: hasta }, 25, { habilitada: buscando });
  const { reiniciarPagina } = lista;
  useEffect(() => reiniciarPagina(), [q, estado, desde, hasta, reiniciarPagina]);
  const anular = useAccion("soats", "anular", soatSchema, { invalidar: ["tablero", "ficha"], alExito: () => setAnulando(null) });

  const columnas: Columna<Soat>[] = [
    { clave: "placa", titulo: "Placa", celda: (s) => <EnlacePlaca placa={s.placa} /> },
    { clave: "fecha", titulo: "Vigencia", celda: (s) => formatearFecha(s.fecha_soat), ordenable: "fecha_soat" },
    { clave: "vence", titulo: "Vencimiento", celda: (s) => formatearFecha(s.fecha_venc_soat), ordenable: "fecha_venc_soat" },
    { clave: "estado", titulo: "Estado", celda: (s) => <InsigniaDocumento estado={s.estado_actual} /> },
    { clave: "propietario", titulo: "Propietario", celda: (s) => <EnlaceContacto nip={s.propietario_nip} nombre={s.propietario_nombre} /> },
    {
      clave: "acciones",
      titulo: "Acciones",
      celda: (s) =>
        puede("revisiones.change_soat") && s.estado !== "ANULADO" ? (
          <div className="flex flex-wrap gap-1">
            <Boton
              variante="texto"
              onClick={() => setEditando(s)}
              aria-label={`Editar SOAT de ${s.placa ?? "placa sin registrar"} que vence el ${formatearFecha(s.fecha_venc_soat)}`}
              icono={<Pencil aria-hidden="true" size={18} />}
            >
              Editar
            </Boton>
            <Boton
              variante="texto"
              onClick={() => setAnulando(s)}
              aria-label={`Anular SOAT de ${s.placa ?? "placa sin registrar"} que vence el ${formatearFecha(s.fecha_venc_soat)}`}
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
        titulo="SOAT"
        descripcion="Pólizas del seguro obligatorio."
        acciones={
          puede("revisiones.add_soat") && (
            <Boton onClick={() => setEditando(null)} icono={<Plus aria-hidden="true" size={18} />}>
              Registrar SOAT
            </Boton>
          )
        }
      />
      <Tarjeta>
        <div role="search" className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <CampoTexto
            etiqueta="Buscar por placa o póliza"
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
            titulo="Busque un SOAT"
            descripcion="Escriba la placa o el número de póliza, o elija un rango de vencimiento. Para ver el vehículo, haga clic en la placa."
            accion={<Search aria-hidden="true" className="texto-secundario" />}
          />
        ) : (
          <TablaPaginada
            titulo="Pólizas SOAT"
            columnas={columnas}
            datos={lista.data}
            cargando={lista.isFetching}
            error={lista.error}
            claveFila={(s) => s.soat}
            pagina={lista.pagina}
            alCambiarPagina={lista.setPagina}
            orden={lista.orden}
            alOrdenar={lista.setOrden}
          />
        )}
      </Tarjeta>
      <FormularioSoat soat={editando} alCerrar={() => setEditando(undefined)} />
      <Confirmacion
        abierto={anulando !== null}
        titulo="Anular SOAT"
        mensaje={
          <p>
            ¿Anular la póliza <strong>{anulando?.soat}</strong>? El registro se conserva marcado como anulado.
          </p>
        }
        textoConfirmar="Anular"
        cargando={anular.isPending}
        alConfirmar={() => anulando && anular.mutate({ id: anulando.soat })}
        alCerrar={() => setAnulando(null)}
      />
    </>
  );
}
