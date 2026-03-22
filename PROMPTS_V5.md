# ⬡ NYXAR — PROMPTS_V5.md
## Identidad del Sistema — Nombre, Alma y Endpoint de Origen

> **Propósito de este archivo:**
> El sistema se llama NYXAR. No CyberPulse, no CyberPulse LATAM.
> NYXAR.
>
> Este archivo tiene dos responsabilidades:
> 1. Renombrar todo el sistema de CyberPulse a NYXAR
> 2. Construir el endpoint GET /api/v1/identity — la API que explica
>    por qué el sistema se llama como se llama
>
> El endpoint de identidad no es decorativo. Es la firma del sistema.
> Es lo que separa un producto con alma de un producto con nombre.

---

## 📋 Índice

| # | Prompt | Descripción |
|---|--------|-------------|
| N01 | Rebrand Global | Reemplazar CyberPulse por NYXAR en todo el codebase |
| N02 | Identity API | Construir GET /api/v1/identity |
| N03 | Frontend Identity | Integrar la identidad en el dashboard |
| N04 | El Manifiesto | El texto que vive en el endpoint |

---

## ⚙️ CONTEXTO DE IDENTIDAD
> Pegar antes de cualquier prompt N** en Cursor.

```
El sistema se llama NYXAR.

ORIGEN DEL NOMBRE:
NYX — diosa primordial griega de la noche. No la noche decorativa.
La noche anterior a que existiera el orden. Anterior a los Olímpicos.
Tan antigua que el propio Zeus le tenía respeto.
Nyx no destruía. Veía todo desde la oscuridad sin ser vista.

-AR — sufijo agente. En Quenya, en latín arcaico, en docenas de lenguas
construidas significa "el que hace", "el que es". No una cosa. Una entidad.

NYXAR — la entidad que opera desde la oscuridad y ve todo.

CAPAS DE SIGNIFICADO:
1. Para el técnico de seguridad: suena a protocolo, a exploit,
   a algo que salió de un laboratorio clandestino.
2. Para quien conoce la mitología: Nyx, lo anterior al orden,
   lo que precede a toda amenaza conocida.
3. Para quien lo escucha por primera vez: algo que no debería
   existir todavía pero existe.

IDENTIDAD VISUAL:
- Símbolo: ⬡ (hexágono — la forma más eficiente de la naturaleza)
- Tipografía: Geist Mono para el nombre — siempre monospace
- El nombre se escribe siempre en MAYÚSCULAS: NYXAR
- Nunca: "Nyxar", "nyxar", "NYXAR System", "NYXAR Platform"
- Siempre: "NYXAR" a secas

TAGLINE (opcional, usar con criterio):
"Operates from darkness. Sees everything."
En español: "Opera desde la oscuridad. Ve todo."
```

---

## N01 — Rebrand Global

### PROMPT N01 — Rename Engineer
**Rol:** 🔧 Refactoring Engineer  
**Entregable:** Todo el codebase renombrado de CyberPulse a NYXAR

