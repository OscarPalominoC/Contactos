import { KeyRound, Pencil, Plus, UserCheck, UserX } from "lucide-react";
import { useEffect, useState } from "react";
import { z } from "zod";

import { Aviso } from "../../components/ui/Aviso";
import { Boton } from "../../components/ui/Boton";
import { CampoSeleccion, CampoTexto } from "../../components/ui/Campos";
import { Confirmacion, Dialogo } from "../../components/ui/Dialogo";
import { EncabezadoPagina, Tarjeta } from "../../components/ui/Pagina";
import { TablaPaginada, type Columna } from "../../components/ui/TablaPaginada";
import { ROLES, usuarioSchema, type Usuario } from "../../services/esquemas";
import { useAccion, useGuardar, useLista } from "../../utils/consultas";
import { formatearFechaHora } from "../../utils/formatters";
import { useRetardo, useTitulo } from "../../utils/hooks";
import { DialogoFormulario, useFormulario } from "../formulario";

const NOMBRES_ROL: Record<(typeof ROLES)[number], string> = {
  administrador: "Administrador",
  ingeniero: "Ingeniero",
  tecnico: "Técnico",
  usuario: "Usuario",
};
const OPCIONES_ROL = ROLES.map((r) => ({ valor: r, texto: NOMBRES_ROL[r] }));

const formularioUsuarioSchema = z.object({
  nip: z.string().trim().regex(/^[0-9A-Za-z-]{2,20}$/, "Escriba el documento (2 a 20 caracteres)."),
  nombre: z.string().trim().min(3, "Escriba el nombre completo."),
  rol: z.enum(ROLES),
});
type Valores = { nip: string; nombre: string; rol: string };

/** Muestra la clave temporal una sola vez. */
function DialogoClaveTemporal({ usuario, alCerrar }: { usuario: Usuario | null; alCerrar: () => void }) {
  return (
    <Dialogo
      abierto={usuario !== null}
      titulo="Clave temporal generada"
      alCerrar={alCerrar}
      pie={
        <Boton onClick={alCerrar} variante="primario">
          Ya la anoté
        </Boton>
      }
    >
      <Aviso tipo="info">
        Entregue esta clave en persona a <strong>{usuario?.nombre}</strong>. No se volverá a mostrar; al ingresar deberá
        cambiarla.
      </Aviso>
      <p className="mt-4 text-center">
        <code className="font-heading rounded-lg bg-slate-500/15 px-4 py-2 text-2xl tracking-wider select-all">
          {usuario?.clave_temporal}
        </code>
      </p>
    </Dialogo>
  );
}

function FormularioUsuario({
  usuario,
  alCerrar,
  alCrear,
}: {
  usuario: Usuario | null | undefined;
  alCerrar: () => void;
  alCrear: (u: Usuario) => void;
}) {
  const edicion = Boolean(usuario);
  const { valores, setValores, errores, cambiar, validar, erroresServidor } = useFormulario<Valores>({ nip: "", nombre: "", rol: "usuario" });
  const guardar = useGuardar("usuarios", usuarioSchema, {
    id: usuario?.nip,
    alExito: (u) => {
      alCerrar();
      if (u.clave_temporal) alCrear(u);
    },
  });
  const { reset } = guardar;
  useEffect(() => {
    if (usuario === undefined) return;
    reset();
    setValores(usuario ? { nip: usuario.nip, nombre: usuario.nombre, rol: usuario.rol } : { nip: "", nombre: "", rol: "usuario" });
  }, [usuario, setValores, reset]);
  const enviar = () => {
    const datos = validar(formularioUsuarioSchema);
    if (!datos) return;
    guardar.mutate(edicion ? { nombre: datos.nombre, rol: datos.rol } : datos, { onError: erroresServidor });
  };
  return (
    <DialogoFormulario
      abierto={usuario !== undefined}
      titulo={edicion ? "Editar usuario" : "Nuevo usuario"}
      alCerrar={alCerrar}
      alEnviar={enviar}
      enviando={guardar.isPending}
      error={guardar.error}
    >
      <CampoTexto etiqueta="Usuario (documento)" value={valores.nip} onChange={cambiar("nip")} error={errores.nip} disabled={edicion} obligatorio />
      <CampoTexto etiqueta="Nombre completo" autoComplete="off" value={valores.nombre} onChange={cambiar("nombre")} error={errores.nombre} obligatorio />
      <CampoSeleccion etiqueta="Rol" value={valores.rol} onChange={cambiar("rol")} error={errores.rol} opciones={OPCIONES_ROL} />
      {!edicion && <p className="texto-secundario text-sm">Se generará una clave temporal que el usuario debe cambiar al ingresar.</p>}
    </DialogoFormulario>
  );
}

