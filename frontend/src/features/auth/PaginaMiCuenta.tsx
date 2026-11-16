import { useSesion } from "../../app/sesion";
import { Detalles, EncabezadoPagina, Tarjeta } from "../../components/ui/Pagina";
import { useTitulo } from "../../utils/hooks";
import { FormularioCambioClave } from "./PaginaCambioClave";

export function PaginaMiCuenta() {
  useTitulo("Mi cuenta");
  const { usuario } = useSesion();
  return (
    <>
      <EncabezadoPagina titulo="Mi cuenta" />
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Tarjeta titulo="Datos">
          <Detalles
            items={[
              { termino: "Usuario", valor: usuario?.nip },
              { termino: "Nombre", valor: usuario?.nombre },
              { termino: "Rol", valor: <span className="capitalize">{usuario?.rol}</span> },
            ]}
          />
        </Tarjeta>
        <Tarjeta titulo="Cambiar clave">
          <FormularioCambioClave />
        </Tarjeta>
      </div>
    </>
  );
}
