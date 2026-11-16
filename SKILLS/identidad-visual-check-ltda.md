# Guía de Identidad Visual — Check Ltda. (CDA Check Motos)

> **Propósito del documento:** Referencia de diseño y desarrollo web basada en el análisis de la presencia digital y física de **Check Ltda.** (Centro de Diagnóstico Automotor especializado en motocicletas, Barrancabermeja, Santander).

---

## 1. Información Institucional

* **Razón Social:** Check Ltda.
* **Nombre Comercial:** CDA Check Motos
* **NIT:** 900.225.272-8
* **Ubicación:** Carrera 4 # 51 - 11, Sector Comercial, Barrancabermeja, Santander, Colombia
* **Acreditación:** ONAC — Norma NTC-ISO-IEC 17020:2012 (Código: `10-OIN-055`)
* **Personalidad de Marca:** Confiable, técnica, directa, accesible y enfocada en seguridad vial.

---

## 2. Arquitectura y Concepto Visual

1. **Emblema Digital (Redes Sociales):** Logotipo circular con estilo ilustrativo tradicional (motociclista con casco rojo sobre fondo natural), rodeado por un anillo amarillo con tipografía curva en alto contraste (`C.D.A. CHECK MOTOS`).
2. **Señalética Física (Fachada):** Enfoque corporativo sobrio y limpio sobre fondo blanco puro, priorizando la legibilidad a distancia con rotulación roja de trazo grueso.
3. **Adaptación Web Recomendada:** Mantener la limpieza visual de la fachada (fondos claros y estructurados) utilizando la paleta primaria vibrante para jerarquizar llamados a la acción (CTA), alertas e indicadores de estado técnico.

---

## 3. Paleta de Colores Corporativos

Los valores **HEX** y **RGB** están optimizados para pantallas y accesibilidad web (contraste WCAG), mientras que los valores **CMYK** sirven como referencia para papelería o material impreso.

| Rol en UI / Marca | Nombre | Muestra | Código HEX | Código RGB | Código CMYK | Uso recomendado en Web |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| **Primario** | Rojo Automotriz | 🟥 | `#D32F2F` | `rgb(211, 47, 47)` | `C:10 M:92 Y:88 K:2` | Botones principales (CTA), encabezados destacados, acentos de marca. |
| **Secundario** | Azul Técnico | 🟦 | `#1565C0` | `rgb(21, 101, 192)` | `C:91 M:62 Y:0 K:0` | Enlaces, iconos informativos, badges de acreditación ONAC, navegación. |
| **Acento** | Amarillo Vial | 🟨 | `#FBC02D` | `rgb(251, 192, 45)` | `C:2 M:24 Y:92 K:0` | Etiquetas de aviso, resaltados de promociones, bordes de énfasis. |
| **Fondo Base** | Blanco Puro | ⬜ | `#FFFFFF` | `rgb(255, 255, 255)` | `C:0 M:0 Y:0 K:0` | Fondo principal de páginas, tarjetas y contenedores limpio-técnicos. |
| **Fondo Alterno** | Gris Claro Neutro | ◽ | `#F4F6F8` | `rgb(244, 246, 248)` | `C:4 M:2 Y:2 K:0` | Secciones alternas, tablas de precios, bloques de requisitos. |
| **Texto Principal** | Gris Asfalto Oscuro | ⬛ | `#1E293B` | `rgb(30, 41, 59)` | `C:82 M:68 Y:48 K:46` | Párrafos, títulos principales, textos de alta legibilidad. |
| **Texto Secundario** | Gris Acero | ◾ | `#64748B` | `rgb(100, 116, 139)` | `C:63 M:48 Y:34 K:12` | Subtítulos, pies de foto, metadatos y descripciones de soporte. |

### Variables CSS listas para copiar (`variables.css`)

