import { useQuery } from "@tanstack/react-query";
import { Cake, ClipboardCheck, Phone, ShieldCheck, UserPlus } from "lucide-react";
import { Link } from "react-router-dom";

import { useSesion } from "../../app/sesion";
import { AvisoError } from "../../components/ui/Aviso";
import { EncabezadoPagina } from "../../components/ui/Pagina";
import type { ApiError } from "../../services/apiClient";
import { tableroSchema } from "../../services/esquemas";
import { obtener } from "../../services/recursos";
import { formatearNumero, hoyBogota, sumarDias } from "../../utils/formatters";
import { useTitulo } from "../../utils/hooks";
import { TarjetaRespaldo } from "./TarjetaRespaldo";

function Indicador({
  titulo,
  valor,
  Icono,
  a,
  detalle,
}: {
  titulo: string;
  valor: number | undefined;
  Icono: typeof Phone;
  a?: string;
  detalle?: string;
}) {
  const contenido = (
    <>
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase">{titulo}</h2>
        <Icono aria-hidden="true" size={24} className="text-marca-azul dark:text-blue-300" />
      </div>
      <p className="font-heading mt-2 text-4xl font-extrabold">{valor === undefined ? "…" : formatearNumero(valor)}</p>
      {detalle && <p className="texto-secundario mt-1 text-sm">{detalle}</p>}
    </>
  );
  return (
    <li className="glass-card p-4 lg:p-6">
      {a ? (
        <Link to={a} className="block rounded-lg">
          {contenido}
          <span className="enlace mt-2 inline-block text-sm">Ver listado de {titulo.toLowerCase()}</span>
        </Link>
      ) : (
        contenido
      )}
    </li>
  );
}

export function PaginaTablero() {
  useTitulo("Tablero");
  const { usuario } = useSesion();
  const consulta = useQuery({ queryKey: ["tablero"], queryFn: ({ signal }) => obtener("/tablero", tableroSchema, signal) });
  const datos = consulta.data;
  const hoy = hoyBogota();
  const limite = sumarDias(hoy, datos?.dias_horizonte ?? 30);
  const esAdmin = usuario?.rol?.toLowerCase() === "administrador" || usuario?.permisos?.includes("cuentas.view_usuario");
  return (
    <>
      <EncabezadoPagina titulo="Tablero" descripcion={`Bienvenido(a), ${usuario?.nombre ?? ""}. Resumen del día.`} />
      <AvisoError error={consulta.error as ApiError | null} />
      <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Indicador
          titulo="RTM por vencer"
          valor={datos?.rtm_por_vencer}
          Icono={ClipboardCheck}
          detalle={`Próximos ${datos?.dias_horizonte ?? 30} días`}
          a={`/revisiones?vence_desde=${hoy}&vence_hasta=${limite}&estado=VIGENTE`}
        />
        <Indicador
          titulo="SOAT por vencer"
          valor={datos?.soat_por_vencer}
          Icono={ShieldCheck}
          detalle={`Próximos ${datos?.dias_horizonte ?? 30} días`}
          a={`/soat?vence_desde=${hoy}&vence_hasta=${limite}&estado=VIGENTE`}
        />
        <Indicador titulo="Cumpleaños de hoy" valor={datos?.cumpleanos_hoy} Icono={Cake} a="/llamadas?pestana=cumpleanos&hoy=1" />
        <Indicador
          titulo="Llamadas de hoy"
          valor={datos ? datos.llamadas_hoy.cumpleanos + datos.llamadas_hoy.rtm + datos.llamadas_hoy.soat : undefined}
          Icono={Phone}
          detalle={
            datos
              ? `Cumpleaños ${datos.llamadas_hoy.cumpleanos} · RTM ${datos.llamadas_hoy.rtm} · SOAT ${datos.llamadas_hoy.soat}`
              : undefined
          }
          a="/llamadas"
        />
        <Indicador titulo="Contactos nuevos del mes" valor={datos?.contactos_nuevos_mes} Icono={UserPlus} a="/contactos" />
      </ul>
      {esAdmin && <TarjetaRespaldo esAdmin={esAdmin} />}
    </>
  );
}
