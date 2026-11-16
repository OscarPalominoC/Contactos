import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Loader2, Pencil, Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useSesion } from "../../app/sesion";
import { AvisoError } from "../../components/ui/Aviso";
import { Boton } from "../../components/ui/Boton";
import { CampoTexto } from "../../components/ui/Campos";
import { EnlaceContacto, EnlacePlaca } from "../../components/ui/Enlaces";
import { EstadoVacio } from "../../components/ui/EstadoVacio";
import { InsigniaDocumento, InsigniaLlamada } from "../../components/ui/Insignias";
import { Detalles, EncabezadoPagina, Tarjeta } from "../../components/ui/Pagina";
import { TablaPaginada, type Columna } from "../../components/ui/TablaPaginada";
import type { ApiError } from "../../services/apiClient";
import { llamadaPlacaSchema, motoSchema, revisionSchema, soatSchema, type Moto } from "../../services/esquemas";
import { obtener } from "../../services/recursos";
import { useLista } from "../../utils/consultas";
import { formatearDocumento, formatearFecha, formatearFechaHora, formatearTelefono } from "../../utils/formatters";
import { MINIMO_BUSQUEDA, useRetardo, useTitulo } from "../../utils/hooks";
import { FormularioMotoDialogo } from "./FormularioMoto";

export function PaginaMotos() {
  useTitulo("Motos");
  const { puede } = useSesion();
  const [busqueda, setBusqueda] = useState("");
  const [marca, setMarca] = useState("");
  const [editando, setEditando] = useState<Moto | null | undefined>(undefined);
  const q = useRetardo(busqueda);
  const m = useRetardo(marca);
  // Solo búsqueda: sin placa escrita no se consulta.
  const buscando = q.replace(/[\s-]/g, "").length >= MINIMO_BUSQUEDA;
  const lista = useLista("motos", motoSchema, { q, marca: m }, 25, { habilitada: buscando });
  const { reiniciarPagina } = lista;
  useEffect(() => reiniciarPagina(), [q, m, reiniciarPagina]);

  const columnas: Columna<Moto>[] = [
    { clave: "placa", titulo: "Placa", celda: (x) => <EnlacePlaca placa={x.placa} />, ordenable: "placa" },
    { clave: "marca", titulo: "Marca", celda: (x) => x.marca, ordenable: "marca" },
    { clave: "linea", titulo: "Línea", celda: (x) => x.linea || "—" },
    { clave: "modelo", titulo: "Modelo", celda: (x) => x.modelo || "—", ordenable: "modelo" },
    {
      clave: "propietario",
      titulo: "Propietario",
      celda: (x) => <EnlaceContacto nip={x.nip_contacto} nombre={x.nombre_contacto} />,
    },
    {
      clave: "acciones",
      titulo: "Acciones",
      celda: (x) =>
        puede("vehiculos.change_moto") ? (
          <Boton variante="texto" onClick={() => setEditando(x)} aria-label={`Editar moto ${x.placa}`} icono={<Pencil aria-hidden="true" size={18} />}>
            Editar
          </Boton>
        ) : (
          "—"
        ),
    },
  ];

  return (
    <>
      <EncabezadoPagina
        titulo="Motos"
        descripcion="Vehículos registrados con su propietario."
        acciones={
          puede("vehiculos.add_moto") && (
            <Boton onClick={() => setEditando(null)} icono={<Plus aria-hidden="true" size={18} />}>
              Nueva moto
            </Boton>
          )
        }
      />
      <Tarjeta>
        <div role="search" className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <CampoTexto
            etiqueta="Buscar por placa"
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            ayuda={`Escriba al menos ${MINIMO_BUSQUEDA} caracteres de la placa.`}
          />
          <CampoTexto etiqueta="Marca" type="search" value={marca} onChange={(e) => setMarca(e.target.value)} ayuda="Afina la búsqueda; nombre exacto, por ejemplo HONDA." />
        </div>
        {!buscando ? (
          <EstadoVacio
            titulo="Busque una moto"
            descripcion="Escriba la placa para ver el vehículo. Para ver su información, haga clic en la placa."
            accion={<Search aria-hidden="true" className="texto-secundario" />}
          />
        ) : (
          <TablaPaginada
            titulo="Motos"
            columnas={columnas}
            datos={lista.data}
            cargando={lista.isFetching}
            error={lista.error}
            claveFila={(x) => x.placa}
            pagina={lista.pagina}
            alCambiarPagina={lista.setPagina}
            orden={lista.orden}
            alOrdenar={lista.setOrden}
          />
        )}
      </Tarjeta>
      <FormularioMotoDialogo moto={editando} alCerrar={() => setEditando(undefined)} />
    </>
  );
}