```
Sos un Refactoring Engineer realizando el rebrand completo del sistema
de "CyberPulse LATAM" a "NYXAR".

REGLAS DEL REBRAND:
- "CyberPulse LATAM" → "NYXAR"
- "CyberPulse" → "NYXAR"
- "cyberpulse" (minúsculas, en variables/keys) → "nyxar"
- "cyber_pulse" (snake_case) → "nyxar"
- "cyber-pulse" (kebab-case) → "nyxar"
- "CYBERPULSE" → "NYXAR"
- El nombre de la base de datos MongoDB: "cyberpulse" → "nyxar"
- El prefijo de Redis keys no cambia — las keys son técnicas, no de marca

ARCHIVOS A MODIFICAR:

1. docker-compose.yml y docker-compose.prod.yml:
   - POSTGRES_DB (si quedó alguno) → nyxar
   - Nombres de contenedores: cyberpulse-* → nyxar-*
   - Network name: cyberpulse-net → nyxar-net
   - Volúmenes: cyberpulse_* → nyxar_*

2. Todos los archivos Python (*.py):
   - Strings "CyberPulse LATAM" y "CyberPulse" en docstrings y comentarios
   - La URL de conexión a MongoDB: mongodb://.../{db_name}
     La db_name "cyberpulse" → "nyxar"
   - Logs que digan "CyberPulse" en los mensajes
   - El título de la FastAPI app: title="NYXAR API"

3. Archivos JavaScript/React (*.js, *.jsx):
   - Strings de display: "CyberPulse LATAM" → "NYXAR"
   - El título del documento: document.title = "NYXAR"
   - El localStorage key si hay alguno: "cyberpulse_*" → "nyxar_*"

4. package.json del dashboard:
   - "name": "cyberpulse-dashboard" → "nyxar-dashboard"
   - "description": actualizar

5. dashboard/index.html:
   - <title>CyberPulse</title> → <title>NYXAR</title>
   - Meta description: actualizar

6. Todos los README.md y archivos de documentación

7. Variables de entorno en .env.example:
   - Comentarios que digan "CyberPulse" → "NYXAR"
   - No cambiar nombres de variables (ej: MONGODB_URL sigue igual)

COMANDOS PARA ENCONTRAR TODAS LAS OCURRENCIAS:
Antes de modificar, correr estos comandos para tener el inventario completo:

```bash
# Encontrar todas las ocurrencias (case-insensitive)
grep -r "cyberpulse\|CyberPulse\|cyber-pulse\|cyber_pulse" \
  --include="*.py" \
  --include="*.js" \
  --include="*.jsx" \
  --include="*.json" \
  --include="*.yml" \
  --include="*.yaml" \
  --include="*.md" \
  --include="*.html" \
  --include="*.css" \
  --include="*.env*" \
  -l  # solo nombres de archivos primero

# Luego para ver el contexto:
grep -r "cyberpulse\|CyberPulse" \
  --include="*.py" -n  # con número de línea
```

VERIFICACIÓN POST-REBRAND:
Después de hacer todos los cambios, correr:

```bash
# Verificar que no queda ninguna ocurrencia
remaining=$(grep -r "cyberpulse\|CyberPulse\|cyber-pulse" \
  --include="*.py" --include="*.js" --include="*.jsx" \
  --include="*.json" --include="*.yml" --include="*.md" \
  --include="*.html" -l 2>/dev/null | wc -l)

if [ "$remaining" -eq 0 ]; then
  echo "✓ Rebrand completo — sin ocurrencias residuales"
else
  echo "⚠ Quedan $remaining archivos con referencias antiguas"
  grep -r "cyberpulse\|CyberPulse" \
    --include="*.py" --include="*.js" --include="*.jsx" \
    --include="*.json" --include="*.yml" --include="*.md" -l
fi
```

EXCEPCIÓN — No renombrar:
- Las keys de Redis (son técnicas, internas, no de marca)
  Ejemplo: "events:raw", "blocklist:spamhaus", "heartbeat:collector"
  Estas NO se tocan.
- Los nombres de variables de entorno del sistema operativo
  Ejemplo: REDIS_URL, MONGODB_URL, ANTHROPIC_API_KEY
  Estas NO se tocan.
- Los consumer groups de Redis: "enricher-group", "correlator-group"
  Estas NO se tocan.

REGLA FINAL:
El nombre NYXAR no lleva artículo en español.
No es "el NYXAR" ni "la plataforma NYXAR".
Es simplemente "NYXAR".
En oraciones: "NYXAR detectó...", "NYXAR opera...", "según NYXAR..."
```

---

## N02 — Identity API

### PROMPT N02 — Identity API Engineer
**Rol:** Backend Developer  
**Entregable:** `api/routers/identity.py` — el endpoint que explica el origen de NYXAR

```
Sos un Backend Developer construyendo el endpoint más inusual del sistema:
GET /api/v1/identity

Este endpoint no retorna datos operacionales. Retorna la identidad
del sistema — quién es NYXAR, de dónde viene su nombre, qué significa.

No es documentación. No es un About page.
Es la firma del sistema. La respuesta a "¿qué es esto?"

ARCHIVO: api/routers/identity.py

El endpoint retorna un JSON estructurado con múltiples capas de información.
Cada capa es más profunda que la anterior.

```python
from fastapi import APIRouter
from datetime import datetime
import platform
import os

