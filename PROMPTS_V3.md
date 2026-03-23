# 🎨 NYXAR — PROMPTS_V3.md
## Sistema de Diseño Frontend Completo

> **Dirección de diseño:** "Operational Intelligence Interface"
> No es una herramienta de hacking. No es un dashboard corporativo.
> Es la interfaz que usaría un analista de élite en 2030.
> Densa en información, silenciosa en estética. Cada elemento justifica su existencia.
>
> **Referencia mental:** Palantir Gotham × Linear.app × Stripe Radar
> **Lo que NO es:** Matrix green-on-black / Bootstrap blue / Sci-fi HUD con círculos girando

---

## 📋 Índice de Prompts V3

| # | Componente | Descripción |
|---|-----------|-------------|
| F01 | Design Tokens | Variables CSS — la fuente de verdad visual |
| F02 | Tipografía | Sistema tipográfico de dos fuentes con jerarquía estricta |
| F03 | Sistema de Color | Paleta semántica y estados de datos |
| F04 | Animaciones | Sistema de motion — propósito sobre espectáculo |
| F05 | Layout Shell | Estructura principal: nav + main + panels |
| F06 | Navigation | Sidebar de navegación con indicadores de estado |
| F07 | Componentes Atómicos | Los bloques de construcción reutilizables |
| F08 | Componentes de Datos | Cards, tablas y listas de eventos |
| F09 | Visualizaciones | Gráficos, sparklines, gauge de riesgo |
| F10 | NetworkMap View | El grafo de red — la vista más técnica |
| F11 | Timeline View | El feed de eventos en tiempo real |
| F12 | Identities View | El panel de comportamiento humano |
| F13 | CEO View | La traducción ejecutiva |
| F14 | Hunting View | La interfaz de investigación |
| F15 | System Health View | Observabilidad del sistema |
| F16 | Response Proposals View | Aprobación de acciones |
| F17 | Estados Vacíos y Carga | Empty states, skeletons, errores |
| F18 | Performance y Accesibilidad | Las restricciones no negociables |

---

## ⚙️ CONTEXTO DE DISEÑO
> Pegar antes de cualquier prompt F** en Cursor.

```
Estás diseñando NYXAR — un sistema de inteligencia de ciberseguridad.

DIRECCIÓN ESTÉTICA: "Operational Intelligence Interface"
Referencia: Palantir Gotham × Linear.app × Stripe Radar.
NO es: Matrix/hacker verde, Bootstrap azul, HUDs con animaciones decorativas.

PRINCIPIO RECTOR:
Cada elemento visual debe ganar su lugar siendo funcional.
Si algo no comunica información o guía la atención, no existe.
El "lujo" de esta interfaz es la precisión y la densidad controlada.

PERSONALIDAD DE LA INTERFAZ:
- Seria pero no fría
- Densa pero no caótica
- Técnica pero no hermética
- Rápida pero no agresiva

STACK:
- React 18 + Vite
- CSS Modules o CSS-in-JS (styled-components)
- Framer Motion para animaciones
- Recharts para gráficos
- D3.js para el grafo de red (NetworkMap)
- Socket.io-client para tiempo real

RESTRICCIONES ABSOLUTAS:
1. Sin efectos que consuman CPU sin aportar información (no particle systems,
   no matrix rain, no scanning lines, no pulsing circles sin significado)
2. Sin animaciones de más de 400ms (excepción: transiciones de ruta)
3. Sin gradientes de más de 2 colores en elementos funcionales
4. Sin sombras decorativas — solo sombras funcionales (elevación)
5. Sin fuentes genéricas (no Inter, no Roboto, no Arial)
6. Cada color debe tener un significado semántico
```

---

## F01 — Design Tokens

### PROMPT F01 — Design System Foundation
**Rol:** Design System Engineer  
**Entregable:** `dashboard/src/styles/tokens.css` — la fuente de verdad de todo el sistema visual

```
Sos un Design System Engineer especializado en sistemas de diseño
para interfaces de datos de alta densidad.

Tu tarea es crear el archivo de design tokens de NYXAR.
Este archivo es la ÚNICA fuente de verdad visual. Nada en la UI
puede tener un color, tamaño o espaciado que no venga de acá.

ARCHIVO: dashboard/src/styles/tokens.css

/* ═══════════════════════════════════════════════════════════
   NYXAR — DESIGN TOKENS
   Operational Intelligence Interface
   ═══════════════════════════════════════════════════════════ */

:root {

  /* ─── ESPACIOS (sistema 4pt) ──────────────────────────── */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  /* ─── COLORES BASE (no usar directamente en componentes) ─ */
  --base-void: #080B0F;          /* el vacío — fondo más profundo */
  --base-deep: #0C1018;          /* fondo principal de la app */
  --base-surface: #111620;       /* cards y paneles */
  --base-raised: #161D2E;        /* elementos elevados sobre surface */
  --base-overlay: #1C2438;       /* tooltips, dropdowns, modales */
  --base-border: #1F2B40;        /* bordes sutiles */
  --base-border-strong: #2A3A55; /* bordes de énfasis */
  --base-muted: #3D4F6A;         /* texto deshabilitado, placeholders */
  --base-subtle: #6B7FA0;        /* texto secundario */
  --base-soft: #A8B8D0;          /* texto terciario */
  --base-text: #D8E4F0;          /* texto principal */
  --base-bright: #EDF3FA;        /* texto de énfasis */

  /* ─── ACENTO PRIMARIO: Cyan operacional ─────────────────
     No es el cyan neón de películas de hacking.
     Es el cyan de monitores de control de misión.
     Frío, preciso, confiable.                              */
  --cyan-dim: #0A2535;           /* background de badges cyan */
  --cyan-muted: #0D3347;         /* hover states suaves */
  --cyan-border: #1A5E7A;        /* bordes de elementos cyan */
  --cyan-soft: #2B8FAD;          /* cyan desaturado para texto */
  --cyan-base: #38B2CC;          /* cyan principal — uso moderado */
  --cyan-bright: #4FC3D9;        /* cyan de énfasis */
  --cyan-glow: #67D4E8;          /* cyan para elementos activos */

  /* ─── ESTADOS SEMÁNTICOS ─────────────────────────────── */
  /* Crítico: no el rojo de error genérico.
     El rojo de "esto requiere atención ahora." */
  --critical-bg: #1A0A0E;
  --critical-border: #5C1A24;
  --critical-muted: #8B3040;
  --critical-base: #C23B52;
  --critical-bright: #E8455F;

  /* Alto: naranja de advertencia industrial */
  --high-bg: #160E05;
  --high-border: #4A2C0A;
  --high-muted: #7A4A14;
  --high-base: #B8692A;
  --high-bright: #D97F3A;

  /* Medio: amarillo-ámbar (no amarillo chillón) */
  --medium-bg: #141006;
  --medium-border: #3D2E08;
  --medium-muted: #6B4E10;
  --medium-base: #A07020;
  --medium-bright: #C08A28;

  /* Limpio: verde de "sistema operando nominalmente" */
  --clean-bg: #080E0A;
  --clean-border: #0F3018;
  --clean-muted: #1A5428;
  --clean-base: #2A8040;
  --clean-bright: #38A050;

  /* Info: azul frío para datos neutrales */
  --info-bg: #080E1A;
  --info-border: #0F2040;
  --info-muted: #1A3A6A;
  --info-base: #2A5C9E;
  --info-bright: #3872B8;

  /* ─── RISK SCORE GRADIENT ────────────────────────────────
     Para el risk score (0-100) usar interpolación entre estos puntos.
     No usar colores planos — el gradiente comunica urgencia graduada. */
  --risk-0: #2A8040;    /* 0 */
  --risk-25: #A07020;   /* 25 */
  --risk-50: #B8692A;   /* 50 */
  --risk-75: #C23B52;   /* 75 */
  --risk-100: #E8455F;  /* 100 */

  /* ─── TIPOGRAFÍA ─────────────────────────────────────── */
  --font-ui: 'Geist', 'IBM Plex Sans', system-ui, sans-serif;
  --font-data: 'Geist Mono', 'IBM Plex Mono', 'Fira Code', monospace;

  --text-xs: 11px;       /* labels, badges, metadata */
  --text-sm: 13px;       /* texto secundario */
  --text-base: 14px;     /* texto de interfaz principal */
  --text-md: 15px;       /* texto de contenido */
  --text-lg: 18px;       /* títulos de sección */
  --text-xl: 22px;       /* títulos de vista */
  --text-2xl: 28px;      /* hero numbers */
  --text-3xl: 36px;      /* métricas grandes */

  --weight-normal: 400;
  --weight-medium: 500;
  --weight-semibold: 600;
  --weight-bold: 700;

  --leading-tight: 1.2;
  --leading-snug: 1.4;
  --leading-normal: 1.6;

  --tracking-tight: -0.02em;
  --tracking-normal: 0em;
  --tracking-wide: 0.04em;
  --tracking-wider: 0.08em;    /* para labels en mayúsculas */

  /* ─── BORDES Y RADIOS ────────────────────────────────── */
  --radius-sm: 3px;      /* badges, chips pequeños */
  --radius-md: 6px;      /* cards, inputs */
  --radius-lg: 10px;     /* paneles principales */
  --radius-full: 9999px; /* pills */

  --border-width: 1px;
  --border-width-strong: 1.5px;

  /* ─── ELEVACIÓN (sombras) ────────────────────────────── 
     Las sombras comunican elevación — no son decorativas.
     Usar azul oscuro, no negro puro (más natural en dark themes). */
  --shadow-sm: 0 1px 3px rgba(4, 8, 16, 0.4);
  --shadow-md: 0 4px 12px rgba(4, 8, 16, 0.5), 0 1px 3px rgba(4, 8, 16, 0.3);
  --shadow-lg: 0 8px 24px rgba(4, 8, 16, 0.6), 0 2px 8px rgba(4, 8, 16, 0.4);
  --shadow-cyan: 0 0 0 1px var(--cyan-border), 0 4px 16px rgba(56, 178, 204, 0.08);
  --shadow-critical: 0 0 0 1px var(--critical-border), 0 4px 16px rgba(194, 59, 82, 0.1);

  /* ─── TRANSICIONES ──────────────────────────────────── */
  --duration-instant: 80ms;
  --duration-fast: 150ms;
  --duration-normal: 250ms;
  --duration-slow: 350ms;

  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);

  /* ─── LAYOUT ─────────────────────────────────────────── */
  --nav-width: 220px;
  --nav-width-collapsed: 56px;
  --panel-width: 360px;
  --header-height: 48px;
  --status-bar-height: 28px;

  /* ─── Z-INDEX ─────────────────────────────────────────── */
  --z-base: 0;
  --z-raised: 10;
  --z-dropdown: 100;
  --z-sticky: 200;
  --z-overlay: 300;
  --z-modal: 400;
  --z-toast: 500;
}

/* ─── SCROLLBAR PERSONALIZADA ────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--base-border-strong);
  border-radius: var(--radius-full);
}
::-webkit-scrollbar-thumb:hover { background: var(--base-muted); }

/* ─── SELECCIÓN DE TEXTO ─────────────────────────────────── */
::selection {
  background: var(--cyan-dim);
  color: var(--cyan-glow);
}

/* ─── FOCUS RING ──────────────────────────────────────────── */
:focus-visible {
  outline: 1.5px solid var(--cyan-base);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

REGLAS:
- Ningún componente puede hardcodear un color hex. Solo variables de tokens.
- Los tokens de estado (--critical-*, --clean-*, etc.) se usan con SIGNIFICADO
  semántico estricto. No usar --critical-base para un botón rojo decorativo.
- El token --base-void es para el fondo del documento, nunca para un elemento.

NO HAGAS:
- No agregues tokens que no tienen un uso concreto en la interfaz.
- No uses shadow con color negro puro (#000000). Solo rgba con azul profundo.
- No pongas gradientes en los tokens. Los gradientes son responsabilidad del componente.
```

