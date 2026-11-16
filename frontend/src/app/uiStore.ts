import { create } from "zustand";

/** Estado de interfaz solamente (tema y barra lateral). El token nunca va aquí. */
export type Tema = "claro" | "oscuro";

interface EstadoUi {
  tema: Tema;
  menuAbierto: boolean;
  alternarTema: () => void;
  alternarMenu: () => void;
  cerrarMenu: () => void;
}

function temaInicial(): Tema {
  try {
    const guardado = localStorage.getItem("tema");
    if (guardado === "claro" || guardado === "oscuro") return guardado;
  } catch {
    /* almacenamiento no disponible: se usa la preferencia del sistema */
  }
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "oscuro"
    : "claro";
}

export function aplicarTema(tema: Tema): void {
  document.documentElement.classList.toggle("dark", tema === "oscuro");
}

export const useUi = create<EstadoUi>((set, get) => ({
  tema: temaInicial(),
  menuAbierto: false,
  alternarTema: () => {
    const tema: Tema = get().tema === "claro" ? "oscuro" : "claro";
    try {
      localStorage.setItem("tema", tema);
    } catch {
      /* sin persistencia */
    }
    aplicarTema(tema);
    set({ tema });
  },
  alternarMenu: () => set((estado) => ({ menuAbierto: !estado.menuAbierto })),
  cerrarMenu: () => set({ menuAbierto: false }),
}));