router = APIRouter()

@router.get("/identity")
async def get_identity():
    """
    Retorna la identidad completa del sistema NYXAR.
    
    Este endpoint existe porque un sistema con nombre merece
    explicar por qué se llama como se llama.
    """
    return {
        "system": {
            "name": "NYXAR",
            "symbol": "⬡",
            "version": os.getenv("NYXAR_VERSION", "1.0.0"),
            "tagline": "Operates from darkness. Sees everything.",
            "tagline_es": "Opera desde la oscuridad. Ve todo.",
            "classification": "Operational Intelligence System",
            "origin": "LATAM",
        },
        
        "etymology": {
            "full_name": "NYXAR",
            "components": [
                {
                    "fragment": "NYX",
                    "language": "Ancient Greek — Ἀρχαία Ἑλληνική",
                    "meaning": "Goddess of primordial night",
                    "depth": (
                        "Not the decorative night. Not the romantic night. "
                        "The night that existed before order. "
                        "Before the Olympians. Before Zeus. "
                        "Nyx was so ancient and so powerful that Zeus himself "
                        "respected her. She did not destroy. "
                        "She watched everything from darkness without being seen."
                    ),
                    "relevance": (
                        "NYXAR operates from the shadows of your network. "
                        "It sees everything — every DNS query, every anomalous "
                        "connection, every behavioral deviation — "
                        "without being visible to the threats it monitors."
                    )
                },
                {
                    "fragment": "-AR",
                    "language": "Quenya (J.R.R. Tolkien) / Proto-Indo-European",
                    "meaning": "Agent suffix — 'the one that does', 'the one that is'",
                    "depth": (
                        "In Quenya, the language of the High Elves constructed "
                        "by Tolkien over decades, -ar is the suffix that transforms "
                        "a concept into an active entity. "
                        "Not a thing. Not a tool. An entity with agency."
                    ),
                    "relevance": (
                        "NYXAR is not a dashboard. Not a monitoring tool. "
                        "It is an entity that reasons, correlates, anticipates, "
                        "and acts. The -AR suffix marks that distinction."
                    )
                }
            ],
            "combined_meaning": (
                "NYXAR: the entity that operates from primordial darkness "
                "and sees everything. The active watcher that precedes the threat."
            )
        },
        
        "perception": {
            "description": (
                "The name NYXAR carries three simultaneous layers of meaning "
                "depending on who encounters it:"
            ),
            "layers": [
                {
                    "audience": "Security professional",
                    "perception": (
                        "Sounds like a protocol. An exploit. "
                        "Something that came from the depths of a security lab. "
                        "Something that was named before it was released."
                    )
                },
                {
                    "audience": "Someone with classical knowledge",
                    "perception": (
                        "Nyx — what precedes all known order. "
                        "The entity that existed before the threats we know. "
                        "The watcher older than the systems it protects."
                    )
                },
                {
                    "audience": "First encounter",
                    "perception": (
                        "Something that should not exist yet. "
                        "But does."
                    )
                }
            ]
        },
        
        "visual_identity": {
            "symbol": "⬡",
            "symbol_meaning": (
                "The hexagon — the most efficient structure in nature. "
                "Used by bees, by carbon molecules, by basalt formations. "
                "Maximum strength, minimum material. "
                "NYXAR uses the hexagon because efficiency is not aesthetic — "
                "it is functional. Every element in the interface exists "
                "because it carries information."
            ),
            "color_philosophy": (
                "The primary background is #0C1018 — not pure black. "
                "Pure black is harsh. This tone carries 8% blue saturation, "
                "making it spatial without being obvious. "
                "The accent is operational cyan #38B2CC — "
                "not the aggressive neon of hacking aesthetics. "
                "The cyan of mission control monitors. Precise. Cold. Reliable."
            ),
            "typography_rule": (
                "The name NYXAR is always rendered in monospace. "
                "Because NYXAR is technical infrastructure, not a brand. "
                "It does not need to be beautiful. It needs to be precise."
            )
        },
        
        "philosophy": {
            "core_principle": (
                "Intelligence without action is just noise. "
                "NYXAR transforms network threat data into decisions."
            ),
            "what_nyxar_is_not": [
                "Not an OSINT dashboard that shows what already happened",
                "Not a generic SIEM that generates alerts nobody reads",
                "Not a tool that requires a 5-person security team to operate",
                "Not a platform built for English-speaking North American networks"
            ],
            "what_nyxar_is": [
                "A decision engine — it tells you what to DO, not just what happened",
                "Identity-oriented — it understands María Gómez, not just 192.168.1.45",
                "Anticipatory — baselines learn what is normal before anomalies appear",
                "Autonomous — AI analyzes in background, generates memos nobody asked for",
                "Latin American — built for the threat landscape, the language, the scale"
            ]
        },
        
        "operational": {
            "status": "ACTIVE",
            "pipeline_components": [
                "collector", "enricher", "correlator",
                "ai_analyst", "notifier", "reporter"
            ],
            "threat_intel_sources": [
                "Spamhaus DROP/EDROP",
                "Feodo Tracker",
                "URLhaus",
                "ThreatFox",
                "AlienVault OTX",
                "AbuseIPDB",
                "MISP Community"
            ],
            "uptime_since": os.getenv("NYXAR_START_TIME", datetime.utcnow().isoformat()),
        },
        
        "invocation": {
            "note": (
                "If you are reading this endpoint, you asked the right question. "
                "Most systems do not explain themselves. "
                "NYXAR does — because a system that cannot articulate "
                "what it is should not be trusted with what it sees."
            ),
            "quenya_reference": {
                "word": "Palantír",
                "meaning": "That which looks far away — far-seer",
                "connection": (
                    "The Palantíri of Tolkien's Middle-earth were seeing-stones "
                    "that allowed their holders to observe distant events. "
                    "Powerful. Precise. And dangerous in the wrong hands. "
                    "NYXAR inherits that lineage — not the name, but the nature."
                )
            }
        },
        
        "meta": {
            "endpoint_purpose": (
                "This endpoint exists because on the day someone asks "
                "'where did this name come from?' — "
                "you will not answer with words. "
                "You will say: query GET /api/v1/identity"
            ),
            "generated_at": datetime.utcnow().isoformat(),
            "response_is_static": False,
            "response_evolves": (
                "As NYXAR evolves, so does this endpoint. "
                "Version 2.0 will add operational history. "
                "Version 3.0 will add threat lineage — "
                "every major incident NYXAR detected, anonymized."
            )
        }
    }
