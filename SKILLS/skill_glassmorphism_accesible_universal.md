---
name: glassmorphism-accesible-universal
description: Guía integral y lista de chequeo para diseñar e implementar interfaces Glassmorphism/Glossy universales y totalmente accesibles (WCAG 2.1 Nivel AA, Directrices MinTIC Res. 1519 y compatibilidad React/Django).
tags:
  - skill
  - frontend
  - ui-ux
  - glassmorphism
  - accesibilidad
  - wcag21aa
  - mintic
version: 2.2
---

# Skill — Glassmorphism Accesible & Universal (WCAG 2.1 AA / Directrices MinTIC)

**Versión:** 2.2 (Unificada, Universal, Exhaustiva y Canónica)  
**Alcance:** Todo tipo de proyecto web (Frontends SPA/React + TypeScript, SSR/Django + Jinja2, o HTML/CSS agnóstico).  
**Norma obligatoria:** WCAG 2.1 Nivel AA estricto + Directrices de accesibilidad web (MinTIC Res. 1519 de 2020 como marco contractual y técnico) + Fundamentos Estructurales de Glassmorphism + Auditoría Google Lighthouse / axe-core (Objetivo: 100 en *Accessibility*, 0 fallos de contraste o estructura).

---

## 0. Propósito y Filosofía de Diseño

Esta skill establece las pautas de ingeniería, arquitectura de estilos y control de calidad para construir interfaces con estética **Glassmorphism / Glossy** garantizando **accesibilidad web universal**:

1. **La estética cede ante la legibilidad:** El efecto de vidrio nunca puede comprometer el contraste, la nitidez ni la comprensión de la información. Si un efecto compite con la lectura, se retira el efecto.
2. **Independencia de marca:** Los tokens y recetas están parametrizados mediante CSS Custom Properties (`--brand-*`, `--glass-*`), permitiendo su adopción en cualquier identidad corporativa sin alterar las garantías de contraste.
3. **Cálculo sobre el peor escenario:** Toda relación de contraste se valida contra el fondo compuesto más desfavorable (fondo base + gradientes/orbes ambientales en su punto más brillante + superficie translúcida).
4. **Regla tipográfica de encabezados principales:** Todos los títulos de primer nivel (`h1`, `.title-l1`, `.glass-title-primary`) deben tener obligatoriamente **1px de separación entre letras** (`letter-spacing: 1px;`).

---

## 1. Fundamentos Técnicos del Glassmorphism (Requisitos Canónicos)

Para que una interfaz sea considerada técnicamente **Glassmorphism** y no una simple caja transparente, debe cumplir con 5 principios físicos y visuales indispensables que simulan las propiedades ópticas del vidrio real flotante:

```
┌──────────────────────────────────────────────────────────┐
│ 1. Brillo especular superior: 1px linear-gradient        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 2. Transluscencia: background rgba(...)                  │
│    + 3. Difuminado de fondo: backdrop-filter: blur(...) │
│                                                          │
│ 4. Borde de refracción sutil: border 1px solid rgba(...) │
└──────────────────────────────────────────────────────────┘
  ▼  5. Sombra de elevación y profundidad: box-shadow
```

1. **Transluscencia y transparencia selectiva:** La superficie debe dejar entrever los colores, formas o imágenes subyacentes sin ocultarlos por completo, empleando canales alfa equilibrados en el fondo (`rgba()` o `hsla()`).
2. **Desenfoque de fondo (*Backdrop Blur*):** La propiedad `backdrop-filter: blur(...)` es obligatoria. Difumina el contenido que pasa por detrás para emular el vidrio esmerilado, eliminar el ruido visual de fondo y estabilizar la luminancia requerida para el contraste del texto.
3. **Borde sutil de refracción (*Subtle Border*):** Un contorno perimetral semitransparente (típicamente `1px` con alfa bajo claro en bordes superiores/izquierdos) que define físicamente el grosor y límite geométrico del cristal sobre fondos dinámicos.
4. **Luz especular y reflejos direccionales (*Specular Highlight / Glossy edge*):** Línea o gradiente de brillo en el borde superior (mediante pseudo-elementos `::before`) que simula la reflexión de una fuente de luz física.
5. **Profundidad espacial y elevación flotante (*Layering & Drop Shadow*):** Empleo de sombras arrojadas multidimensionales (`box-shadow`) combinadas con fondos oscuros, gradientes u orbes flotantes que demuestren que el cristal está suspendido por encima del plano de fondo.