---

## F02 — Tipografía

### PROMPT F02 — Typography System
**Rol:** Typography Designer  
**Entregable:** `dashboard/src/styles/typography.css` + guía de uso

```
Sos un Typography Designer especializado en interfaces de datos técnicos.

DECISIÓN DE FUENTES:

Primaria UI: Geist (de Vercel — libre, moderna, extremadamente legible en pantalla)
Fallback: IBM Plex Sans (mismo carácter técnico pero más establecida)

Por qué Geist: Fue diseñada específicamente para interfaces de código y datos.
Tiene una geometría ligeramente cuadrada que la hace diferente a Inter
(demasiado neutral) y Space Grotesk (sobreusada). Los números son
proporcionalmente perfectos para tabular datos.

Secundaria DATA: Geist Mono
Para IPs, dominios, hashes, timestamps, código.
La monospace de Geist mantiene la coherencia visual con la UI.
Fallback: IBM Plex Mono.

ARCHIVO: dashboard/src/styles/typography.css

/* Cargar desde Google Fonts o CDN */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

/* Intentar Geist si está disponible localmente */
@font-face {
  font-family: 'Geist';
  src: local('Geist');
  /* Si Geist no está disponible, IBM Plex Sans como fallback automático */
}

CLASES TIPOGRÁFICAS A DEFINIR:

/* Labels — pequeñas etiquetas en mayúsculas */
.label {
  font-family: var(--font-ui);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  letter-spacing: var(--tracking-wider);
  text-transform: uppercase;
  color: var(--base-subtle);
  /* USO: títulos de columnas, categorías, badges de estado */
}

/* Body UI — texto de interfaz estándar */
.body-ui {
  font-family: var(--font-ui);
  font-size: var(--text-base);
  font-weight: var(--weight-normal);
  line-height: var(--leading-normal);
  color: var(--base-text);
}

/* Body UI Secondary */
.body-secondary {
  font-family: var(--font-ui);
  font-size: var(--text-sm);
  font-weight: var(--weight-normal);
  line-height: var(--leading-snug);
  color: var(--base-subtle);
}

/* Data Text — para valores técnicos: IPs, dominios, hashes */
.data-text {
  font-family: var(--font-data);
  font-size: var(--text-sm);
  font-weight: var(--weight-normal);
  letter-spacing: 0.01em;
  color: var(--base-soft);
  /* Los datos técnicos son SIEMPRE monospace */
}

/* Data Value — números grandes, métricas hero */
.data-value {
  font-family: var(--font-data);
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-tight);
  font-variant-numeric: tabular-nums;
  /* Los números de métricas siempre tabular para que no "salten" */
}

/* Section Title */
.section-title {
  font-family: var(--font-ui);
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  letter-spacing: var(--tracking-tight);
  color: var(--base-bright);
}

/* View Title */
.view-title {
  font-family: var(--font-ui);
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
  letter-spacing: -0.03em;
  color: var(--base-bright);
}

REGLA TIPOGRÁFICA FUNDAMENTAL:
Todo texto técnico (IPs, dominios, hashes, timestamps exactos, ports, 
nombres de archivos, valores de configuración) usa SIEMPRE --font-data.
Todo texto de UI (títulos, descripciones, labels) usa SIEMPRE --font-ui.
Esta distinción es funcional, no solo estética: el usuario sabe
inmediatamente qué tipo de información está mirando.

NÚMEROS EN MÉTRICAS:
Usar font-variant-numeric: tabular-nums en TODOS los números que cambian
en tiempo real. Esto evita que el layout salte cuando un "1" reemplaza
a un "100" (los números ocupan el mismo ancho).

JERARQUÍA DE GRISES:
- --base-bright: títulos, valores importantes, elementos activos
- --base-text: texto de interfaz estándar
- --base-soft: texto terciario, descripciones
- --base-subtle: labels, texto secundario
- --base-muted: placeholders, texto deshabilitado
NUNCA usar blanco puro (#fff) directamente en texto.

NO HAGAS:
- No uses italic para énfasis en datos técnicos. El énfasis en datos
  es bold + color, nunca italic (dificulta la lectura de código).
- No mezcles fuentes en la misma línea de texto.
  Un token puede ser --font-data dentro de una oración en --font-ui,
  pero visualmente son segmentos claramente diferenciados.
- No hagas que los títulos de vista sean más grandes de 22px.
  El "peso" de un título viene de su contraste y posición, no su tamaño.
```

---

## F03 — Sistema de Color

### PROMPT F03 — Color Semantics
**Rol:** Color Systems Designer  
**Entregable:** `dashboard/src/styles/colors.js` — helper de color semántico

```
Sos un Color Systems Designer especializado en interfaces de datos
donde el color comunica estado crítico de forma precisa.

FILOSOFÍA DE COLOR EN NYXAR:
El color es información, no decoración.
Cuando algo es rojo, significa "crítico". Siempre.
Si un elemento decorativo usa rojo, destruye esa semántica.

COLOR PRIMARIO: Cyan operacional (#38B2CC)
Por qué: Es el color del cyan de monitores de control de misión de la NASA.
No es el neón agresivo del diseño "hacker". Es preciso, técnico, confiable.
Se usa con moderación: bordes activos, indicadores, acciones primarias.
NO para fondos grandes.

FONDO PRINCIPAL: #0C1018 (azul-negro)
No negro puro. El negro puro es áspero y fatiga la vista en sesiones largas.
Este tono tiene un 8% de saturación azul que lo hace "espacial" sin ser obvio.

ARCHIVO: dashboard/src/utils/colors.js

```javascript
/**
 * Convierte un risk score (0-100) a un color hex interpolado.
 * Usa la escala semántica: verde → ámbar → naranja → rojo
 * 
 * @param {number} score - 0 a 100
 * @returns {{ color: string, bg: string, border: string, label: string }}
 */
export function scoreToColor(score) {
  if (score < 20) return {
    color: 'var(--clean-bright)',
    bg: 'var(--clean-bg)',
    border: 'var(--clean-border)',
    label: 'NOMINAL'
  }
  if (score < 40) return {
    color: 'var(--info-bright)',
    bg: 'var(--info-bg)',
    border: 'var(--info-border)',
    label: 'BAJO'
  }
  if (score < 60) return {
    color: 'var(--medium-bright)',
    bg: 'var(--medium-bg)',
    border: 'var(--medium-border)',
    label: 'MEDIO'
  }
  if (score < 80) return {
    color: 'var(--high-bright)',
    bg: 'var(--high-bg)',
    border: 'var(--high-border)',
    label: 'ALTO'
  }
  return {
    color: 'var(--critical-bright)',
    bg: 'var(--critical-bg)',
    border: 'var(--critical-border)',
    label: 'CRÍTICO'
  }
}

/**
 * Color semántico para fuentes de datos (source).
 * Cada fuente tiene un color consistente en toda la app.
 */
export const SOURCE_COLORS = {
  dns:      { color: 'var(--cyan-base)',     icon: '◈', label: 'DNS' },
  proxy:    { color: 'var(--info-bright)',   icon: '◎', label: 'PROXY' },
  firewall: { color: 'var(--high-bright)',   icon: '◉', label: 'FW' },
  wazuh:    { color: 'var(--medium-bright)', icon: '◆', label: 'WAZUH' },
  endpoint: { color: 'var(--base-soft)',     icon: '◇', label: 'HOST' },
  misp:     { color: 'var(--critical-bright)', icon: '⬡', label: 'MISP' },
}

/**
 * Color para áreas de la empresa.
 * Derivado del nombre del área para ser consistente y sin hardcodeo.
 * Usa colores del espectro azul-teal para no confundir con estados semánticos.
 */
export function areaToColor(area) {
  const AREA_PALETTE = [
    '#2B8FAD', '#3872B8', '#4A6FA5', '#5B6E99',
    '#3D7A8A', '#2E6B7A', '#4A7C8A', '#3A6B8A',
  ]
  let hash = 0
  for (let i = 0; i < area.length; i++) {
    hash = area.charCodeAt(i) + ((hash << 5) - hash)
  }
  return AREA_PALETTE[Math.abs(hash) % AREA_PALETTE.length]
}

/**
 * Opacidad semántica para estados de elementos.
 * No usar opacity arbitraria — solo estos valores.
 */
export const OPACITY = {
  disabled: 0.35,
  muted: 0.55,
  soft: 0.7,
  full: 1.0,
}
```

REGLAS DE USO DE COLOR:
- Cyan activo solo en: bordes de elementos seleccionados, indicadores live,
  botones de acción primaria, el indicador "conectado" del WebSocket.
  MÁXIMO 10% de la pantalla en cyan en cualquier momento.
- Crítico solo en: risk scores > 80, honeypot hits, alertas confirmadas.
  No en mensajes de error de formulario (eso es un problema de UX, no de seguridad).
- Verde solo en: risk score bajo, estado "limpio" en enrichment, sistema nominal.
  No en botones de "éxito" genéricos.

FONDO Y PROFUNDIDAD:
Los colores de fondo crean capas de profundidad:
--base-void (más profundo) → sidebar background
--base-deep → main content background
--base-surface → cards, panels
--base-raised → hover states, dropdowns
--base-overlay → modales, tooltips

NO HAGAS:
- No uses gradientes de cyan sobre fondos oscuros para "hacer bonito".
  Los gradientes son para el risk score gauge y nada más.
- No uses el mismo color para dos conceptos distintos.
  Si algo nuevo necesita color, amplía la paleta con un motivo semántico.
- No pongas texto blanco sobre fondos de color (ej: fondo cyan + texto blanco).
  El contraste mínimo es 4.5:1 (WCAG AA).
```

---

