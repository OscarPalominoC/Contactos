import { PhoneCall, Plus } from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { z } from "zod";

import { useSesion } from "../../app/sesion";
import { Boton } from "../../components/ui/Boton";
import { CampoFecha } from "../../components/ui/CampoFecha";
import { CampoAreaTexto, CampoSeleccion, CampoTexto } from "../../components/ui/Campos";
import { EnlaceContacto, EnlacePlaca } from "../../components/ui/Enlaces";
import { InsigniaLlamada, NOMBRES_ESTADO_LLAMADA } from "../../components/ui/Insignias";
import { EncabezadoPagina, Tarjeta } from "../../components/ui/Pagina";
import { SelectorRangoFechas, type RangoFechas } from "../../components/ui/SelectorRangoFechas";
import { TablaPaginada, type Columna } from "../../components/ui/TablaPaginada";
import {
  contactoSchema,
  ESTADOS_LLAMADA,
  llamadaCumpleanosSchema,
  llamadaPlacaSchema,
  porLlamarSchema,
  type Contacto,
  type LlamadaCumpleanos,
  type LlamadaPlaca,
  type PorLlamar,
} from "../../services/esquemas";
import { useAccion, useGuardar, useLista } from "../../utils/consultas";
import { cumpleanos, formatearDocumento, formatearFecha, formatearFechaHora, formatearTelefono, hoyBogota, normalizarPlaca, sumarDias } from "../../utils/formatters";
import { useTitulo } from "../../utils/hooks";
import { DialogoFormulario, useFormulario } from "../formulario";

type Pestana = "cumpleanos" | "rtm" | "soat";
type VistaLlamada = "pendientes" | "historial";

const PESTANAS: { id: Pestana; texto: string; recurso: string; permiso: string }[] = [
  { id: "cumpleanos", texto: "Cumpleaños", recurso: "llamadas-cumpleanos", permiso: "llamadas.add_llamadacumpleanos" },
  { id: "rtm", texto: "RTM", recurso: "llamadas-rtm", permiso: "llamadas.add_llamadartm" },
  { id: "soat", texto: "SOAT", recurso: "llamadas-soat", permiso: "llamadas.add_llamadasoat" },
];

/** Horizonte por defecto de las llamadas por vencimiento (igual al del tablero). */
const DIAS_HORIZONTE = 30;

const OPCIONES_ESTADO = ESTADOS_LLAMADA.filter((e) => e !== "sin_estado").map((e) => ({ valor: e, texto: NOMBRES_ESTADO_LLAMADA[e] }));

const formularioLlamadaSchema = z.object({
  destino: z.string().trim().min(3, "Escriba el documento o la placa."),
  fecha: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, "Elija la fecha objetivo."),
  estado: z.enum(["realizada", "no_realizada", "realizada_sin_exito", "ocupada"]),
  observacion: z.string().trim().max(2000, "Máximo 2000 caracteres."),
});
type Valores = z.input<typeof formularioLlamadaSchema>;

interface NuevaLlamada {
  destino: string;
  fecha?: string;
}