---

## 2. Tokens de Superficie y Sistema de Diseño Adaptable

### 2.1 Variables globales de marca (Parametrizables)
Configura los colores base del proyecto en `:root`:

```css
:root {
  /* Identidad principal y acentos */
  --brand-primary: #C81D25;          /* Color de acción / CTA */
  --brand-primary-hover: #b01920;
  --brand-accent: #9A6B3E;           /* Acento secundario o corporativo */
  --brand-accent-light: #E5C185;

  /* Superficies neutras */
  --bg-app-dark: #07080b;
  --bg-app-light: #f1f5f9;

  /* Tipografía base */
  --font-family-base: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-family-heading: inherit;
}

/* Regla estructural obligatoria: Títulos de primer nivel */
h1, .title-l1, .glass-title-primary {
  letter-spacing: 1px;
}
```

### 2.2 Tokens de vidrio en modo oscuro (`.dark`)

```css
.dark {
  --glass-bg: rgba(18, 20, 28, 0.86);        /* Superficie principal con texto */
  --glass-bg-subtle: rgba(14, 16, 23, 0.75); /* Superficies secundarias */
  --glass-border: rgba(255, 255, 255, 0.12);
  --glass-border-subtle: rgba(255, 255, 255, 0.06);
  --glass-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.55),
                  0 0 1px 1px rgba(255, 255, 255, 0.08) inset;
  --glass-highlight: inset 0 1px 1px 0 rgba(255, 255, 255, 0.22);
  --glass-blur: blur(18px);

  /* Texto seguro en modo oscuro */
  --text-main: #F5F1E8;         /* Blanco cálido/hueso: evita fatiga visual */
  --text-secondary: #94a3b8;    /* ≥ 4.5:1 sobre vidrio compuesto */
  --text-focus: #ff6b72;        /* Contraste ≥ 3:1 para foco visible */
}
```

### 2.3 Tokens de vidrio en modo claro (`html:not(.dark)`)

```css
html:not(.dark) {
  --glass-bg: rgba(255, 255, 255, 0.80);      /* Superficie principal */
  --glass-bg-subtle: rgba(255, 255, 255, 0.62);
  --glass-border: rgba(15, 23, 42, 0.10);
  --glass-border-subtle: rgba(15, 23, 42, 0.06);
  --glass-shadow: 0 10px 30px -8px rgba(15, 23, 42, 0.12),
                  0 0 0 1px rgba(255, 255, 255, 0.7) inset;
  --glass-highlight: inset 0 1px 1px 0 rgba(255, 255, 255, 0.9);
  --glass-blur: blur(18px);

  /* Texto seguro en modo claro */
  --text-main: #0f172a;         /* Pizarra profunda (≥ 12:1) */
  --text-secondary: #475569;    /* ≥ 4.5:1 sobre vidrio compuesto */
  --text-focus: #C81D25;
}
```

### 2.4 Reglas de opacidad (Alpha blending)
- **Contenedores con texto (cards, paneles, tablas, inputs):** Alfa mínimo de **0.80** en modo claro y **0.86** en modo oscuro. En pantallas con imagen de fondo estática sin orbes saturados, el piso tolerable es **0.70** (claro) y **0.62** (oscuro).
- **Prohibición de transparencia baja en texto:** Nunca coloques texto normal sobre fondos con alfa `< 0.60` ni directamente sobre orbes decorativos.
- **Halos luminosos (tarjetas KPI):** Opacidad máxima del **0.10** (10 %) para evitar que degraden el contraste del fondo que mide Lighthouse bajo números o etiquetas.

---

## 3. Componentes Base Accesibles

### 3.1 Contenedor Glassmorphism con borde de luz especular
El efecto glossy radica en el reflejo superior fino (1 px) sin alterar la opacidad central donde reside el texto:

```css
.glass-card {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  border-radius: 1rem;
  position: relative;
  overflow: hidden;
}

.glass-card::before {
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.45), transparent);
  pointer-events: none;
}
html:not(.dark) .glass-card::before {
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.95), transparent);
}
```

### 3.2 Botones de acción (CTAs)
Los botones interactivos **no usan fondos translúcidos**. Usan gradientes o fondos sólidos donde **cada parada** satisface `≥ 4.5:1` de contraste contra el texto:

