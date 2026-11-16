import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Loader2, Pencil } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";

import { useSesion } from "../../app/sesion";
import { AvisoError } from "../../components/ui/Aviso";
import { Boton } from "../../components/ui/Boton";
import { EstadoVacio } from "../../components/ui/EstadoVacio";
import { InsigniaContacto, InsigniaDocumento, InsigniaLlamada } from "../../components/ui/Insignias";
import { Detalles, EncabezadoPagina, Tarjeta } from "../../components/ui/Pagina";
import type { ApiError } from "../../services/apiClient";
import { fichaSchema } from "../../services/esquemas";
import { obtener } from "../../services/recursos";
import { cumpleanos, formatearDocumento, formatearFecha, formatearFechaHora, formatearTelefono } from "../../utils/formatters";
import { useTitulo } from "../../utils/hooks";
import { FormularioContactoDialogo } from "./FormularioContacto";

function TablaSimple({ titulo, encabezados, filas }: { titulo: string; encabezados: string[]; filas: ReactNode[][] }) {
  if (filas.length === 0) return <EstadoVacio titulo={`Sin ${titulo.toLowerCase()} registradas`} />;
  return (
    <div className="overflow-x-auto" tabIndex={0} role="region" aria-label={titulo}>
      <table className="tabla">
        <caption className="sr-only">{titulo}</caption>
        <thead>
          <tr>
            {encabezados.map((e) => (
              <th key={e} scope="col">
                {e}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filas.map((fila, i) => (
            <tr key={i}>
              {fila.map((celda, j) => (
                <td key={j}>{celda}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PaginaFichaContacto() {
  const { nip = "" } = useParams();
  const { puede } = useSesion();
  const [editando, setEditando] = useState(false);
  const consulta = useQuery({
    queryKey: ["ficha", nip],
    queryFn: ({ signal }) => obtener(`/contactos/${encodeURIComponent(nip)}/ficha`, fichaSchema, signal),
  });
  const ficha = consulta.data;
  useTitulo(ficha ? `Ficha de ${ficha.contacto.nombre}` : "Ficha del contacto");

  if (consulta.isPending) {
    return (
      <div role="status" className="flex items-center gap-2 p-8">
        <Loader2 aria-hidden="true" className="giro" /> Cargando ficha…
      </div>
    );
  }
  if (consulta.error || !ficha) return <AvisoError error={consulta.error as ApiError} />;
  const { contacto } = ficha;
  const textoObs = (texto: string) => <span className="whitespace-pre-line">{texto || "—"}</span>;

  return (
    <>
      <Link to="/contactos" className="enlace mb-4 inline-flex items-center gap-1">
        <ArrowLeft aria-hidden="true" size={16} /> Volver a contactos
      </Link>
      <EncabezadoPagina
        titulo={contacto.nombre}
        descripcion={`Documento ${formatearDocumento(contacto.nip)}`}
        acciones={
          puede("contactos.change_contacto") && (
            <Boton onClick={() => setEditando(true)} icono={<Pencil aria-hidden="true" size={18} />}>
              Editar contacto
            </Boton>
          )
        }
      />
      <div className="flex flex-col gap-6">
        <Tarjeta titulo="Datos del contacto">
          <Detalles
            items={[
              { termino: "Estado", valor: <InsigniaContacto estado={contacto.estado} /> },
              { termino: "Celular", valor: formatearTelefono(contacto.celular) },
              { termino: "Teléfono", valor: formatearTelefono(contacto.telefono) },
              { termino: "Correo", valor: contacto.correo || "—" },
              { termino: "Dirección", valor: contacto.direccion || "—" },
              { termino: "Cumpleaños", valor: cumpleanos(contacto.dia_nac, contacto.mes_nac) },
              { termino: "Registrado", valor: formatearFechaHora(contacto.fecha_registro) },
              { termino: "Registrado por", valor: contacto.usuario || "—" },
            ]}
          />
        </Tarjeta>
        <Tarjeta titulo={`Motos (${ficha.motos.length})`}>
          <TablaSimple
            titulo="Motos"
            encabezados={["Placa", "Marca", "Línea", "Modelo"]}
            filas={ficha.motos.map((m) => [
              <Link key="p" to={`/motos/${m.placa}`} className="enlace">
                {m.placa}
              </Link>,
              m.marca,
              m.linea || "—",
              m.modelo || "—",
            ])}
          />
        </Tarjeta>
        <Tarjeta titulo="Revisiones técnico-mecánicas">
          <TablaSimple
            titulo="Revisiones"
            encabezados={["Certificado", "Placa", "Fecha", "Vence", "Estado"]}
            filas={ficha.revisiones.map((r) => [
              r.certificado,
              r.placa,
              formatearFecha(r.fecha_certificado),
              formatearFecha(r.fecha_venc_certificado),
              <InsigniaDocumento key="e" estado={r.estado_actual} />,
            ])}
          />
        </Tarjeta>
        <Tarjeta titulo="SOAT">
          <TablaSimple
            titulo="Pólizas SOAT"
            encabezados={["Póliza", "Placa", "Fecha", "Vence", "Estado"]}
            filas={ficha.soats.map((s) => [
              s.soat,
              s.placa ?? "—",
              formatearFecha(s.fecha_soat),
              formatearFecha(s.fecha_venc_soat),
              <InsigniaDocumento key="e" estado={s.estado_actual} />,
            ])}
          />
        </Tarjeta>
        <Tarjeta titulo="Llamadas">
          <div className="flex flex-col gap-6">
            <section aria-label="Llamadas de cumpleaños">
              <h3 className="mb-2 font-bold">Cumpleaños</h3>
              <TablaSimple
                titulo="Llamadas de cumpleaños"
                encabezados={["Fecha", "Estado", "Intentos", "Observación", "Usuario"]}
                filas={ficha.llamadas_cumpleanos.map((l) => [
                  formatearFechaHora(l.fecha),
                  <InsigniaLlamada key="e" estado={l.estado} />,
                  l.num_llamadas,
                  textoObs(l.observacion),
                  l.usuario || "—",
                ])}
              />
            </section>
            <section aria-label="Llamadas de RTM">
              <h3 className="mb-2 font-bold">RTM</h3>
              <TablaSimple
                titulo="Llamadas de RTM"
                encabezados={["Fecha objetivo", "Placa", "Estado", "Intentos", "Observación"]}
                filas={ficha.llamadas_rtm.map((l) => [
                  formatearFecha(l.fecha),
                  l.placa,
                  <InsigniaLlamada key="e" estado={l.estado} />,
                  l.num_llamadas,
                  textoObs(l.observacion),
                ])}
              />
            </section>
            <section aria-label="Llamadas de SOAT">
              <h3 className="mb-2 font-bold">SOAT</h3>
              <TablaSimple
                titulo="Llamadas de SOAT"
                encabezados={["Fecha objetivo", "Placa", "Estado", "Intentos", "Observación"]}
                filas={ficha.llamadas_soat.map((l) => [
                  formatearFecha(l.fecha),
                  l.placa,
                  <InsigniaLlamada key="e" estado={l.estado} />,
                  l.num_llamadas,
                  textoObs(l.observacion),
                ])}
              />
            </section>
          </div>
        </Tarjeta>
      </div>
      <FormularioContactoDialogo contacto={editando ? contacto : undefined} alCerrar={() => setEditando(false)} />
    </>
  );
}