```css
:root {
  /* Colores de Marca */
  --brand-red: #D32F2F;
  --brand-red-hover: #B71C1C;
  --brand-blue: #1565C0;
  --brand-blue-hover: #0D47A1;
  --brand-yellow: #FBC02D;

  /* Neutros y Superficies */
  --bg-primary: #FFFFFF;
  --bg-secondary: #F4F6F8;
  --border-light: #E2E8F0;

  /* Tipografía */
  --text-primary: #1E293B;
  --text-secondary: #64748B;
  --text-on-dark: #FFFFFF;
}
```

---

## 4. Sistema Tipográfico (Equivalentes Modernos para Web)

Dado que la empresa utiliza fuentes clásicas de alto impacto (`Arial Black` / `Impact`) en sus piezas físicas y logotipo, se proponen **equivalentes modernos de código abierto (Google Fonts)** que conservan la robustez del sector automotriz pero garantizan nitidez en pantallas y dispositivos móviles.

### Opción A: Enfoque Técnico y Moderno (Recomendada para Web)

* **Títulos y Encabezados (`H1` – `H3`):** **Montserrat** (Pesos: `700 Bold`, `800 ExtraBold`)
  * *Por qué funciona:* Geométrica, ancha y contundente. Replica la fuerza visual de las letras del logotipo circular con un acabado contemporáneo.
  * *Estilo sugerido:* Mayúsculas (`text-transform: uppercase`) con ligero espaciado (`letter-spacing: 0.03em`) para títulos principales.
* **Cuerpo de Texto e Interfaz (`Body`, `Buttons`, `Forms`):** **Inter** (Pesos: `400 Regular`, `500 Medium`, `600 SemiBold`)
  * *Por qué funciona:* Máxima legibilidad en pantallas pequeñas, ideal para formularios de agendamiento de citas, requisitos técnico-mecánicos y tarifas.

### Opción B: Enfoque Industrial y Condensado (Fiel a la Fachada)

* **Títulos de Impacto (`Hero Banners`):** **Oswald** o **Barlow Condensed** (Pesos: `600 SemiBold`, `700 Bold`)
  * *Por qué funciona:* Mantiene la estética condensada y vertical de la rotulación exterior de la sede física, ahorrando espacio horizontal en encabezados grandes.
* **Cuerpo de Texto:** **Roboto** o **Plus Jakarta Sans** (Pesos: `400 Regular`, `500 Medium`)

### Escala Tipográfica Sugerida (Web Responsive)

| Elemento | Fuente | Peso | Tamaño Desktop | Tamaño Mobile | Interlineado |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **H1 (Hero)** | Montserrat | 800 (ExtraBold) | `2.75rem` (44px) | `2rem` (32px) | `1.15` |
| **H2 (Sección)** | Montserrat | 700 (Bold) | `2rem` (32px) | `1.625rem` (26px) | `1.2` |
| **H3 (Tarjeta)** | Montserrat | 700 (Bold) | `1.25rem` (20px) | `1.125rem` (18px) | `1.3` |
| **Cuerpo (Body)** | Inter | 400 (Regular) | `1rem` (16px) | `1rem` (16px) | `1.6` |
| **Botones (CTA)** | Inter | 600 (SemiBold) | `0.9375rem` (15px) | `0.9375rem` (15px) | `1.0` |

---

## 5. Lineamientos Rápidos de Aplicación Web

* **Contraste de Botones:** Usar el **Rojo Automotriz (`#D32F2F`)** con texto blanco (`#FFFFFF`) para la acción principal (ej. *"Agendar Revisión"*). Reservar el **Amarillo Vial (`#FBC02D`)** exclusivamente con texto oscuro (`#1E293B`) para garantizar contraste legible.
* **Confianza Normativa:** Destacar el sello de acreditación **ONAC (`10-OIN-055`)** utilizando el **Azul Técnico (`#1565C0`)** en el encabezado o pie de página para transmitir respaldo legal y técnico.
* **Iconografía:** Utilizar iconos de trazo limpio y grosor medio (`2px`, estilo *Lucide Icons* o *Heroicons*) relacionados con motocicletas, herramientas de diagnóstico, certificados y calendarios.