```css
.glass-btn-primary {
  font-weight: 600;
  border-radius: 0.5rem;
  padding: 0.625rem 1.25rem;
  min-height: 44px; /* Área táctil accesible recomendada */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 4px 18px -2px rgba(0, 0, 0, 0.25),
              inset 0 1px 1px 0 rgba(255, 255, 255, 0.4);
}

html:not(.dark) .glass-btn-primary {
  background: linear-gradient(135deg, #d0222b 0%, #C81D25 55%, #9b1319 100%);
  color: #ffffff;
}

.dark .glass-btn-primary {
  background: linear-gradient(135deg, #C81D25 0%, #b01920 55%, #8f1217 100%);
  color: #F5F1E8;
}
```

### 3.3 Inputs y controles (WCAG 1.4.11)
El borde identificador del campo debe ofrecer `≥ 3:1` de contraste visible contra la superficie adyacente:

```css
.glass-input {
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(12px);
  border: 1px solid #64748b; /* ≥ 3:1 en ambos modos */
  color: #0f172a;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
  min-height: 44px;
}

.glass-input::placeholder { color: #64748b; }

.dark .glass-input {
  background: rgba(14, 16, 23, 0.65);
  color: #f8fafc;
  border-color: #94a3b8;
}

.dark .glass-input::placeholder { color: #94a3b8; }
```

### 3.4 Foco visible universal (WCAG 2.4.7)
Nunca remuevas el `outline` sin proporcionar un sustituto de alto contraste:

```css
:where(a, button, input, select, textarea, [tabindex]):focus-visible {
  outline: 2px solid var(--text-focus);
  outline-offset: 2px;
}
```

---

## 4. Matriz de Estados Funcionales Universales

El color no puede ser el único portador de información (WCAG 1.4.1); todo badge o estado debe incluir **icono visible + texto explícito**.

| Estado Semántico | Modo Oscuro (Fondo / Borde / Texto) | Modo Claro (Fondo / Borde / Texto) | Contraste |
| :--- | :--- | :--- | :---: |
| **Éxito / Disponible** | `rgba(16,185,129,0.18)` / `rgba(16,185,129,0.45)` / `#34d399` | `rgba(16,185,129,0.14)` / `rgba(16,185,129,0.30)` / `#065f46` | ≥ 5.8:1 ✅ |
| **Alerta / Crítico** | `rgba(239,68,68,0.18)` / `rgba(239,68,68,0.45)` / `#ff8a8f` | `rgba(220,38,38,0.10)` / `rgba(220,38,38,0.30)` / `#a3161d` | ≥ 5.4:1 ✅ |
| **Advertencia / Espera** | `rgba(245,158,11,0.18)` / `rgba(245,158,11,0.45)` / `#fbbf24` | `rgba(245,158,11,0.16)` / `rgba(245,158,11,0.30)` / `#92400e` | ≥ 5.4:1 ✅ |
| **Informativo / Neutro** | `rgba(59,130,246,0.18)` / `rgba(59,130,246,0.45)` / `#93c5fd` | `rgba(59,130,246,0.12)` / `rgba(59,130,246,0.30)` / `#1d4ed8` | ≥ 4.9:1 ✅ |

---

## 5. Implementación por Stack Tecnológico

### 5.1 React 18+ & TypeScript
*Nota:* `@axe-core/react` no es compatible con React 18+ y falla en silencio. Usa `jest-axe` sobre Vitest y `@axe-core/playwright` para páginas renderizadas.

```tsx
import { useId, type InputHTMLAttributes } from 'react';

interface AccessibleInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  helperText?: string;
}

export function AccessibleInputField({
  label,
  error,
  helperText,
  ...props
}: AccessibleInputProps) {
  const id = useId();
  const errorId = `${id}-error`;
  const helperId = `${id}-helper`;

  const descriptions = [
    helperText ? helperId : null,
    error ? errorId : null,
  ].filter(Boolean).join(' ') || undefined;

  return (
    <div className="flex flex-col gap-1.5 w-full">
      <label htmlFor={id} className="text-sm font-medium text-slate-700 dark:text-slate-200">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={Boolean(error)}
        aria-describedby={descriptions}
        className="glass-input transition-colors duration-150"
        {...props}
      />
      {helperText && !error && (
        <p id={helperId} className="text-xs text-slate-500 dark:text-slate-400">
          {helperText}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-xs font-semibold text-red-600 dark:text-red-400 flex items-center gap-1">
          <span aria-hidden="true">⚠</span> {error}
        </p>
      )}
    </div>
  );
}
```

