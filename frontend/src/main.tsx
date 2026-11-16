import "./styles/index.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app/App";
import { aplicarTema, useUi } from "./app/uiStore";

aplicarTema(useUi.getState().tema);

const raiz = document.getElementById("root");
if (!raiz) throw new Error("No se encontró el elemento #root");

createRoot(raiz).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