## F04 — Sistema de Animaciones

### PROMPT F04 — Motion System
**Rol:** Motion Designer  
**Entregable:** `dashboard/src/styles/motion.css` + `dashboard/src/hooks/useAnimation.js`

```
Sos un Motion Designer especializado en interfaces de datos en tiempo real
donde las animaciones comunican estado, no entretenimiento.

FILOSOFÍA DE MOTION EN NYXAR:
Las animaciones tienen UNA de estas funciones o no existen:
1. ORIENTAR: mostrar de dónde viene y a dónde va un elemento
2. JERARQUIZAR: confirmar que algo cambió y cuánto importa
3. RESPONDER: dar feedback instantáneo a la acción del usuario

Lo que NO hace una animación aquí:
- No "embellecer" un elemento estático
- No demostrar capacidad técnica del desarrollador
- No simular procesos que no están ocurriendo

ARCHIVO: dashboard/src/styles/motion.css

/* ─── ENTRADA DE ELEMENTOS ───────────────────────────────────
   fadeUp: elemento nuevo que aparece en un feed (evento, alerta)    */
@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* slideInRight: panel lateral que aparece (detalle de identidad, etc.) */
@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(16px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* ─── INDICADORES DE ESTADO ──────────────────────────────────
   
   livePulse: el punto que indica "conectado y recibiendo datos"
   ES DIFERENTE a un loading spinner — comunica presencia, no espera.
   Muy sutil: solo el anillo exterior pulsa, el punto interior es fijo. */
@keyframes livePulse {
  0%, 100% { 
    box-shadow: 0 0 0 0 rgba(56, 178, 204, 0.4);
  }
  50% { 
    box-shadow: 0 0 0 5px rgba(56, 178, 204, 0);
  }
}

/* criticalPulse: para honeypot hits y alertas críticas
   Más agresivo que livePulse — requiere atención AHORA */
@keyframes criticalPulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(232, 69, 95, 0.5);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(232, 69, 95, 0);
  }
}

/* ─── TRANSICIÓN DE DATOS ─────────────────────────────────────
   dataFlip: cuando un número cambia en tiempo real
   No es un fade — es un flip vertical sutil que comunica "nuevo dato"
   Duración: 150ms (imperceptible pero presente) */
@keyframes dataFlip {
  0% { transform: rotateX(-30deg); opacity: 0.3; }
  100% { transform: rotateX(0deg); opacity: 1; }
}

/* ─── LOADING ────────────────────────────────────────────────
   shimmer: skeleton loading state
   No es un spinner. Los skeletons comunican la FORMA del contenido
   que va a aparecer, preparando al usuario sin sorpresas de layout. */
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* ─── CLASES DE UTILIDAD ─────────────────────────────────────── */

.animate-fadeUp {
  animation: fadeUp var(--duration-normal) var(--ease-out) both;
}

.animate-slideInRight {
  animation: slideInRight var(--duration-normal) var(--ease-out) both;
}

.animate-live {
  animation: livePulse 2.5s ease-in-out infinite;
}

.animate-critical {
  animation: criticalPulse 1.5s ease-in-out infinite;
}

.animate-dataFlip {
  animation: dataFlip var(--duration-fast) var(--ease-out) both;
}

/* Stagger para listas que cargan múltiples items */
.stagger-1 { animation-delay: 50ms; }
.stagger-2 { animation-delay: 100ms; }
.stagger-3 { animation-delay: 150ms; }
.stagger-4 { animation-delay: 200ms; }
.stagger-5 { animation-delay: 250ms; }

/* Respetar preferencias de accesibilidad */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}

ARCHIVO: dashboard/src/hooks/useAnimation.js

```javascript
import { useEffect, useRef } from 'react'

/**
 * Hook que detecta cuando un valor numérico cambia
 * y aplica la clase animate-dataFlip al elemento.
 * Para métricas que se actualizan en tiempo real.
 */
export function useDataFlip(value, elementRef) {
  const prevValue = useRef(value)
  
  useEffect(() => {
    if (prevValue.current !== value && elementRef.current) {
      elementRef.current.classList.remove('animate-dataFlip')
      void elementRef.current.offsetWidth // reflow
      elementRef.current.classList.add('animate-dataFlip')
      prevValue.current = value
    }
  }, [value])
}

/**
 * Hook que aplica stagger delay a una lista de items.
 * Usar cuando una lista de elementos carga o se actualiza.
 */
export function useStagger(count, baseDelay = 50) {
  return Array.from({ length: count }, (_, i) => ({
    style: { animationDelay: `${i * baseDelay}ms` },
    className: 'animate-fadeUp'
  }))
}
```

REGLAS DE MOTION:
- Transiciones hover: siempre var(--duration-fast) — 150ms.
  Más lento es torpe. Más rápido es invisible.
- Entradas de elementos: var(--duration-normal) — 250ms.
- Salidas de elementos: var(--duration-fast) — 150ms.
  Las salidas siempre más rápidas que las entradas.
- Modales y paneles grandes: var(--duration-slow) — 350ms.

NO HAGAS:
- No pongas transition: all. Especificar exactamente qué transiciona.
  transition: all mata la performance silenciosamente.
- No animes width ni height directamente. Animar transform: scaleY()
  o usar CSS Grid para expandir (grid-template-rows: 0fr → 1fr).
- No uses bounce (ease-spring) en datos. Solo en feedback de UI
  (un botón que se presiona, un item que se selecciona).
- No animes más de 3 propiedades simultáneamente en el mismo elemento.
```

---

## F05 — Layout Shell

### PROMPT F05 — App Shell Layout
**Rol:** Frontend Developer  
**Entregable:** `dashboard/src/components/layout/AppShell.jsx`

```
Sos un Frontend Developer especializado en layouts de aplicaciones
de datos de alta densidad con navegación lateral.

ARCHIVO: dashboard/src/components/layout/AppShell.jsx

ESTRUCTURA DEL LAYOUT:

```
┌─────────────────────────────────────────────────────┐
│  STATUS BAR (28px)                                   │  ← siempre visible
│  NYXAR  ●LIVE  EVENTOS/MIN  ALERTAS ABIERTAS        │
├──────────┬──────────────────────────┬────────────────┤
│          │                          │                │
│   NAV    │     MAIN CONTENT         │  DETAIL PANEL  │
│  220px   │     (flex-1)             │   360px        │
│          │                          │  (condicional) │
│          │                          │                │
└──────────┴──────────────────────────┴────────────────┘
```

COMPONENTE APPSHELL:
- StatusBar: barra horizontal superior de 28px
  * Indicador LIVE con punto cyan animado (animate-live)
  * Contador de eventos/min que se actualiza con dataFlip
  * N alertas abiertas (con color según severidad más alta activa)
  * Timestamp actual en --font-data
  * Si WebSocket desconectado: punto gris + texto "RECONECTANDO"

- Sidebar: 220px de ancho
  * Logo/nombre del sistema en la parte superior
  * Links de navegación (ver PROMPT F06)
  * Indicadores de estado de módulos en la parte inferior
  * Collapsable a 56px con solo íconos (persiste en localStorage)

- Main Content: flex-1, scroll interno independiente
  * Cada vista se monta aquí con React Router
  * Transición entre rutas: crossfade de 200ms (no slide)

- Detail Panel: 360px, aparece al seleccionar un elemento
  * Slide in desde la derecha (animate-slideInRight)
  * Botón de cierre en la esquina superior
  * Comprime el main content en lugar de sobreponerse
  * Persiste mientras el usuario navega entre vistas

APPSHELL DEBE:
- No tener scroll en el nivel root. El scroll es dentro de cada zona.
- Mantener la StatusBar siempre visible (position: fixed o sticky).
- El detail panel NO es un modal — es un panel fijo que cambia el layout.
- Si hay una alerta crítica activa: el borde izquierdo del viewport
  tiene una línea de 2px en --critical-bright.
  Sutil, pero se ve en visión periférica.

DETAIL PANEL — el "contenedor inteligente":
El detail panel muestra el detalle de lo que el usuario seleccionó,
sin importar desde qué vista lo seleccionó:
- Click en un nodo del NetworkMap → detalle de identidad
- Click en un evento del Timeline → detalle del evento + contexto
- Click en un incidente → detalle del incidente + timeline
- Click en una alerta de honeypot → detalle del hit + identidad involucrada

El panel recibe el tipo de contenido y el ID, y renderiza el componente
correcto. El estado del panel vive en Zustand: { type, id, isOpen }.

REGLAS:
- El layout es 100vh, sin scroll en el body.
- Usar CSS Grid para el layout principal: `grid-template-columns: var(--nav-width) 1fr auto`
- El detail panel usa `width: 0` cuando está cerrado y `width: var(--panel-width)`
  cuando está abierto, con transition en width.
- En viewport < 1280px: el detail panel pasa a ser un modal de pantalla completa.

NO HAGAS:
- No uses position: absolute para el layout principal.
- No pongas padding en AppShell — cada zona maneja su propio padding.
- No hagas que el StatusBar sea un componente de React si se puede hacer con CSS.
  Si es solo texto y CSS, es más rápido.
```

---

## F06 — Navigation

### PROMPT F06 — Sidebar Navigation
**Rol:** Frontend Developer  
**Entregable:** `dashboard/src/components/layout/Sidebar.jsx`