### 5.2 Django & Jinja2
Garantiza enlace de salto con entrada de foco (`tabindex="-1"`), idioma del documento y macros con ARIA integrado:

```jinja
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Plataforma Web{% endblock %}</title>
</head>
<body class="bg-slate-100 dark:bg-neutral-950 text-slate-900 dark:text-[#F5F1E8]">
  <a href="#contenido-principal" class="sr-only focus:not-sr-only focus:absolute focus:p-4 focus:bg-white focus:text-black focus:z-50">
    Saltar al contenido principal
  </a>

  <header role="banner">
    <nav aria-label="Principal"><!-- Menú --></nav>
  </header>

  <main id="contenido-principal" tabindex="-1" class="outline-none">
    {% if messages %}
      <div role="status" aria-live="polite" class="sr-only">
        {% for message in messages %}{{ message }}{% endfor %}
      </div>
    {% endif %}
    {% block content %}{% endblock %}
  </main>
</body>
</html>
```

---

## 6. Preferencias de Usuario y Robustez

```css
/* Soporte sin backdrop-filter */
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .dark { --glass-bg: rgba(18, 20, 28, 0.96); }
  html:not(.dark) { --glass-bg: rgba(255, 255, 255, 0.94); }
}

/* Reducción de transparencia */
@media (prefers-reduced-transparency: reduce) {
  .dark { --glass-bg: rgba(18, 20, 28, 0.98); }
  html:not(.dark) { --glass-bg: rgba(255, 255, 255, 0.98); }
  .liquid-orb, [class*="halo-"] { display: none !important; }
}

/* Movimiento reducido (WCAG 2.2.2) */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* Modo de colores forzados / Alto contraste */
@media (forced-colors: active) {
  .glass-card, .glass-btn-primary, .glass-input {
    border: 1px solid CanvasText !important;
    backdrop-filter: none !important;
    background: Canvas !important;
    color: CanvasText !important;
  }
}
```

---

## 7. Lista de Chequeo Integral: Requisitos Glassmorphism, WCAG 2.1 AA y Directrices MinTIC 1519

Esta lista reúne de manera exhaustiva todos los requisitos necesarios para considerar un diseño como **Glassmorphism auténtico y accesible**, junto a los cuatro principios **POUR** (Perceptible, Operable, Comprensible y Robusto) conforme a la Resolución MinTIC 1519 de 2020 (Anexo 1) y la especificación WCAG 2.1 AA.

### Regla Estructural Obligatoria
- [ ] **Tipografía de encabezados de nivel 1:** Todo título de primer nivel (`h1`, `.title-l1`, `.glass-title-primary`) tiene configurado estrictamente `letter-spacing: 1px;`.

---

### A. Requisitos de Estilo y Composición Glassmorphism

- [ ] **Transluscencia de superficie:** Contenedores y paneles emplean colores de fondo con canal alfa (`rgba()` o `hsla()`) sin ser 100 % opacos ni 100 % transparentes.
- [ ] **Desenfoque de fondo activo (`backdrop-filter`):** Se aplica `backdrop-filter: blur(...)` (y `-webkit-backdrop-filter`) para dispersar las frecuencias del fondo y evitar bordes duros que alteren la luminancia local bajo los textos.
- [ ] **Borde perimetral de refracción:** Las tarjetas poseen un borde fino semitransparente (`1px solid rgba(...)`) que demarca el contorno de la superficie vítrea.
- [ ] **Brillo especular (*Glossy highlight*):** Implementación de una línea de luz o gradiente superior (vía `::before` o borde superior más claro) que simula el reflejo físico direccional.
- [ ] **Profundidad y flotación espacial:** El cristal proyecta sombras suaves (`box-shadow`) sobre planos inferiores oscuros, degradados o con orbes sutiles para denotar elevación tridimensional.
- [ ] **Opacidad mínima de seguridad para texto:** Las superficies con texto cumplen con el alfa mínimo no negociable: `≥ 0.80` en modo claro y `≥ 0.86` en modo oscuro (o mínimo absoluto `0.70`/`0.62` sobre fondos ilustrados estáticos).
- [ ] **Fondo de botones sólido o gradiente opaco:** Los botones de acción no usan transparencias difusas con texto blanco; el fondo del botón es sólido o un degradado con cada parada validada en contraste.
- [ ] **Halos decorativos acotados:** Los orbes o halos luminosos interiores/exteriores no exceden el 10 % de opacidad (`0.10`) detrás de zonas con contenido textual.
- [ ] **Degradación elegante (*Fallback* sin `backdrop-filter`):** El CSS incluye `@supports not (backdrop-filter: blur(1px))` elevando la opacidad al 94–96 % en navegadores antiguos.