/** Registrar una llamada nueva (cumpleaños por documento; RTM/SOAT por placa y fecha objetivo). */
function DialogoNuevaLlamada({ pestana, inicial, alCerrar }: { pestana: Pestana; inicial: NuevaLlamada | null; alCerrar: () => void }) {
  const config = PESTANAS.find((p) => p.id === pestana) as (typeof PESTANAS)[number];
  const esquema = pestana === "cumpleanos" ? llamadaCumpleanosSchema : llamadaPlacaSchema;
  const { valores, setValores, errores, cambiar, validar, erroresServidor } = useFormulario<Valores>({
    destino: "",
    fecha: hoyBogota(),
    estado: "realizada",
    observacion: "",
  });
  const guardar = useGuardar(config.recurso, esquema, { invalidar: ["tablero", "ficha", "contactos", `${config.recurso}/por-llamar`], alExito: alCerrar });
  const { reset } = guardar;
  const [errorDestino, setErrorDestino] = useState<string | undefined>();

  useEffect(() => {
    if (inicial) {
      reset();
      setErrorDestino(undefined);
      setValores({ destino: inicial.destino, fecha: inicial.fecha ?? hoyBogota(), estado: "realizada", observacion: "" });
    }
  }, [inicial, setValores, reset]);

  const enviar = () => {
    const datos = validar(formularioLlamadaSchema);
    if (!datos) return;
    const cuerpo =
      pestana === "cumpleanos"
        ? { nip: datos.destino, estado: datos.estado, observacion: datos.observacion }
        : { placa: normalizarPlaca(datos.destino), fecha: datos.fecha, estado: datos.estado, observacion: datos.observacion };
    guardar.mutate(cuerpo, {
      onError: (error) => {
        erroresServidor(error);
        const campos = error.erroresDeCampo();
        setErrorDestino(campos.nip ?? campos.placa);
      },
    });
  };

  return (
    <DialogoFormulario
      abierto={inicial !== null}
      titulo={`Registrar llamada de ${config.texto}`}
      alCerrar={alCerrar}
      alEnviar={enviar}
      enviando={guardar.isPending}
      error={guardar.error}
    >
      <CampoTexto
        etiqueta={pestana === "cumpleanos" ? "Documento del contacto" : "Placa"}
        value={valores.destino}
        onChange={cambiar("destino")}
        error={errores.destino ?? errorDestino}
        obligatorio
      />
      {pestana !== "cumpleanos" && (
        <CampoFecha
          etiqueta="Fecha objetivo (vencimiento)"
          valor={valores.fecha}
          alCambiar={(fecha) => setValores((v) => ({ ...v, fecha }))}
          error={errores.fecha}
          ayuda="Una llamada por placa y fecha; los intentos siguientes se agregan a la misma."
          obligatorio
        />
      )}
      <CampoSeleccion etiqueta="Resultado" value={valores.estado} onChange={cambiar("estado")} error={errores.estado} opciones={OPCIONES_ESTADO} />
      <CampoAreaTexto etiqueta="Observación" value={valores.observacion} onChange={cambiar("observacion")} error={errores.observacion} maxLength={2000} />
    </DialogoFormulario>
  );
}

/** Agregar un intento a una llamada existente. */
function DialogoIntento({ recurso, llamada, alCerrar }: { recurso: string; llamada: { id: string; titulo: string } | null; alCerrar: () => void }) {
  const esquema = recurso === "llamadas-cumpleanos" ? llamadaCumpleanosSchema : llamadaPlacaSchema;
  const [estado, setEstado] = useState("realizada");
  const [observacion, setObservacion] = useState("");
  const accion = useAccion(recurso, "intentos", esquema, { invalidar: ["tablero", "ficha", "contactos", `${recurso}/por-llamar`], alExito: alCerrar });
  const { reset } = accion;
  useEffect(() => {
    if (llamada) {
      reset();
      setEstado("realizada");
      setObservacion("");
    }
  }, [llamada, reset]);
  return (
    <DialogoFormulario
      abierto={llamada !== null}
      titulo={`Nuevo intento: ${llamada?.titulo ?? ""}`}
      alCerrar={alCerrar}
      alEnviar={() => llamada && accion.mutate({ id: llamada.id, cuerpo: { estado, observacion } })}
      enviando={accion.isPending}
      error={accion.error}
      textoEnviar="Registrar intento"
    >
      <CampoSeleccion etiqueta="Resultado" value={estado} onChange={(e) => setEstado(e.target.value)} opciones={OPCIONES_ESTADO} />
      <CampoAreaTexto etiqueta="Observación" value={observacion} onChange={(e) => setObservacion(e.target.value)} maxLength={2000} />
    </DialogoFormulario>
  );
}

const textoObservacion = (texto: string) => <span className="whitespace-pre-line">{texto || "—"}</span>;

function Intentos({ estado, num }: { estado: string; num: number }) {
  return (
    <span>
      {num}
      {estado !== "realizada" && num > 1 && (
        <span className="ml-1 text-xs font-semibold text-amber-700 dark:text-amber-400" title="Pasa al final de pendientes">
          (Reintento)
        </span>
      )}
    </span>
  );
}

