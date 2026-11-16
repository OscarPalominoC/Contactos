# Adaptación de Prácticas Django / Jinja / HTMX a React + TypeScript

> **Documento de análisis, equivalencias arquitectónicas y guía de implementación.**  
> Basado en la inspección de patrones y convenciones documentadas en `d:\projects\Forms\Dev Django Jinja` (arquitectura SOPROTECO TH / Jinja2 / HTMX / Clean Architecture) y su transposición práctica al frontend SPA moderno (React 18 + TypeScript + Vite + Tailwind CSS) de **DevForms**.

---

## 1. Diagnóstico General: ¿Se pueden adaptar las prácticas?

**Sí, absolutamente.**  
Aunque el motor de renderizado Jinja2 y HTMX operan bajo un paradigma de **Server-Driven UI** (el servidor devuelve fragmentos HTML procesados) y React opera como una **Single Page Application (SPA)** reactiva en el navegador basada en un árbol virtual de componentes, **los principios de diseño subyacentes son 100% transferibles y altamente beneficiosos**.

Las directrices encontradas en `Dev Django Jinja` destacan por:
1. **Separación estricta de responsabilidades** (lógica fuera de las vistas/plantillas, centralización de formatos y validaciones).
2. **Jerarquía y composición de interfaz** (herencia de 3 niveles, plantillas base, parciales `_partial` y componentes atómicos).
3. **Manejo defensivo de estados de carga e indicadores visuales** (`hx-indicator`, deshabilitación de botones para evitar dobles envíos).
4. **Resiliencia en formularios y validaciones** (errores a nivel de campo vs. errores globales, validación de esquemas antes de enviar).
5. **Normalización y formato uniforme de datos** (`formatos/`: cédula, moneda, teléfono E.164, nombres en mayúsculas).
6. **Manejo explícito de estados vacíos** (`{% empty %}` -> `EmptyState`).
7. **Seguridad y auditoría** (trazabilidad de `request_id`, control estricto de roles y visibilidad condicional).

A continuación se detalla la matriz de correspondencia y los patrones recomendados para el ecosistema React de DevForms.

---

## 2. Matriz de Equivalencias Conceptuales

| Concepto en Django / Jinja / HTMX | Equivalente Directo en React + TypeScript | Propósito y Buenas Prácticas |
| :--- | :--- | :--- |
| **Herencia de Plantillas (3 niveles)**<br>`base.html` -> `section.html` -> `page.html` | **Layouts Anidados con React Router (`<Outlet />`)**<br>`RootLayout` -> `DashboardLayout` -> `ViewPage` | Mantiene el esqueleto HTML, barras de navegación y pie de página compartidos sin re-renderizar todo el árbol. |
| **Bloques de Plantilla**<br>`{% block content %}`, `{% block title %}` | **Children Props & Portals / Document Title Hooks**<br>`props.children`, `useDocumentTitle()`, React Portal | Inyección de contenido dinámico en ranuras específicas del contenedor padre. |
| **Componentes con inclusión aislada**<br>`{% include "comp/_button.html" with ... only %}` | **Componentes Funcionales Fuertemente Tipados**<br>`<Button variant="primary" text="..." />` | Props aisladas con interfaces TypeScript (`interface ButtonProps`), evitando herencia accidental de contexto. |
| **Parciales dinámicos**<br>`_list.html`, `_card.html` (prefijo `_`) | **Subcomponentes Atómicos / Memoizados**<br>`QuestionCard.tsx`, `ResponseListItem.tsx` | Fragmentos modulares enfocados en una sola responsabilidad visual. |
| **Custom Filters de Jinja**<br>`{{ user.nombre \| formato_nombre }}`<br>`{{ valor \| moneda_cop }}` | **Módulo de Utilidades Puras de Formato**<br>`src/utils/formatters.ts`<br>`formatCurrency(valor)`, `formatCedula(cc)` | Funciones puras e inmutables que formatean valores para la vista sin alterar el valor crudo subyacente. |
| **HTMX `hx-indicator`**<br>Spinner visual durante peticiones | **Estados de Carga Reactivos**<br>`isLoading`, `isPending` (TanStack Query / Axios) + Skeleton Loaders | Los usuarios nunca deben dudar de si una acción está en progreso. |
| **HTMX `hx-disabled-elt="this"`**<br>Bloqueo de botón mientras envía | **`disabled={isSubmitting}` en Botones de Envío** | Previene doble clic, duplicidad de envíos y desincronizaciones de red. |
| **HTMX Eventos `HX-Trigger`**<br>Disparar eventos personalizados tras respuesta | **Invalidación de Caché en TanStack Query / Zustand**<br>`queryClient.invalidateQueries(['responses'])` | Actualiza partes no adyacentes de la interfaz cuando un recurso cambia. |
| **Cláusula `{% empty %}` en bucles** | **Renderizado Condicional de `EmptyState`**<br>`items.length === 0 ? <EmptyState /> : items.map(...)` | Manejo explícito y amigable de listas vacías o sin resultados de búsqueda. |
| **Validaciones `clean_<field>` y `clean()`** | **Validación de Esquemas con Zod o validadores dedicados** | Validar a nivel de campo (formato) y cross-field (coherencia entre múltiples campos) antes del submit. |
| **Módulo Central de Formatos (`formatos/`)** | **`src/formatters/` o `src/utils/formats.ts`** | Centralización de formatos para Bogotá/Colombia: Cédula `1.018.459.201`, Teléfono `+57 ...`, Fecha `dd/mm/aaaa`. |