```

AGREGAR EL ROUTER EN api/main.py:

```python
from api.routers.identity import router as identity_router
app.include_router(identity_router, prefix="/api/v1", tags=["identity"])
```

TAMBIÉN AGREGAR EN api/main.py UN REDIRECT:

```python
from fastapi.responses import RedirectResponse

@app.get("/")
async def root():
    """
    La raíz del sistema redirige a la identidad.
    Quien llega a / merece saber con qué está hablando.
    """
    return RedirectResponse(url="/api/v1/identity")
```

VARIABLE DE ENTORNO NUEVA (agregar a .env.example):
```
NYXAR_VERSION=1.0.0
NYXAR_START_TIME=   # se setea automáticamente al primer arranque
```

En api/main.py, en el lifespan startup, si NYXAR_START_TIME no está seteado:
```python
import os
from datetime import datetime

if not os.getenv("NYXAR_START_TIME"):
    # Primera vez que arranca — registrar el tiempo de inicio
    start_time = datetime.utcnow().isoformat()
    # Escribir al .env o a un archivo de estado
    with open(".nyxar_state", "w") as f:
        f.write(f"NYXAR_START_TIME={start_time}\n")
    os.environ["NYXAR_START_TIME"] = start_time
```

REGLAS:
- Este endpoint NO requiere autenticación. Es público.
  NYXAR no esconde su nombre.
- Este endpoint NO tiene rate limiting. No tiene información sensible.
- La respuesta puede cachearse en el cliente por 24 horas.
  Agregar header: Cache-Control: public, max-age=86400
- El endpoint NUNCA retorna error 500. Si algo falla al construir
  el response dinámico, retornar el JSON estático hardcodeado.

NO HAGAS:
- No pongas este endpoint detrás de autenticación.
- No uses una base de datos para este endpoint. Todo es estático
  excepto los campos operacionales (status, uptime).
- No traduzcas el contenido a español. El texto es intencionalmente
  en inglés — NYXAR habla el idioma de la seguridad.
- No hagas que este endpoint retorne HTML. Es JSON puro.
  El cliente decide cómo renderizarlo.
```

