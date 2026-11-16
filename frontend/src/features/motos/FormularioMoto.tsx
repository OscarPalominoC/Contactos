import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { z } from "zod";

import { CampoSeleccion, CampoTexto } from "../../components/ui/Campos";
import { lineaSchema, marcaSchema, motoSchema, type Moto } from "../../services/esquemas";
import { obtenerLista, parametrosLista } from "../../services/recursos";
import { useGuardar } from "../../utils/consultas";
import { normalizarPlaca } from "../../utils/formatters";
import { DialogoFormulario, fechaOpcional, nulo, useFormulario } from "../formulario";

export const formularioMotoSchema = z.object({
  placa: z
    .string()
    .transform(normalizarPlaca)
    .pipe(z.string().regex(/^[A-Z0-9]{5,6}$/, "La placa debe tener 5 o 6 letras y números, por ejemplo ABC12D.")),
  marca: z.string().trim().min(1, "Elija la marca."),
  linea: z.string().trim(),
  modelo: z
    .string()
    .trim()
    .refine((v) => v === "" || /^\d{4}$/.test(v), "El modelo es el año de 4 dígitos."),
  nip_contacto: z.string().trim().min(3, "Escriba el documento del propietario."),
  fecha_venc_soat: fechaOpcional,
  fecha_venc_rtmg: fechaOpcional,
});

type Valores = z.input<typeof formularioMotoSchema>;

const VACIO: Valores = { placa: "", marca: "", linea: "", modelo: "", nip_contacto: "", fecha_venc_soat: "", fecha_venc_rtmg: "" };

/** Marcas y líneas dependientes: las líneas se filtran por la marca elegida. */
export function useCatalogoMarcas(marcaNombre: string) {
  const marcas = useQuery({
    queryKey: ["marcas", "todas"],
    queryFn: async ({ signal }) => {
      const pagina = await obtenerLista("/marcas", marcaSchema, parametrosLista(1, 100, {}, "nombre"), signal);
      const resto = await Promise.all(
        Array.from({ length: pagina.meta.page.total_pages - 1 }, (_, i) =>
          obtenerLista("/marcas", marcaSchema, parametrosLista(i + 2, 100, {}, "nombre"), signal),
        ),
      );
      return [pagina, ...resto].flatMap((p) => p.data);
    },
    staleTime: 5 * 60 * 1000,
  });
  const codigo = marcas.data?.find((m) => m.nombre === marcaNombre)?.codigo;
  const lineas = useQuery({
    queryKey: ["lineas", "por-marca", codigo],
    enabled: Boolean(codigo),
    queryFn: ({ signal }) => obtenerLista("/lineas", lineaSchema, parametrosLista(1, 100, { marca: codigo }, "linea"), signal),
    staleTime: 5 * 60 * 1000,
  });
  return { marcas: marcas.data ?? [], lineas: lineas.data?.data ?? [] };
}

export function FormularioMotoDialogo({
  moto,
  nipInicial,
  alCerrar,
}: {
  moto: Moto | null | undefined;
  nipInicial?: string;
  alCerrar: () => void;
}) {
  const edicion = Boolean(moto);
  const { valores, setValores, errores, cambiar, validar, erroresServidor } = useFormulario<Valores>(VACIO);
  const { marcas, lineas } = useCatalogoMarcas(valores.marca);
  const guardar = useGuardar("motos", motoSchema, { id: moto?.placa, invalidar: ["ficha"], alExito: alCerrar });
  const { reset } = guardar;

  useEffect(() => {
    if (moto === undefined) return;
    reset();
    setValores(
      moto
        ? {
            placa: moto.placa,
            marca: moto.marca,
            linea: moto.linea,
            modelo: moto.modelo,
            nip_contacto: moto.nip_contacto,
            fecha_venc_soat: moto.fecha_venc_soat ?? "",
            fecha_venc_rtmg: moto.fecha_venc_rtmg ?? "",
          }
        : { ...VACIO, nip_contacto: nipInicial ?? "" },
    );
  }, [moto, nipInicial, setValores, reset]);

  const enviar = () => {
    const datos = validar(formularioMotoSchema);
    if (!datos) return;
    const cuerpo: Record<string, unknown> = {
      marca: datos.marca,
      linea: datos.linea,
      modelo: datos.modelo,
      nip_contacto: datos.nip_contacto,
      fecha_venc_soat: nulo(datos.fecha_venc_soat),
      fecha_venc_rtmg: nulo(datos.fecha_venc_rtmg),
    };
    if (!edicion) cuerpo.placa = datos.placa;
    guardar.mutate(cuerpo, { onError: erroresServidor });
  };

  const opcionesMarca = marcas.map((m) => ({ valor: m.nombre, texto: m.nombre }));
  if (valores.marca && !opcionesMarca.some((o) => o.valor === valores.marca)) {
    opcionesMarca.unshift({ valor: valores.marca, texto: `${valores.marca} (del registro)` });
  }
  const opcionesLinea = lineas.map((l) => ({ valor: l.linea, texto: l.linea }));
  if (valores.linea && !opcionesLinea.some((o) => o.valor === valores.linea)) {
    opcionesLinea.unshift({ valor: valores.linea, texto: `${valores.linea} (del registro)` });
  }

  return (
    <DialogoFormulario
      abierto={moto !== undefined}
      titulo={edicion ? `Editar moto ${moto?.placa}` : "Nueva moto"}
      alCerrar={alCerrar}
      alEnviar={enviar}
      enviando={guardar.isPending}
      error={guardar.error}
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <CampoTexto
          etiqueta="Placa"
          value={valores.placa}
          onChange={cambiar("placa")}
          error={errores.placa}
          disabled={edicion}
          autoCapitalize="characters"
          obligatorio
        />
        <CampoTexto
          etiqueta="Documento del propietario"
          value={valores.nip_contacto}
          onChange={cambiar("nip_contacto")}
          error={errores.nip_contacto}
          obligatorio
        />
        <CampoSeleccion
          etiqueta="Marca"
          value={valores.marca}
          onChange={(e) => setValores((v) => ({ ...v, marca: e.target.value, linea: "" }))}
          error={errores.marca}
          vacio="Elija una marca"
          opciones={opcionesMarca}
          obligatorio
        />
        <CampoSeleccion
          etiqueta="Línea"
          value={valores.linea}
          onChange={cambiar("linea")}
          error={errores.linea}
          vacio={valores.marca ? "Sin línea" : "Elija primero la marca"}
          opciones={opcionesLinea}
          disabled={!valores.marca}
        />
        <CampoTexto
          etiqueta="Modelo (año)"
          inputMode="numeric"
          value={valores.modelo}
          onChange={cambiar("modelo")}
          error={errores.modelo}
        />
        <CampoTexto
          etiqueta="Vencimiento SOAT"
          type="date"
          value={valores.fecha_venc_soat}
          onChange={cambiar("fecha_venc_soat")}
          error={errores.fecha_venc_soat}
        />
        <CampoTexto
          etiqueta="Vencimiento RTM"
          type="date"
          value={valores.fecha_venc_rtmg}
          onChange={cambiar("fecha_venc_rtmg")}
          error={errores.fecha_venc_rtmg}
        />
      </div>
    </DialogoFormulario>
  );
}