---

## 3. Guía Práctica de Implementación de Patrones Jinja en React

### 3.1 Estructura y Composición de Vistas (Herencia de 3 Niveles)

En Jinja se utiliza:
```html
{# base.html #}
<!DOCTYPE html>
<html>
  <body>
    {% include "partials/_navbar.html" %}
    <main>{% block content %}{% endblock %}</main>
  </body>
</html>

{# section.html #}
{% extends "base.html" %}
{% block content %}
  <aside>Menú de Sección</aside>
  <div>{% block section_content %}{% endblock %}</div>
{% endblock %}
```

#### En React (con React Router v6):
```tsx
// 1. Root Layout (base.html)
export const AppLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-neutral-50 flex flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6">
          <Outlet /> {/* Equivale a {% block content %} */}
        </main>
      </div>
    </div>
  );
};

// 2. Section Layout (section.html)
export const FormDashboardLayout: React.FC = () => {
  return (
    <div className="space-y-6">
      <DashboardHeaderTabs />
      <div className="bg-white p-6 rounded-lg shadow-sm">
        <Outlet /> {/* Equivale a {% block section_content %} */}
      </div>
    </div>
  );
};
```

---

### 3.2 Patrón de Filtros Jinja -> Módulo de Formateadores Puros (`src/utils/formatters.ts`)

La documentación de SOPROTECO estipula reglas de formato estrictas para Colombia:
- **Cédula**: Guardada en dígitos, mostrada con puntos (`1.018.459.201`).
- **Nombres**: MAYÚSCULAS limpias sin espacios dobles.
- **Teléfono**: E.164 (`+57 300 123 4567`).
- **Moneda**: `numeric` guardado, mostrado como `$1.423.500`.
- **Fechas**: Guardadas en UTC/ISO, mostradas en `dd/mm/aaaa`.

#### Implementación recomendada en React:
```typescript
// src/utils/formatters.ts

/** Formatea número de documento con separación de miles */
export function formatCedula(value: string | number): string {
  const digits = String(value).replace(/\D/g, '');
  if (!digits) return '';
  return new Intl.NumberFormat('es-CO').format(Number(digits));
}

/** Formatea moneda colombiana */
export function formatCOP(amount: number): string {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(amount);
}

/** Limpia y convierte nombres a MAYÚSCULAS preservando tildes */
export function formatNombre(name: string): string {
  return (name || '').trim().replace(/\s+/g, ' ').toUpperCase();
}

/** Formatea fecha ISO a formato local colombiano dd/mm/aaaa */
export function formatDateCO(isoDate: string | Date): string {
  if (!isoDate) return '-';
  const d = new Date(isoDate);
  return d.toLocaleDateString('es-CO', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}
```

*Uso en componentes React:*
```tsx
<span>{formatCedula(candidato.cedula)}</span>
<span>{formatCOP(postulacion.aspiracion_salarial)}</span>
```

---

### 3.3 Patrón `hx-indicator` & `hx-disabled-elt` -> Botones Defensivos y Feedback Visual

En HTMX es una regla crítica de SOPROTECO: *"Users should never wonder if their action worked. Disable submit buttons during requests."*

#### En React:
```tsx
// src/components/ui/SubmitButton.tsx
import React from 'react';
import { Loader2 } from 'lucide-react';

interface SubmitButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading?: boolean;
  loadingText?: string;
  children: React.ReactNode;
}

export const SubmitButton: React.FC<SubmitButtonProps> = ({
  isLoading = false,
  loadingText = 'Guardando...',
  disabled,
  children,
  className = '',
  ...props
}) => {
  return (
    <button
      type="submit"
      disabled={isLoading || disabled}
      className={`inline-flex items-center justify-center px-4 py-2 font-medium rounded-lg transition-colors 
        ${isLoading ? 'opacity-70 cursor-not-allowed bg-red-400' : 'bg-red-700 hover:bg-red-800 text-white'} 
        ${className}`}
      {...props}
    >
      {isLoading ? (
        <>
          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          <span>{loadingText}</span>
        </>
      ) : (
        children
      )}
    </button>
  );
};
```