---

### B. Principio 1: Perceptible

#### Información no textual y multimedia
- [ ] **1.1.1 Contenido no textual (Nivel A):** Toda imagen no decorativa dispone de un atributo `alt` claro y descriptivo. Las imágenes decorativas llevan `alt=""` o `aria-hidden="true"`.
- [ ] **1.2.1 Solo audio o solo vídeo pregrabado (Nivel A):** Se proveen alternativas textuales o transcripciones descriptivas equivalentes.
- [ ] **1.2.2 Subtítulos pregrabados (Nivel A):** Todo vídeo con pista de audio cuenta con subtítulos sincronizados.
- [ ] **1.2.3 / 1.2.5 Audiodescripción o descripción textual (Niveles A y AA):** Se entrega descripción sonora o textual de las acciones visuales clave en medios temporizados.

#### Adaptabilidad y estructura
- [ ] **1.3.1 Información y relaciones (Nivel A):** Encabezados (`h1`-`h6`) jerárquicos y continuos sin saltos arbitrarios; uso de etiquetas semánticas (`nav`, `main`, `header`, `footer`, `section`, `table` con encabezados `th` asociados mediante `scope`).
- [ ] **1.3.2 Secuencia con significado (Nivel A):** El orden de lectura en el árbol DOM es lógico y equivalente a la disposición visual.
- [ ] **1.3.3 Características sensoriales (Nivel A):** Las instrucciones no dependen únicamente de atributos físicos como tamaño, forma, posición ("el botón redondo de la derecha") o sonido.
- [ ] **1.3.4 Orientación (WCAG 2.1 - Nivel AA):** La interfaz no bloquea ni restringe su presentación a modo horizontal o vertical, salvo requerimiento técnico indispensable.
- [ ] **1.3.5 Identificación del propósito de las entradas (WCAG 2.1 - Nivel AA):** Los campos que recolectan información del usuario incorporan el atributo `autocomplete` correspondiente (`name`, `email`, `tel`, `address-line1`, etc.).

#### Distinguible y contraste en vidrio
- [ ] **1.4.1 Uso del color (Nivel A):** El color no es el único medio para transmitir información, indicar acciones o marcar errores (se combina siempre color + texto + icono).
- [ ] **1.4.2 Control del audio (Nivel A):** Ningún audio inicia automáticamente con duración superior a 3 segundos sin controles para pausarlo, detenerlo o silenciarlo.
- [ ] **1.4.3 Contraste mínimo de texto (Nivel AA):** 
  - Texto normal: Ratio `≥ 4.5:1` calculado sobre el peor escenario compuesto (vidrio + orbe ambiental más brillante).
  - Texto grande (≥ 24 px o ≥ 18.66 px negrita): Ratio `≥ 3:1`.
  - En modo oscuro se emplea blanco cálido/hueso (`#F5F1E8`) en lugar de blanco puro para evitar fatiga visual.
- [ ] **1.4.4 Cambio de tamaño del texto (Nivel AA):** El contenido se escala hasta un 200 % con zoom de navegador sin desbordarse ni truncar información (`rem`/`em` en tipografías y contenedores fluidos).
- [ ] **1.4.5 Imágenes de texto (Nivel AA):** Se usa texto real renderizado por CSS y no imágenes que representen texto tipográfico.
- [ ] **1.4.10 Reflujo (WCAG 2.1 - Nivel AA):** La interfaz responde fluidamente hasta un ancho de 320 px CSS sin presentar doble barra de desplazamiento (scroll horizontal).
- [ ] **1.4.11 Contraste no textual (WCAG 2.1 - Nivel AA):** Bordes de inputs, casillas de selección, estados interactivos e iconos informativos tienen `≥ 3:1` contra el fondo adyacente.
- [ ] **1.4.12 Espaciado de texto (WCAG 2.1 - Nivel AA):** El layout tolera sin roturas las métricas forzadas: interlineado a 1.5, espacio tras párrafo a 2 veces el tamaño de la fuente, espaciado entre letras a 0.12 veces y palabras a 0.16 veces.
- [ ] **1.4.13 Contenido en hover o foco (WCAG 2.1 - Nivel AA):** Menús, tooltips o desplegables emergentes son descartables (tecla `Esc`), hoverables (el puntero se puede mover hacia ellos sin que desaparezcan) y persistentes.