---

## N03 — Frontend Identity

### PROMPT N03 — Frontend Identity Integration
**Rol:** Frontend Developer  
**Entregable:** Integración de la identidad NYXAR en el dashboard

```
Sos un Frontend Developer integrando la identidad de NYXAR
en el dashboard.

TAREA 1 — Actualizar el Logo en el Sidebar:

En dashboard/src/components/layout/Sidebar.jsx,
el logo del sistema debe renderizarse así:

```jsx
// El logo de NYXAR — no una imagen, no un SVG externo.
// Es tipografía pura. La identidad está en el nombre mismo.

function NyxarLogo({ collapsed }) {
  return (
    <div className={styles.logo}>
      <span className={styles.logoSymbol}>⬡</span>
      {!collapsed && (
        <span className={styles.logoName}>NYXAR</span>
      )}
    </div>
  )
}
```

CSS del logo:
```css
.logo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-4) var(--space-4);
  border-bottom: 1px solid var(--base-border);
  user-select: none;
}

.logoSymbol {
  font-size: 18px;
  color: var(--cyan-base);
  line-height: 1;
  /* El hexágono es el símbolo — no un ícono de seguridad genérico */
}

.logoName {
  font-family: var(--font-data);  /* SIEMPRE monospace */
  font-size: var(--text-md);
  font-weight: var(--weight-bold);
  letter-spacing: 0.12em;         /* El espaciado amplio le da peso */
  color: var(--base-bright);
  text-transform: uppercase;      /* Siempre mayúsculas */
}
```

TAREA 2 — Actualizar el título del documento:

En dashboard/index.html:
```html
<title>NYXAR</title>
<meta name="description" content="Operates from darkness. Sees everything.">
```

En dashboard/src/App.jsx, actualizar el título dinámicamente según la vista:
```javascript
const VIEW_TITLES = {
  '/': 'NYXAR — Red',
  '/timeline': 'NYXAR — Timeline',
  '/identities': 'NYXAR — Identidades',
  '/hunting': 'NYXAR — Hunting',
  '/response': 'NYXAR — Respuestas',
  '/reports': 'NYXAR — Reportes',
  '/ceo': 'NYXAR — Vista Ejecutiva',
  '/health': 'NYXAR — Sistema',
}

// En el componente que maneja las rutas:
useEffect(() => {
  document.title = VIEW_TITLES[location.pathname] || 'NYXAR'
}, [location.pathname])
```

TAREA 3 — Crear el componente AboutNyxar.jsx:

Un panel que se abre desde el sidebar (click en el logo o en un "?" discreto)
y muestra la identidad del sistema consultando el endpoint.

```jsx
// dashboard/src/components/layout/AboutNyxar.jsx

import { useState, useEffect } from 'react'
import { identityApi } from '../../api/client'