```
Sos un Frontend Developer especializado en navegación de aplicaciones
de datos complejas.

ARCHIVO: dashboard/src/components/layout/Sidebar.jsx

DISEÑO DEL SIDEBAR:

Parte superior (marca NYXAR únicamente; el wordmark puede ir en el SVG, sin subtítulos regionales ni nombres legacy):
```
┌────────────────────────┐
│  ⬡ NYXAR               │  ← logo + marca, ~44px de alto
├────────────────────────┤
│                        │
│  ◉ Red                 │  ← NetworkMap
│  ≡ Timeline        (3) │  ← badge con alertas activas
│  ◎ Identidades         │
│  ◈ Hunting             │
│                        │
│  ──────────────────    │  ← separador visual
│                        │
│  ⚡ Respuestas      (2) │  ← proposals pendientes
│  ✉ Reportes            │
│                        │
│  ──────────────────    │
│                        │
│  ♦ CEO View            │
│                        │
└────────────────────────┘
```

Parte inferior (siempre al fondo del sidebar):
```
│  ────────────────────  │
│  ◈ Sistema          ●  │  ← puntito de salud del sistema
│                        │
│  ⊡ Colapsar           │  ← toggle para modo compacto
└────────────────────────┘
```

CADA NAV ITEM:
- Estado default: ícono + texto, color --base-subtle
- Estado hover: background --base-surface, color --base-text
  Transición: var(--duration-fast)
- Estado activo: background --cyan-dim, color --cyan-bright,
  borde izquierdo de 2px en --cyan-base
  NO usar un highlight full-width chillón
- Badge de conteo: aparece solo cuando N > 0
  Fondo --critical-bg, borde --critical-border, texto --critical-bright
  Font: --font-data, --text-xs, tabular-nums
  Se actualiza en tiempo real via WebSocket

INDICADOR DE ESTADO DEL SISTEMA (en el fondo del sidebar):
Un punto de color que comunica el estado del sistema:
- Verde + animate-live: todo nominal
- Naranja: algún servicio en warning
- Rojo + animate-critical: algún servicio crítico o WebSocket desconectado
Al hacer hover: tooltip con el resumen del estado.

MODO COLAPSADO (56px):
Solo muestran íconos. Los badges de conteo se mantienen.
El logo se convierte en solo el ícono "⬡".
La transición entre modos: var(--duration-slow), suave.
El estado (expandido/colapsado) se persiste en localStorage.

ÍCONOS:
Usar caracteres Unicode geométricos, NO librerías de íconos.
Son más livianos, más únicos, y renderizan mejor en --font-data.
- ⬡ hexágono (logo)
- ◉ círculo con punto (red/mapa)
- ≡ líneas horizontales (timeline/lista)
- ◎ círculo vacío (identidades)
- ◈ diamante (hunting/AI)
- ⚡ rayo (respuestas)
- ✉ sobre (reportes)
- ♦ diamante sólido (CEO)
- ⊡ cuadrado (sistema/health)

REGLAS:
- Marca en UI: solo NYXAR (alineado a la dirección "Operational Intelligence Interface");
  prohibido CP LATAM, CyberPulse, subtítulos regionales o variantes de nombre legacy.
- Los nav items son <a> o <NavLink> de React Router, nunca <div> clickeable.
- El indicador activo es CSS puro — no requiere JavaScript para el estilo.
- Los badges se actualizan via Zustand sin re-renderizar todo el Sidebar.

NO HAGAS:
- No uses un ícono SVG de Heroicons o Lucide. Los caracteres Unicode
  son más únicos y no requieren una dependencia.
- No pongas texto de descripción bajo cada nav item (no hay espacio).
- No animes el borde activo — aparece instantáneamente.
```

---

## F07 — Componentes Atómicos

### PROMPT F07 — Atomic Components
**Rol:** Frontend Developer  
**Entregable:** Todos los componentes base en `dashboard/src/components/ui/`

```
Sos un Frontend Developer especializado en sistemas de componentes
de UI para interfaces de datos técnicos.

Implementar todos los componentes atómicos. Cada uno en su propio archivo.
Usar CSS Modules para los estilos de cada componente.

COMPONENTE 1: Badge.jsx
Props: variant ("default" | "critical" | "high" | "medium" | "clean" | "info" | "cyan"),
       size ("sm" | "md"), children, dot (bool)

Aspecto: píldora con fondo semitransparente y borde sutil.
No un badge plano de color sólido — eso es amateur.
El fondo es --{variant}-bg, el borde es --{variant}-border, el texto es --{variant}-bright.
Si dot=true: un punto de 5px del color de la variante antes del texto.

```jsx
// Ejemplo visual esperado:
// ╔══════════════╗
// ║ ● CRÍTICO 91 ║   ← fondo rojo muy oscuro, borde rojo, texto rojo claro
// ╚══════════════╝
```

COMPONENTE 2: RiskGauge.jsx
Props: score (0-100), size ("sm" | "md" | "lg"), showLabel (bool)

No una barra de progreso horizontal (aburrida).
Es un número con contexto visual:
- El número en --font-data, grande, con el color de scoreToColor(score)
- Debajo: el label (NOMINAL / BAJO / MEDIO / ALTO / CRÍTICO)
- A la izquierda del número: una línea vertical de 3px con el color del score
- Si score > 80: el número tiene animate-critical
- Si score cambia: animate-dataFlip

COMPONENTE 3: LiveIndicator.jsx
Props: connected (bool), eventsPerMin (number)

Muestra el estado de conexión WebSocket.
- Punto de 8px con animate-live si connected=true
- Punto gris estático si connected=false
- Al lado: "{eventsPerMin} ev/min" en --font-data --text-xs
- Si desconectado: "RECONECTANDO..." con opacity: 0.6, parpadeante lento

COMPONENTE 4: DataChip.jsx
Props: value (string), type ("ip" | "domain" | "hash" | "port" | "user")
       copyable (bool), truncate (bool)

Para mostrar valores técnicos inline.
- Fondo --base-surface, borde --base-border
- Texto en --font-data, color según tipo:
  * ip: --cyan-soft
  * domain: --base-soft
  * hash: --base-muted (los hashes no son el dato principal)
  * port: --medium-bright
  * user: --info-bright
- Si copyable=true: ícono de copia que aparece al hover
  Al copiar: el ícono cambia a ✓ por 1.5 segundos
- Si truncate=true: hash largo se muestra como "a4f3...8c2d"

COMPONENTE 5: TimeAgo.jsx
Props: timestamp (ISO8601 string)

"hace 3 min" | "hace 2 h" | "hace 1 d" en español.
- Color: --base-subtle
- Font: --font-ui, --text-xs
- Se actualiza cada 30 segundos con un intervalo en useEffect
- Si timestamp tiene menos de 60 segundos: "hace un momento"
- Si timestamp tiene más de 7 días: mostrar la fecha completa

COMPONENTE 6: SourceTag.jsx
Props: source ("dns" | "proxy" | "firewall" | "wazuh" | "endpoint" | "misp")

Muestra la fuente de un evento de forma compacta.
- Usa SOURCE_COLORS del utils/colors.js
- Ícono Unicode + label en --text-xs --font-data
- Sin fondo, sin borde — solo el ícono coloreado y el texto

COMPONENTE 7: Skeleton.jsx
Props: width, height, rounded (bool)

Para estados de carga — comunica la forma del contenido antes de que llegue.
- Fondo: gradiente animado de --base-surface a --base-raised
- El shimmer es horizontal, de izquierda a derecha
- Usar animate-shimmer
- No usar para todo — solo cuando la carga tarda > 200ms

COMPONENTE 8: Tooltip.jsx
Props: children, content (string | ReactNode), side ("top" | "bottom" | "left" | "right")

Tooltip custom, no el title nativo del navegador.
- Aparece después de 400ms de hover (no inmediatamente)
- Fondo --base-overlay, borde --base-border-strong
- Sombra --shadow-md
- Max-width: 240px, texto wrapeado
- Animación: fadeUp de 150ms

COMPONENTE 9: EmptyState.jsx
Props: icon (string), title, description, action (opcional)

Para cuando no hay datos que mostrar.
- No un illustration genérica
- El ícono es un carácter Unicode grande (48px) en --base-muted
- Título en --base-soft
- Descripción en --base-muted, --text-sm
- Si action: un link/botón de acción sugerida

REGLAS:
- Todos los componentes son funcionales con hooks, sin clases.
- Todos aceptan className como prop para extensión desde el exterior.
- Todos manejan sus estados de loading/empty/error internamente si aplica.
- CSS Modules: el archivo .module.css vive al lado del .jsx.

NO HAGAS:
- No importes ninguna librería de UI (no Radix, no HeadlessUI, no Chakra).
  Solo los componentes que construyas vos mismo.
- No uses inline styles para nada que no sea dinámico.
- No crees un componente "Button" genérico. En NYXAR, los botones
  son contextuales (ApproveButton, RunHuntButton, etc.) con semántica propia.
```

---

## F08 — Componentes de Datos

### PROMPT F08 — Data Components
**Rol:** Frontend Developer  
**Entregable:** `dashboard/src/components/data/` — cards y listas

```
Sos un Frontend Developer especializado en presentación de datos
de seguridad de alta densidad.

COMPONENTE 1: EventCard.jsx
Props: event (Evento), compact (bool), selected (bool), onClick

La card de evento es el bloque fundamental del Timeline.
Diseño cuando compact=false:

```
┌──────────────────────────────────────────────────────┐
│  ◈ DNS  │  maria.gomez  ·  CONTABILIDAD  │  hace 2m  │  ← header row
├──────────────────────────────────────────────────────┤
│  dominio-raro.ru                                      │  ← valor principal
│  192.168.1.45  →  RU  ·  AS49505                     │  ← contexto de enrich
│                                     ⚠ SOSPECHOSO  67 │  ← badge de riesgo
└──────────────────────────────────────────────────────┘
```

- Borde izquierdo de 2px con el color de la fuente (SOURCE_COLORS)
- Si risk_score > 60: el borde izquierdo toma el color del risk score
- Si es nuevo (< 30 segundos): animate-fadeUp
- Hover: --base-surface → --base-raised, sombra --shadow-sm
- Selected: borde izquierdo más grueso (3px), background ligeramente más claro
- El valor principal (dominio/IP) usa DataChip (font-data, truncable)
- Sin bordes redondeados agresivos — border-radius: var(--radius-sm) solo

COMPONENTE 2: IdentityRow.jsx
Props: identity (Identidad), onClick, compact (bool)

Para la lista de identidades.

```
┌────────────────────────────────────────────────────────┐
│  MG  │  María Gómez          │  ●  │  CONTABILIDAD  │  67 ──▲──  │
│      │  mgarcia  ·  PC-CONT-03│     │                │  ALTO      │
└────────────────────────────────────────────────────────┘
```

- Avatar: círculo de 32px con las iniciales del nombre.
  El color del avatar se deriva del área (areaToColor).
  Sin foto, sin ícono genérico — las iniciales son más técnicas.
- Indicador de actividad: punto de 6px
  Verde con animate-live: activo ahora
  Gris: inactivo
- Risk score: número + badge + flecha de tendencia
  Si subió en las últimas 2h: ▲ en --critical-bright
  Si bajó: ▼ en --clean-bright
  Si estable: sin flecha
- Si es_privilegiado=true: ◆ pequeño al lado del nombre

COMPONENTE 3: IncidentCard.jsx
Props: incident (Incidente), onClick, expanded (bool)

```
┌──────────────────────────────────────────────────────────┐
│  ████  CRÍTICO  │  Beaconing C2 detectado               │  ← header
│        hace 15m │  ventas.garcia  ·  PC-VENTAS-07       │
├──────────────────────────────────────────────────────────┤
│  (expanded=true)                                          │
│  "Comunicación cada 5.0 min exactos a dominio registrado │
│   hace 4 días. 12 consultas detectadas. Patrón consistente│
│   con malware de tipo C2. Riesgo de exfiltración activa." │
│                                              [ Investigar ]│
└──────────────────────────────────────────────────────────┘
```

- El bloque de color sólido a la izquierda (████) comunica severidad
  Es 4px de ancho, full height de la card.
- Header siempre visible, descripción colapsada por default
- Al expandir: la descripción del memo de Claude (si existe) o la descripción raw
- El botón [Investigar] abre el DetailPanel con el incidente completo

COMPONENTE 4: MetricCard.jsx
Props: label, value, delta (opcional), unit (opcional), trend (bool)

Para el header de cada vista con las métricas principales.

```
┌───────────────┐
│  EVENTOS HOY  │  ← label en .label class
│               │
│  2,847        │  ← value en data-value + dataFlip al cambiar
│  +124 ↑       │  ← delta con color verde/rojo
└───────────────┘
```

- Fondo --base-surface, borde --base-border
- Sin sombra (están en el header, no elevados)
- El delta es positivo (verde) o negativo (rojo) con ícono de flecha
- El valor usa animate-dataFlip al cambiar

REGLAS:
- Ninguna card tiene border-radius mayor a var(--radius-md).
  Las interfaces técnicas son más cuadradas, no redondeadas.
- Los avatares de letras no tienen sombra ni gradiente.
  Son círculos planos con color sólido derivado del área.
- La jerarquía visual en cada card: tipo/fuente → identidad → valor → estado.
  El ojo va de izquierda a derecha, de arriba a abajo, en ese orden.

NO HAGAS:
- No pongas más de 4 líneas de información en una card colapsada.
- No uses íconos de imágenes o SVG en las cards. Solo caracteres Unicode.
- No animes la expansión/colapso con max-height (genera jank).
  Usar grid-template-rows: 0fr → 1fr para expand/collapse smooth.
```