/** Contactos cuyo cumpleaños (día y mes) cae en el periodo elegido; por defecto, hoy. */
function ListaCumpleanos({ alLlamar }: { alLlamar: (nip: string) => void }) {
  const hoy = hoyBogota();
  const [rango, setRango] = useState<RangoFechas>({ desde: hoy, hasta: hoy });
  // Sin fechas se vuelve a «hoy»: un periodo vacío no debe listar a todos los contactos.
  const cambiarRango = (r: RangoFechas) => setRango(r.desde || r.hasta ? r : { desde: hoy, hasta: hoy });
  const lista = useLista(
    "contactos",
    contactoSchema,
    { cumple_desde: rango.desde, cumple_hasta: rango.hasta, estado: "habilitado", contactar_cumpleanos: "true" },
    50,
  );
  const { reiniciarPagina } = lista;
  useEffect(() => reiniciarPagina(), [rango, reiniciarPagina]);
  const columnas: Columna<Contacto>[] = [
    { clave: "nombre", titulo: "Nombre", celda: (c) => <EnlaceContacto nip={c.nip} nombre={c.nombre} />, ordenable: "nombre" },
    { clave: "cumpleanos", titulo: "Cumpleaños", celda: (c) => cumpleanos(c.dia_nac, c.mes_nac), ordenable: "cumpleanos" },
    { clave: "celular", titulo: "Celular", celda: (c) => formatearTelefono(c.celular), ordenable: "celular" },
    {
      clave: "accion",
      titulo: "Acción",
      celda: (c) => (
        <Boton variante="texto" onClick={() => alLlamar(c.nip)} aria-label={`Registrar llamada a ${c.nombre}`} icono={<PhoneCall aria-hidden="true" size={18} />}>
          Registrar llamada
        </Boton>
      ),
    },
  ];
  return (
    <Tarjeta titulo="Cumpleaños del periodo">
      <div role="search" aria-label="Filtro de cumpleaños" className="mb-4 grid grid-cols-1 items-end gap-4 md:grid-cols-3">
        <SelectorRangoFechas
          desde={rango.desde}
          hasta={rango.hasta}
          alCambiar={cambiarRango}
          leyenda="Periodo de cumpleaños"
          etiquetaDesde="Cumpleaños desde"
          etiquetaHasta="Cumpleaños hasta"
        />
      </div>
      <TablaPaginada
        titulo="Cumpleaños del periodo"
        columnas={columnas}
        datos={lista.data}
        cargando={lista.isFetching}
        error={lista.error}
        claveFila={(c) => c.nip}
        pagina={lista.pagina}
        alCambiarPagina={lista.setPagina}
        orden={lista.orden}
        alOrdenar={lista.setOrden}
      />
    </Tarjeta>
  );
}