---

### C. Principio 2: Operable

#### Accesibilidad por teclado y tiempos
- [ ] **2.1.1 Teclado (Nivel A):** Toda función, botón, control o navegación es operable enteramente mediante teclado (`Tab`, `Shift+Tab`, `Enter`, `Espacio`, flechas) sin requerir ratón.
- [ ] **2.1.2 Sin trampas para el foco (Nivel A):** El foco de teclado nunca queda atrapado; modales y diálogos capturan el foco mientras están abiertos y lo liberan devolviéndolo al disparador al cerrarse (`Esc`).
- [ ] **2.1.4 Atajos de teclas de un solo carácter (WCAG 2.1 - Nivel A):** Si existen atajos de teclado de una sola tecla (sin Ctrl/Alt), estos pueden desactivarse o reasignarse.
- [ ] **2.2.1 Tiempo ajustable (Nivel A):** Si existen sesiones temporizadas, el usuario recibe alerta y al menos 20 segundos para prorrogar el tiempo con una acción simple.
- [ ] **2.2.2 Pausar, detener, ocultar (Nivel A):** Animaciones o transiciones continuas de más de 5 segundos disponen de control de pausa o respetan `prefers-reduced-motion: reduce`.
- [ ] **2.3.1 Tres destellos o por debajo del umbral (Nivel A):** Ningún elemento visual parpadea más de tres veces por segundo para evitar episodios fotosensibles.

#### Navegabilidad y foco
- [ ] **2.4.1 Evitar bloques (Nivel A):** Existe un enlace visible al recibir el foco (`skip link`) para "Saltar al contenido principal", cuyo contenedor destino cuenta con `tabindex="-1"`.
- [ ] **2.4.2 Titulado de páginas (Nivel A):** Cada página o vista posee una etiqueta `<title>` única, clara y descriptiva del propósito o sección actual.
- [ ] **2.4.3 Orden del foco (Nivel A):** El recorrido de navegación con teclado respeta estrictamente la coherencia de lectura visual y operativa.
- [ ] **2.4.4 Propósito de los enlaces en contexto (Nivel A):** El texto de cada enlace describe claramente su destino (evitar textos genéricos como "clic aquí" o "ver más" sin texto accesible de contexto).
- [ ] **2.4.5 Múltiples vías (Nivel AA):** Se proporcionan al menos dos formas distintas de localizar una página dentro del sitio (p. ej., menú principal, mapa de sitio, buscador interno o enlaces de pie).
- [ ] **2.4.6 Encabezados y etiquetas (Nivel AA):** Los encabezados (`h1`-`h6`) y las etiquetas describen claramente el tema, propósito o información requerida.
- [ ] **2.4.7 Foco visible (Nivel AA):** Todo elemento con foco interactivo muestra un contorno visual sólido y bien diferenciado (`outline: 2px solid ...`), evitando el uso exclusivo de sombras difusas o `outline: none`.

#### Modalidades de entrada
- [ ] **2.5.1 Gestos de puntero (WCAG 2.1 - Nivel A):** Cualquier operación realizada mediante gestos complejos (deslizar, pellizcar) puede ejecutarse también mediante un puntero simple (toque o clic).
- [ ] **2.5.2 Cancelación del puntero (WCAG 2.1 - Nivel A):** Las funciones por clic o toque se disparan en el evento `up` (al soltar), permitiendo cancelar la acción si se retira el puntero antes de completar.
- [ ] **2.5.3 Inclusión de la etiqueta en el nombre (WCAG 2.1 - Nivel A):** El nombre accesible de un botón o enlace contiene el mismo texto visible en su etiqueta para compatibilidad con software de control por voz.
- [ ] **2.5.4 Activación por movimiento (WCAG 2.1 - Nivel A):** Funciones accionables por sacudir o inclinar el dispositivo pueden ser desactivadas y cuentan con alternativa de interfaz tradicional.
- [ ] **Tamaño de objetivos táctiles (Recomendación universal):** Controles primarios con dimensión mínima recomendada de **44 × 44 px CSS** en pantallas móviles o táctiles, y no menor a 24 × 24 px en escritorios densos.