---

### 3.4 Patrón `{% empty %}` -> Componente Estándar `EmptyState`

En Jinja:
```html
{% for item in items %}
  {% include "components/_item.html" %}
{% empty %}
  <p>No se encontraron registros coincidentes.</p>
{% endfor %}
```

#### En React:
```tsx
// src/components/ui/EmptyState.tsx
interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ title, description, icon, action }) => (
  <div className="flex flex-col items-center justify-center py-12 px-4 text-center border-2 border-dashed border-neutral-200 rounded-xl">
    {icon && <div className="text-neutral-400 mb-3">{icon}</div>}
    <h3 className="text-sm font-semibold text-neutral-800">{title}</h3>
    {description && <p className="text-xs text-neutral-500 mt-1 max-w-sm">{description}</p>}
    {action && <div className="mt-4">{action}</div>}
  </div>
);
```

*Uso en listas:*
```tsx
{responses.length === 0 ? (
  <EmptyState
    title="No hay respuestas registradas"
    description="Cuando los usuarios completen este formulario aparecerán aquí."
    icon={<FileQuestion className="w-8 h-8" />}
  />
) : (
  responses.map((resp) => <ResponseCard key={resp.id} response={resp} />)
)}
```

---

### 3.5 Patrón de Validación de Formularios (Equivalente a `ModelForm.clean()`)

En Django/Jinja, las validaciones de campo se separan de las validaciones cruzadas. En React, la forma más limpia y robusta de adoptar este patrón es separar la validación en dos capas:
1. **Validación Inmediata de Campo** (mientras el usuario escribe o hace `onBlur`).
2. **Validación Completa de Formulario** (antes del envío).

```typescript
// Ejemplo de validador desacoplado (estilo Django clean())
export interface FormErrors {
  [fieldName: string]: string | undefined;
  _nonFieldErrors?: string;
}

export function validateVacunacionForm(data: FormSubmissionData): FormErrors {
  const errors: FormErrors = {};

  // 1. Validaciones por campo (clean_<field>)
  if (!data.nombres || data.nombres.trim().length < 3) {
    errors.nombres = 'Debe ingresar nombres completos válidos.';
  }

  if (!data.cedula || !/^\d{6,12}$/.test(data.cedula.replace(/\D/g, ''))) {
    errors.cedula = 'La cédula debe contener entre 6 y 12 dígitos.';
  }

  // 2. Validación cruzada (clean() / cross-field)
  if (data.recibio_vacunas && (!data.vacunas || data.vacunas.length === 0)) {
    errors._nonFieldErrors = 'Indicó que recibió vacunas pero no seleccionó ningún biológico.';
  }

  return errors;
}
```

---

### 3.6 Patrón `HX-Trigger` -> Sincronización Global sin Acoplamiento

En HTMX, una vista de Django devuelve la cabecera `HX-Trigger: itemCreated`, lo cual hace que otros componentes de la página se enteren y se refresquen.

En React, adaptamos este patrón usando **Custom Events del navegador** o **invalidación reactiva en Zustand / TanStack Query**:

```typescript
// Disparador (emisor equivalente a HX-Trigger)
export function dispatchGlobalEvent(eventName: string, detail?: any) {
  window.dispatchEvent(new CustomEvent(eventName, { detail }));
}

// Hook receptor (equivalente a hx-trigger="itemCreated from:body")
export function useGlobalEventListener(eventName: string, callback: (detail: any) => void) {
  useEffect(() => {
    const handler = (e: Event) => callback((e as CustomEvent).detail);
    window.addEventListener(eventName, handler);
    return () => window.removeEventListener(eventName, handler);
  }, [eventName, callback]);
}
```

---

## 4. Resumen de Reglas de Oro Adaptadas para el Frontend

1. **Sin lógica de negocio pesada en los componentes JSX**: Mantener el JSX declarativo; cálculos y filtros deben vivir en `utils/` o hooks personalizados (similar a mantener la lógica fuera de las plantillas Jinja).
2. **Componentes pequeños con prefijo o sufijo claro**: Nombres atómicos y reutilizables (`QuestionCard`, `SettingsDrawer`).
3. **Todo botón de acción asíncrona debe mostrar spinner y deshabilitarse** (`isLoading` + `disabled`).
4. **Validación previa y manejo explícito de errores de servidor**: Nunca silenciar errores en el `catch` de las llamadas a la API; mapear los errores a los campos correspondientes.
5. **Formatos colombianos unificados**: Usar siempre las funciones centralizadas de `src/utils/formatters.ts` para cédulas, monedas, teléfonos y fechas.
6. **Manejo defensivo de listas**: Todas las tablas y listas deben contar con su estado vacío (`EmptyState`).