/** RTM o SOAT que vencen en el rango y aún no tienen una llamada realizada (calculado en el servidor). */
function ListaPorVencimiento({
  config,
  puedeRegistrar,
  alLlamar,
  alIntentar,
}: {
  config: (typeof PESTANAS)[number];
  puedeRegistrar: boolean;
  alLlamar: (fila: PorLlamar) => void;
  alIntentar: (fila: PorLlamar) => void;
}) {
  const hoy = hoyBogota();
  const porDefecto = { desde: hoy, hasta: sumarDias(hoy, DIAS_HORIZONTE) };
  const [rango, setRango] = useState<RangoFechas>(porDefecto);
  // Sin fechas se vuelve al horizonte por defecto: la lista siempre tiene un rango acotado.
  const cambiarRango = (r: RangoFechas) => setRango(r.desde || r.hasta ? r : porDefecto);
  const lista = useLista(`${config.recurso}/por-llamar`, porLlamarSchema, { desde: rango.desde, hasta: rango.hasta });
  const { reiniciarPagina } = lista;
  useEffect(() => reiniciarPagina(), [rango, reiniciarPagina]);

  const columnas: Columna<PorLlamar>[] = [
    { clave: "fecha", titulo: "Vencimiento", celda: (f) => formatearFecha(f.fecha) },
    { clave: "placa", titulo: "Placa", celda: (f) => <EnlacePlaca placa={f.placa} /> },
    { clave: "propietario", titulo: "Propietario", celda: (f) => <EnlaceContacto nip={f.propietario_nip} nombre={f.propietario_nombre} /> },
    { clave: "celular", titulo: "Celular", celda: (f) => formatearTelefono(f.celular) },
    {
      clave: "estado",
      titulo: "Estado",
      celda: (f) => (f.estado === "sin_llamar" ? <span className="insignia insignia-info">Sin llamar</span> : <InsigniaLlamada estado={f.estado} />),
    },
    { clave: "intentos", titulo: "Intentos", celda: (f) => <Intentos estado={f.estado} num={f.num_llamadas} /> },
    { clave: "obs", titulo: "Observación", celda: (f) => textoObservacion(f.observacion) },
    {
      clave: "acciones",
      titulo: "Acciones",
      celda: (f) =>
        !puedeRegistrar ? (
          "—"
        ) : f.llamada_id ? (
          <Boton variante="texto" onClick={() => alIntentar(f)} aria-label={`Nuevo intento para ${f.placa}`} icono={<PhoneCall aria-hidden="true" size={18} />}>
            Nuevo intento
          </Boton>
        ) : (
          <Boton variante="texto" onClick={() => alLlamar(f)} aria-label={`Registrar llamada a ${f.placa}`} icono={<PhoneCall aria-hidden="true" size={18} />}>
            Registrar llamada
          </Boton>
        ),
    },
  ];

  return (
    <Tarjeta titulo={`Llamadas pendientes de ${config.texto}`}>
      <p className="texto-secundario mb-4 text-xs">
        Vencimientos de {config.texto} del rango que aún no tienen una llamada realizada. Las motos que ya renovaron no aparecen, y solo se
        listan clientes habilitados que autorizan este canal. Los intentos sin éxito quedan al final para reintentarlos.
      </p>
      <div role="search" aria-label={`Filtros de ${config.texto}`} className="mb-4 grid grid-cols-1 items-end gap-4 md:grid-cols-3">
        <SelectorRangoFechas desde={rango.desde} hasta={rango.hasta} alCambiar={cambiarRango} etiquetaDesde="Vence desde" etiquetaHasta="Vence hasta" />
      </div>
      <TablaPaginada
        titulo={`Llamadas de ${config.texto} pendientes`}
        columnas={columnas}
        datos={lista.data}
        cargando={lista.isFetching}
        error={lista.error}
        claveFila={(f) => `${f.placa}.${f.fecha}`}
        pagina={lista.pagina}
        alCambiarPagina={lista.setPagina}
      />
    </Tarjeta>
  );
}