---

## F09 — Visualizaciones

### PROMPT F09 — Data Visualizations
**Rol:** Frontend Developer  
**Entregable:** `dashboard/src/components/charts/`

```
Sos un Frontend Developer especializado en visualización de datos
de seguridad con Recharts y D3.js.

COMPONENTE 1: RiskSparkline.jsx
Props: data ([{timestamp, score}]), width (default 80), height (default 32)

Una línea minimalista de la evolución del risk score en 24h.
Sin ejes, sin labels, sin grid — solo la línea.
- La línea usa strokeWidth: 1.5
- El color de la línea es el color actual del score (scoreToColor)
- Un área bajo la línea con el mismo color a opacity 0.1
- El último punto: un círculo de 4px del color actual
- Sin tooltips en el sparkline (es demasiado pequeño)
- Usar Recharts AreaChart con ejes hidden

COMPONENTE 2: EventsPerHourBar.jsx
Props: data ([{hour, count}]), height (default 120)

Barras verticales por hora del día (24 barras).
- Barras finas (width: 6px con gap de 4px)
- Color: cyan con opacity proporcional al valor (barras de poco tráfico son tenues)
- La hora actual: barra con borde --cyan-bright
- Sin ejes Y — la altura relativa comunica suficiente
- Eje X: solo las horas 0, 6, 12, 18, 24 en --font-data --text-xs
- Tooltip al hover: "{N} eventos a las {H}:00"
- Animación de entrada: las barras crecen desde 0 en stagger

COMPONENTE 3: ThreatDistribution.jsx
Props: data ([{fuente, count, color}])

No un pie chart. Los pie charts son difíciles de comparar.
Es una serie de barras horizontales con labels.

```
DNS      ████████████████████ 1,847  (64%)
PROXY    ██████               431    (15%)
WAZUH    ████                 312    (11%)
FIREWALL ██                   178    (6%)
ENDPOINT █                    79     (3%)
```

- Barras con el color de SOURCE_COLORS
- Los números en --font-data
- Animación: las barras se expanden de izquierda a derecha al montar

COMPONENTE 4: RiskDistributionDots.jsx
Props: identities ([{id, score, usuario}])

Una visualización tipo scatter plot de los risk scores actuales.
Cada punto es una identidad. El eje X es el score (0-100).
Los puntos se apilan verticalmente cuando tienen scores similares.

- Los puntos de score > 80 son más grandes (8px vs 5px para los demás)
- Color según scoreToColor
- Al hover: tooltip con nombre del usuario y score
- Al click: abre el detail panel de esa identidad

COMPONENTE 5: ActivityHeatmap.jsx
Props: data ([{hour, day, count}])

Un heatmap de actividad 7×24 (7 días × 24 horas).
Similar al heatmap de GitHub Contributions pero para actividad de red.

- Celdas pequeñas (14px × 14px) con gap de 2px
- Color: de --base-surface (sin actividad) a --cyan-bright (alta actividad)
- Días en el eje Y: Lu Ma Mi Ju Vi Sa Do en --font-data --text-xs
- Horas en el eje X: 0, 6, 12, 18 en --font-data --text-xs
- Al hover: tooltip con N eventos ese día/hora
- Sin borde exterior — los gaps crean la cuadrícula implícitamente

REGLAS DE VISUALIZACIÓN:
- Recharts debe usar colors de CSS variables, no hex hardcodeados.
  Usar la función `getComputedStyle(document.documentElement).getPropertyValue`
  para leer las CSS variables en el render.
- Todos los charts tienen tooltips custom que usan --font-data para números
  y --font-ui para labels.
- Los charts no tienen título interno — el título lo pone el componente padre.
- Los charts son responsive por default: usar ResponsiveContainer de Recharts.

NO HAGAS:
- No uses pie charts ni donut charts. Son difíciles de comparar precisamente.
- No animes los datos mientras el usuario hace hover sobre un chart.
  Las animaciones y los hover no conviven bien en Recharts.
- No pongas más de 5 series en un mismo chart. La complejidad visual no escala.
- No uses gradientes de colores múltiples en las barras (es ruido visual).
```

---

## F10 — NetworkMap View

### PROMPT F10 — Network Map View
**Rol:** Frontend Developer  
**Entregable:** `dashboard/src/views/NetworkMap.jsx`

```
Sos un Frontend Developer especializado en visualizaciones de grafos
de red con D3.js para interfaces de seguridad.

DISEÑO CONCEPTUAL:
El NetworkMap NO es el típico "force-directed graph" que parece un
accidente de partículas. Es un layout intencional:
- Los nodos se organizan por ÁREA en clusters
- Los clusters tienen posición fija (no flotan)
- Las conexiones son líneas curvas, no rectas
- Solo se muestran conexiones ACTIVAS (últimos 5 minutos)

LAYOUT POR CLUSTERS:
```
         [IT]              
        ● ● ●             
                   [VENTAS]
  [CONTABILIDAD]    ● ● ● ● ●
      ● ● ● ●               
                       [GERENCIA]
   [RRHH]                ● ● ●
    ● ● ●                  
              [MARKETING]
               ● ● ●
```

Cada cluster tiene un label del área en --base-muted --text-xs --label.
Los clusters son irregulares, no perfectamente circulares.
Cada nodo es un círculo de radio proporcional al risk_score:
- score < 20: radio 8px
- score 20-60: radio 12px
- score > 60: radio 16px
- score > 80: radio 20px + animate-critical

COLOR DEL NODO:
El fill del círculo es scoreToColor(score).color con opacity 0.85.
El stroke es el mismo color con opacity 1.
StrokeWidth: 1.5px.
Si el nodo está seleccionado: strokeWidth 3px + color cyan.

CONEXIONES:
Solo conexiones activas (eventos en los últimos 5 minutos).
Las conexiones internas (entre nodos de la red) son líneas curvas
de un color según el tipo de comunicación:
- Conexión normal: --base-border con opacity 0.4
- Conexión sospechosa (enrichment=sospechoso): --medium-muted
- Conexión maliciosa: --critical-muted con animate (opacity 0.4→0.8)

Cuando llega un evento nuevo por WebSocket:
- Una partícula viaja a lo largo de la línea de conexión correspondiente
- La partícula es un punto de 4px del color de la conexión
- Animación de 600ms, una sola vez, sin repetición

INTERACCIONES:
- Hover en nodo: tooltip con nombre, área, risk score, N eventos activos
- Click en nodo: abre el Detail Panel con el perfil de identidad
- Hover en conexión: tooltip con tipo de tráfico y volumen
- Scroll: zoom en el canvas (usando D3 zoom)
- Drag: pan del canvas

PANEL DE CONTROLES (esquina superior derecha, flotante):
- Toggle para mostrar/ocultar conexiones
- Filtro de severidad mínima (solo mostrar nodos con score > N)
- Botón "Centrar vista"
- Botón "Mostrar solo activos"

PERFORMANCE:
El grafo usa <canvas> para los nodos y conexiones (no SVG).
D3 maneja los cálculos, canvas maneja el render.
Para > 50 nodos, SVG tiene jank inaceptable.
Usar requestAnimationFrame para el loop de render.
Solo re-renderizar cuando hay cambios (no en cada frame).

REGLAS:
- El canvas ocupa el 100% del contenedor, sin scrollbar.
- Los nodos nunca se superponen — usar collision detection en D3.
- El label del área es SVG overlay sobre el canvas (más fácil de estilizar).
- Las posiciones de los clusters se calculan una vez al montar.
  Solo los nodos dentro de cada cluster tienen fuerza de simulación.

NO HAGAS:
- No uses react-force-graph ni similares. D3 directo sobre canvas.
- No hagas que el grafo se reorganice completamente con cada nuevo evento.
  Solo actualizar el nodo afectado.
- No animes la posición de los nodos en tiempo real.
  Solo animar el tamaño y color cuando cambia el risk score.
- No muestres conexiones con el exterior (IPs externas).
  El mapa es de la red interna. Las IPs externas van en el Timeline.
```

---

## F11 — Timeline View

### PROMPT F11 — Timeline View
**Rol:** Frontend Developer  
**Entregable:** `dashboard/src/views/Timeline.jsx`

