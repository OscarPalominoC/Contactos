import { Plus, Trash2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { useSesion } from "../../app/sesion";
import { AvisoError } from "../../components/ui/Aviso";
import { Boton } from "../../components/ui/Boton";
import { CampoTexto } from "../../components/ui/Campos";
import { Confirmacion } from "../../components/ui/Dialogo";
import { EncabezadoPagina, Tarjeta } from "../../components/ui/Pagina";
import { TablaPaginada, type Columna } from "../../components/ui/TablaPaginada";
import type { ApiError } from "../../services/apiClient";
import { lineaSchema, marcaSchema, type Linea, type Marca } from "../../services/esquemas";
import { eliminar } from "../../services/recursos";
import { useGuardar, useLista } from "../../utils/consultas";
import { useRetardo, useTitulo } from "../../utils/hooks";
import { DialogoFormulario } from "../formulario";

function useEliminar(recurso: string, alExito: () => void) {
  const queryClient = useQueryClient();
  return useMutation<unknown, ApiError, string>({
    mutationFn: (id) => eliminar(`/${recurso}/${encodeURIComponent(id)}`),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: [recurso] });
      alExito();
    },
  });
}

function SeccionMarcas({ alElegir, elegida }: { alElegir: (m: Marca) => void; elegida?: string }) {
  const { puede } = useSesion();
  const [busqueda, setBusqueda] = useState("");
  const [nueva, setNueva] = useState(false);
  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [borrando, setBorrando] = useState<Marca | null>(null);
  const q = useRetardo(busqueda);
  const lista = useLista("marcas", marcaSchema, { q });
  const { reiniciarPagina } = lista;
  useEffect(() => reiniciarPagina(), [q, reiniciarPagina]);
  const guardar = useGuardar("marcas", marcaSchema, { alExito: () => setNueva(false) });
  const borrar = useEliminar("marcas", () => setBorrando(null));
  const errores = guardar.error?.erroresDeCampo() ?? {};

  const columnas: Columna<Marca>[] = [
    { clave: "codigo", titulo: "Código", celda: (m) => m.codigo, ordenable: "codigo" },
    {
      clave: "nombre",
      titulo: "Nombre",
      celda: (m) => (
        <button type="button" className="enlace text-left" aria-pressed={elegida === m.codigo} onClick={() => alElegir(m)}>
          {m.nombre}
        </button>
      ),
      ordenable: "nombre",
    },
    {
      clave: "acciones",
      titulo: "Acciones",
      celda: (m) =>
        puede("vehiculos.delete_marca") ? (
          <Boton variante="texto" onClick={() => setBorrando(m)} aria-label={`Eliminar marca ${m.nombre}`} icono={<Trash2 aria-hidden="true" size={18} />}>
            Eliminar
          </Boton>
        ) : (
          "—"
        ),
    },
  ];
  return (
    <Tarjeta titulo="Marcas">
      <div className="mb-4 flex flex-wrap items-end gap-4">
        <div className="min-w-48 flex-1">
          <CampoTexto etiqueta="Buscar marca" type="search" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
        </div>
        {puede("vehiculos.add_marca") && (
          <Boton
            onClick={() => {
              setCodigo("");
              setNombre("");
              guardar.reset();
              setNueva(true);
            }}
            icono={<Plus aria-hidden="true" size={18} />}
          >
            Nueva marca
          </Boton>
        )}
      </div>
      <TablaPaginada
        titulo="Marcas"
        columnas={columnas}
        datos={lista.data}
        cargando={lista.isFetching}
        error={lista.error}
        claveFila={(m) => m.codigo}
        pagina={lista.pagina}
        alCambiarPagina={lista.setPagina}
        orden={lista.orden}
        alOrdenar={lista.setOrden}
      />
      <DialogoFormulario
        abierto={nueva}
        titulo="Nueva marca"
        alCerrar={() => setNueva(false)}
        alEnviar={() => guardar.mutate({ codigo, nombre })}
        enviando={guardar.isPending}
        error={guardar.error}
      >
        <CampoTexto etiqueta="Código" value={codigo} onChange={(e) => setCodigo(e.target.value)} error={errores.codigo} obligatorio />
        <CampoTexto etiqueta="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} error={errores.nombre} obligatorio />
      </DialogoFormulario>
      <Confirmacion
        abierto={borrando !== null}
        titulo="Eliminar marca"
        mensaje={
          <>
            <p>
              ¿Eliminar la marca <strong>{borrando?.nombre}</strong>? Esta acción no se puede deshacer. No se permite si tiene
              líneas o motos asociadas.
            </p>
            <div className="mt-3">
              <AvisoError error={borrar.error} />
            </div>
          </>
        }
        textoConfirmar="Eliminar"
        cargando={borrar.isPending}
        alConfirmar={() => borrando && borrar.mutate(borrando.codigo)}
        alCerrar={() => {
          setBorrando(null);
          borrar.reset();
        }}
      />
    </Tarjeta>
  );
}