/** Bitácora de llamadas ya registradas, con rango de fechas y estado. */
function Historial({
  config,
  puedeEditar,
  alIntentar,
}: {
  config: (typeof PESTANAS)[number];
  puedeEditar: boolean;
  alIntentar: (llamada: { id: string; titulo: string }) => void;
}) {
  const [rango, setRango] = useState<RangoFechas>({ desde: "", hasta: "" });
  const [estado, setEstado] = useState("");
  const filtros = { estado, desde: rango.desde, hasta: rango.hasta };
  const esCumple = config.id === "cumpleanos";
  const cumple = useLista("llamadas-cumpleanos", llamadaCumpleanosSchema, filtros, 25, { habilitada: esCumple });
  const placa = useLista(esCumple ? "llamadas-rtm" : config.recurso, llamadaPlacaSchema, filtros, 25, { habilitada: !esCumple });
  const { reiniciarPagina: reiniciarCumple } = cumple;
  const { reiniciarPagina: reiniciarPlaca } = placa;
  useEffect(() => {
    reiniciarCumple();
    reiniciarPlaca();
  }, [estado, rango, reiniciarCumple, reiniciarPlaca]);

  const comunes = <T extends { estado: LlamadaPlaca["estado"]; num_llamadas: number; observacion: string; usuario: string }>(): Columna<T>[] => [
    { clave: "estado", titulo: "Estado", celda: (l) => <InsigniaLlamada estado={l.estado} /> },
    { clave: "intentos", titulo: "Intentos", celda: (l) => <Intentos estado={l.estado} num={l.num_llamadas} />, ordenable: "num_llamadas" },
    { clave: "obs", titulo: "Observación", celda: (l) => textoObservacion(l.observacion) },
    { clave: "usuario", titulo: "Usuario", celda: (l) => l.usuario || "—" },
  ];
  const columnasCumple: Columna<LlamadaCumpleanos>[] = [
    { clave: "fecha", titulo: "Fecha", celda: (l) => formatearFechaHora(l.fecha), ordenable: "fecha" },
    { clave: "nombre", titulo: "Contacto", celda: (l) => <EnlaceContacto nip={l.nip} nombre={l.nombre} /> },
    ...comunes<LlamadaCumpleanos>(),
    {
      clave: "acciones",
      titulo: "Acciones",
      celda: (l) =>
        puedeEditar ? (
          <Boton
            variante="texto"
            onClick={() => alIntentar({ id: String(l.id), titulo: l.nombre || formatearDocumento(l.nip) })}
            aria-label={`Nuevo intento para ${l.nombre || "contacto no registrado"}`}
            icono={<PhoneCall aria-hidden="true" size={18} />}
          >
            Nuevo intento
          </Boton>
        ) : (
          "—"
        ),
    },
  ];
  const columnasPlaca: Columna<LlamadaPlaca>[] = [
    { clave: "fecha", titulo: "Fecha objetivo", celda: (l) => formatearFecha(l.fecha), ordenable: "fecha" },
    { clave: "placa", titulo: "Placa", celda: (l) => <EnlacePlaca placa={l.placa} /> },
    ...comunes<LlamadaPlaca>(),
    {
      clave: "acciones",
      titulo: "Acciones",
      celda: (l) =>
        puedeEditar ? (
          <Boton
            variante="texto"
            onClick={() => alIntentar({ id: l.id, titulo: l.placa })}
            aria-label={`Nuevo intento para ${l.placa}`}
            icono={<PhoneCall aria-hidden="true" size={18} />}
          >
            Nuevo intento
          </Boton>
        ) : (
          "—"
        ),
    },
  ];

  return (
    <Tarjeta titulo={`Historial de llamadas de ${config.texto}`}>
      <div role="search" aria-label={`Filtros de ${config.texto}`} className="mb-4 grid grid-cols-1 items-end gap-4 md:grid-cols-3">
        <SelectorRangoFechas desde={rango.desde} hasta={rango.hasta} alCambiar={setRango} />
        <CampoSeleccion etiqueta="Estado" value={estado} onChange={(e) => setEstado(e.target.value)} vacio="Todos" opciones={OPCIONES_ESTADO} />
      </div>
      {esCumple ? (
        <TablaPaginada
          titulo="Llamadas de cumpleaños"
          columnas={columnasCumple}
          datos={cumple.data}
          cargando={cumple.isFetching}
          error={cumple.error}
          claveFila={(l) => String(l.id)}
          pagina={cumple.pagina}
          alCambiarPagina={cumple.setPagina}
          orden={cumple.orden}
          alOrdenar={cumple.setOrden}
        />
      ) : (
        <TablaPaginada
          titulo={`Llamadas de ${config.texto}`}
          columnas={columnasPlaca}
          datos={placa.data}
          cargando={placa.isFetching}
          error={placa.error}
          claveFila={(l) => l.id}
          pagina={placa.pagina}
          alCambiarPagina={placa.setPagina}
          orden={placa.orden}
          alOrdenar={placa.setOrden}
        />
      )}
    </Tarjeta>
  );
}

