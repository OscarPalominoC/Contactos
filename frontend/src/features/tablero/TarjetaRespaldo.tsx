import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUp,
  CheckCircle2,
  Database,
  Folder,
  FolderCheck,
  FolderOpen,
  HardDrive,
  Info,
  RefreshCw,
  Server,
  Upload,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Aviso, AvisoError } from "../../components/ui/Aviso";
import { Boton } from "../../components/ui/Boton";
import { CampoTexto } from "../../components/ui/Campos";
import { Dialogo } from "../../components/ui/Dialogo";
import type { ApiError } from "../../services/apiClient";
import {
  esServidorSchema,
  exploracionRutaResponseSchema,
  respaldoEjecucionResponseSchema,
  respaldoEstadoSchema,
  restaurarRespaldoResponseSchema,
  rutaConfigResponseSchema,
  rutaValidacionResponseSchema,
  subirRespaldoResponseSchema,
  type ArchivoSqlItem,
  type RespaldoEstado,
} from "../../services/esquemas";
import { crear, obtener } from "../../services/recursos";
import { formatearFechaHora } from "../../utils/formatters";

/** Resuelve la ruta relativa o absoluta por loopback si el navegador corre en el servidor pero navega por IP LAN. */
function rutaApi(subruta: string, usarLoopback: boolean): string {
  if (usarLoopback && typeof window !== "undefined") {
    const puerto = window.location.port ? `:${window.location.port}` : "";
    return `${window.location.protocol}//127.0.0.1${puerto}/api/v1${subruta}`;
  }
  return subruta;
}

type PestanaRespaldo = "generar" | "cargar";

