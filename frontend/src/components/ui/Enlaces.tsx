import { Link } from "react-router-dom";

/** Nombre del contacto como enlace a su ficha (la cédula solo se ve en la ficha). */
export function EnlaceContacto({ nip, nombre }: { nip: string | null | undefined; nombre: string | null | undefined }) {
  if (!nip || !nombre) return <span className="texto-secundario">Contacto no registrado</span>;
  return (
    <Link to={`/contactos/${encodeURIComponent(nip)}`} className="enlace">
      {nombre}
    </Link>
  );
}

/** Placa como enlace a la información del vehículo. */
export function EnlacePlaca({ placa }: { placa: string | null | undefined }) {
  if (!placa) return <span className="texto-secundario">—</span>;
  return (
    <Link to={`/motos/${encodeURIComponent(placa)}`} className="enlace">
      {placa}
    </Link>
  );
}