```
Sos un Frontend Developer especializado en feeds de datos en tiempo real
con virtualización para alto volumen.

DISEÑO DEL TIMELINE:

HEADER DE LA VISTA:
Row de 4 MetricCards:
- Eventos hoy: N (con ↑ delta desde ayer)
- Eventos/min ahora: N.N
- Alertas abiertas: N (coloreado si N > 0)
- Honeypots activados hoy: N (siempre rojo si N > 0)

BARRA DE FILTROS:
Una sola línea de filtros compactos:
[ TODAS LAS FUENTES ▾ ]  [ SEVERIDAD MÍNIMA ▾ ]  [ ÁREA ▾ ]  [≡ Solo alertas]

Los dropdowns son custom (no <select> nativo):
- Fondo --base-overlay, borde --base-border-strong
- Font --font-ui --text-sm
- Los items de fuente muestran el ícono coloreado de SOURCE_COLORS

FEED DE EVENTOS:
Lista virtualizada (react-window FixedSizeList o VariableSizeList).
Máximo 500 eventos en memoria (ring buffer — los más viejos se eliminan).

Los nuevos eventos aparecen arriba con animate-fadeUp.
Si el usuario scrolleó hacia abajo: NO hacer scroll automático.
En cambio: mostrar un badge "▲ N nuevos" flotante en la parte superior.
Al hacer click en el badge: scroll suave al tope + badge desaparece.

CADA EVENTO en el feed: usar EventCard.jsx.

SEPARADORES DE TIEMPO:
Entre eventos de diferentes momentos, insertar separadores:
```
──────────── hace 2 horas ────────────
```
Esto da contexto temporal sin ocupar mucho espacio.
Se inserta automáticamente cuando hay un gap de > 30 minutos.

DETAIL PANEL del evento seleccionado (slide desde la derecha):
Cuando el usuario hace click en un evento, el Detail Panel muestra:

1. Header: fuente, tipo, timestamp exacto
2. Identidad involucrada: nombre, área, IP, hostname
   Botón "Ver en mapa" que centra el NetworkMap en ese nodo
3. Valor externo: DataChip con el IP/dominio/URL
4. Enrichment completo:
   - Reputación con badge
   - País y ASN
   - Fuente de threat intel
   - Tags de malware si los hay
   - Link a VirusTotal / AbuseIPDB si corresponde
5. Contexto de la identidad:
   - Risk score actual con RiskGauge
   - "Este usuario generó N eventos similares en las últimas 24h"
   - Botón "Ver perfil completo"
6. Si hay incidente relacionado: card compacta del incidente
   Botón "Ver incidente"

REGLAS:
- La lista virtualizada usa itemSize fijo de 76px para compact,
  y 120px para expanded. NO usar VariableSizeList (complejo sin ganancia).
- El separador de tiempo no es un item de la lista — es un overlay CSS.
- Los filtros son AND (todos los filtros activos se aplican simultáneamente).
- Cambiar un filtro hace fadeOut de los items que salen y fadeIn de los nuevos.

NO HAGAS:
- No renderices todos los eventos en el DOM. Virtualización obligatoria.
- No hagas que el feed se pause al hacer hover. Solo se pausa cuando
  el usuario scrollea hacia abajo.
- No pongas un botón "Limpiar" que elimine eventos. Los eventos son el
  historial — solo se pueden filtrar, no eliminar desde la UI.
```

---

## F12 — Identities View

### PROMPT F12 — Identities View
**Rol:** Frontend Developer  
**Entregable:** `dashboard/src/views/Identities.jsx`

```
Sos un Frontend Developer especializado en tablas de datos con
ordenamiento, filtros y drill-down.

DISEÑO DE LA VISTA:

HEADER: MetricCards
- Total identidades monitoreadas
- Activas ahora (actividad en últimos 30 min)
- En riesgo alto (score > 60)
- Administradores privilegiados

CONTROLES:
[ Buscar identidad...        ]  [ ÁREA ▾ ]  [ ORDENAR: RIESGO ▾ ]  [◉ Solo activos]

El search filtra en tiempo real por nombre, usuario, hostname o área.

LISTA DE IDENTIDADES:
Usando IdentityRow.jsx.
Ordenamiento por default: risk_score DESC.
Ordenamiento clickeable en el header de columna.

Cuando se hace click en una identidad:
El Detail Panel muestra el PERFIL COMPLETO:

```
┌──────────────────────────────────────┐
│  MG   María Gómez              ● ACTIVA
│       mgarcia · CONTABILIDAD        │
│       PC-CONT-03 · 192.168.1.45     │
│                                     │
│  RIESGO ACTUAL                      │
│  ████████░░░░░░░░  67  ALTO  ↑+12  │
│                                     │
│  COMPORTAMIENTO                     │
│  Horario habitual: 08:30 → 18:00   │
│  Hoy activo desde: 09:05           │
│  Dominios habituales: 8 conocidos  │
│  Volumen hoy: 94MB / 85MB base     │
│  ─────────────────────────────────  │
│  DESVIACIONES DETECTADAS HOY       │
│  ⚠ Consultó 3 dominios nuevos     │
│  ⚠ Volumen 10% sobre baseline     │
│  ─────────────────────────────────  │
│  ÚLTIMOS EVENTOS              [ + ] │
│  (EventCards compactos)            │
└──────────────────────────────────────┘
```

SECCIÓN DE DESVIACIONES:
Las desviaciones del baseline son el dato más valioso de esta vista.
Se listan en orden de anomalía descendente.
Cada una tiene:
- Un ícono ⚠ en --medium-bright
- Una descripción en lenguaje natural (no técnico): 
  "Visitó 3 sitios que no están en su historial habitual"
  "El tráfico de hoy supera en 10% su promedio de 7 días"
- Si la desviación disparó una alerta: el ícono cambia a ⊘ en --critical-bright

BASELINE VISUAL:
Una pequeña visualización del baseline vs comportamiento actual:

```
Horario    ░░░░████████████████░░░░   (banda gris=habitual, cyan=hoy)
Volumen    ████████████░            base: 85MB | hoy: 94MB
Dominios   Conocidos: 8  Nuevos: 3
```

REGLAS:
- La lista puede tener 200 items — usar virtualización.
- Las desviaciones se recalculan en el cliente con los datos del baseline de Zustand.
  No hacer fetch por cada identidad al abrir el detail panel.
- Si una identidad está siendo investigada en un Hunt activo:
  mostrar un badge "◈ EN HUNTING" al lado del nombre.

NO HAGAS:
- No uses una tabla HTML con <table><tr><td>. Usar divs con CSS Grid.
  Las tablas HTML son rígidas para un layout de identidades complejas.
- No muestres el baseline en formato JSON. Siempre en lenguaje visual.
- No uses barras de progreso de HTML nativo (<progress>). Construir custom.
```

---

## F13 — CEO View

### PROMPT F13 — CEO View
**Rol:** Frontend Developer + Content Designer  
**Entregable:** `dashboard/src/views/CeoView.jsx`

```
Sos un Frontend Developer y Content Designer especializado en
interfaces ejecutivas para personas no técnicas.

FILOSOFÍA DE LA VISTA CEO:
Esta vista es la única en el sistema donde el diseño es deliberadamente
más simple, más espacioso, más "periodístico".
El CEO no quiere densidad — quiere claridad.

HEADER: Un solo botón prominente
```
[ ⟳ Actualizar análisis ]
Último análisis: hace 8 minutos
```

El botón dispara POST /ai/ceo-view. Durante la generación:
El botón cambia a "Analizando... ██████░░░░" con una barra de progreso
animada (no un spinner). La barra se llena en ~8 segundos (estimado de
cuánto tarda Claude). Si tarda más, la barra llega al 90% y espera.

ESTADO ACTUAL — SEMÁFORO PRINCIPAL:
```
┌─────────────────────────────────────────────────────┐
│                                                      │
│      🟢  La red opera con normalidad                │
│         No hay incidentes críticos activos.          │
│                                                      │
└─────────────────────────────────────────────────────┘
```
O:
```
┌─────────────────────────────────────────────────────┐
│                                                      │
│      🔴  Hay una situación que requiere atención    │
│         Un equipo del área de Ventas está            │
│         mostrando comportamiento inusual.            │
│                                                      │
└─────────────────────────────────────────────────────┘
```

El semáforo es un ícono Unicode grande (24px) + título grande + subtítulo.
Sin terminología técnica. Sin IPs. Sin CVEs.

ANÁLISIS DE CLAUDE:
Los 3 párrafos generados por Claude en un layout editorial:
- Tipografía más grande que el resto de la app: --text-md --leading-normal
- Color --base-text (no el gris más suave)
- Espaciado generoso entre párrafos: --space-8
- Sin bullets, sin headers dentro del texto — es una narración continua

ACCIÓN RECOMENDADA (si hay algo):
```
┌──────────────────────────────────────────┐
│  ► Acción recomendada                    │
│                                          │
│  El equipo de IT debería revisar el      │
│  equipo de Juan Pérez antes del          │
│  cierre del día.                         │
└──────────────────────────────────────────┘
```
Card con borde izquierdo cyan de 3px. El texto es la `accion_inmediata`
del memo de Claude. Solo si existe.

HISTORIAL:
Los últimos 5 análisis CEO con su timestamp y primer párrafo truncado.
Expandibles al hacer click.
```
[ 20 mar, 09:15 ] La red operó con normalidad...
[ 19 mar, 17:30 ] Se detectó un comportamiento inusual...
[ 19 mar, 09:10 ] La red operó con normalidad...
```

REGLAS:
- Esta vista NO tiene métricas ni gráficos (el CEO no los leerá).
- El semáforo puede ser verde (nominal), naranja (atención) o rojo (crítico).
  No 5 niveles. Solo 3. Más simple es más accionable.
- El font-size del texto de análisis es 15px — ligeramente más grande
  que el resto de la app. Intencionalmente más legible.
- Si no hay análisis todavía: EmptyState con instrucción de generar uno.

NO HAGAS:
- No muestres el JSON del AiMemo directamente. Solo el texto procesado.
- No pongas un "back to technical view" prominente. Esta vista es para
  personas que no quieren la vista técnica.
- No uses el color rojo para el estado "atención". El naranja es suficiente.
  El rojo es solo para "crítico" — cuando necesita acción AHORA.
```

---

## F14 — Hunting View

### PROMPT F14 — Threat Hunting View
**Rol:** ⚛️ Frontend Developer  
**Entregable:** Refinamiento visual de `dashboard/src/views/HuntingView.jsx`