export function PaginaLlamadas() {
  useTitulo("Llamadas");
  const { puede } = useSesion();
  const [params, setParams] = useSearchParams();
  const pestana = (PESTANAS.some((p) => p.id === params.get("pestana")) ? params.get("pestana") : "rtm") as Pestana;
  const config = PESTANAS.find((p) => p.id === pestana) as (typeof PESTANAS)[number];
  const [vista, setVista] = useState<VistaLlamada>("pendientes");
  const [nuevo, setNuevo] = useState<NuevaLlamada | null>(null);
  const [intento, setIntento] = useState<{ id: string; titulo: string } | null>(null);
  const botones = useRef<(HTMLButtonElement | null)[]>([]);

  const cambiarPestana = (id: Pestana) => setParams({ pestana: id }, { replace: true });
  const teclado = (evento: KeyboardEvent<HTMLButtonElement>, indice: number) => {
    const delta = evento.key === "ArrowRight" ? 1 : evento.key === "ArrowLeft" ? -1 : 0;
    if (!delta) return;
    evento.preventDefault();
    const siguiente = (indice + delta + PESTANAS.length) % PESTANAS.length;
    const destino = PESTANAS[siguiente];
    if (destino) cambiarPestana(destino.id);
    botones.current[siguiente]?.focus();
  };

  const puedeRegistrar = puede(config.permiso);
  const puedeEditar = puede(config.permiso.replace("add_", "change_"));

  return (
    <>
      <EncabezadoPagina
        titulo="Llamadas"
        descripcion="Gestión de llamadas preventivas y de fidelización: cumpleaños, RTM y SOAT."
        acciones={
          puedeRegistrar && (
            <Boton onClick={() => setNuevo({ destino: "" })} icono={<Plus aria-hidden="true" size={18} />}>
              Registrar llamada
            </Boton>
          )
        }
      />

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div role="tablist" aria-label="Tipo de llamada" className="flex flex-wrap gap-2">
          {PESTANAS.map((p, i) => (
            <button
              key={p.id}
              ref={(el) => {
                botones.current[i] = el;
              }}
              role="tab"
              id={`pestana-${p.id}`}
              aria-selected={pestana === p.id}
              aria-controls={`panel-${p.id}`}
              tabIndex={pestana === p.id ? 0 : -1}
              onClick={() => cambiarPestana(p.id)}
              onKeyDown={(e) => teclado(e, i)}
              className={`btn ${pestana === p.id ? "btn-primario" : "btn-secundario"}`}
            >
              {p.texto}
            </button>
          ))}
        </div>

        <div role="group" aria-label="Sub-vista de llamadas" className="glass-card flex items-center gap-1 p-1">
          <button
            type="button"
            onClick={() => setVista("pendientes")}
            className={`btn min-h-[36px] px-3 py-1.5 text-xs ${vista === "pendientes" ? "btn-primario" : "btn-texto"}`}
            aria-pressed={vista === "pendientes"}
          >
            Llamadas pendientes
          </button>
          <button
            type="button"
            onClick={() => setVista("historial")}
            className={`btn min-h-[36px] px-3 py-1.5 text-xs ${vista === "historial" ? "btn-primario" : "btn-texto"}`}
            aria-pressed={vista === "historial"}
          >
            Historial de llamadas
          </button>
        </div>
      </div>

      {/* `key` reinicia los filtros al cambiar de pestaña o vista: cada una tiene su propio rango. */}
      <div role="tabpanel" id={`panel-${pestana}`} aria-labelledby={`pestana-${pestana}`} key={`${pestana}-${vista}`}>
        {vista === "historial" ? (
          <Historial config={config} puedeEditar={puedeEditar} alIntentar={setIntento} />
        ) : pestana === "cumpleanos" ? (
          <ListaCumpleanos alLlamar={(nip) => setNuevo({ destino: nip })} />
        ) : (
          <ListaPorVencimiento
            config={config}
            puedeRegistrar={puedeRegistrar}
            alLlamar={(f) => setNuevo({ destino: f.placa, fecha: f.fecha })}
            alIntentar={(f) => f.llamada_id && setIntento({ id: f.llamada_id, titulo: f.placa })}
          />
        )}
      </div>

      <DialogoNuevaLlamada pestana={pestana} inicial={nuevo} alCerrar={() => setNuevo(null)} />
      <DialogoIntento recurso={config.recurso} llamada={intento} alCerrar={() => setIntento(null)} />
    </>
  );
}