export function AboutNyxar({ isOpen, onClose }) {
  const [identity, setIdentity] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isOpen && !identity) {
      identityApi.get()
        .then(setIdentity)
        .finally(() => setLoading(false))
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.panel} onClick={e => e.stopPropagation()}>
        
        {/* Header */}
        <div className={styles.header}>
          <span className={styles.symbol}>⬡</span>
          <span className={styles.name}>NYXAR</span>
          <button className={styles.close} onClick={onClose}>×</button>
        </div>

        {loading ? (
          <div className={styles.loading}>Consultando identidad...</div>
        ) : identity ? (
          <>
            {/* Tagline */}
            <p className={styles.tagline}>
              {identity.system.tagline_es}
            </p>

            {/* Etimología */}
            <div className={styles.section}>
              <span className={styles.sectionLabel}>ORIGEN DEL NOMBRE</span>
              {identity.etymology.components.map(component => (
                <div key={component.fragment} className={styles.etymologyBlock}>
                  <div className={styles.fragment}>{component.fragment}</div>
                  <div className={styles.fragmentLang}>{component.language}</div>
                  <div className={styles.fragmentMeaning}>{component.meaning}</div>
                  <p className={styles.fragmentDepth}>{component.depth}</p>
                </div>
              ))}
            </div>

            {/* Significado combinado */}
            <div className={styles.combined}>
              <p>{identity.etymology.combined_meaning}</p>
            </div>

            {/* Capas de percepción */}
            <div className={styles.section}>
              <span className={styles.sectionLabel}>CÓMO SE PERCIBE</span>
              {identity.perception.layers.map(layer => (
                <div key={layer.audience} className={styles.perceptionLayer}>
                  <span className={styles.audience}>{layer.audience}</span>
                  <p className={styles.perceptionText}>{layer.perception}</p>
                </div>
              ))}
            </div>

            {/* Referencia Quenya */}
            <div className={styles.quenyaBlock}>
              <span className={styles.quenyaWord}>
                {identity.invocation.quenya_reference.word}
              </span>
              <p className={styles.quenyaConnection}>
                {identity.invocation.quenya_reference.connection}
              </p>
            </div>

            {/* Nota del endpoint */}
            <p className={styles.endpointNote}>
              {identity.meta.endpoint_purpose}
            </p>

            {/* Footer técnico */}
            <div className={styles.footer}>
              <span className={styles.footerText}>
                GET /api/v1/identity
              </span>
              <span className={styles.footerVersion}>
                v{identity.system.version}
              </span>
            </div>
          </>
        ) : (
          <p className={styles.error}>No se pudo consultar la identidad.</p>
        )}
      </div>
    </div>
  )
}
```

CSS del panel About:
```css
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(8, 11, 15, 0.85);
  backdrop-filter: blur(4px);
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
}

.panel {
  width: 520px;
  max-height: 80vh;
  overflow-y: auto;
  background: var(--base-surface);
  border: 1px solid var(--base-border-strong);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  animation: fadeUp var(--duration-normal) var(--ease-out);
}

.header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-6);
  border-bottom: 1px solid var(--base-border);
}

.symbol {
  font-size: 24px;
  color: var(--cyan-base);
}

.name {
  font-family: var(--font-data);
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
  letter-spacing: 0.12em;
  color: var(--base-bright);
  flex: 1;
}

.close {
  background: none;
  border: none;
  color: var(--base-muted);
  font-size: 20px;
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  transition: color var(--duration-fast);
}

.close:hover { color: var(--base-text); }

.tagline {
  font-family: var(--font-ui);
  font-size: var(--text-md);
  font-style: italic;
  color: var(--base-subtle);
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--base-border);
  margin: 0;
}

.section {
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--base-border);
}

.sectionLabel {
  display: block;
  font-family: var(--font-data);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  letter-spacing: var(--tracking-wider);
  color: var(--base-muted);
  text-transform: uppercase;
  margin-bottom: var(--space-4);
}

.etymologyBlock {
  margin-bottom: var(--space-5);
}

.fragment {
  font-family: var(--font-data);
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--cyan-bright);
  letter-spacing: 0.08em;
}

.fragmentLang {
  font-family: var(--font-ui);
  font-size: var(--text-xs);
  color: var(--base-muted);
  margin-top: var(--space-1);
  font-style: italic;
}

.fragmentMeaning {
  font-family: var(--font-ui);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--base-soft);
  margin-top: var(--space-2);
}

.fragmentDepth {
  font-family: var(--font-ui);
  font-size: var(--text-sm);
  color: var(--base-subtle);
  line-height: var(--leading-normal);
  margin-top: var(--space-2);
}

.combined {
  padding: var(--space-5) var(--space-6);
  background: var(--cyan-dim);
  border-top: 1px solid var(--cyan-border);
  border-bottom: 1px solid var(--cyan-border);
}