export function PaginaUsuarios() {
  useTitulo("Usuarios");
  const [busqueda, setBusqueda] = useState("");
  const [rol, setRol] = useState("");
  const [editando, setEditando] = useState<Usuario | null | undefined>(undefined);
  const [clave, setClave] = useState<Usuario | null>(null);
  const [reiniciando, setReiniciando] = useState<Usuario | null>(null);
  const [cambiandoEstado, setCambiandoEstado] = useState<Usuario | null>(null);
  const q = useRetardo(busqueda);
  const lista = useLista("usuarios", usuarioSchema, { q, rol });
  const { reiniciarPagina } = lista;
  useEffect(() => reiniciarPagina(), [q, rol, reiniciarPagina]);
  const reiniciar = useAccion("usuarios", "reiniciar-clave", usuarioSchema, {
    alExito: (u) => {
      setReiniciando(null);
      setClave(u);
    },
  });
  const estado = useGuardar("usuarios", usuarioSchema, { id: cambiandoEstado?.nip, alExito: () => setCambiandoEstado(null) });

  const columnas: Columna<Usuario>[] = [
    { clave: "nip", titulo: "Usuario", celda: (u) => u.nip, ordenable: "nip" },
    { clave: "nombre", titulo: "Nombre", celda: (u) => u.nombre, ordenable: "nombre" },
    { clave: "rol", titulo: "Rol", celda: (u) => NOMBRES_ROL[u.rol], ordenable: "rol" },
    {
      clave: "estado",
      titulo: "Estado",
      celda: (u) => (
        <div className="flex flex-col gap-1">
          <span className={`insignia ${u.is_active ? "insignia-exito" : "insignia-alerta"}`}>
            {u.is_active ? <UserCheck aria-hidden="true" size={14} /> : <UserX aria-hidden="true" size={14} />}
            {u.is_active ? "Activo" : "Desactivado"}
          </span>
          {u.debe_cambiar_clave && (
            <span className="insignia insignia-aviso">
              <KeyRound aria-hidden="true" size={14} />
              Clave temporal
            </span>
          )}
        </div>
      ),
    },
    { clave: "ingreso", titulo: "Último ingreso", celda: (u) => formatearFechaHora(u.last_login) },
    {
      clave: "acciones",
      titulo: "Acciones",
      celda: (u) => (
        <div className="flex flex-wrap gap-1">
          <Boton variante="texto" onClick={() => setEditando(u)} aria-label={`Editar ${u.nombre}`} icono={<Pencil aria-hidden="true" size={18} />}>
            Editar
          </Boton>
          <Boton variante="texto" onClick={() => setReiniciando(u)} aria-label={`Reiniciar clave de ${u.nombre}`} icono={<KeyRound aria-hidden="true" size={18} />}>
            Reiniciar clave
          </Boton>
          <Boton
            variante="texto"
            onClick={() => setCambiandoEstado(u)}
            aria-label={`${u.is_active ? "Desactivar" : "Activar"} a ${u.nombre}`}
            icono={u.is_active ? <UserX aria-hidden="true" size={18} /> : <UserCheck aria-hidden="true" size={18} />}
          >
            {u.is_active ? "Desactivar" : "Activar"}
          </Boton>
        </div>
      ),
    },
  ];

  return (
    <>
      <EncabezadoPagina
        titulo="Usuarios"
        descripcion="Cuentas del sistema. Los desbloqueos por intentos fallidos se hacen al reiniciar la clave o en Django Admin."
        acciones={
          <Boton onClick={() => setEditando(null)} icono={<Plus aria-hidden="true" size={18} />}>
            Nuevo usuario
          </Boton>
        }
      />
      <Tarjeta>
        <div role="search" className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          <CampoTexto etiqueta="Buscar por usuario o nombre" type="search" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
          <CampoSeleccion etiqueta="Rol" value={rol} onChange={(e) => setRol(e.target.value)} vacio="Todos" opciones={OPCIONES_ROL} />
        </div>
        <TablaPaginada
          titulo="Usuarios"
          columnas={columnas}
          datos={lista.data}
          cargando={lista.isFetching}
          error={lista.error}
          claveFila={(u) => u.nip}
          pagina={lista.pagina}
          alCambiarPagina={lista.setPagina}
          orden={lista.orden}
          alOrdenar={lista.setOrden}
        />
      </Tarjeta>
      <FormularioUsuario usuario={editando} alCerrar={() => setEditando(undefined)} alCrear={setClave} />
      <DialogoClaveTemporal usuario={clave} alCerrar={() => setClave(null)} />
      <Confirmacion
        abierto={reiniciando !== null}
        titulo="Reiniciar clave"
        mensaje={
          <p>
            Se generará una clave temporal nueva para <strong>{reiniciando?.nombre}</strong>, se cerrarán sus sesiones y se
            levantará cualquier bloqueo. ¿Continuar?
          </p>
        }
        textoConfirmar="Reiniciar clave"
        cargando={reiniciar.isPending}
        alConfirmar={() => reiniciando && reiniciar.mutate({ id: reiniciando.nip })}
        alCerrar={() => setReiniciando(null)}
      />
      <Confirmacion
        abierto={cambiandoEstado !== null}
        titulo={cambiandoEstado?.is_active ? "Desactivar usuario" : "Activar usuario"}
        mensaje={
          <p>
            {cambiandoEstado?.is_active
              ? `¿Desactivar a ${cambiandoEstado?.nombre}? No podrá ingresar y se cerrarán sus sesiones.`
              : `¿Activar de nuevo a ${cambiandoEstado?.nombre}?`}
          </p>
        }
        textoConfirmar={cambiandoEstado?.is_active ? "Desactivar" : "Activar"}
        cargando={estado.isPending}
        alConfirmar={() => cambiandoEstado && estado.mutate({ is_active: !cambiandoEstado.is_active })}
        alCerrar={() => setCambiandoEstado(null)}
      />
    </>
  );
}
