import { Check, Pencil, Plus, Search, X } from "lucide-react";
import { useEffect, useState } from "react";

import { useSesion } from "../../app/sesion";
import { Boton } from "../../components/ui/Boton";
import { CampoSeleccion, CampoTexto } from "../../components/ui/Campos";
import { EnlaceContacto } from "../../components/ui/Enlaces";
import { EstadoVacio } from "../../components/ui/EstadoVacio";
import { InsigniaContacto } from "../../components/ui/Insignias";
import { EncabezadoPagina, Tarjeta } from "../../components/ui/Pagina";
import { TablaPaginada, type Columna } from "../../components/ui/TablaPaginada";
import { contactoSchema, type Contacto } from "../../services/esquemas";
import { useLista } from "../../utils/consultas";
import { MESES, cumpleanos, formatearTelefono } from "../../utils/formatters";
import { MINIMO_BUSQUEDA, useRetardo, useTitulo } from "../../utils/hooks";
import { CANALES, FormularioContactoDialogo } from "./FormularioContacto";

const OPCIONES_MES = MESES.map((mes, i) => ({
  valor: String(i + 1),
  texto: mes,
}));
// Valor "campo:true|false" → filter[campo]=true|false.
const OPCIONES_CANAL = [
  ...CANALES.map((c) => ({
    valor: `${c.campo}:true`,
    texto: `Acepta ${c.texto}`,
  })),
  ...CANALES.map((c) => ({
    valor: `${c.campo}:false`,
    texto: `No acepta ${c.texto}`,
  })),
];

/** Insignias compactas: icono + texto visible + estado para lectores de pantalla (no solo color). */
function CanalesAutorizados({ contacto }: { contacto: Contacto }) {
  return (
    <ul aria-label="Canales autorizados" className="flex flex-wrap gap-1">
      {CANALES.map((c) => {
        const si = contacto[c.campo];
        const Icono = si ? Check : X;
        return (
          <li
            key={c.campo}
            className={`insignia ${si ? "insignia-exito" : "insignia-info line-through"}`}
            title={`${c.texto}: ${si ? "autorizado" : "no autorizado"}`}
          >
            <Icono aria-hidden="true" size={12} />
            {c.texto}
            <span className="sr-only">: {si ? "autorizado" : "no autorizado"}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function PaginaContactos() {
  useTitulo("Contactos");
  const { puede } = useSesion();
  const [busqueda, setBusqueda] = useState("");
  const [estado, setEstado] = useState("");
  const [mes, setMes] = useState("");
  const [canal, setCanal] = useState("");
  const [editando, setEditando] = useState<Contacto | null | undefined>(undefined);
  const q = useRetardo(busqueda);
  const [campoCanal, valorCanal] = canal ? canal.split(":") : ["", ""];
  // Solo búsqueda: sin texto no se consulta (no se listan los 54 mil contactos al entrar).
  const buscando = q.trim().length >= MINIMO_BUSQUEDA;
  const lista = useLista(
    "contactos",
    contactoSchema,
    {
      q: q.trim(),
      estado,
      mes_nac: mes,
      ...(campoCanal ? { [campoCanal]: valorCanal } : {}),
    },
    25,
    { habilitada: buscando },
  );
  const { reiniciarPagina } = lista;
  useEffect(() => reiniciarPagina(), [q, estado, mes, canal, reiniciarPagina]);

  const columnas: Columna<Contacto>[] = [
    {
      clave: "nombre",
      titulo: "Nombre",
      celda: (c) => <EnlaceContacto nip={c.nip} nombre={c.nombre} />,
      ordenable: "nombre",
    },
    {
      clave: "celular",
      titulo: "Celular",
      celda: (c) => formatearTelefono(c.celular),
    },
    {
      clave: "cumple",
      titulo: "Cumpleaños",
      celda: (c) => cumpleanos(c.dia_nac, c.mes_nac),
      ordenable: "mes_nac",
    },
    {
      clave: "estado",
      titulo: "Estado",
      celda: (c) => <InsigniaContacto estado={c.estado} />,
    },
    {
      clave: "canales",
      titulo: "Canales",
      celda: (c) => <CanalesAutorizados contacto={c} />,
    },
    {
      clave: "acciones",
      titulo: "Acciones",
      celda: (c) =>
        puede("contactos.change_contacto") ? (
          <Boton variante="texto" onClick={() => setEditando(c)} aria-label={`Editar ${c.nombre}`} icono={<Pencil aria-hidden="true" size={18} />}>
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
        titulo="Contactos"
        descripcion="Clientes de CDA Check Motos."
        acciones={
          puede("contactos.add_contacto") && (
            <Boton onClick={() => setEditando(null)} icono={<Plus aria-hidden="true" size={18} />}>
              Nuevo contacto
            </Boton>
          )
        }
      />
      <Tarjeta>
        <div role="search" className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <CampoTexto
            etiqueta="Buscar por documento o nombre"
            type="search"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            ayuda={`Escriba al menos ${MINIMO_BUSQUEDA} caracteres; los demás filtros afinan la búsqueda.`}
          />
          <CampoSeleccion
            etiqueta="Estado"
            value={estado}
            onChange={(e) => setEstado(e.target.value)}
            vacio="Todos"
            opciones={[
              { valor: "habilitado", texto: "Habilitado" },
              { valor: "inhabilitado", texto: "Inhabilitado" },
            ]}
          />
          <CampoSeleccion etiqueta="Mes de cumpleaños" value={mes} onChange={(e) => setMes(e.target.value)} vacio="Todos" opciones={OPCIONES_MES} />
          <CampoSeleccion etiqueta="Canal de contacto" value={canal} onChange={(e) => setCanal(e.target.value)} vacio="Todos" opciones={OPCIONES_CANAL} />
        </div>
        {!buscando ? (
          <EstadoVacio
            titulo="Busque un contacto"
            descripcion="Escriba el nombre o el documento para ver sus datos. Para ver la ficha, haga clic en el nombre."
            accion={<Search aria-hidden="true" className="texto-secundario" />}
          />
        ) : (
          <TablaPaginada
            titulo="Contactos"
            columnas={columnas}
            datos={lista.data}
            cargando={lista.isFetching}
            error={lista.error}
            claveFila={(c) => c.nip}
            pagina={lista.pagina}
            alCambiarPagina={lista.setPagina}
            orden={lista.orden}
            alOrdenar={lista.setOrden}
            vacio={
              <EstadoVacio
                titulo="No se encontraron contactos"
                descripcion={busqueda ? `No hay resultados para «${busqueda}».` : "Cambie los filtros o cree un contacto nuevo."}
                accion={<Search aria-hidden="true" className="texto-secundario" />}
              />
            }
          />
        )}
      </Tarjeta>
      <FormularioContactoDialogo contacto={editando} alCerrar={() => setEditando(undefined)} />
    </>
  );
}