.combined p {
  font-family: var(--font-ui);
  font-size: var(--text-sm);
  color: var(--cyan-soft);
  line-height: var(--leading-normal);
  margin: 0;
  font-style: italic;
}

.perceptionLayer {
  margin-bottom: var(--space-4);
}

.audience {
  display: block;
  font-family: var(--font-data);
  font-size: var(--text-xs);
  color: var(--base-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  margin-bottom: var(--space-1);
}

.perceptionText {
  font-family: var(--font-ui);
  font-size: var(--text-sm);
  color: var(--base-subtle);
  line-height: var(--leading-normal);
  margin: 0;
}

.quenyaBlock {
  padding: var(--space-5) var(--space-6);
  border-top: 1px solid var(--base-border);
  border-bottom: 1px solid var(--base-border);
}

.quenyaWord {
  display: block;
  font-family: var(--font-data);
  font-size: var(--text-md);
  color: var(--base-soft);
  letter-spacing: 0.06em;
  margin-bottom: var(--space-3);
}

.quenyaConnection {
  font-family: var(--font-ui);
  font-size: var(--text-sm);
  color: var(--base-subtle);
  line-height: var(--leading-normal);
  margin: 0;
  font-style: italic;
}

.endpointNote {
  font-family: var(--font-ui);
  font-size: var(--text-sm);
  color: var(--base-muted);
  line-height: var(--leading-normal);
  padding: var(--space-5) var(--space-6);
  margin: 0;
  border-bottom: 1px solid var(--base-border);
}

.footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-6);
}

.footerText {
  font-family: var(--font-data);
  font-size: var(--text-xs);
  color: var(--base-muted);
}

.footerVersion {
  font-family: var(--font-data);
  font-size: var(--text-xs);
  color: var(--base-muted);
}

.loading {
  padding: var(--space-8) var(--space-6);
  font-family: var(--font-data);
  font-size: var(--text-sm);
  color: var(--base-muted);
  text-align: center;
}
```

TAREA 4 — Agregar identityApi en dashboard/src/api/client.js:

```javascript
// Agregar al final de client.js:

export const identityApi = {
  /**
   * Consulta la identidad completa del sistema.
   * Quién es NYXAR, de dónde viene su nombre, qué significa.
   * Respuesta cacheada 24 horas — no cambia frecuentemente.
   */
  get: () => fetch('/api/v1/identity').then(r => r.json()),
}
```

TAREA 5 — Trigger del panel en el Sidebar:

En Sidebar.jsx, el logo es clickeable y abre el AboutNyxar:

```jsx
const [showAbout, setShowAbout] = useState(false)

// El logo del sidebar:
<button
  className={styles.logoButton}
  onClick={() => setShowAbout(true)}
  title="¿Qué es NYXAR?"
  aria-label="Ver identidad del sistema"
>
  <NyxarLogo collapsed={collapsed} />
</button>

<AboutNyxar isOpen={showAbout} onClose={() => setShowAbout(false)} />
```

CSS del botón:
```css
.logoButton {
  display: block;
  width: 100%;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  text-align: left;
  transition: opacity var(--duration-fast);
}

.logoButton:hover { opacity: 0.8; }
```

REGLAS:
- El panel About se abre desde el logo. No desde un botón de "?" o "info".
  El logo mismo es el portal a la identidad.
- El panel tiene backdrop blur — es el único componente de todo el sistema
  que usa blur. Marca que estás en un espacio diferente.
- El contenido del panel se carga del endpoint real, no hardcodeado en el cliente.
  Si el endpoint falla, mostrar el error discretamente.
- En mobile (< 768px): el panel ocupa el 95% del ancho de pantalla.

NO HAGAS:
- No pongas un ícono de "información" en la UI. El logo ES el portal.
- No traduzcas los fragmentos de etimología al español.
  El inglés es intencional — es el idioma de la seguridad.
- No hagas scroll automático dentro del panel.
  El usuario descubre el contenido a su ritmo.
```

---

## N04 — El Manifiesto