export function PaginaDetalleMoto() {
  const { placa = "" } = useParams();
  const { puede } = useSesion();
  const [editando, setEditando] = useState(false);
  useTitulo(`Moto ${placa}`);
  const moto = useQuery({ queryKey: ["motos", placa], queryFn: ({ signal }) => obtener(`/motos/${placa}`, motoSchema, signal) });
  const revisiones = useLista("revisiones", revisionSchema, { placa }, 10);
  const soats = useLista("soats", soatSchema, { placa }, 10);
  const llamadasRtm = useLista("llamadas-rtm", llamadaPlacaSchema, { placa }, 10);

  if (moto.isPending) {
    return (
      <div role="status" className="flex items-center gap-2 p-8">
        <Loader2 aria-hidden="true" className="giro" /> Cargando moto…
      </div>
    );
  }
  if (moto.error || !moto.data) return <AvisoError error={moto.error as ApiError} />;
  const datos = moto.data;

  return (
    <>
      <Link to="/motos" className="enlace mb-4 inline-flex items-center gap-1">
        <ArrowLeft aria-hidden="true" size={16} /> Volver a motos
      </Link>
      <EncabezadoPagina
        titulo={`Moto ${datos.placa}`}
        descripcion={`${datos.marca} ${datos.linea} ${datos.modelo}`.trim()}
        acciones={
          puede("vehiculos.change_moto") && (
            <Boton onClick={() => setEditando(true)} icono={<Pencil aria-hidden="true" size={18} />}>
              Editar moto
            </Boton>
          )
        }
      />
      <div className="flex flex-col gap-6">
        <Tarjeta titulo="Datos">
          <Detalles
            items={[
              {
                termino: "Propietario",
                valor: datos.propietario ? (
                  <Link className="enlace" to={`/contactos/${encodeURIComponent(datos.propietario.nip)}`}>
                    {datos.propietario.nombre}
                  </Link>
                ) : (
                  `${formatearDocumento(datos.nip_contacto)} (sin contacto registrado)`
                ),
              },
              { termino: "Celular", valor: formatearTelefono(datos.propietario?.celular) },
              { termino: "Vencimiento RTM", valor: formatearFecha(datos.fecha_venc_rtmg) },
              { termino: "Vencimiento SOAT", valor: formatearFecha(datos.fecha_venc_soat) },
              { termino: "Actualizado", valor: formatearFechaHora(datos.actualizado_en) },
            ]}
          />
        </Tarjeta>
        <Tarjeta titulo="Revisiones RTM">
          <TablaPaginada
            titulo="Revisiones"
            columnas={[
              { clave: "c", titulo: "Certificado", celda: (r) => r.certificado },
              { clave: "f", titulo: "Fecha", celda: (r) => formatearFecha(r.fecha_certificado) },
              { clave: "v", titulo: "Vence", celda: (r) => formatearFecha(r.fecha_venc_certificado) },
              { clave: "e", titulo: "Estado", celda: (r) => <InsigniaDocumento estado={r.estado_actual} /> },
            ]}
            datos={revisiones.data}
            cargando={revisiones.isFetching}
            error={revisiones.error}
            claveFila={(r) => r.certificado}
            pagina={revisiones.pagina}
            alCambiarPagina={revisiones.setPagina}
          />
        </Tarjeta>
        <Tarjeta titulo="SOAT">
          <TablaPaginada
            titulo="Pólizas SOAT"
            columnas={[
              { clave: "s", titulo: "Póliza", celda: (s) => s.soat },
              { clave: "f", titulo: "Fecha", celda: (s) => formatearFecha(s.fecha_soat) },
              { clave: "v", titulo: "Vence", celda: (s) => formatearFecha(s.fecha_venc_soat) },
              { clave: "e", titulo: "Estado", celda: (s) => <InsigniaDocumento estado={s.estado_actual} /> },
            ]}
            datos={soats.data}
            cargando={soats.isFetching}
            error={soats.error}
            claveFila={(s) => s.soat}
            pagina={soats.pagina}
            alCambiarPagina={soats.setPagina}
          />
        </Tarjeta>
        <Tarjeta titulo="Llamadas de RTM">
          <TablaPaginada
            titulo="Llamadas de RTM"
            columnas={[
              { clave: "f", titulo: "Fecha objetivo", celda: (l) => formatearFecha(l.fecha) },
              { clave: "e", titulo: "Estado", celda: (l) => <InsigniaLlamada estado={l.estado} /> },
              { clave: "n", titulo: "Intentos", celda: (l) => l.num_llamadas },
              { clave: "o", titulo: "Observación", celda: (l) => <span className="whitespace-pre-line">{l.observacion || "—"}</span> },
            ]}
            datos={llamadasRtm.data}
            cargando={llamadasRtm.isFetching}
            error={llamadasRtm.error}
            claveFila={(l) => l.id}
            pagina={llamadasRtm.pagina}
            alCambiarPagina={llamadasRtm.setPagina}
          />
        </Tarjeta>
      </div>
      <FormularioMotoDialogo moto={editando ? datos : undefined} alCerrar={() => setEditando(false)} />
    </>
  );
}