```
Sos un Frontend Developer especializado en interfaces de investigación
para analistas de seguridad avanzados.

El componente ya tiene su lógica definida en PROMPTS_V2 (PROMPT V11).
Este prompt define los detalles visuales que lo hacen destacar.

ESTÉTICA DE LA VISTA DE HUNTING:
Si el Timeline es el "stream de conciencia" de la red
y el NetworkMap es la "vista de satélite",
el Hunting es el "laboratorio de análisis forense".

Paleta específica para esta vista:
Ligeramente más oscura que el resto. El fondo es --base-void
en lugar de --base-deep. Comunica que estás en un espacio diferente,
más especializado.

PANEL DE HIPÓTESIS:
Cada hipótesis es una card con diseño tipo "ficha de investigación":

```
╔══════════════════════════════════════╗
║  ◈ T1071.004  ·  PRIORIDAD 4/5      ║  ← técnica MITRE + prioridad
╠══════════════════════════════════════╣
║  Posible C2 no detectado en          ║
║  cuentas privilegiadas               ║  ← título de la hipótesis
╠══════════════════════════════════════╣
║  NUEVA  ·  Generada hace 12 min     ║  ← estado + timestamp
║                          [Investigar] ║  ← acción
╚══════════════════════════════════════╝
```

Las cards de hipótesis usan borde completo (no solo izquierdo).
El borde tiene el color de la prioridad:
- Prioridad 5: --critical-border
- Prioridad 4: --high-border
- Prioridad 3: --medium-border
- Prioridad 1-2: --base-border-strong

SESIÓN DE HUNTING ACTIVA:
Cuando el analista hace click en "Investigar", la columna derecha
muestra la sesión en progreso con una estética de "terminal":

```
╔════════════════════════════════════════════════════╗
║  HUNT SESSION #047  ·  ACTIVA                      ║
╠════════════════════════════════════════════════════╣
║  Hipótesis: Posible C2 en cuentas privilegiadas    ║
║  MITRE: T1071.004 · DNS Protocol                   ║
║                                                    ║
║  ─── QUERIES ─────────────────────────────────── ─ ║
║  ✓  Dominios con alta entropía desde IPs admin      ║
║     → 3 resultados encontrados                     ║
║  ⟳  Beaconing en intervalo < 2min desde IT...      ║
║     → Procesando...                                ║
║  ○  Consultas DNS fuera de horario en admins       ║
║     → Pendiente                                    ║
║                                                    ║
║  ─── RESULTADOS PARCIALES ──────────────────────── ║
║  PC-IT-02  ·  it.rodriguez  ·  hace 3h            ║
║  sub.xn--e1affm.com  ·  entropía: 4.2             ║
║  (DataChip + contexto inline)                      ║
╚════════════════════════════════════════════════════╝
```

La apariencia de "terminal" se logra con:
- Fondo --base-void
- Borde --base-border-strong con radius: var(--radius-sm)
- Header con fondo --base-surface y texto --font-data
- Separadores de sección: líneas de guiones (─────)
  generadas con CSS border-bottom, no con caracteres literales
- Font --font-data para valores, --font-ui para labels

ESTADO VACÍO (sin hipótesis activas):
```
◈

No hay hipótesis activas

El sistema genera hipótesis automáticamente
a las 6:00 AM cada día.
También podés iniciar una investigación manual.

[ + Nueva hipótesis ]
```

REGLAS:
- El textarea de hipótesis manual tiene auto-resize (crece con el contenido).
- Las queries en progreso tienen un cursor parpadeante al final: |
  CSS animation: blink 1s step-end infinite.
  (Solo el cursor, no el texto completo).
- Los resultados de queries se muestran como EventCards compactas.

NO HAGAS:
- No uses verde en esta vista para indicar "encontrado".
  En el contexto de hunting, "encontrado" puede ser malo.
  Usar cyan para "encontrado sin amenaza confirmada"
  y rojo para "amenaza confirmada".
- No simules una terminal con texto que se escribe letra por letra.
  Es un efecto molesto en datos reales.
- No muestres el pipeline de MongoDB al usuario.
```

---

## F15 — System Health View

### PROMPT F15 — System Health View
**Rol:** ⚛️ Frontend Developer  
**Entregable:** Refinamiento visual de `dashboard/src/views/SystemHealth.jsx`

```
Sos un Frontend Developer especializado en dashboards de operaciones
e infraestructura.

ESTÉTICA:
La vista de salud del sistema tiene la estética más "técnica" de todas.
Es para el administrador del sistema, no para el analista de seguridad.
Más densa, más datos, menos narrativa.

GRID DE COMPONENTES:
Layout CSS Grid de 3 columnas en desktop, 2 en tablet.
Cada card de componente tiene altura fija de 88px.

CARD DE COMPONENTE:
```
┌────────────────────────────────────┐
│  ● NOMINAL  │  Redis               │
│  0.8ms latencia  │  12MB RAM usada │
│  Hace 15s ─────────────────────── │
└────────────────────────────────────┘
```

El ● es un StatusDot grande (12px) con animate-live si nominal.
La latencia usa --font-data.
El timestamp de último check es relativo (TimeAgo).

Si un componente está en WARNING:
- El borde de la card pasa a --high-border
- El StatusDot pasa a naranja

Si un componente está en CRITICAL:
- El borde pasa a --critical-border con --shadow-critical
- El StatusDot pasa a rojo con animate-critical
- La card tiene fondo --critical-bg (muy sutil)
- En el StatusBar del AppShell: el indicador de sistema cambia

THROUGHPUT CHART:
Debajo del grid, un EventsPerHourBar de los últimos 120 minutos
(2 horas con granularidad por minuto en lugar de por hora).
Título: "EVENTOS PROCESADOS — ÚLTIMAS 2 HORAS"

Si hay un gap (período sin eventos): la barra de ese minuto
tiene un fondo de --critical-bg para destacar el "silencio".

LISTA DE HEARTBEATS:
Una tabla compacta de los servicios internos:
```
collector    ● hace 8s   ◉ 847 ev/min procesados
enricher     ● hace 12s  ◎ 94% cache hits
correlator   ● hace 6s   ◆ 2 patrones activos
ai_analyst   ● hace 22s  ◈ 1,247 tokens/h
notifier     ● hace 9s   ✉ 3 enviados hoy
```

- Font --font-data para todos los valores
- Los tiempos de heartbeat cambian cada 30s
- animate-dataFlip cuando el valor cambia

BANNER DE ESTADO CRÍTICO:
Si cualquier componente es CRITICAL, mostrar un banner en la parte superior:
```
┌──────────────────────────────────────────────────────────┐
│  ⊘  SISTEMA DEGRADADO  ·  enricher no responde (> 90s)  │
└──────────────────────────────────────────────────────────┘
```
Fondo --critical-bg, borde --critical-border, texto --critical-bright.
Este banner también aparece en el AppShell StatusBar.

REGLAS:
- Las cards de componentes no tienen hover effects. Son informativas, no clickeables.
  Excepción: el card de AI Analyst tiene un link "Ver memos recientes".
- El throughput chart se actualiza cada 30 segundos (no en tiempo real puro).
- Si TODOS los componentes están nominales: mostrar un estado "All systems operational"
  prominente antes del grid (como la página de status de GitHub).

NO HAGAS:
- No pongas logs crudos en esta vista. Los logs van al sistema de logging, no al dashboard.
- No hagas que esta vista sea la que se abre por default. Es una vista de soporte,
  no de uso cotidiano.
```

---

## F16 — Response Proposals View

### PROMPT F16 — Response Proposals View
**Rol:** ⚛️ Frontend Developer  
**Entregable:** `dashboard/src/views/ResponseView.jsx`

```
Sos un Frontend Developer especializado en interfaces de aprobación
y flujos de decisión en sistemas de seguridad.

FILOSOFÍA:
Esta vista es donde se toman decisiones con consecuencias reales.
El diseño debe comunicar:
1. Qué pasó (el incidente)
2. Qué se propone hacer (las acciones)
3. Qué impacto tendrá en el negocio
4. Dos botones: APROBAR o RECHAZAR

No debe ser rápida de clickear. Debe invitar a leer antes de actuar.

LAYOUT:
Cuando hay proposals pendientes: la vista tiene UN proposal a la vez,
centrado, con todo el espacio necesario para entenderlo.
Navegación entre proposals: "1 de 3 pendientes →"

CARD DE PROPOSAL:
```
╔══════════════════════════════════════════════════════════╗
║  ACCIÓN REQUERIDA  ·  hace 8 minutos                    ║
╠══════════════════════════════════════════════════════════╣
║  INCIDENTE RELACIONADO                                   ║
║  ─────────────────                                       ║
║  ⊘ CRÍTICO  |  Ransomware detectado en ventas.garcia    ║
║  PC-VENTAS-07 · hace 23 minutos                         ║
╠══════════════════════════════════════════════════════════╣
║  ACCIONES PROPUESTAS                                     ║
║  ──────────────────                                      ║
║  1.  Cuarentena de dispositivo              [REVERSIBLE] ║
║      PC-VENTAS-07 · 192.168.1.72                        ║
║      "El dispositivo será aislado de la red.            ║
║       Juan Pérez no podrá acceder hasta que             ║
║       se levante la cuarentena manualmente."            ║
║                                                         ║
║  2.  Bloquear IP externa                    [REVERSIBLE] ║
║      185.220.101.47                                     ║
║      "La IP del servidor C2 detectado será              ║
║       bloqueada en el firewall perimetral."             ║
║                                                         ║
║  3.  Notificar responsable de Ventas       ────────────  ║
║      gerencia.ventas@empresa.com                        ║
╠══════════════════════════════════════════════════════════╣
║  JUSTIFICACIÓN                                          ║
║  "Este dispositivo mostró 12 consultas de beaconing     ║
║   a un C2 conocido, activó el honeypot de red, y        ║
║   generó tráfico saliente 8x por encima del baseline." ║
╠══════════════════════════════════════════════════════════╣
║                                                         ║
║  [ APROBAR TODAS LAS ACCIONES ]  [ RECHAZAR ]           ║
║                                  + campo para motivo    ║
║                                                         ║
╚══════════════════════════════════════════════════════════╝
```

BOTÓN APROBAR:
Es el único botón de acción primaria de todo el sistema que tiene
un estado de confirmación de dos pasos:
1. Click en "Aprobar todas las acciones" → el botón cambia a:
   "¿Confirmar ejecución? [ SÍ, EJECUTAR ] [ Cancelar ]"
2. El usuario debe hacer click en "SÍ, EJECUTAR" para confirmar.

Esto NO es una fricción innecesaria. Es intencional: las acciones
tienen consecuencias reales y el doble-click previene errores.

El botón "SÍ, EJECUTAR" es deliberadamente más pequeño y menos prominente
que el de rechazo. Estamos en el territorio de "Make it easy to do the right thing."

COLOR DEL BOTÓN APROBAR:
No verde (verde = "sin riesgo"). No rojo (rojo = "peligro").
Es un botón de --cyan-base con --cyan-dim como fondo.
El cyan dice "acción técnica deliberada", no "adelante sin pensar".

LISTA DE PROPOSALS RESUELTOS:
Debajo del proposal activo, una lista compacta de proposals anteriores:
```
✓ Aprobado  |  hace 2 días  |  Cuarentena PC-CONT-03        [ Ver ]
✗ Rechazado |  hace 5 días  |  Bloquear IP 45.33.32.156     [ Ver ]
✓ Aprobado  |  hace 1 sem   |  Deshabilitar usuario hr_test  [ Ver ]
```

REGLAS:
- El campo de motivo de rechazo es obligatorio. No se puede rechazar sin texto.
- Después de aprobar o rechazar: animación de fadeOut del proposal
  y aparece el siguiente (si hay) o el EmptyState.
- Si el sistema ejecutó la acción exitosamente: mostrar confirmación inline
  con los resultados de cada playbook.

NO HAGAS:
- No hagas que el botón de aprobar sea prominentemente verde.
  Verde en esta interfaz significa "limpio/seguro", no "go".
- No permitas aprobar actions sin leer la justificación (scroll tracking no,
  pero al menos 3 segundos de tiempo en la página antes de habilitar el botón).
- No uses un modal para la confirmación. El cambio in-place en el botón
  es más claro y menos disruptivo.
```