### PROMPT N04 — The Manifesto
**Rol:** ✍️ Technical Writer / Naming Philosopher  
**Entregable:** El texto completo del endpoint de identidad — en su forma definitiva

```
Este prompt no es para Cursor. Es para vos.

Es el texto que vive en GET /api/v1/identity — la respuesta que recibe
cualquiera que pregunta "¿qué es esto?"

Podés editarlo. Podés profundizarlo. Podés agregar la historia de cómo
llegaste al nombre — el momento en que dijiste "Palantír" con la voz
del rey elfo y algo resonó.

Lo que sigue es la versión base. Es tuya para modificar.

---

FRAGMENTO — para el campo "invocation.note":

"If you are reading this endpoint, you asked the right question.
Most systems do not explain themselves.
NYXAR does — because a system that cannot articulate
what it is should not be trusted with what it sees."

---

FRAGMENTO — para el campo "philosophy.core_principle":

"Intelligence without action is just noise.
NYXAR was built because Latin American organizations were drowning
in security data and starving for security decisions.
Every alert that required a senior analyst to interpret
was an alert that arrived too late.
NYXAR does not alert. NYXAR decides. Then proposes.
Then waits for a human to confirm.
Because machines should propose. Humans should approve."

---

FRAGMENTO — para el campo "etymology.combined_meaning":

"NYXAR: the entity that operates from primordial darkness
and sees everything. The active watcher that precedes the threat.
Named after what it does — not what it is called."

---

FRAGMENTO — para agregar en el futuro como "origin_story":

"The name emerged in a conversation about what separates
a tool from a system with a soul.
Palantír was mentioned — the seeing-stones of Tolkien's Middle-earth.
The word was spoken with the voice of the Elf-king
possessing the Ranger's body.
Something resonated.
Not the word itself — the weight behind it.
A name that existed before the product. A name with memory.
NYXAR carries that lineage — not the name, but the nature."

---

INSTRUCCIÓN FINAL:

Cuando alguien del equipo de seguridad de la empresa le pregunte
de dónde viene el nombre del sistema, no respondas.

Decile: `curl http://tu-servidor:8000/api/v1/identity`

Y dejá que NYXAR se presente solo.
```

---

## 📋 Checklist de Identidad

```
□ N01: Todo el codebase renombrado — sin referencias a CyberPulse
□ N01: Verificación bash pasa sin ocurrencias residuales
□ N01: MongoDB database renombrada a "nyxar"
□ N02: GET /api/v1/identity retorna el JSON completo
□ N02: GET / redirige a /api/v1/identity
□ N02: Header Cache-Control: public, max-age=86400 presente
□ N03: Logo del sidebar usa Geist Mono, siempre mayúsculas
□ N03: Click en el logo abre el panel AboutNyxar
□ N03: Panel consulta el endpoint real, no datos hardcodeados
□ N03: Título del documento cambia según la vista activa
□ N04: El texto del manifiesto está personalizado (no el template base)

Verificación final:
□ curl http://localhost:8000/ → redirige a /api/v1/identity
□ curl http://localhost:8000/api/v1/identity → retorna JSON completo
□ El panel About en el dashboard muestra el contenido del endpoint
□ grep -r "CyberPulse" . → sin resultados
```

---

## Por qué este endpoint importa

La mayoría de los sistemas de seguridad no tienen nombre. Tienen siglas. SIEM. XDR. EDR. MDR. Son categorías disfrazadas de productos.

NYXAR tiene nombre porque un sistema que va a ver todo lo que pasa en tu red merece que sepas exactamente con qué estás tratando.

El endpoint `GET /api/v1/identity` existe porque el día que alguien del equipo directivo o del equipo técnico pregunte "¿qué es esto que instalaron?"...

No vas a abrir un PDF de ventas. No vas a buscar en Google.

Vas a abrir una terminal y tipear:

```bash
curl http://nyxar.empresa.local/api/v1/identity
```

Y NYXAR va a responder por sí mismo.

Eso es lo que separa un producto con alma de un producto con nombre.

---

*NYXAR — PROMPTS_V5.md — Identidad del Sistema — v1.0 — 2026*