function SeccionLineas({ marca }: { marca: Marca | null }) {
  const { puede } = useSesion();
  const [nueva, setNueva] = useState(false);
  const [linea, setLinea] = useState("");
  const [borrando, setBorrando] = useState<Linea | null>(null);
  const lista = useLista("lineas", lineaSchema, { marca: marca?.codigo });
  const guardar = useGuardar("lineas", lineaSchema, { alExito: () => setNueva(false) });
  const borrar = useEliminar("lineas", () => setBorrando(null));
  const errores = guardar.error?.erroresDeCampo() ?? {};
  const columnas: Columna<Linea>[] = [
    { clave: "linea", titulo: "Línea", celda: (l) => l.linea, ordenable: "linea" },
    { clave: "marca", titulo: "Marca", celda: (l) => l.marca_nombre ?? l.marca },
    {
      clave: "acciones",
      titulo: "Acciones",
      celda: (l) =>
        puede("vehiculos.delete_linea") ? (
          <Boton variante="texto" onClick={() => setBorrando(l)} aria-label={`Eliminar línea ${l.linea}`} icono={<Trash2 aria-hidden="true" size={18} />}>
            Eliminar
          </Boton>
        ) : (
          "—"
        ),
    },
  ];
  return (
    <Tarjeta titulo={marca ? `Líneas de ${marca.nombre}` : "Líneas (todas las marcas)"}>
      {marca && puede("vehiculos.add_linea") && (
        <div className="mb-4">
          <Boton
            onClick={() => {
              setLinea("");
              guardar.reset();
              setNueva(true);
            }}
            icono={<Plus aria-hidden="true" size={18} />}
          >
            Nueva línea de {marca.nombre}
          </Boton>
        </div>
      )}
      <TablaPaginada
        titulo="Líneas"
        columnas={columnas}
        datos={lista.data}
        cargando={lista.isFetching}
        error={lista.error}
        claveFila={(l) => l.linea}
        pagina={lista.pagina}
        alCambiarPagina={lista.setPagina}
        orden={lista.orden}
        alOrdenar={lista.setOrden}
      />
      <DialogoFormulario
        abierto={nueva}
        titulo="Nueva línea"
        alCerrar={() => setNueva(false)}
        alEnviar={() => marca && guardar.mutate({ linea, marca: marca.codigo })}
        enviando={guardar.isPending}
        error={guardar.error}
      >
        <CampoTexto etiqueta="Nombre de la línea" value={linea} onChange={(e) => setLinea(e.target.value)} error={errores.linea} obligatorio />
      </DialogoFormulario>
      <Confirmacion
        abierto={borrando !== null}
        titulo="Eliminar línea"
        mensaje={
          <>
            <p>
              ¿Eliminar la línea <strong>{borrando?.linea}</strong>? Esta acción no se puede deshacer. No se permite si tiene motos
              asociadas.
            </p>
            <div className="mt-3">
              <AvisoError error={borrar.error} />
            </div>
          </>
        }
        textoConfirmar="Eliminar"
        cargando={borrar.isPending}
        alConfirmar={() => borrando && borrar.mutate(borrando.linea)}
        alCerrar={() => {
          setBorrando(null);
          borrar.reset();
        }}
      />
    </Tarjeta>
  );
}

export function PaginaCatalogos() {
  useTitulo("Marcas y líneas");
  const [marca, setMarca] = useState<Marca | null>(null);
  return (
    <>
      <EncabezadoPagina titulo="Marcas y líneas" descripcion="Elija una marca para ver y agregar sus líneas." />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <SeccionMarcas alElegir={setMarca} elegida={marca?.codigo} />
        <SeccionLineas marca={marca} />
      </div>
    </>
  );
}
