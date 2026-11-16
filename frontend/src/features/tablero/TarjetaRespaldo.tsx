import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Database, FolderCheck, HardDrive, Info, RefreshCw, Server, XCircle } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import { Aviso, AvisoError } from "../../components/ui/Aviso";
import { Boton } from "../../components/ui/Boton";
import { CampoTexto } from "../../components/ui/Campos";
import type { ApiError } from "../../services/apiClient";
import {
  esServidorSchema,
  respaldoEjecucionResponseSchema,
  respaldoEstadoSchema,
  rutaConfigResponseSchema,
  rutaValidacionResponseSchema,
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

export function TarjetaRespaldo({ esAdmin = true }: { esAdmin?: boolean }) {
  const queryClient = useQueryClient();
  const [rutaInput, setRutaInput] = useState<string>("");
  const [rutaInicializada, setRutaInicializada] = useState<boolean>(false);
  const [validacion, setValidacion] = useState<{ valida: boolean; mensaje: string } | null>(null);
  const [mensajeExito, setMensajeExito] = useState<string | null>(null);
  const [usarLoopback, setUsarLoopback] = useState<boolean>(false);

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
      setRutaInicializada(true);
    }
  }, [estado?.ruta_configurada, rutaInicializada]);

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

  // REGLA FUNDAMENTAL: Si no es administrador o si el dispositivo es remoto, NO se renderiza en el DOM
  if (!esAdmin || !esServidor) {
    return null;
  }

  const ejecutando = Boolean(estado?.ejecutando || mutacionEjecutar.isPending);

  return (
    <section aria-labelledby="titulo-respaldo" className="glass-card mt-6 p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Database aria-hidden="true" size={24} className="text-marca-azul dark:text-blue-300" />
            <h2 id="titulo-respaldo" className="font-heading text-lg font-bold">
              Copia de Seguridad de la Base de Datos
            </h2>
          </div>
          <p className="texto-secundario mt-1 text-sm">
            La copia se ejecuta por consola en el servidor con <code className="rounded bg-black/5 px-1 py-0.5 dark:bg-white/10">pg_dump</code> en formato SQL plano (<code className="rounded bg-black/5 px-1 py-0.5 dark:bg-white/10">.sql</code>) y se guarda directamente en su disco local, sin sobrecargar el explorador web.
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
        <AvisoError error={(consulta.error || mutacionValidar.error || mutacionGuardarRuta.error || mutacionEjecutar.error) as ApiError | null} />
        {mensajeExito && <Aviso tipo="exito">{mensajeExito}</Aviso>}
      </div>

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
              className={`flex items-center gap-2 rounded-lg p-2.5 text-xs font-semibold ${validacion.valida
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
    </section>
  );
}