---

### D. Principio 3: Comprensible

#### Legibilidad e idioma
- [ ] **3.1.1 Idioma de la página (Nivel A):** El elemento raíz declara el idioma base correcto (ej. `<html lang="es">`).
- [ ] **3.1.2 Idioma de partes (Nivel AA):** Cualquier cambio de lengua dentro del texto está delimitado con su respectivo atributo `lang` (ej. `<span lang="en">...</span>`).

#### Previsibilidad
- [ ] **3.2.1 Al recibir el foco (Nivel A):** Ningún elemento desencadena un cambio automático de contexto (envío de formulario, apertura de modal o cambio de página) por el mero hecho de recibir el foco.
- [ ] **3.2.2 Al recibir entradas (Nivel A):** Escribir o seleccionar una opción en un input/select no altera el contexto abruptamente a menos que se haya advertido al usuario antes.
- [ ] **3.2.3 Navegación coherente (Nivel AA):** Los elementos repetidos de navegación (menús, cabeceras) se sitúan en el mismo orden visual relativo en todas las vistas.
- [ ] **3.2.4 Identificación coherente (Nivel AA):** Componentes con la misma funcionalidad mantienen etiquetas, iconos y nombres consistentes a lo largo del sistema.

#### Asistencia a la entrada de datos
- [ ] **3.3.1 Identificación de errores (Nivel A):** Los errores de validación se identifican en texto, indicando claramente el campo afectado.
- [ ] **3.3.2 Etiquetas o instrucciones (Nivel A):** Todo control de formulario dispone de una etiqueta `<label>` visible vinculada por `for`/`id` (o `htmlFor`/`id` en React). El `placeholder` no sustituye a la etiqueta.
- [ ] **3.3.3 Sugerencias ante errores (Nivel AA):** El sistema no solo señala que hubo un error, sino que expone en texto cómo corregirlo adecuadamente.
- [ ] **3.3.4 Prevención de errores en transacciones legales, financieras o de datos sensibles (Nivel AA):** Las acciones críticas, envíos legales o transacciones irreversibles son reversibles, confirmables mediante un paso previo de revisión, o verificadas antes de su confirmación final.

---

### E. Principio 4: Robusto

- [ ] **4.1.1 Procesamiento / Parsing (Nivel A):** HTML válido, sin IDs duplicados, etiquetas correctamente anidadas y sin errores de cierre.
- [ ] **4.1.2 Nombre, función y valor (Nivel A):** Todos los componentes de interfaz exponen su rol semántico nativo (`button`, `dialog`, `a`, `input`) o sus atributos ARIA equivalentes (`aria-expanded`, `aria-selected`, `aria-hidden`). Prohibidos contenedores estáticos (`<div>`, `<span>`) actuando como botones con solo eventos de clic.
- [ ] **4.1.3 Mensajes de estado (WCAG 2.1 - Nivel AA):** Las notificaciones de alerta, confirmaciones o cambios dinámicos sin desplazamiento de foco se transmiten a tecnologías de asistencia mediante regiones en vivo estables (`role="status"`, `role="alert"`, o `aria-live="polite"`).

---

### F. Entregables y Auditoría Final de Cierre

- [ ] **Auditoría de contraste automatizada (Playwright / axe-core):** Análisis sobre página completamente renderizada con etiquetas `wcag2a`, `wcag2aa`, `wcag21a` y `wcag21aa`, arrojando **0 violaciones**.
- [ ] **Puntaje Lighthouse:** Calificación de **100 en Accessibility** en modo desktop y móvil.
- [ ] **Prueba de teclado completa:** Verificación manual de navegación con `Tab` / `Shift+Tab` a través de todas las pantallas, formularios y modales sin bloqueos.
- [ ] **Prueba con lector de pantalla:** Recorrido funcional validado con un lector de pantalla real (NVDA, JAWS o VoiceOver).
- [ ] **Declaración de accesibilidad:** Publicación de la página accesible con estado de conformidad, mecanismos de contacto (PQR) y canales de reporte de barreras (obligatorio según marco MinTIC).