export function TarjetaRespaldo({ esAdmin = true }: { esAdmin?: boolean }) {
  const queryClient = useQueryClient();
  const [pestanaActiva, setPestanaActiva] = useState<PestanaRespaldo>("generar");

  // Estado pestaña Generar Respaldo
  const [rutaInput, setRutaInput] = useState<string>("");
  const [rutaInicializada, setRutaInicializada] = useState<boolean>(false);
  const [validacion, setValidacion] = useState<{ valida: boolean; mensaje: string } | null>(null);
  const [mensajeExito, setMensajeExito] = useState<string | null>(null);
  const [usarLoopback, setUsarLoopback] = useState<boolean>(false);

  // Estado pestaña Cargar Respaldo / Explorador
  const [rutaExplorar, setRutaExplorar] = useState<string>("");
  const [rutaExplorarInput, setRutaExplorarInput] = useState<string>("");
  const [archivoSeleccionado, setArchivoSeleccionado] = useState<ArchivoSqlItem | null>(null);
  const [dialogoConfirmarAbierto, setDialogoConfirmarAbierto] = useState<boolean>(false);
  const inputSubirRef = useRef<HTMLInputElement>(null);

  // 1. Verificación estricta de dispositivo: solo el equipo servidor tiene acceso
  const consultaServidor = useQuery({
    queryKey: ["respaldo-es-servidor"],
    queryFn: async ({ signal }) => {
      // 1.1 Si el origen actual es localhost o 127.0.0.1, consultar directamente
      try {
        const res = await obtener("/respaldos/es-servidor", esServidorSchema, signal);
        if (res.es_servidor) {
          setUsarLoopback(false);
          return res;
        }
      } catch {
        // Continuar con sondeo loopback si aplica
      }

      // 1.2 Si estamos navegando por IP LAN (ej: http://192.168.1.50:5174), verificar si este dispositivo
      // tiene acceso local al puerto de loopback (127.0.0.1:5174).
      // Solo el computador físico del servidor puede alcanzar 127.0.0.1:5174.
      if (typeof window !== "undefined" && window.location.hostname !== "127.0.0.1" && window.location.hostname !== "localhost") {
        try {
          const puerto = window.location.port ? `:${window.location.port}` : "";
          const urlLoopback = `${window.location.protocol}//127.0.0.1${puerto}/api/v1/respaldos/es-servidor`;
          const resLoopback = await obtener(urlLoopback, esServidorSchema, signal);
          if (resLoopback.es_servidor) {
            setUsarLoopback(true);
            return resLoopback;
          }
        } catch {
          // En dispositivos remotos (celulares, tablets en LAN), 127.0.0.1 falla de inmediato
        }
      }

      return { es_servidor: false };
    },
    enabled: esAdmin,
    staleTime: 60000,
  });

  const esServidor = Boolean(consultaServidor.data?.es_servidor);

  // 2. Consulta de estado en el servidor: sondeo cada 2 segundos mientras esté ejecutando
  const consulta = useQuery({
    queryKey: ["respaldo-estado", usarLoopback],
    queryFn: ({ signal }) => obtener(rutaApi("/respaldos/estado", usarLoopback), respaldoEstadoSchema, signal),
    enabled: esAdmin && esServidor,
    refetchInterval: (query) => {
      const datos = query.state.data as RespaldoEstado | undefined;
      return datos?.ejecutando ? 2000 : false;
    },
  });

  const estado = consulta.data;

  // Sincronizar el input de la ruta con la ruta configurada en el servidor al cargar
  useEffect(() => {
    if (estado?.ruta_configurada && !rutaInicializada) {
      setRutaInput(estado.ruta_configurada);
      setRutaExplorar(estado.ruta_configurada);
      setRutaExplorarInput(estado.ruta_configurada);
      setRutaInicializada(true);
    }
  }, [estado?.ruta_configurada, rutaInicializada]);

  // 3. Consulta del explorador de archivos en el servidor (solo en pestaña Cargar)
  const consultaExplorador = useQuery({
    queryKey: ["respaldo-explorar", rutaExplorar, usarLoopback],
    queryFn: ({ signal }) => {
      const url = rutaExplorar
        ? `${rutaApi("/respaldos/explorar", usarLoopback)}?ruta=${encodeURIComponent(rutaExplorar)}`
        : rutaApi("/respaldos/explorar", usarLoopback);
      return obtener(url, exploracionRutaResponseSchema, signal);
    },
    enabled: esAdmin && esServidor && pestanaActiva === "cargar",
  });

  // Mutación para validar la ruta en el servidor
  const mutacionValidar = useMutation({
    mutationFn: (ruta: string) => crear(rutaApi("/respaldos/validar-ruta", usarLoopback), rutaValidacionResponseSchema, { ruta }),
    onSuccess: (res) => {
      setValidacion({ valida: res.valida, mensaje: res.mensaje });
      setMensajeExito(null);
    },
    onError: (err: ApiError) => {
      setValidacion({ valida: false, mensaje: err.problema.detail || "Error validando ruta." });
    },
  });

  // Mutación para guardar la ruta configurada en el servidor
  const mutacionGuardarRuta = useMutation({
    mutationFn: (ruta: string) => crear(rutaApi("/respaldos/configurar-ruta", usarLoopback), rutaConfigResponseSchema, { ruta }),
    onSuccess: (res) => {
      setValidacion({ valida: true, mensaje: res.mensaje });
      setMensajeExito("Ruta guardada correctamente en el servidor.");
      void queryClient.invalidateQueries({ queryKey: ["respaldo-estado"] });
    },
  });

  // Mutación para ejecutar el respaldo SQL por consola en el servidor
  const mutacionEjecutar = useMutation({
    mutationFn: () => crear(rutaApi("/respaldos/ejecutar", usarLoopback), respaldoEjecucionResponseSchema, {}),
    onSuccess: (res) => {
      setMensajeExito(res.mensaje);
      setValidacion(null);
      void queryClient.invalidateQueries({ queryKey: ["respaldo-estado"] });
    },
  });

  // Mutación para restaurar la base de datos desde un archivo SQL
  const mutacionRestaurar = useMutation({
    mutationFn: (rutaArchivo: string) =>
      crear(rutaApi("/respaldos/restaurar", usarLoopback), restaurarRespaldoResponseSchema, { ruta_archivo: rutaArchivo }),
    onSuccess: (res) => {
      setMensajeExito(res.mensaje);
      setDialogoConfirmarAbierto(false);
      void queryClient.invalidateQueries({ queryKey: ["respaldo-estado"] });
    },
    onError: () => {
      setDialogoConfirmarAbierto(false);
      setMensajeExito(null);
    },
  });

  // Mutación para subir un archivo .sql de respaldo al servidor
  const mutacionSubir = useMutation({
    mutationFn: async (archivo: File) => {
      const datos = new FormData();
      datos.append("archivo", archivo);
      return crear(rutaApi("/respaldos/subir", usarLoopback), subirRespaldoResponseSchema, datos);
    },
    onSuccess: (res) => {
      setMensajeExito(res.mensaje);
      void queryClient.invalidateQueries({ queryKey: ["respaldo-explorar"] });
      setArchivoSeleccionado({
        nombre: res.archivo,
        ruta_completa: res.ruta_completa,
        tamano_bytes: 0,
        tamano_formateado: res.tamano_formateado,
        modificado_en: new Date().toISOString(),
      });
    },
  });

  const handleValidar = (e: FormEvent) => {
    e.preventDefault();
    if (!rutaInput.trim()) return;
    mutacionValidar.mutate(rutaInput.trim());
  };

  const handleGuardarRuta = () => {
    if (!rutaInput.trim()) return;
    mutacionGuardarRuta.mutate(rutaInput.trim());
  };

  const handleEjecutarRespaldo = () => {
    setMensajeExito(null);
    mutacionEjecutar.mutate();
  };

  const handleExplorarRuta = (e: FormEvent) => {
    e.preventDefault();
    if (!rutaExplorarInput.trim()) return;
    setRutaExplorar(rutaExplorarInput.trim());
  };

  const handleNavegarCarpeta = (nombreCarpeta: string) => {
    const separador = rutaExplorar.includes("/") ? "/" : "\\";
    const rutaBase = rutaExplorar.endsWith(separador) ? rutaExplorar : `${rutaExplorar}${separador}`;
    const nuevaRuta = `${rutaBase}${nombreCarpeta}`;
    setRutaExplorar(nuevaRuta);
    setRutaExplorarInput(nuevaRuta);
  };

  const handleSubirNivel = () => {
    if (consultaExplorador.data?.ruta_padre) {
      setRutaExplorar(consultaExplorador.data.ruta_padre);
      setRutaExplorarInput(consultaExplorador.data.ruta_padre);
    }
  };

  const handleCambiarUnidad = (unidad: string) => {
    setRutaExplorar(unidad);
    setRutaExplorarInput(unidad);
  };

  const handleArchivoSeleccionadoInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const archivos = e.target.files;
    if (archivos && archivos.length > 0) {
      const archivo = archivos[0];
      if (archivo) {
        mutacionSubir.mutate(archivo);
      }
    }
  };

  const handleConfirmarRestauracion = () => {
    if (!archivoSeleccionado) return;
    setMensajeExito(null);
    mutacionRestaurar.mutate(archivoSeleccionado.ruta_completa);
  };

  // REGLA FUNDAMENTAL: Si no es administrador o si el dispositivo es remoto, NO se renderiza en el DOM
  if (!esAdmin || !esServidor) {
    return null;
  }

  const ejecutando = Boolean(estado?.ejecutando || mutacionEjecutar.isPending || mutacionRestaurar.isPending);
  const explorador = consultaExplorador.data;

  return (
    <section aria-labelledby="titulo-respaldo" className="glass-card mt-6 p-6 overflow-hidden">
      {/* Pestañas de estilo explorador web */}
      <div
        role="tablist"
        aria-label="Pestañas de copia y carga de respaldo"
        className="flex items-end gap-1.5 border-b border-black/10 dark:border-white/10 px-3 pt-2 -mx-6 -mt-6 mb-6 bg-black/5 dark:bg-white/5"
      >
        <button
          type="button"
          role="tab"
          id="tab-generar"
          aria-selected={pestanaActiva === "generar"}
          aria-controls="panel-generar"
          onClick={() => {
            setPestanaActiva("generar");
            setMensajeExito(null);
          }}
          className={`flex items-center gap-2 rounded-t-xl px-4 py-2.5 text-xs sm:text-sm font-semibold transition-all relative ${
            pestanaActiva === "generar"
              ? "bg-[var(--glass-bg)] border-t border-x border-[var(--glass-border)] text-marca-azul dark:text-blue-300 shadow-sm -mb-px"
              : "text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200 hover:bg-white/5"
          }`}
        >
          <Database size={16} aria-hidden="true" />
          <span>Generar respaldo (.sql)</span>
        </button>

        <button
          type="button"
          role="tab"
          id="tab-cargar"
          aria-selected={pestanaActiva === "cargar"}
          aria-controls="panel-cargar"
          onClick={() => {
            setPestanaActiva("cargar");
            setMensajeExito(null);
          }}
          className={`flex items-center gap-2 rounded-t-xl px-4 py-2.5 text-xs sm:text-sm font-semibold transition-all relative ${
            pestanaActiva === "cargar"
              ? "bg-[var(--glass-bg)] border-t border-x border-[var(--glass-border)] text-marca-azul dark:text-blue-300 shadow-sm -mb-px"
              : "text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200 hover:bg-white/5"
          }`}
        >
          <Upload size={16} aria-hidden="true" />
          <span>Cargar respaldo (Restaurar)</span>
        </button>
      </div>

      {/* Encabezado común con indicador de servidor */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            {pestanaActiva === "generar" ? (
              <Database aria-hidden="true" size={24} className="text-marca-azul dark:text-blue-300" />
            ) : (
              <Upload aria-hidden="true" size={24} className="text-marca-azul dark:text-blue-300" />
            )}
            <h2 id="titulo-respaldo" className="font-heading text-lg font-bold">
              {pestanaActiva === "generar"
                ? "Copia de Seguridad de la Base de Datos"
                : "Cargar y Restaurar Respaldo al Sistema"}
            </h2>
          </div>
          <p className="texto-secundario mt-1 text-sm">
            {pestanaActiva === "generar"
              ? "La copia se ejecuta por consola en el servidor con pg_dump en formato SQL plano (.sql) y se guarda directamente en su disco local, sin sobrecargar el explorador web."
              : "Explora los archivos del servidor para localizar y restaurar una base de datos (.sql), o sube una copia para incorporarla al sistema."}
          </p>
        </div>

        {/* Indicador exclusivo de máquina servidora */}
        <div className="flex items-center gap-1.5 self-start rounded-full border border-blue-500/20 bg-blue-500/10 px-3 py-1 text-xs font-semibold text-blue-700 dark:text-blue-300">
          <Server aria-hidden="true" size={14} />
          <span>Conectado en el servidor</span>
        </div>
      </div>

      {/* Avisos de error o éxito */}
      <div className="mt-4">
        <AvisoError
          error={
            (consulta.error ||
              mutacionValidar.error ||
              mutacionGuardarRuta.error ||
              mutacionEjecutar.error ||
              mutacionRestaurar.error ||
              mutacionSubir.error ||
              consultaExplorador.error) as ApiError | null
          }
        />
        {mensajeExito && <Aviso tipo="exito">{mensajeExito}</Aviso>}
      </div>

      {/* CONTENIDO PESTAÑA 1: GENERAR RESPALDO */}
      {pestanaActiva === "generar" && (
        <div role="tabpanel" id="panel-generar" aria-labelledby="tab-generar">
          {/* Información del último respaldo en el servidor */}
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div className="glass-subtle rounded-xl p-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
                <HardDrive aria-hidden="true" size={16} />
                <span>Último respaldo en servidor</span>
              </div>
              <p className="mt-2 text-sm font-semibold truncate" title={estado?.ultimo_respaldo?.archivo ?? "Sin respaldos previos"}>
                {estado?.ultimo_respaldo?.archivo ?? "Ningún respaldo registrado"}
              </p>
              <p className="texto-secundario mt-0.5 text-xs">
                {estado?.ultimo_respaldo
                  ? `${estado.ultimo_respaldo.tamano_formateado} · ${formatearFechaHora(estado.ultimo_respaldo.creado_en)}`
                  : "Genera el primer respaldo con el botón inferior"}
              </p>
            </div>

            <div className="glass-subtle rounded-xl p-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
                <FolderCheck aria-hidden="true" size={16} />
                <span>Respaldos conservados</span>
              </div>
              <p className="font-heading mt-2 text-2xl font-bold">
                {estado?.total_respaldos ?? 0} <span className="text-xs font-normal text-neutral-500 dark:text-neutral-400">/ 14 máx.</span>
              </p>
              <p className="texto-secundario mt-0.5 text-xs">Rotación automática de los 14 archivos SQL más recientes.</p>
            </div>

            <div className="glass-subtle rounded-xl p-4 sm:col-span-2 lg:col-span-1">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
                <RefreshCw aria-hidden="true" size={16} className={ejecutando ? "giro text-marca-azul" : ""} />
                <span>Estado de ejecución</span>
              </div>
              <p className="mt-2 text-sm font-semibold">
                {ejecutando ? (
                  <span className="inline-flex items-center gap-1.5 text-marca-azul dark:text-blue-300">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75"></span>
                      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-blue-600"></span>
                    </span>
                    Ejecutando por consola en el servidor…
                  </span>
                ) : (
                  <span className="text-emerald-700 dark:text-emerald-300">Listo para respaldar</span>
                )}
              </p>
              <p className="texto-secundario mt-0.5 text-xs">
                {ejecutando
                  ? "Proceso desacoplado en segundo plano en el servidor."
                  : estado?.ultimo_resultado ?? "Sin procesos en ejecución."}
              </p>
            </div>
          </div>

          {/* Configuración de la ruta del servidor */}
          <div className="mt-6 border-t border-black/10 pt-4 dark:border-white/10">
            <form onSubmit={handleValidar} className="space-y-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <div className="flex-1">
                  <CampoTexto
                    etiqueta="Ruta de almacenamiento en el servidor"
                    ayuda="Carpeta absoluta en el disco del servidor donde se guardarán los archivos .sql."
                    value={rutaInput}
                    onChange={(e) => {
                      setRutaInput(e.target.value);
                      setValidacion(null);
                    }}
                    disabled={ejecutando}
                    placeholder="Ej: F:\Check\respaldos"
                  />
                </div>
                <div className="flex gap-2">
                  <Boton
                    type="submit"
                    variante="secundario"
                    cargando={mutacionValidar.isPending}
                    textoCargando="Validando…"
                    disabled={ejecutando || !rutaInput.trim()}
                  >
                    Validar ruta
                  </Boton>
                  <Boton
                    type="button"
                    variante="azul"
                    onClick={handleGuardarRuta}
                    cargando={mutacionGuardarRuta.isPending}
                    textoCargando="Guardando…"
                    disabled={ejecutando || !rutaInput.trim()}
                  >
                    Guardar ruta
                  </Boton>
                </div>
              </div>

              {/* Resultado de la validación de la ruta */}
              {validacion && (
                <div
                  role="status"
                  aria-live="polite"
                  className={`flex items-center gap-2 rounded-lg p-2.5 text-xs font-semibold ${
                    validacion.valida
                      ? "bg-emerald-500/10 text-emerald-800 dark:text-emerald-200 border border-emerald-500/20"
                      : "bg-red-500/10 text-red-800 dark:text-red-200 border border-red-500/20"
                  }`}
                >
                  {validacion.valida ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                  <span>{validacion.mensaje}</span>
                </div>
              )}
            </form>
          </div>

          {/* Botón principal de ejecución del respaldo en formato SQL */}
          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2 text-xs text-neutral-500 dark:text-neutral-400">
              <Info aria-hidden="true" size={15} />
              <span>El respaldo no congelará tu pantalla ni ralentizará otros dispositivos.</span>
            </div>

            <Boton
              variante="primario"
              cargando={ejecutando}
              textoCargando="Generando respaldo por consola en el servidor…"
              icono={<Database aria-hidden="true" size={18} />}
              onClick={handleEjecutarRespaldo}
              disabled={ejecutando}
              className="w-full sm:w-auto"
            >
              Generar copia de seguridad en servidor (.sql)
            </Boton>
          </div>
        </div>
      )}

      {/* CONTENIDO PESTAÑA 2: CARGAR RESPALDO / EXPLORADOR DE ARCHIVOS */}
      {pestanaActiva === "cargar" && (
        <div role="tabpanel" id="panel-cargar" aria-labelledby="tab-cargar" className="space-y-6">
          {/* Barra de navegación de carpetas del servidor */}
          <div className="rounded-xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 flex items-center gap-1.5">
                <FolderOpen size={15} />
                <span>Explorador de archivos del servidor</span>
              </span>

              {/* Botones de unidades disponibles */}
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-neutral-500 mr-1">Unidades:</span>
                {explorador?.unidades_disponibles?.map((u) => (
                  <button
                    key={u}
                    type="button"
                    onClick={() => handleCambiarUnidad(u)}
                    className="rounded bg-black/5 dark:bg-white/10 px-2 py-0.5 text-xs font-mono font-semibold hover:bg-marca-azul hover:text-white transition-colors"
                  >
                    {u}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => handleCambiarUnidad("F:\\Check")}
                  className="rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 px-2.5 py-0.5 text-xs font-semibold hover:bg-emerald-500/20 transition-colors ml-1"
                >
                  F:\Check
                </button>
                {estado?.ruta_configurada && (
                  <button
                    type="button"
                    onClick={() => handleCambiarUnidad(estado.ruta_configurada)}
                    className="rounded bg-blue-500/10 text-blue-700 dark:text-blue-300 px-2.5 py-0.5 text-xs font-semibold hover:bg-blue-500/20 transition-colors ml-1"
                  >
                    Carpeta de respaldos
                  </button>
                )}
              </div>
            </div>

            {/* Input para escribir/explorar ruta arbitraria */}
            <form onSubmit={handleExplorarRuta} className="flex gap-2">
              <div className="flex-1">
                <input
                  type="text"
                  value={rutaExplorarInput}
                  onChange={(e) => setRutaExplorarInput(e.target.value)}
                  placeholder="Ruta a explorar en el servidor (ej: F:\Check\respaldos)"
                  className="campo w-full font-mono text-xs sm:text-sm"
                  aria-label="Ruta a explorar en el servidor"
                />
              </div>
              <Boton
                type="submit"
                variante="secundario"
                cargando={consultaExplorador.isFetching}
                textoCargando="Explorando…"
                disabled={!rutaExplorarInput.trim()}
              >
                Explorar
              </Boton>
              {explorador?.ruta_padre && (
                <Boton
                  type="button"
                  variante="secundario"
                  onClick={handleSubirNivel}
                  icono={<ArrowUp size={15} />}
                  title="Subir a carpeta superior"
                >
                  Subir nivel
                </Boton>
              )}
            </form>

            <div className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
              Ruta actual: <code className="font-mono font-semibold">{explorador?.ruta_actual ?? rutaExplorar}</code>
            </div>
          </div>

          {/* Listado de carpetas y archivos .sql */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Subcarpetas */}
            <div className="rounded-xl border border-black/10 dark:border-white/10 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 mb-2 flex items-center gap-1.5">
                <Folder size={14} />
                <span>Carpetas ({explorador?.carpetas?.length ?? 0})</span>
              </h3>
              {explorador && (explorador.carpetas?.length ?? 0) > 0 ? (
                <div className="max-h-56 overflow-y-auto space-y-1 pr-1">
                  {explorador.carpetas.map((carp) => (
                    <button
                      key={carp}
                      type="button"
                      onClick={() => handleNavegarCarpeta(carp)}
                      className="w-full text-left flex items-center gap-2 p-2 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 text-xs sm:text-sm transition-colors group"
                    >
                      <Folder size={16} className="text-amber-500 group-hover:scale-110 transition-transform" />
                      <span className="truncate">{carp}</span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="texto-secundario text-xs py-4 text-center">No hay subcarpetas en este directorio.</p>
              )}
            </div>

            {/* Archivos .sql encontrados */}
            <div className="rounded-xl border border-black/10 dark:border-white/10 p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400 mb-2 flex items-center gap-1.5">
                <Database size={14} />
                <span>Bases de datos .sql ({explorador?.archivos_sql?.length ?? 0})</span>
              </h3>
              {explorador && (explorador.archivos_sql?.length ?? 0) > 0 ? (
                <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
                  {explorador.archivos_sql.map((archivo) => {
                    const seleccionado = archivoSeleccionado?.ruta_completa === archivo.ruta_completa;
                    return (
                      <div
                        key={archivo.ruta_completa}
                        className={`flex items-center justify-between gap-2 p-2.5 rounded-lg border text-xs sm:text-sm transition-all ${
                          seleccionado
                            ? "border-marca-azul bg-blue-500/10 dark:bg-blue-500/20"
                            : "border-black/5 dark:border-white/10 hover:border-black/20"
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <p className="font-semibold truncate" title={archivo.nombre}>
                            {archivo.nombre}
                          </p>
                          <p className="texto-secundario text-xs">
                            {archivo.tamano_formateado} · {formatearFechaHora(archivo.modificado_en)}
                          </p>
                        </div>
                        <Boton
                          type="button"
                          variante={seleccionado ? "primario" : "secundario"}
                          className="text-xs px-2.5 py-1"
                          onClick={() => setArchivoSeleccionado(archivo)}
                          disabled={ejecutando}
                        >
                          {seleccionado ? "Seleccionado" : "Seleccionar"}
                        </Boton>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="texto-secundario text-xs py-4 text-center">
                  No se encontraron archivos .sql en esta carpeta.
                </p>
              )}
            </div>
          </div>

          {/* Subida opcional de archivo desde el navegador */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 rounded-xl border border-dashed border-black/20 dark:border-white/20 bg-black/[0.01] dark:bg-white/[0.01]">
            <div className="flex items-center gap-2">
              <Upload size={18} className="text-neutral-500" />
              <div>
                <p className="text-xs sm:text-sm font-semibold">¿Tienes el archivo de respaldo en este dispositivo?</p>
                <p className="texto-secundario text-xs">
                  Puedes subir un archivo .sql (hasta 500 MB). Si el archivo ya está en el servidor físico (ej: <code className="font-mono">F:\Check\CONTACTOS2026-11-07.sql</code>), puedes seleccionarlo directamente en el explorador superior sin tener que subirlo.
                </p>
              </div>
            </div>
            <div>
              <input
                ref={inputSubirRef}
                type="file"
                accept=".sql"
                className="hidden"
                onChange={handleArchivoSeleccionadoInput}
                disabled={ejecutando || mutacionSubir.isPending}
              />
              <Boton
                type="button"
                variante="secundario"
                cargando={mutacionSubir.isPending}
                textoCargando="Subiendo…"
                onClick={() => inputSubirRef.current?.click()}
                disabled={ejecutando}
                icono={<Upload size={15} />}
              >
                Examinar archivo .sql
              </Boton>
            </div>
          </div>

          {/* Panel de confirmación del archivo seleccionado para restaurar */}
          {archivoSeleccionado && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 space-y-3">
              <div className="flex items-start gap-2.5">
                <AlertTriangle size={20} className="text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                <div className="space-y-1 flex-1">
                  <h3 className="text-sm font-bold text-amber-900 dark:text-amber-200">
                    Archivo preparado para restaurar: {archivoSeleccionado.nombre}
                  </h3>
                  <p className="text-xs text-amber-800 dark:text-amber-300">
                    Ruta: <code className="font-mono font-semibold">{archivoSeleccionado.ruta_completa}</code> ({archivoSeleccionado.tamano_formateado})
                  </p>
                  <p className="text-xs text-amber-800 dark:text-amber-300">
                    ⚠️ Advertencia: Al cargar este respaldo se reemplazarán las tablas y datos actuales de la base de datos por los contenidos en este archivo SQL.
                  </p>
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-amber-500/20">
                <Boton
                  type="button"
                  variante="secundario"
                  onClick={() => setArchivoSeleccionado(null)}
                  disabled={ejecutando}
                >
                  Cancelar selección
                </Boton>
                <Boton
                  type="button"
                  variante="peligro"
                  onClick={() => setDialogoConfirmarAbierto(true)}
                  disabled={ejecutando}
                  icono={<Database size={16} />}
                >
                  Cargar respaldo al sistema (.sql)
                </Boton>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modal de confirmación para restaurar la base de datos */}
      <Dialogo
        abierto={dialogoConfirmarAbierto}
        titulo="Confirmar restauración de base de datos"
        alCerrar={() => setDialogoConfirmarAbierto(false)}
        pie={
          <>
            <Boton
              type="button"
              variante="secundario"
              onClick={() => setDialogoConfirmarAbierto(false)}
              disabled={mutacionRestaurar.isPending}
            >
              Cancelar
            </Boton>
            <Boton
              type="button"
              variante="peligro"
              cargando={mutacionRestaurar.isPending}
              textoCargando="Iniciando restauración…"
              onClick={handleConfirmarRestauracion}
              disabled={mutacionRestaurar.isPending}
            >
              Sí, restaurar base de datos
            </Boton>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm">
            Está a punto de cargar y restaurar la base de datos desde el archivo:
          </p>
          <div className="rounded-lg bg-black/5 dark:bg-white/10 p-3 font-mono text-xs break-all">
            {archivoSeleccionado?.ruta_completa}
          </div>
          <p className="text-xs text-red-600 dark:text-red-400 font-semibold">
            Esta operación sobreescribirá los registros actuales de contactos, motos, revisiones, SOATs y llamadas por los registros almacenados en el archivo seleccionado.
          </p>
          <p className="text-xs texto-secundario">
            La restauración se ejecuta directamente en el motor PostgreSQL por consola en el servidor.
          </p>
        </div>
      </Dialogo>
    </section>
  );
}