---

## F17 — Estados Vacíos y Carga

### PROMPT F17 — Empty States, Skeletons & Errors
**Rol:** ⚛️ Frontend Developer  
**Entregable:** `dashboard/src/components/states/`

```
Sos un Frontend Developer especializado en micro-estados de interfaz.

Los estados vacíos, de carga y de error son la diferencia entre una app
que "se ve rota" y una que comunica con precisión en todo momento.

ARCHIVO 1: LoadingView.jsx
El loading inicial de la aplicación (mientras se conecta el WebSocket
y carga el estado inicial).

NO es un spinner genérico. Es:
```
                    ⬡
              NYXAR
          Estableciendo conexión...
```
Centrado vertical y horizontal.
El ⬡ tiene una animación muy sutil: scale 1.0 → 1.05 → 1.0, 2s, infinito.
El texto "Estableciendo conexión..." tiene un cursor parpadeante al final.
En --font-data para el texto técnico.

ARCHIVO 2: Skeleton de EventCard
Cuando el timeline está cargando los primeros eventos históricos:
Mostrar 8 EventCard.Skeleton con el shape correcto:
- Una línea corta (tipo de fuente) + una más larga (usuario)
- Una línea larga (el valor del evento)
- Una línea corta (el badge de riesgo)
Todo con el shimmer de Skeleton.jsx.

ARCHIVO 3: ErrorBoundary.jsx
Si un componente crashea (React Error Boundary):

```
┌──────────────────────────────────┐
│  ⊘  Componente no disponible    │
│                                  │
│  Este panel encontró un error    │
│  inesperado y fue deshabilitado. │
│  El resto del sistema sigue      │
│  funcionando normalmente.        │
│                                  │
│  [ Reintentar ]                  │
└──────────────────────────────────┘
```

Fondo --base-surface, borde --base-border-strong.
El mensaje es técnicamente honesto pero no alarmante.
El botón "Reintentar" hace un reset del Error Boundary.

ARCHIVO 4: EmptyStates predefinidos

NetworkMap sin nodos:
```
◉
No hay dispositivos detectados

El sistema está esperando los primeros
eventos de la red. Verificá que el
collector esté corriendo.
```

Timeline sin eventos:
```
≡
No hay eventos en el período seleccionado

Probá ampliando el filtro de severidad
o el rango de tiempo.
```

Identidades sin actividad:
```
◎
Sin actividad reciente

No hay identidades con eventos
en las últimas 24 horas.
```

Hunting sin hipótesis:
```
◈
Listo para investigar

No hay hipótesis activas.
El próximo análisis automático
es a las 06:00 AM.
[ + Nueva hipótesis manual ]
```

REGLAS:
- Los íconos de los empty states son caracteres Unicode en 48px, --base-muted.
- El título del empty state es --base-soft, 16px.
- La descripción es --base-muted, 13px.
- El botón de acción (si hay) es minimal: solo texto con borde fino.
- Los skeleton loaders se muestran solo cuando la carga tarda > 200ms.
  Usar un delay en el CSS para no hacer flash de skeleton en cargas rápidas:
  animation-delay: 200ms + opacity 0 → 1.

NO HAGAS:
- No uses ilustraciones (SVGs decorativos) en los empty states.
  Son genéricos, lentos de cargar, y no casan con la estética técnica.
- No uses "Oops!" ni exclamaciones en los mensajes de error.
  El tono es técnico y directo.
- No hagas que el loading inicial tarde más de lo necesario.
  Si el WebSocket conecta en 200ms, el usuario no debería ver el loading.
```

---

## F18 — Performance y Accesibilidad

### PROMPT F18 — Performance & Accessibility
**Rol:** ⚛️ Frontend Developer + Performance Engineer  
**Entregable:** Checklist implementado + configuración de Vite

```
Sos un Frontend Developer especializado en performance de React
y accesibilidad en interfaces de datos complejas.

PERFORMANCE — REGLAS NO NEGOCIABLES:

1. VIRTUALIZACIÓN
   - Timeline: react-window FixedSizeList obligatorio
   - Identities: react-window FixedSizeList obligatorio
   - Hunting results: react-window si > 50 resultados
   - Sin virtualización = sin aprobación del código

2. MEMOIZACIÓN
   Todos los componentes que reciben arrays u objetos como props
   deben estar envueltos en React.memo.
   Las funciones en props deben usar useCallback.
   Los cálculos costosos deben usar useMemo.
   
   Candidatos obligatorios de memo:
   - EventCard (renderizado miles de veces)
   - IdentityRow (renderizado 50-200 veces)
   - NetworkMap (D3 + canvas, muy costoso)
   - RiskSparkline (un por cada identidad)

3. WEBSOCKET — THROTTLING
   El WebSocket puede recibir 50+ eventos/segundo en picos.
   Implementar un buffer de 200ms:
   ```javascript
   // useWebSocket.js
   const buffer = useRef([])
   const flushTimer = useRef(null)
   
   socket.on('new_event', (event) => {
     buffer.current.push(event)
     if (!flushTimer.current) {
       flushTimer.current = setTimeout(() => {
         // Procesar todo el buffer de una vez
         addEvents(buffer.current)
         buffer.current = []
         flushTimer.current = null
       }, 200)
     }
   })
   ```
   Esto agrupa los updates de React y evita re-renders continuos.

4. LAZY LOADING DE VISTAS
   Todas las vistas usan React.lazy():
   ```javascript
   const NetworkMap = lazy(() => import('./views/NetworkMap'))
   const Hunting = lazy(() => import('./views/HuntingView'))
   ```
   El bundle inicial solo incluye AppShell + Timeline.
   El NetworkMap (D3.js pesado) se carga cuando el usuario navega a él.

5. D3 EN EL NetworkMap
   D3 corre en un Web Worker para no bloquear el main thread.
   El canvas principal recibe los datos calculados del worker.
   Si Web Workers no están disponibles: fallback a main thread con
   requestIdleCallback para los cálculos de layout.

6. IMÁGENES Y FUENTES
   - Sin imágenes en la UI (caracteres Unicode como íconos)
   - Las fuentes se cargan con font-display: swap
   - Critical CSS inline en el index.html para evitar FOUC

CONFIGURACIÓN: dashboard/vite.config.js
```javascript
export default {
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'd3': ['d3'],           // chunk separado para D3 (pesado)
          'recharts': ['recharts'], // chunk separado para Recharts
          'motion': ['framer-motion'], // chunk separado
        }
      }
    },
    chunkSizeWarningLimit: 400,
  },
  optimizeDeps: {
    include: ['d3', 'recharts', 'framer-motion']
  }
}
```

ACCESIBILIDAD — REGLAS:

1. KEYBOARD NAVIGATION
   Toda la app es operable con teclado:
   - Tab: navega entre elementos interactivos
   - Enter/Space: activa botones y links
   - Escape: cierra el detail panel
   - Arrow keys: navega dentro de listas (usando aria-activedescendant)

2. SCREEN READERS
   - Los DataChips de IPs tienen aria-label="IP: 192.168.1.45"
   - Los RiskGauge tienen aria-label="Riesgo: 67 de 100, ALTO"
   - Los badges de status tienen role="status"
   - Las alertas críticas nuevas tienen aria-live="assertive"
   - Los events del timeline tienen role="feed" y aria-label descriptivo

3. COLOR NO ES EL ÚNICO INDICADOR
   Los estados críticos tienen:
   - Color (rojo) Y
   - Ícono (⊘) Y
   - Texto ("CRÍTICO")
   Nunca solo color.

4. REDUCCIÓN DE MOVIMIENTO
   El archivo motion.css ya incluye @media (prefers-reduced-motion: reduce).
   Verificar que todas las animaciones usen var(--duration-*) para que
   el media query las afecte.

5. CONTRASTE MÍNIMO
   Verificar con herramienta:
   - Texto principal sobre fondo: ratio >= 7:1 (WCAG AAA)
   - Texto secundario sobre fondo: ratio >= 4.5:1 (WCAG AA)
   - Texto de badge sobre fondo de badge: ratio >= 4.5:1

BUNDLE SIZE TARGETS:
- JavaScript inicial (sin lazy chunks): < 150KB gzipped
- CSS total: < 30KB gzipped
- D3 chunk (lazy): < 80KB gzipped
- Recharts chunk (lazy): < 60KB gzipped
- Total de la app: < 400KB gzipped

PERFORMANCE METRICS TARGETS:
- First Contentful Paint: < 800ms
- Time to Interactive: < 2s
- Layout Shift: CLS < 0.05 (usar font-size fijo y tabular-nums para evitar shifts)
- Frame rate durante animaciones: > 55fps (no 60, sé realista)

NO HAGAS:
- No instales moment.js. Usar date-fns o Intl.RelativeTimeFormat nativo.
- No uses lodash completo. Solo las funciones específicas que necesites.
- No uses index.jsx como punto de importación para componentes individuales.
  Importar siempre el archivo directo para permitir tree-shaking.
- No pongas estilos globales en archivos de componentes.
  Solo en tokens.css y typography.css.
```

---

## 📌 Guía de implementación del sistema de diseño

### Orden de implementación

```
1. tokens.css           → foundation, todo depende de esto
2. typography.css       → segundo, los componentes lo necesitan
3. colors.js            → helpers de color
4. motion.css           → animations
5. AppShell.jsx         → estructura antes que contenido
6. Sidebar.jsx          → navegación
7. Componentes atómicos → los bloques (Badge, DataChip, etc.)
8. Componentes de datos → EventCard, IdentityRow, etc.
9. Visualizaciones      → charts
10. Vistas              → una a la vez, en orden de prioridad:
    Timeline → Identities → NetworkMap → CEO → Health → Response → Hunting
11. Empty states        → al final, cuando tenés todos los shapes
12. Performance         → último, cuando la funcionalidad está completa
```

### Lo que hace que esto se vea de "próxima generación"

No es ningún efecto especial. Es la combinación de:

1. **Geist/IBM Plex** sobre fondos muy oscuros (no negro puro) →
   el contraste preciso sin ser agresivo

2. **Cyan operacional muy usado con moderación** →
   cuando aparece, tiene peso. Si está en todo, no significa nada.

3. **Monospace para todo lo técnico** →
   la distinción visual inmediata entre "UI text" y "data text"

4. **Números tabulares** →
   el dashboard no "salta" cuando los datos cambian

5. **Sin borders radius grandes** →
   las interfaces técnicas son más angulares. El redondeo excesivo es decorativo.

6. **Densidad controlada** →
   mucha información pero con jerarquía visual estricta

7. **Animaciones de 150-250ms con ease-out** →
   el sistema "responde". No hay lag, no hay exageración.

---

*NYXAR — PROMPTS_V3.md — Sistema de Diseño Frontend — v1.0 — 2026*
