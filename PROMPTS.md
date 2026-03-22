# 🧠 CyberPulse LATAM — Master Prompts para Cursor AI

# > **Cómo usar este archivo**
# > Cada prompt está diseñado para ser copiado y pegado directamente en un agente de Cursor.
# > Cada uno representa el trabajo de un rol especializado sobre un componente específico.
# > Seguí el orden de fases. No saltees pasos. Cada agente debe recibir **un solo prompt a la vez**.
# > Antes de pasar al siguiente prompt, verificá que el output del anterior esté aprobado.

---

## 📋 Índice de Prompts

| # | Rol | Componente | Fase |
|---|-----|-----------|------|
| 01 | Architect | Estructura base del repositorio | 1 |
| 02 | DevOps Engineer | docker-compose.yml completo | 1 |
| 03 | Backend Dev | Modelos de datos y esquema MongoDB | 1 |
| 04 | Backend Dev | Redis Bus — estructura de colas y caché | 1 |
| 05 | Backend Dev | Collector — normalizer.py | 1 |
| 06 | Backend Dev | Collector — parsers DNS | 1 |
| 07 | Backend Dev | Collector — parsers Proxy/Firewall/Wazuh | 1 |
| 08 | Simulator Dev | personas.json — definición de identidades sintéticas | 1 |
| 09 | Simulator Dev | generator.py — motor de tráfico sintético | 1 |
| 10 | Simulator Dev | attack_scenarios — todos los escenarios | 1 |
| 11 | Security Dev | Enricher — cache.py y feeds downloader | 2 |
| 12 | Security Dev | Enricher — blocklists locales (todos los feeds) | 2 |
| 13 | Security Dev | Enricher — APIs externas (AbuseIPDB, OTX, VT) | 2 |
| 14 | Security Dev | Correlator — baseline.py (UEBA) | 2 |
| 15 | Security Dev | Correlator — patrones de ataque | 2 |
| 16 | Security Dev | Correlator — risk_score.py | 2 |
| 17 | Security Dev | Honeypots — detección y alertas | 2 |
| 18 | Backend Dev | FastAPI — estructura y routers base | 3 |
| 19 | Backend Dev | FastAPI — WebSocket para tiempo real | 3 |
| 20 | UI/UX Designer | Sistema de diseño y componentes base React | 3 |
| 21 | Frontend Dev | Dashboard — NetworkMap.jsx | 3 |
| 22 | Frontend Dev | Dashboard — Timeline.jsx | 3 |
| 23 | Frontend Dev | Dashboard — Identities.jsx | 3 |
| 24 | Frontend Dev | Dashboard — AttackInjector.jsx (lab mode) | 3 |
| 25 | AI Engineer | ai_analyst — autonomous_analyst.py | 4 |
| 26 | AI Engineer | ai_analyst — incident_analyzer.py | 4 |
| 27 | AI Engineer | ai_analyst — ceo_translator.py | 4 |
| 28 | AI Engineer | Todos los prompts de Claude (prompts/) | 4 |
| 29 | Frontend Dev | Dashboard — CeoView.jsx y AiMemo.jsx | 4 |
| 30 | QA Engineer | Suite de tests — collector y enricher | 5 |
| 31 | QA Engineer | Suite de tests — correlator y patrones | 5 |
| 32 | QA Engineer | Suite de tests — API y WebSocket | 5 |
| 33 | Tester | Tester de escenarios de ataque end-to-end | 5 |
| 34 | DevOps Engineer | docker-compose.prod.yml y hardening | 6 |
| 35 | Tech Writer | README.md del proyecto completo | 6 |

---

## ⚙️ CONTEXTO GLOBAL
# > **Pegá esto al inicio de cualquier sesión nueva en Cursor antes de usar cualquier prompt.**

```
Estás trabajando en CyberPulse LATAM, un motor de decisión de ciberseguridad
diseñado para empresas latinoamericanas de 50-200 usuarios.

STACK TECNOLÓGICO:
- Backend: Python 3.12 + FastAPI + asyncio
- Bus de eventos: Redis 7 (Streams + caché de enrichment)
- Base de datos: MongoDB 7 + motor (driver async oficial — pip install motor)
- Frontend: React 18 + Vite + Zustand + socket.io-client
- Contenedores: Docker + docker-compose
- IA: Anthropic Claude API (claude-sonnet-4-20250514)
- Lenguaje de desarrollo: Python y JavaScript/JSX únicamente

POR QUÉ MONGODB (no negociable):
- Todos los datos son documentos JSON con estructura variable → schema nativo
- Time Series Collections nativas para el stream de eventos (compresión automática)
- Aggregation Pipeline para calcular baselines sin SQL complejo
- Change Streams para escuchar nuevos incidentes en tiempo real
- Sin migraciones cuando evoluciona el schema de enrichment
- Driver async oficial: motor (mismo autor que pymongo, mantenido por MongoDB Inc.)

PRINCIPIOS DE DISEÑO NO NEGOCIABLES:
1. Cada módulo hace UNA sola cosa. Sin responsabilidades mezcladas.
2. Todos los eventos tienen un formato JSON único y estricto (ver schema más abajo).
3. El sistema nunca bloquea. Todo es async/await.
4. El caché siempre va antes que cualquier llamada externa.
5. Ningún secreto (API keys, passwords) va hardcodeado. Todo viene de .env.
6. Los logs siempre incluyen timestamp ISO8601, nivel, módulo y mensaje.
7. Todo error es capturado, logueado y el sistema continúa operando.

SCHEMA DE EVENTO (inmutable, no modificar):
{
  "id": "evt_{timestamp}_{random4}",
  "timestamp": "ISO8601",
  "source": "dns|proxy|firewall|wazuh|endpoint",
  "tipo": "query|request|block|alert|process",
  "interno": {
    "ip": "str",
    "hostname": "str",
    "usuario": "str",
    "area": "str"
  },
  "externo": {
    "valor": "str",
    "tipo": "ip|dominio|url|hash"
  },
  "enrichment": null | { ver EnrichmentSchema },
  "risk_score": null | int(0-100),
  "correlaciones": []
}

ESTRUCTURA DE CARPETAS (ya definida, no modificar):
cyber-pulse-lab/
├── docker-compose.yml
├── .env
├── simulator/
├── collector/
├── enricher/
├── correlator/
├── ai_analyst/
├── api/
└── dashboard/
```

---

## FASE 1 — El Esqueleto

---

### PROMPT 01 — Architect
**Rol:** Software Architect  
**Componente:** Estructura base del repositorio  
**Entregable:** Todos los archivos y carpetas vacías con su estructura correcta

```
Sos un Software Architect senior especializado en sistemas de seguridad distribuidos.

Tu tarea es crear la estructura completa de archivos y carpetas del proyecto
CyberPulse LATAM. No escribís código todavía — solo creás los archivos
con docstrings/comentarios que explican qué hará cada uno.

ESTRUCTURA A CREAR (exactamente esta, sin agregar ni quitar):

cyber-pulse-lab/
├── docker-compose.yml            (vacío por ahora)
├── docker-compose.prod.yml       (vacío por ahora)
├── .env.example                  (con todas las variables necesarias, sin valores reales)
├── .gitignore                    (Python + Node + .env)
├── README.md                     (título y descripción de una línea por ahora)
│
├── simulator/
│   ├── Dockerfile
│   ├── requirements.txt          (solo las dependencias: faker, httpx, asyncio)
│   ├── main.py                   (docstring explicando su rol)
│   ├── personas.json             (array vacío [])
│   ├── generator.py              (docstring)
│   └── attack_scenarios/
│       ├── __init__.py
│       ├── phishing.py           (docstring)
│       ├── ransomware.py         (docstring)
│       ├── dns_tunneling.py      (docstring)
│       ├── lateral_movement.py   (docstring)
│       └── exfiltration.py      (docstring)
│
├── collector/
│   ├── Dockerfile
│   ├── requirements.txt          (watchdog, redis, pydantic, asyncio)
│   ├── main.py                   (docstring)
│   ├── normalizer.py             (docstring)
│   └── parsers/
│       ├── __init__.py
│       ├── dns_parser.py         (docstring)
│       ├── proxy_parser.py       (docstring)
│       ├── firewall_parser.py    (docstring)
│       ├── wazuh_parser.py       (docstring)
│       └── endpoint_parser.py    (docstring)
│
├── enricher/
│   ├── Dockerfile
│   ├── requirements.txt          (httpx, redis, asyncio, schedule)
│   ├── main.py                   (docstring)
│   ├── cache.py                  (docstring)
│   ├── feeds/
│   │   ├── __init__.py
│   │   ├── downloader.py         (docstring)
│   │   ├── spamhaus.py           (docstring)
│   │   ├── urlhaus.py            (docstring)
│   │   └── threatfox.py          (docstring)
│   └── apis/
│       ├── __init__.py
│       ├── abuseipdb.py          (docstring)
│       ├── virustotal.py         (docstring)
│       └── otx.py               (docstring)
│
├── correlator/
│   ├── Dockerfile
│   ├── requirements.txt          (redis, motor, asyncio)
│   ├── main.py                   (docstring)
│   ├── baseline.py               (docstring)
│   ├── risk_score.py             (docstring)
│   ├── honeypot.py               (docstring)
│   └── patterns/
│       ├── __init__.py
│       ├── beaconing.py          (docstring)
│       ├── dns_tunneling.py      (docstring)
│       ├── lateral_movement.py   (docstring)
│       ├── volume_anomaly.py     (docstring)
│       └── time_anomaly.py       (docstring)
│
├── ai_analyst/
│   ├── Dockerfile
│   ├── requirements.txt          (anthropic, motor, redis)
│   ├── main.py                   (docstring)
│   ├── autonomous_analyst.py     (docstring)
│   ├── incident_analyzer.py      (docstring)
│   ├── ceo_translator.py         (docstring)
│   └── prompts/
│       ├── autonomous.txt        (placeholder: "PROMPT AQUÍ")
│       ├── incident.txt          (placeholder)
│       └── ceo_view.txt          (placeholder)
│
├── api/
│   ├── Dockerfile
│   ├── requirements.txt          (fastapi, uvicorn, motor, redis, python-socketio)
│   ├── main.py                   (docstring)
│   ├── models.py                 (docstring)
│   ├── websocket.py              (docstring)
│   └── routers/
│       ├── __init__.py
│       ├── events.py             (docstring)
│       ├── identities.py         (docstring)
│       ├── incidents.py          (docstring)
│       └── alerts.py             (docstring)
│
└── dashboard/
    ├── Dockerfile
    ├── package.json              (React 18, Vite, Zustand, socket.io-client, d3)
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── store/
        │   └── index.js
        ├── hooks/
        │   ├── useWebSocket.js
        │   └── useEvents.js
        ├── views/
        │   ├── NetworkMap.jsx
        │   ├── Timeline.jsx
        │   ├── Identities.jsx
        │   └── CeoView.jsx
        └── components/
            ├── RiskBadge.jsx
            ├── IncidentCard.jsx
            ├── AttackInjector.jsx
            └── AiMemo.jsx

REGLAS:
- El .env.example debe tener TODAS las variables que el sistema va a necesitar,
  con comentarios explicando cada una. Variables mínimas:
  REDIS_URL, MONGODB_URL, ANTHROPIC_API_KEY, ABUSEIPDB_KEY,
  VIRUSTOTAL_KEY, OTX_KEY, LAB_MODE (true/false), LOG_LEVEL.
- Los Dockerfiles deben ser funcionales con imagen base python:3.12-slim.
- El .gitignore debe ignorar: .env, __pycache__, node_modules, *.pyc, dist/.
- No escribas lógica de negocio todavía. Solo estructura y documentación mínima.

NO HAGAS:
- No agregues carpetas que no están en la lista.
- No uses frameworks que no están en requirements.txt.
- No escribas código funcional todavía.
```

---

### PROMPT 02 — DevOps Engineer
**Rol:** DevOps / Infrastructure Engineer  
**Componente:** docker-compose.yml  
**Entregable:** docker-compose.yml completamente funcional para el laboratorio

```
Sos un DevOps Engineer especializado en contenedores y redes Docker.

Tu tarea es escribir el archivo docker-compose.yml para el laboratorio de
CyberPulse LATAM. Este archivo debe levantar TODO el entorno con un solo
comando: `docker-compose up --build`.

SERVICIOS A DEFINIR (en este orden):

1. redis
   - Imagen: redis:7-alpine
   - Puerto expuesto: 6379:6379
   - Volumen persistente: ./data/redis:/data
   - Comando: redis-server --appendonly yes
   - Health check: redis-cli ping

2. mongodb
   - Imagen: mongo:7.0
   - Variables: MONGO_INITDB_ROOT_USERNAME, MONGO_INITDB_ROOT_PASSWORD (desde .env)
   - Puerto: 5432:5432
   - Volumen: ./data/mongodb:/data/db
   - Health check: mongosh --eval "db.adminCommand({ping:1})"
   - Init script: ./data/mongo-init.js (crea colecciones y índices al iniciar)

3. pihole (DNS del laboratorio)
   - Imagen: pihole/pihole:latest
   - Puertos: 53:53/udp, 53:53/tcp, 8080:80
   - Variables: WEBPASSWORD desde .env
   - Volumen de logs: ./data/pihole/logs:/var/log/pihole
   - El collector debe poder leer esos logs

4. collector
   - Build: ./collector
   - Depends on: redis (healthy), mongodb (healthy)
   - Variables desde .env
   - Volumen: monta ./data/pihole/logs como read-only en /logs/dns
   - Restart: unless-stopped

5. enricher
   - Build: ./enricher
   - Depends on: redis (healthy), mongodb (healthy)
   - Variables desde .env
   - Restart: unless-stopped

6. correlator
   - Build: ./correlator
   - Depends on: redis (healthy), mongodb (healthy)
   - Variables desde .env
   - Restart: unless-stopped

7. ai_analyst
   - Build: ./ai_analyst
   - Depends on: mongodb (healthy), redis (healthy)
   - Variables desde .env (incluye ANTHROPIC_API_KEY)
   - Restart: unless-stopped

8. api
   - Build: ./api
   - Depends on: mongodb (healthy), redis (healthy)
   - Puerto: 8000:8000
   - Variables desde .env
   - Restart: unless-stopped

9. simulator (SOLO EN LAB MODE)
   - Build: ./simulator
   - Depends on: collector, redis
   - Variables desde .env
   - Profile: lab  (se activa con --profile lab)
   - Restart: unless-stopped

10. dashboard
    - Build: ./dashboard
    - Puerto: 3000:3000
    - Depends on: api
    - Restart: unless-stopped

REGLAS TÉCNICAS:
- Todos los servicios Python deben estar en la misma red interna: cyberpulse-net
- El dashboard se comunica con api en http://api:8000 (red interna Docker)
- Usar `env_file: .env` en todos los servicios
- Todos los servicios deben tener `restart: unless-stopped`
- Los health checks son obligatorios en redis y mongodb
- El simulator solo corre con: docker-compose --profile lab up

TAMBIÉN CREAR:
- ./data/mongo-init.js con la creación de colecciones e índices:

```javascript
// Time Series Collection para eventos — compresión automática + queries por rango optimizadas
db.createCollection("events", {
  timeseries: {
    timeField: "timestamp",
    metaField: "meta",       // { source, area, usuario, ip }
    granularity: "seconds"
  },
  expireAfterSeconds: 2592000  // auto-elimina eventos de más de 30 días
})
db.events.createIndex({ "meta.ip": 1, "timestamp": -1 })
db.events.createIndex({ "meta.source": 1, "timestamp": -1 })
db.events.createIndex({ "externo.valor": 1 })
db.events.createIndex({ "risk_score": -1 })

// Identidades con baseline embebido (un solo documento por usuario)
db.createCollection("identities")
db.identities.createIndex({ "id": 1 }, { unique: true })
db.identities.createIndex({ "risk_score_actual": -1 })
db.identities.createIndex({ "area": 1 })

// Incidentes
db.createCollection("incidents")
db.incidents.createIndex({ "estado": 1, "severidad": 1 })
db.incidents.createIndex({ "created_at": -1 })

// Memos de IA
db.createCollection("ai_memos")
db.ai_memos.createIndex({ "created_at": -1 })
db.ai_memos.createIndex({ "prioridad": 1 })

// Honeypot hits — sin TTL, retener siempre como evidencia
db.createCollection("honeypot_hits")
db.honeypot_hits.createIndex({ "timestamp": -1 })
```

NO HAGAS:
- No uses docker swarm ni kubernetes. Solo docker-compose.
- No expongas MongoDB al exterior (sin mapeo de puertos al host).
- No uses latest como imagen en producción (excepto pihole que no tiene alternativa).
- No mezcles configuración de lab con configuración de producción en el mismo archivo.
```

---

### PROMPT 03 — Backend Dev
**Rol:** Backend Developer  
**Componente:** Modelos de datos (models.py) y schemas Pydantic  
**Entregable:** api/models.py y un schemas.py compartido

```
Sos un Backend Developer Python senior especializado en FastAPI y Pydantic v2.

Tu tarea es escribir los modelos de datos del sistema CyberPulse LATAM.
Estos modelos son la fuente de verdad para toda la aplicación.
Todos los demás módulos los van a importar.

ARCHIVO A CREAR: api/models.py

MODELOS REQUERIDOS (con Pydantic v2, usando `model_validator` y `field_validator`):

1. EventoInterno
   - ip: str (validar formato IPv4)
   - hostname: str
   - usuario: str
   - area: str

2. EventoExterno
   - valor: str
   - tipo: Literal["ip", "dominio", "url", "hash"]

3. Enrichment
   - reputacion: Literal["limpio", "sospechoso", "malicioso", "desconocido"]
   - fuente: str
   - categoria: Optional[str]
   - pais_origen: Optional[str]  (código ISO 2 letras)
   - asn: Optional[str]
   - registrado_hace_dias: Optional[int]
   - virustotal_detecciones: Optional[str]  (formato "N/87")
   - tags: list[str] = []

4. Evento (modelo principal — INMUTABLE una vez creado)
   - id: str (auto-generado: "evt_{timestamp_unix}_{uuid4[:4]}")
   - timestamp: datetime (con timezone UTC)
   - source: Literal["dns", "proxy", "firewall", "wazuh", "endpoint"]
   - tipo: Literal["query", "request", "block", "alert", "process"]
   - interno: EventoInterno
   - externo: EventoExterno
   - enrichment: Optional[Enrichment] = None
   - risk_score: Optional[int] = None  (Field ge=0, le=100)
   - correlaciones: list[str] = []  (lista de IDs de eventos relacionados)
   - Método: to_mongo_dict() → dict serializable para insertar en MongoDB
   - Método: to_redis_dict() → dict serializable para Redis

5. Identidad
   - id: str  (formato: "{area}.{usuario}")
   - usuario: str
   - area: str
   - dispositivo: str
   - hostname: str
   - baseline: Optional[BaselineData] = None
   - risk_score_actual: int = 0
   - ultima_actividad: Optional[datetime]

6. BaselineData
   - horario_inicio: str  (formato "HH:MM")
   - horario_fin: str
   - dias_laborales: list[str]
   - dominios_habituales: list[str]
   - volumen_mb_dia_media: float
   - volumen_mb_dia_std: float
   - servidores_internos: list[str]
   - muestras_recolectadas: int = 0  (días de datos acumulados)
   - baseline_valido: bool = False  (True cuando muestras >= 7)

7. Incidente
   - id: str
   - titulo: str
   - descripcion: str
   - severidad: Literal["critica", "alta", "media", "baja", "info"]
   - eventos_ids: list[str]
   - estado: Literal["abierto", "investigando", "cerrado", "falso_positivo"] = "abierto"
   - created_at: datetime
   - closed_at: Optional[datetime]

8. AiMemo
   - id: str
   - tipo: Literal["autonomo", "incidente", "ceo", "hunting"]
   - contenido: str
   - prioridad: Literal["critica", "alta", "media", "info"]
   - eventos_relacionados: list[str]
   - created_at: datetime

9. HoneypotHit
   - id: str
   - recurso: str  (nombre del recurso trampa tocado)
   - tipo_recurso: Literal["share", "ip_fantasma", "usuario_ad", "dns_interno", "archivo"]
   - ip_interna: str
   - usuario: Optional[str]
   - timestamp: datetime

TAMBIÉN EN models.py:
- Constante RISK_SCORE_THRESHOLDS: dict con umbrales
  {"critico": 80, "alto": 60, "medio": 40, "bajo": 20}
- Función get_severidad(risk_score: int) -> str
- Función generate_event_id() -> str

REGLAS:
- Usar Pydantic v2 (from pydantic import BaseModel, Field, field_validator)
- Todos los datetime deben ser timezone-aware (UTC)
- Los Optional siempre tienen default None
- No uses ODM (no MongoEngine). Solo Pydantic para validación y motor para queries.
- El método to_mongo_dict() transforma `id` → `_id` y serializa datetime nativos.
- Agregar ejemplos en Config class para la documentación automática de FastAPI

NO HAGAS:
- No uses MongoEngine ni ningún ODM.
- No mezcles modelos de request HTTP con modelos de dominio.
- No uses datetime sin timezone.
- No uses Any como tipo en ningún campo.
- No conviertas ObjectId a string en los modelos — usá el campo `id` propio del sistema.
```

---

### PROMPT 04 — Backend Dev
**Rol:** Backend Developer  
**Componente:** Redis Bus — estructura de colas y helpers  
**Entregable:** Un módulo compartido `shared/redis_bus.py`

```
Sos un Backend Developer Python senior especializado en Redis y sistemas de mensajería.

Tu tarea es crear el módulo compartido que todos los servicios van a usar para
comunicarse via Redis. Este módulo es el bus central del sistema.

ARCHIVO A CREAR: shared/redis_bus.py
(Crear también shared/__init__.py vacío)

REQUERIMIENTOS TÉCNICOS:

El módulo debe exportar una clase RedisBus con los siguientes métodos,
todos async usando redis.asyncio:

```python
class RedisBus:
    STREAM_RAW = "events:raw"
    STREAM_ENRICHED = "events:enriched"
    STREAM_ALERTS = "events:alerts"
    CACHE_PREFIX_ENRICH = "enrich:"
    CACHE_PREFIX_BASELINE = "baseline:"
    CACHE_TTL_ENRICH = 86400       # 24 horas
    CACHE_TTL_BASELINE = 3600      # 1 hora
    
    async def connect(self) -> None
    async def disconnect(self) -> None
    
    # STREAMS (cola de eventos)
    async def publish_event(self, stream: str, evento: dict) -> str
        # Publica en Redis Stream, retorna el ID asignado por Redis
        # maxlen=10000 para no crecer infinitamente
    
    async def consume_events(self, stream: str, group: str, 
                             consumer: str, count: int = 10) -> list[dict]
        # Consume del stream como consumer group
        # Crea el group si no existe (MKSTREAM)
        # Retorna lista de (redis_id, event_dict)
    
    async def acknowledge(self, stream: str, group: str, *ids: str) -> None
        # ACK de mensajes procesados
    
    # CACHÉ (enrichment y baselines)
    async def cache_get(self, key: str) -> Optional[dict]
        # GET con deserialización JSON, retorna None si no existe
    
    async def cache_set(self, key: str, value: dict, ttl: int) -> None
        # SET con serialización JSON y TTL
    
    async def cache_exists(self, key: str) -> bool
        # EXISTS sin traer el valor
    
    # SETS para blocklists
    async def blocklist_add(self, lista: str, *valores: str) -> None
        # SADD al set "blocklist:{lista}"
    
    async def blocklist_check(self, lista: str, valor: str) -> bool
        # SISMEMBER en el set "blocklist:{lista}"
    
    async def blocklist_size(self, lista: str) -> int
        # SCARD del set
    
    # PUBLISH/SUBSCRIBE para alertas en tiempo real al dashboard
    async def publish_alert(self, canal: str, data: dict) -> None
        # PUBLISH en canal PubSub
    
    async def subscribe_alerts(self, canal: str, callback) -> None
        # SUBSCRIBE con callback async
```

TAMBIÉN CREAR: shared/mongo_client.py
Cliente MongoDB compartido usando motor (driver async oficial):

```python
from motor.motor_asyncio import AsyncIOMotorClient

class MongoClient:
    """
    Singleton de conexión a MongoDB.
    Todos los servicios importan esto para acceder a las colecciones.
    
    Uso:
        client = MongoClient()
        await client.connect()
        evento = await client.db.events.find_one({"_id": event_id})
    
    Change Streams (para el WebSocket del dashboard):
        async with client.db.incidents.watch() as stream:
            async for change in stream:
                # nuevo incidente detectado en tiempo real
    """
    
    COLLECTIONS = {
        "events":        "events",        # Time Series
        "identities":    "identities",
        "incidents":     "incidents",
        "ai_memos":      "ai_memos",
        "honeypot_hits": "honeypot_hits",
    }
    
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def ping(self) -> bool: ...
```

TAMBIÉN CREAR: shared/logger.py
Un logger estructurado estándar que todos los módulos usen:
- Formato: JSON con campos: timestamp, level, module, message, extra
- Niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Lee LOG_LEVEL desde variable de entorno
- Función: get_logger(module_name: str) -> Logger

REGLAS:
- Usar redis.asyncio (no redis síncrono)
- Connection pooling: max_connections=20
- Todos los métodos manejan sus propias excepciones con logging
- En caso de error de conexión, reintentar 3 veces con backoff exponencial
- La URL de Redis viene de variable de entorno REDIS_URL

NO HAGAS:
- No uses redis síncrono (import redis sin .asyncio).
- No hagas conexiones nuevas en cada llamada. Usar el pool.
- No serialices con pickle, solo JSON.
- No captures excepciones silenciosamente sin loggear.
```

---

### PROMPT 05 — Backend Dev
**Rol:** Backend Developer  
**Componente:** Collector — normalizer.py  
**Entregable:** collector/normalizer.py funcional

```
Sos un Backend Developer Python senior especializado en procesamiento de logs
y normalización de datos de seguridad.

Tu tarea es escribir el normalizer.py del collector. Este módulo recibe
un log crudo de cualquier fuente y lo convierte al formato Evento estándar.

ARCHIVO A CREAR: collector/normalizer.py

El normalizer debe implementar la clase Normalizer con estos métodos:

class Normalizer:
    
    def normalize(self, raw_log: dict, source: str) -> Optional[Evento]:
        """
        Punto de entrada principal. Recibe un log crudo y la fuente.
        Llama al método específico según source.
        Retorna None si el log no es válido o no tiene suficientes datos.
        Nunca lanza excepciones — captura todo y retorna None con log de warning.
        """
    
    def _normalize_dns(self, raw: dict) -> Optional[Evento]:
        """
        Espera estos campos en raw (formato PiHole):
        - timestamp: str (varios formatos posibles)
        - client: str (IP interna)
        - domain: str (dominio consultado)
        - status: str (NOERROR, NXDOMAIN, BLOCKED, etc.)
        
        Genera:
        - interno.ip = raw["client"]
        - interno.hostname = resolver_hostname(raw["client"])  # desde tabla local
        - interno.usuario = resolver_usuario(raw["client"])    # desde tabla local
        - externo.valor = raw["domain"]
        - externo.tipo = "dominio"
        - tipo = "query"
        """
    
    def _normalize_proxy(self, raw: dict) -> Optional[Evento]:
        """
        Espera formato de log Squid/NGINX access log:
        - timestamp, client_ip, method, url, status_code,
          bytes_sent, user_agent
        
        Extrae dominio de la URL para externo.valor
        tipo = "request"
        """
    
    def _normalize_firewall(self, raw: dict) -> Optional[Evento]:
        """
        Formato genérico de firewall:
        - timestamp, src_ip, dst_ip, dst_port, action (ALLOW/BLOCK/DROP)
        
        Si src_ip es IP interna: interno.ip = src_ip, externo.valor = dst_ip
        Si dst_ip es IP interna: interno.ip = dst_ip, externo.valor = src_ip
        tipo = "block" si action != ALLOW, sino "request"
        externo.tipo = "ip"
        """
    
    def _normalize_wazuh(self, raw: dict) -> Optional[Evento]:
        """
        Formato webhook de Wazuh:
        - timestamp, agent.ip, agent.name, rule.description,
          rule.level, rule.groups[]
        
        interno.ip = agent.ip
        interno.hostname = agent.name
        externo.valor = rule.description
        externo.tipo = "dominio" (semántico, no literal)
        tipo = "alert"
        """
    
    def _normalize_endpoint(self, raw: dict) -> Optional[Evento]:
        """
        Formato de agente de endpoint:
        - timestamp, host_ip, hostname, username,
          process_name, process_pid, network_dst (opcional)
        
        tipo = "process"
        """

TABLA DE RESOLUCIÓN INTERNA:
Implementar dos métodos auxiliares que leen desde Redis:
- resolver_hostname(ip: str) -> str: retorna hostname o "unknown"
- resolver_usuario(ip: str) -> str: retorna usuario o "unknown"

Estas tablas se populan desde el simulador (en lab mode) o
desde la integración con AD/DHCP en producción.

NORMALIZACIÓN DE TIMESTAMPS:
Soportar estos formatos de entrada y convertir siempre a datetime UTC:
- Unix timestamp (int o float)
- "2026-03-20T14:32:11"
- "2026-03-20 14:32:11"
- "20/Mar/2026:14:32:11 +0000"
- "Mar 20 14:32:11"

DETECCIÓN DE IPs INTERNAS:
Considerar internas los rangos RFC1918:
- 10.0.0.0/8
- 172.16.0.0/12
- 192.168.0.0/16

REGLAS:
- Todo método retorna Optional[Evento], nunca lanza excepciones
- Loggear cada normalización fallida con el raw_log completo a nivel DEBUG
- El ID del evento se genera en el normalizer (no en el parser)
- Importar el modelo Evento desde shared/ o api/models.py

NO HAGAS:
- No hagas requests HTTP en el normalizer (solo normaliza, no enriquece).
- No accedas a MongoDB directamente desde el normalizer.
- No uses regex para parsear IPs. Usar ipaddress stdlib.
- No asumas que todos los campos del raw_log existen. Siempre .get() con default.
```

---

### PROMPT 06 — Backend Dev
**Rol:** Backend Developer  
**Componente:** Collector — parser de DNS  
**Entregable:** collector/parsers/dns_parser.py funcional

```
Sos un Backend Developer Python senior especializado en parsing de logs de red.

Tu tarea es escribir el parser de DNS para el collector de CyberPulse LATAM.
Este parser lee el archivo de logs de PiHole en tiempo real y convierte cada
línea en un dict que el normalizer puede procesar.

ARCHIVO A CREAR: collector/parsers/dns_parser.py

IMPLEMENTAR la clase DnsParser:

class DnsParser:
    """
    Lee /logs/dns/pihole.log en tiempo real usando watchdog.
    Por cada línea nueva, parsea y publica en Redis Stream events:raw.
    """
    
    def __init__(self, log_path: str, redis_bus: RedisBus):
        ...
    
    async def start(self) -> None:
        """
        Inicia el tail del archivo usando asyncio.
        Guarda la posición del último byte leído para sobrevivir reinicios.
        Lee posición desde Redis key "parser:dns:last_position".
        """
    
    def _parse_line(self, line: str) -> Optional[dict]:
        """
        Parsea una línea del formato PiHole log.
        
        Ejemplos de líneas reales a manejar:
        
        "Mar 20 14:32:11 dnsmasq[123]: query[A] google.com from 192.168.1.45"
        "Mar 20 14:32:11 dnsmasq[123]: reply google.com is 142.250.200.46"
        "Mar 20 14:32:11 dnsmasq[123]: gravity blocked evil.ru for 192.168.1.45"
        "Mar 20 14:32:11 dnsmasq[123]: query[AAAA] domain.com from 192.168.1.50"
        
        Retorna dict con campos:
        {
            "timestamp": "Mar 20 14:32:11",
            "client": "192.168.1.45",
            "domain": "google.com",
            "type": "A",          # tipo de query DNS
            "status": "NOERROR",  # o "BLOCKED", "NXDOMAIN"
            "blocked": False
        }
        
        Solo procesar líneas con "query[" (ignorar reply, cached, etc.)
        Retornar None para líneas que no sean consultas DNS.
        """
    
    def _is_internal_domain(self, domain: str) -> bool:
        """
        Retorna True para dominios que no deben enriquecerse:
        - *.local
        - *.internal  
        - *.empresa.local
        - PTR queries (terminan en .arpa)
        Estos se filtran y no se publican al bus.
        """

MANEJO DE ARCHIVOS EN TIEMPO REAL:
Usar asyncio para hacer el tail del archivo sin bloquear:
- Abrir en modo 'r' con encoding='utf-8', errors='ignore'
- Ir al final del archivo al iniciar (o a last_position guardada)
- Cada 0.1 segundos, intentar leer nuevas líneas
- Si el archivo fue rotado (tamaño < last_position), resetear a 0

FILTROS (no publicar estos eventos):
- Dominios internos (ver _is_internal_domain)
- IPs que no son internas como cliente
- Líneas de reply, cached, forwarded (solo query)
- Dominios con menos de 2 puntos (sin TLD válido)

REGLAS:
- El parser nunca detiene el sistema. Errores son logueados y se continúa.
- Publicar en Redis con source="dns"
- Guardar posición cada 100 líneas procesadas (no cada línea)
- Logging: una línea INFO cada 1000 eventos procesados con estadísticas

NO HAGAS:
- No uses subprocess para hacer tail. Implementar el file reading en Python puro.
- No cargues el archivo completo en memoria.
- No bloquees el event loop con operaciones de I/O síncronas.
- No filtres dominios como google.com, amazon.com. Solo los internos.
```

---

### PROMPT 07 — Backend Dev
**Rol:** Backend Developer  
**Componente:** Collector — parsers Proxy, Firewall y Wazuh  
**Entregable:** Los tres archivos de parsers restantes

```
Sos un Backend Developer Python senior especializado en integración de sistemas
de seguridad y parsing de logs.

Tu tarea es escribir los tres parsers restantes del collector:
proxy_parser.py, firewall_parser.py y wazuh_parser.py.
Seguir el mismo patrón que dns_parser.py (ya implementado).

ARCHIVO 1: collector/parsers/proxy_parser.py

Parsea logs de Squid en formato Combined Log:
"1711020731.000  42 192.168.1.45 TCP_MISS/200 8523 GET http://example.com/ - DIRECT/93.184.216.34 text/html"

Campos a extraer:
- timestamp: unix timestamp (primer campo)
- client: IP interna
- method: GET/POST/CONNECT
- url: URL completa
- status_code: código HTTP
- bytes: bytes transferidos
- destination_ip: IP destino (opcional)

Extraer dominio de la URL usando urllib.parse.urlparse()
Filtrar: status_code 0, métodos CONNECT a puertos != 443

ARCHIVO 2: collector/parsers/firewall_parser.py

Soportar dos formatos de log:
A) iptables/nftables:
   "Mar 20 14:32:11 kernel: [UFW BLOCK] IN=eth0 SRC=185.220.101.47 DST=192.168.1.1 PROTO=TCP DPT=22"

B) Formato genérico CSV del laboratorio (para el simulador):
   "timestamp,action,src_ip,dst_ip,src_port,dst_port,protocol"

Para el formato A: usar regex para extraer SRC, DST, PROTO, DPT, action (BLOCK/ALLOW)
Para el formato B: usar csv.DictReader

Detectar automáticamente el formato según si la línea contiene "kernel:" o no.

ARCHIVO 3: collector/parsers/wazuh_parser.py

Este parser NO lee un archivo. Expone un endpoint HTTP (usando FastAPI mini-app
o un simple HTTP server) que recibe webhooks POST de Wazuh.

Wazuh envía JSON con esta estructura:
{
  "timestamp": "2026-03-20T14:32:11.000+0000",
  "agent": { "ip": "192.168.1.45", "name": "PC-CONT-03" },
  "rule": {
    "level": 7,
    "description": "Multiple failed logins",
    "groups": ["authentication_failed", "pam"],
    "id": "5503"
  },
  "data": { "srcip": "10.0.0.5" }
}

El webhook escucha en puerto 9000 (configurable por .env: WAZUH_WEBHOOK_PORT)
Solo procesar alertas con rule.level >= 3 (ignorar las de muy bajo nivel)
Mapear rule.level a risk_score base:
- level 3-5: risk base 20
- level 6-9: risk base 50  
- level 10-12: risk base 75
- level 13+: risk base 90

PARA LOS TRES PARSERS:
- Misma interface que DnsParser: método async start() y _parse_line()
- Publicar a Redis con el source correcto ("proxy", "firewall", "wazuh")
- Mismo manejo de errores y logging
- El endpoint de Wazuh debe retornar {"status": "ok"} en 200ms máximo

TAMBIÉN CREAR: collector/main.py
Que inicie todos los parsers en paralelo usando asyncio.gather():
asyncio.gather(
    dns_parser.start(),
    proxy_parser.start(),
    firewall_parser.start(),
    wazuh_parser.start()
)

NO HAGAS:
- No uses frameworks pesados para el webhook de Wazuh. Un simple
  http.server o un micro FastAPI con un solo endpoint es suficiente.
- No proceses el mismo evento dos veces (deduplicación por hash del contenido).
- No asumas que los campos de Wazuh siempre existen.
```

---

### PROMPT 08 — Simulator Dev
**Rol:** Simulation Engineer  
**Componente:** personas.json — identidades sintéticas  
**Entregable:** simulator/personas.json con 25 usuarios sintéticos

```
Sos un Simulation Engineer especializado en generación de datos sintéticos
para pruebas de sistemas de seguridad.

Tu tarea es crear el archivo personas.json con 25 usuarios ficticios que
representen una empresa argentina mediana típica.

ESTRUCTURA DE CADA PERSONA:
{
  "id": "area.nombre",               // ej: "contabilidad.garcia"
  "nombre_completo": "...",
  "area": "...",                     // ver áreas abajo
  "dispositivo": "192.168.X.Y",      // IP interna única
  "hostname": "PC-AREA-NN",
  "horario_inicio": "HH:MM",
  "horario_fin": "HH:MM",
  "dias_laborales": ["lun","mar","mie","jue","vie"],
  "dominios_habituales": [...],      // 5-10 dominios típicos del área
  "volumen_mb_dia": N,               // MB promedio por día laboral
  "variacion": 0.15,                 // variación ±15% del volumen
  "servidores_internos": [...],      // hostnames internos que accede
  "probabilidad_anomalia": 0.02      // 2% de chance de comportamiento raro/día
}

ÁREAS Y CANTIDAD:
- contabilidad: 4 personas (horario 8:30-18:00)
- rrhh: 3 personas (horario 9:00-18:00)
- ventas: 5 personas (horario 9:00-19:30, algunos sábado mañana)
- it: 3 personas (horario variable, acceden a más servidores internos)
- gerencia: 3 personas (horario irregular, viajan mucho)
- marketing: 3 personas (horario 9:00-18:00, mucho tráfico a redes sociales)
- legal: 2 personas (horario 9:00-18:00)
- operaciones: 2 personas (horario 7:00-16:00)

DOMINIOS POR ÁREA (ejemplos, expandir):
- contabilidad: afip.gov.ar, bancogalicia.com.ar, bbva.com.ar, sistemaerp.local
- rrhh: linkedin.com, workday.com, drive.google.com, legajodigital.local
- ventas: salesforce.com, zoom.us, linkedin.com, mercadolibre.com.ar
- it: github.com, stackoverflow.com, docs.docker.com, grafana.local, wazuh.local
- gerencia: mail.google.com, zoom.us, drive.google.com, notion.so
- marketing: instagram.com, facebook.com, hootsuite.com, canva.com
- legal: errepar.com, infoleg.gob.ar, mail.google.com
- operaciones: proveedoresinterno.local, stock.local, afip.gov.ar

SERVIDORES INTERNOS DISPONIBLES (usar subconjuntos por área):
fileserver01.local, erp-server.local, hr-server.local, mail-server.local,
dc01.local, backup01.local, monitoring.local, vpn-gw.local

REGLAS:
- IPs en rango 192.168.1.10 a 192.168.1.250 (sin repetir)
- Nombres argentinos reales (García, López, Martínez, González, etc.)
- Los de IT tienen más servidores internos y mayor volumen
- Los de gerencia tienen horario más irregular (variacion: 0.30)
- Incluir 1 usuario con probabilidad_anomalia más alta (0.10) — el "insider threat"
- volumen_mb_dia entre 40 (legal) y 200 (it/marketing)

NO HAGAS:
- No uses IPs duplicadas.
- No uses dominios que no existen (inventá subdominios de dominios reales).
- No pongas a todos en el mismo horario.
- No uses nombres de personas reales conocidas.
```

---

### PROMPT 09 — Simulator Dev
**Rol:** Simulation Engineer  
**Componente:** generator.py — motor de tráfico sintético  
**Entregable:** simulator/generator.py completamente funcional

```
Sos un Simulation Engineer especializado en generación de tráfico de red sintético
para sistemas de detección de intrusiones.

Tu tarea es escribir el generator.py del simulador. Este es el motor principal
que genera tráfico realista basado en las personas definidas en personas.json.

ARCHIVO A CREAR: simulator/generator.py

CLASE PRINCIPAL: TrafficGenerator

```python
class TrafficGenerator:
    
    def __init__(self, personas: list[dict], redis_bus: RedisBus):
        self.personas = personas
        self.redis_bus = redis_bus
    
    async def run(self) -> None:
        """
        Loop principal. Para cada persona activa (según horario actual),
        genera eventos con distribución temporal realista.
        Corre indefinidamente hasta señal de stop.
        """
    
    async def _generate_for_persona(self, persona: dict) -> None:
        """
        Genera eventos para una persona específica.
        
        Frecuencia base: una persona genera entre 2-8 eventos DNS por minuto
        durante horario laboral, con picos en 10:00-12:00 y 15:00-17:00.
        Fuera de horario: 0 eventos (0.5% de chance de 1 evento ocasional).
        
        Distribuir eventos entre los dominios habituales con peso:
        70% a los primeros 3 dominios (más usados)
        30% al resto de la lista
        """
    
    def _esta_en_horario(self, persona: dict) -> bool:
        """
        Verifica si la persona debería estar activa ahora.
        Considerar: día de la semana, hora actual, variación ±20 min.
        """
    
    async def _emit_dns_event(self, persona: dict, dominio: str) -> None:
        """
        Genera un evento DNS y lo publica en Redis Stream events:raw
        como si viniera del dns_parser.
        
        Agregar ruido humano:
        - Variación de ±30 segundos en el timestamp
        - 5% de chance de consultar un dominio aleatorio no habitual
          (simula curiosidad normal de navegación)
        - 1% de chance de consultar un dominio nuevo no visto antes
        """
    
    async def _emit_proxy_event(self, persona: dict, url: str) -> None:
        """
        Genera evento de proxy. Misma persona, misma sesión de navegación.
        50% de los eventos DNS generan también un evento de proxy.
        """
    
    async def _populate_identity_table(self) -> None:
        """
        Al iniciar, publica en Redis la tabla ip->usuario y ip->hostname
        para que el normalizer pueda resolver identidades.
        Keys: "identity:{ip}" → {"usuario": "...", "hostname": "...", "area": "..."}
        """
```

RUIDO HUMANO (fundamental para que sea realista):
- Los tiempos entre eventos no son exactos: usar random.gauss(mean, std)
- Las personas hacen "pausas" (reuniones, almuerzo): períodos de 20-60 min sin actividad
- Las personas del área de marketing generan más tráfico a imágenes/videos (mayor volumen)
- Los de IT generan eventos en horarios más erráticos

MODO LABORATORIO:
Leer variable de entorno LAB_MODE=true.
En lab mode, comprimir el tiempo: 1 minuto real = 5 minutos simulados.
Esto permite ver un "día de trabajo" en ~3 horas reales.

ESTADÍSTICAS:
Cada 60 segundos, loggear:
- Personas activas en este momento
- Eventos generados en el último minuto
- Dominios únicos vistos
- Tráfico total simulado (MB)

REGLAS:
- Toda la generación es async. No bloquear el event loop.
- Las personas del mismo área a veces visitan el mismo dominio (reuniones compartidas)
- No generar eventos con timestamps en el futuro
- Usar asyncio.sleep con valores pequeños (0.1-2.0 seg) entre eventos

NO HAGAS:
- No generes todos los eventos de un día de golpe. Generarlos en tiempo real.
- No uses threading. Solo asyncio.
- No generes eventos DNS para dominios como "localhost" o IPs numéricas.
- No hagas que todos empiecen exactamente a las 9:00. Dispersar ±15 minutos.
```

---

### PROMPT 10 — Simulator Dev
**Rol:** Simulation Engineer  
**Componente:** attack_scenarios — todos los escenarios de ataque  
**Entregable:** Los 5 archivos de escenarios de ataque

```
Sos un Simulation Engineer y Red Teamer especializado en emulación de amenazas
para pruebas de detección en sistemas SIEM.

Tu tarea es implementar los 5 escenarios de ataque del simulador.
Cada escenario debe generar exactamente el tipo de tráfico que el correlator
necesita detectar. Ni más, ni menos.

INTERFACE COMÚN (todos los escenarios la implementan):

```python
class BaseAttackScenario:
    def __init__(self, redis_bus: RedisBus, target_persona: dict):
        self.redis_bus = redis_bus
        self.target = target_persona
    
    async def execute(self, intensity: Literal["baja","media","alta"]) -> None:
        """Ejecuta el escenario completo de forma async"""
    
    async def cleanup(self) -> None:
        """Limpia cualquier estado que el escenario haya dejado"""
    
    @property
    def description(self) -> str:
        """Descripción en español de qué hace este escenario"""
```

ESCENARIO 1: phishing.py — PhishingScenario
Simula un email de phishing recibido por varios usuarios del mismo área.
Comportamiento generado:
1. Seleccionar 3-5 usuarios del mismo área que el target
2. Todos consultan el mismo dominio malicioso (generarlo con Faker: dominio
   de 1-2 semanas de antigüedad, TLD .com o .info, nombre plausible)
3. Las consultas ocurren dentro de una ventana de 30-40 minutos
4. 60% de los usuarios hace click (genera evento de proxy también)
5. El dominio NO está en ninguna blocklist (es "nuevo" y desconocido)
Pausa entre consultas: entre 3 y 15 minutos (distribución natural)

ESCENARIO 2: ransomware.py — RansomwareScenario
Simula las etapas de un ransomware moderno.
Fases (con delays realistas entre cada una):
1. INICIAL (día 0): Consulta DNS a dominio C2 cada 5 minutos EXACTOS (beaconing)
   El dominio cambia cada 6 horas (DGA — generar con alta entropía)
2. EXPLORACIÓN (día 0, +2 horas): Conexiones de firewall a otras IPs internas
   que el dispositivo nunca había tocado (lateral movement inicial)
3. ACTIVACIÓN (día 1): Tráfico saliente 10x por encima del baseline
4. HONEYPOT: Intentar acceder al share \\\\fileserver01\\BACKUP_FINANCIERO_2025
   (genera un evento especial de tipo honeypot_hit)
En mode intensity="baja": solo fase 1. "media": fases 1-2. "alta": fases 1-4.

ESCENARIO 3: dns_tunneling.py — DnsTunnelingScenario
Simula exfiltración de datos a través de DNS.
Comportamiento:
1. Consultas a subdominios del mismo dominio base con longitud 40-60 chars
2. Los subdominios tienen alta entropía (datos codificados en base32)
3. Patrón: {64_chars_random}.{8_chars}.{dominio_base}.com
4. Frecuencia: 1 consulta cada 15-30 segundos durante 2-4 horas
5. El volumen de datos representado aumenta gradualmente (exfiltración en progreso)
Generar con: import base64, secrets → base64.b32encode(secrets.token_bytes(30))

ESCENARIO 4: lateral_movement.py — LateralMovementScenario
Simula movimiento lateral de un atacante ya dentro de la red.
Comportamiento (generado como eventos de firewall):
1. Desde el dispositivo del target, intentos de conexión a:
   - Todos los otros dispositivos del mismo segmento /24
   - Puertos comunes: 22, 445, 3389, 5985
2. Patrón: escaneo por rango de IPs, 1 intento cada 2-5 segundos
3. Algunos intentos "exitosos" (ALLOW en firewall): conexiones a 2-3 hosts
4. Finalmente: conexión exitosa al DC (dc01.local) — alerta crítica

ESCENARIO 5: exfiltration.py — ExfiltrationScenario
Simula exfiltración de datos por volumen anómalo.
Comportamiento:
1. Fuera del horario laboral habitual del target (ej: 2am)
2. Múltiples conexiones proxy a servicios de almacenamiento en la nube
   (mega.nz, drive.google.com, dropbox.com, wetransfer.com)
3. Volumen de transferencia: 5-10x por encima del baseline diario
4. Duración: 45-90 minutos
5. User-agent inusual o diferente al habitual del usuario

TAMBIÉN CREAR: simulator/attack_scenarios/__init__.py
Que exporte un diccionario SCENARIOS:
SCENARIOS = {
    "phishing": PhishingScenario,
    "ransomware": RansomwareScenario,
    "dns_tunneling": DnsTunnelingScenario,
    "lateral_movement": LateralMovementScenario,
    "exfiltration": ExfiltrationScenario,
}

Y una función:
async def run_scenario(name: str, target_persona: dict, 
                       intensity: str, redis_bus: RedisBus) -> None

REGLAS:
- Cada escenario debe ser detectado por al menos UN patrón del correlator.
- Los escenarios no destruyen datos reales. Solo generan eventos en Redis.
- El cleanup() de cada escenario debe dejar el estado limpio.
- Loggear el inicio y fin de cada fase con timestamp.

NO HAGAS:
- No generes ataques contra IPs externas reales.
- No hagas que un ataque se detecte inmediatamente (deben pasar minutos/horas).
- No hardcodees IPs. Leer las IPs del target_persona.
- No generes eventos con timestamps en el futuro.
```

---

## 🔐 FASE 2 — Enrichment e Inteligencia de Amenazas

---

### PROMPT 11 — Security Dev
**Rol:** 🔐 Security Engineer  
**Componente:** Enricher — cache.py y feeds/downloader.py  
**Entregable:** Sistema de caché y descarga de feeds funcionando

```
Sos un Security Engineer especializado en threat intelligence y sistemas de
reputación de IPs y dominios.

Tu tarea es implementar el sistema de caché y el descargador de feeds
de inteligencia de amenazas del enricher.

ARCHIVO 1: enricher/cache.py

Clase EnrichmentCache que wrappea RedisBus para la lógica específica de enriquecimiento:

class EnrichmentCache:
    
    async def get_enrichment(self, valor: str) -> Optional[Enrichment]:
        """
        Busca en Redis el enrichment guardado para este valor (IP o dominio).
        Key: "enrich:{valor}"
        Retorna None si no existe o expiró.
        """
    
    async def set_enrichment(self, valor: str, enrichment: Enrichment, 
                              ttl_seconds: int = 86400) -> None:
        """Guarda el enrichment en Redis con TTL."""
    
    async def get_stats(self) -> dict:
        """
        Retorna estadísticas del caché:
        - total_keys: cuántos valores enriquecidos hay en caché
        - hit_rate: porcentaje de hits en las últimas 1000 consultas
        (usar contador en Redis para esto)
        """
    
    async def record_hit(self) -> None:
        """Incrementa contador de cache hits (para estadísticas)."""
    
    async def record_miss(self) -> None:
        """Incrementa contador de cache misses."""

ARCHIVO 2: enricher/feeds/downloader.py

Clase FeedDownloader que descarga y actualiza todas las blocklists automáticamente:

class FeedDownloader:
    
    FEEDS = {
        "spamhaus_drop": {
            "url": "https://www.spamhaus.org/drop/drop.txt",
            "tipo": "cidr",
            "redis_key": "blocklist:spamhaus_drop"
        },
        "spamhaus_edrop": {
            "url": "https://www.spamhaus.org/drop/edrop.txt", 
            "tipo": "cidr",
            "redis_key": "blocklist:spamhaus_edrop"
        },
        "feodo_ip": {
            "url": "https://feodotracker.abuse.ch/downloads/ipblocklist.txt",
            "tipo": "ip",
            "redis_key": "blocklist:feodo"
        },
        "urlhaus_domains": {
            "url": "https://urlhaus.abuse.ch/downloads/text/",
            "tipo": "dominio",
            "redis_key": "blocklist:urlhaus"
        },
        "threatfox_iocs": {
            "url": "https://threatfox.abuse.ch/export/json/recent/",
            "tipo": "json",
            "redis_key": "blocklist:threatfox"
        }
    }
    
    async def start_scheduler(self) -> None:
        """
        Corre el loop de descarga. Primera descarga inmediata al iniciar.
        Luego cada 3600 segundos (1 hora).
        Usar asyncio.sleep, no librería externa de scheduling.
        """
    
    async def download_all(self) -> None:
        """Descarga todos los feeds en paralelo con asyncio.gather()"""
    
    async def download_feed(self, nombre: str, config: dict) -> None:
        """
        Descarga un feed específico y lo guarda en Redis.
        
        Para tipo "cidr": parsear rangos CIDR y guardar cada IP/red en un Redis SET
        Para tipo "ip": guardar cada línea (que no empiece con #) en Redis SET
        Para tipo "dominio": guardar cada línea en Redis SET
        Para tipo "json": parsear JSON y extraer IOCs según estructura de la API
        
        Antes de guardar: loggear cuántos IOCs nuevos se agregaron.
        Ignorar líneas vacías y comentarios (empiezan con #).
        Timeout de descarga: 30 segundos.
        """
    
    async def check_ip(self, ip: str) -> Optional[str]:
        """
        Verifica si una IP está en alguna blocklist.
        También verifica pertenencia a rangos CIDR.
        Retorna nombre de la lista si está bloqueada, None si está limpia.
        """
    
    async def check_domain(self, domain: str) -> Optional[str]:
        """
        Verifica si un dominio está en alguna blocklist.
        También verificar el dominio padre (ej: si "sub.evil.com" no está,
        verificar "evil.com").
        """
    
    async def get_stats(self) -> dict:
        """Retorna tamaño de cada blocklist y timestamp de última actualización."""

REGLAS:
- Usar httpx.AsyncClient para todas las descargas (no requests)
- Si una descarga falla, loggear el error y continuar con las demás
- Guardar timestamp de última actualización exitosa en Redis
- Los sets en Redis no tienen TTL (se sobreescriben en cada descarga)
- Para CIDRs, usar la librería ipaddress de stdlib para la verificación

NO HAGAS:
- No uses requests síncrono. Solo httpx async.
- No descargues todos los feeds secuencialmente. Usar gather().
- No dejes el sistema sin blocklists si una descarga falla
  (mantener las anteriores hasta la próxima descarga exitosa).
- No almacenes los feeds completos en memoria. Procesar línea por línea.
```

---

### PROMPT 12 — Security Dev
**Rol:** Security Engineer  
**Componente:** Enricher — main.py (motor de enriquecimiento)  
**Entregable:** enricher/main.py — el loop de enriquecimiento completo

```
Sos un Security Engineer especializado en pipelines de threat intelligence.

Tu tarea es implementar el motor principal del enricher. Este es el componente
que consume eventos del bus, los enriquece con contexto de seguridad,
y los republica enriquecidos.

ARCHIVO: enricher/main.py

CLASE PRINCIPAL: EnrichmentEngine

async def enrich_event(self, evento: Evento) -> Evento:
    """
    Pipeline de enriquecimiento para un evento.
    
    PASO 1: Determinar qué enriquecer
    - Si externo.tipo == "dominio": enriquecer el dominio
    - Si externo.tipo == "ip": enriquecer la IP
    - Si externo.tipo == "url": extraer dominio y enriquecer ambos
    - Si externo.tipo == "hash": consultar solo VirusTotal
    
    PASO 2: Verificar caché (si existe, retornar inmediatamente)
    
    PASO 3: Verificar blocklists locales (si match, retornar sin consultar API)
    
    PASO 4: Solo si los pasos 2 y 3 fallaron → consultar APIs externas
    El orden de consulta de APIs:
    a) AbuseIPDB (para IPs)
    b) AlienVault OTX (para dominios e IPs)
    c) VirusTotal (solo si los anteriores dan "desconocido")
    
    PASO 5: Calcular risk_score base según enrichment:
    - "malicioso" + fuente confiable: 70-90
    - "sospechoso": 40-60
    - "limpio": 0-10
    - "desconocido": 15
    
    PASO 6: Guardar resultado en caché
    
    PASO 7: Retornar evento con enrichment y risk_score completados
    """

LOOP PRINCIPAL:
```python
async def run(self):
    """
    Consumer del Redis Stream events:raw
    Consumer group: "enricher-group"
    Consumer name: "enricher-{uuid4[:8]}"  # único por instancia
    
    Por cada batch de 10 eventos:
    1. Procesar en paralelo con asyncio.gather()
    2. Publicar enriquecidos en events:enriched
    3. ACK los procesados
    4. Loggear throughput cada 100 eventos
    """
```

MANEJO DE RATE LIMITS:
Implementar un RateLimiter por API:
- AbuseIPDB: 1000/día → máx 1 req/86 segundos en promedio
- VirusTotal: 500/día → máx 1 req/172 segundos en promedio
- OTX: sin límite pero respetar 10 req/segundo

Si se alcanza el rate limit de una API, loggear warning y
continuar con la siguiente API en el pipeline.
No fallar el enriquecimiento por rate limit agotado.

TAMBIÉN IMPLEMENTAR: enricher/apis/abuseipdb.py
```python
class AbuseIPDB:
    BASE_URL = "https://api.abuseipdb.com/api/v2"
    
    async def check_ip(self, ip: str) -> Optional[Enrichment]:
        """
        GET /check con params: ipAddress, maxAgeInDays=30, verbose
        Si confidence_score > 50: reputacion = "malicioso"
        Si confidence_score > 20: reputacion = "sospechoso"
        Si confidence_score == 0: reputacion = "limpio"
        """
```

Y enricher/apis/otx.py (AlienVault OTX):
```python
class AlienVaultOTX:
    BASE_URL = "https://otx.alienvault.com/api/v1"
    
    async def check_indicator(self, valor: str, tipo: str) -> Optional[Enrichment]:
        """
        Para dominios: GET /indicators/domain/{domain}/general
        Para IPs: GET /indicators/IPv4/{ip}/general
        Extraer: pulse_count, tags de los pulses, país, ASN
        Si pulse_count > 0: enriquecimiento con datos de los pulses
        """
```

REGLAS:
- Todos los clientes HTTP usan httpx.AsyncClient con timeout=10
- Las API keys vienen de variables de entorno
- Si la API key no está configurada, saltear esa API sin error
- Loggear cada llamada a API externa con: api_name, valor, latencia, resultado

NO HAGAS:
- No hagas más de una llamada a la misma API para el mismo valor.
- No bloquees el enriquecimiento si todas las APIs fallan
  (retornar evento con enrichment={"reputacion": "desconocido", "fuente": "timeout"}).
- No uses sleep() para rate limiting. Usar un semáforo async.
- No loggees las API keys en ningún mensaje de log.
```

---

### PROMPT 13 — Security Dev
**Rol:** Security Engineer  
**Componente:** Correlator — baseline.py (UEBA)  
**Entregable:** correlator/baseline.py completamente funcional

```
Sos un Security Engineer especializado en User and Entity Behavior Analytics (UEBA).

Tu tarea es implementar el sistema de baselines de comportamiento del correlator.
Este es el componente que aprende qué es "normal" para cada usuario y dispositivo.

ARCHIVO: correlator/baseline.py

CLASE: BaselineManager

El baseline de cada identidad se almacena en MongoDB (colección identities)
y se cachea en Redis con TTL de 1 hora.

MÉTODOS REQUERIDOS:

async def update_baseline(self, evento: Evento) -> None:
    """
    Actualiza el baseline de la identidad afectada por el evento.
    
    Usar Media Móvil Ponderada (EMA - Exponential Moving Average):
    nueva_media = alpha * valor_nuevo + (1 - alpha) * media_anterior
    alpha = 0.1  (aprende lento, no se afecta por eventos únicos raros)
    
    Actualizar estos campos del baseline:
    - dominios_habituales: agregar dominio si se vio 3+ veces en 7 días
    - volumen_mb_dia_media: actualizar con EMA
    - volumen_mb_dia_std: actualizar varianza con EMA
    - horario_inicio/fin: ajustar si el horario cambió consistentemente por 3+ días
    - servidores_internos: agregar si se accede 5+ veces
    - muestras_recolectadas: incrementar 1/día
    - baseline_valido: True cuando muestras_recolectadas >= 7
    """

async def get_baseline(self, identidad_id: str) -> Optional[BaselineData]:
    """
    Primero buscar en Redis (caché 1h).
    Si no está, buscar en MongoDB y cachear.
    Si no existe en ninguno, retornar None (identidad nueva).
    """

async def calcular_anomalia(self, evento: Evento) -> float:
    """
    Retorna un score de anomalía entre 0.0 y 1.0 para el evento.
    0.0 = completamente normal
    1.0 = completamente anómalo
    
    Factores a evaluar (con pesos):
    
    1. HORARIO (peso 0.25):
       - Evento dentro de horario laboral habitual: 0.0
       - Evento fuera de horario ±2hs: 0.3
       - Evento fuera de horario >2hs: 0.8
       - Evento en fin de semana si no es habitual: 0.7
    
    2. DOMINIO (peso 0.30):
       - Dominio en lista habitual: 0.0
       - Dominio no visto antes pero categoría conocida (social media, etc.): 0.2
       - Dominio completamente nuevo y no categorizado: 0.6
       - Dominio con TLD de alto riesgo (.ru, .cn, .tk, .xyz): +0.2 adicional
    
    3. VOLUMEN (peso 0.25):
       - Dentro de media ± 2*std: 0.0
       - Entre 2-3 std: 0.4
       - Más de 3 std: 0.9
    
    4. DESTINO INTERNO (peso 0.20):
       - Servidor habitual: 0.0
       - Servidor interno nuevo: 0.5
       - Servidor de otra área sin razón aparente: 0.8
    
    Si el baseline NO es válido (< 7 días): retornar 0.1 siempre
    (no hay suficientes datos para determinar anomalía)
    """

async def get_identidades_activas(self) -> list[dict]:
    """
    Retorna todas las identidades con actividad en las últimas 24h.
    Para el dashboard de identidades.
    """

async def inicializar_identidad(self, evento: Evento) -> None:
    """
    Crea la identidad si no existe.
    Se llama cuando llega el primer evento de una IP/usuario desconocido.
    """

REGLAS:
- El baseline nunca se resetea manualmente, solo evoluciona con el tiempo.
- No usar ML. Solo estadística básica (media, desviación estándar, EMA).
- Las actualizaciones de baseline son async y no bloquean el procesamiento de eventos.
- Los cambios de baseline se loggean a nivel DEBUG con el valor anterior y nuevo.

NO HAGAS:
- No actualices el baseline en tiempo real por cada evento individual.
  Actualizar en batches cada 5 minutos para no sobrecargar MongoDB.
- No consideres anomalía a un usuario de IT que accede a servidores de infraestructura.
- No hagas que el baseline tarde más de 50ms en retornar.
- No uses scikit-learn ni ninguna librería de ML.
```

---

### PROMPT 14 — Security Dev
**Rol:** Security Engineer  
**Componente:** Correlator — todos los patrones de ataque  
**Entregable:** Los 5 archivos de patterns/

```
Sos un Security Engineer y especialista en detección de amenazas (threat detection).

Tu tarea es implementar los 5 detectores de patrones del correlator.
Cada uno detecta un tipo específico de técnica de ataque.

INTERFACE COMÚN (todos implementan):

```python
class BasePattern:
    name: str           # nombre del patrón
    description: str    # descripción en español
    mitre_technique: str  # ID de técnica MITRE ATT&CK (ej: "T1071.004")
    
    async def check(self, evento: Evento, contexto: dict) -> Optional[Incidente]:
        """
        Analiza el evento en su contexto histórico.
        Retorna un Incidente si detecta el patrón, None si no.
        El contexto incluye: eventos recientes de la misma IP (últimos 30 min),
        baseline de la identidad, eventos del mismo dominio.
        """
```

PATRÓN 1: patterns/beaconing.py — BEACONINGPattern
Detecta: malware llamando a su C2 con intervalos regulares.

Algoritmo:
1. Para cada IP interna, mantener en Redis los últimos 20 timestamps
   de consultas al mismo dominio externo.
   Key: "pattern:beacon:{ip}:{domain}" → sorted set con timestamps
2. Cuando hay 5+ consultas, calcular el coeficiente de variación (std/mean)
   de los intervalos entre consultas.
3. Si CV < 0.15 (intervalos muy regulares) Y total de consultas > 5:
   → DETECCIÓN. Severidad según frecuencia:
   - Cada < 1 minuto: CRÍTICA
   - Cada 1-5 min: ALTA  
   - Cada 5-15 min: MEDIA
4. Incluir en el incidente: intervalo promedio, CV calculado, 
   cantidad de consultas detectadas, dominio destino.
MITRE: T1071.001 (Application Layer Protocol: Web Protocols)

PATRÓN 2: patterns/dns_tunneling.py — DNSTUNNELINGPattern
Detecta: exfiltración de datos encodificados en consultas DNS.

Algoritmo:
1. Para cada consulta DNS, calcular:
   a) Longitud del subdominio más largo (antes del dominio base)
   b) Entropía de Shannon del subdominio
   c) Ratio consonante/vocal (datos base32/base64 tienen ratios anómalos)
2. DETECCIÓN si CUALQUIERA de estas condiciones:
   - Subdominio > 45 caracteres
   - Entropía > 3.8 bits por carácter
   - Mismo dominio base con >20 subdominios distintos en 10 minutos
3. La entropía de Shannon se calcula como:
   H = -sum(p * log2(p) for cada carácter único)
MITRE: T1071.004 (DNS)

PATRÓN 3: patterns/lateral_movement.py — LATERALMOVEMENTPattern
Detecta: dispositivo que empieza a escanear o conectarse a otros hosts internos.

Algoritmo:
1. Para cada IP interna origen en eventos de firewall, mantener en Redis
   el set de IPs internas destino contactadas en las últimas 2 horas.
   Key: "pattern:lateral:{ip_origen}" → set de IPs destino
2. DETECCIÓN si:
   - El set crece a más de 5 IPs internas distintas en 30 minutos (escaneo)
   - O: aparece conexión a DC/servidor de AD que nunca se había visto
   - O: se detectan intentos a puertos típicos de movimiento lateral
     (22, 445, 3389, 5985, 5986) desde una IP que no es de IT
3. Severidad CRÍTICA si el destino es dc01.local o similar.
MITRE: T1021 (Remote Services)

PATRÓN 4: patterns/volume_anomaly.py — VOLUMEANOMALYPattern
Detecta: volumen de tráfico anormalmente alto (posible exfiltración).

Algoritmo:
1. Mantener en Redis el volumen acumulado por IP interna en ventanas de 1h.
   Key: "pattern:volume:{ip}:{hora_del_dia}" → int (bytes)
2. Comparar con el baseline de la identidad (volumen_mb_dia_media)
3. DETECCIÓN si el volumen de la última hora supera:
   - intensity="alta": > 5x el volumen horario promedio
   - intensity="media": > 3x (solo fuera del horario laboral)
4. También detectar: muchas conexiones a servicios de cloud storage
   (drive.google.com, dropbox.com, mega.nz, wetransfer.com) en < 30 min.
MITRE: T1048 (Exfiltration Over Alternative Protocol)

PATRÓN 5: patterns/time_anomaly.py — TIMEANOMALYPattern
Detecta: actividad en horarios inusuales para el usuario.

Algoritmo:
1. Para cada evento, verificar:
   a) ¿El usuario tiene baseline válido? (>7 días)
   b) ¿El evento ocurre fuera del horario habitual del usuario?
   c) ¿El volumen del evento es significativo? (>10MB o dominio no habitual)
2. DETECCIÓN si evento fuera de horario + (volumen alto OR dominio nuevo)
3. Severidad basada en:
   - Entre medianoche y 5am: ALTA
   - Fin de semana si no es habitual: MEDIA
   - Fuera de horario ±3h: BAJA
4. Suprimir falsos positivos: si la persona tiene
   probabilidad_anomalia alta (IT, Gerencia), elevar el umbral.
MITRE: T1078 (Valid Accounts)

TAMBIÉN CREAR: correlator/main.py
Loop principal del correlator que:
1. Consume eventos de events:enriched
2. Para cada evento, corre TODOS los patrones en paralelo
3. Actualiza baseline async
4. Si algún patrón retorna Incidente: publicar en events:alerts y guardar en MongoDB
5. Actualizar risk_score de la identidad en MongoDB

REGLAS:
- Cada patrón es independiente. No comparten estado entre sí.
- Los contextos históricos se guardan en Redis con TTL apropiado.
- Un evento puede disparar múltiples patrones simultáneamente.
- Los incidentes duplicados (mismo patrón, mismo host, < 30 min) no se vuelven a crear.

NO HAGAS:
- No accedas a MongoDB desde los patrones individualmente.
  El correlator/main.py es el único que escribe a la base de datos.
- No hagas que un patrón tarde más de 100ms en evaluar un evento.
- No uses regex complejas para detectar entropía. Implementar el algoritmo directamente.
```

---

### PROMPT 15 — Security Dev
**Rol:** Security Engineer  
**Componente:** risk_score.py y honeypot.py  
**Entregable:** Los dos archivos de soporte del correlator

```
Sos un Security Engineer especializado en sistemas de scoring de riesgo.

ARCHIVO 1: correlator/risk_score.py

Clase RiskScoreEngine que calcula el risk score dinámico de una identidad.

El risk score es un número entre 0 y 100 que representa el nivel de
riesgo actual de una identidad. Tiene INERCIA: si ayer fue alto,
hoy el umbral para volver a subir es más bajo.

ALGORITMO:

```python
def calcular_nuevo_score(
    score_actual: int,
    anomalia_score: float,      # 0.0-1.0 del baseline
    enrichment_score: float,    # 0.0-1.0 según reputación
    patron_score: float,        # 0.0-1.0 si algún patrón disparó
    historial_clean_days: int   # días consecutivos sin anomalías
) -> int:
    
    # Factor de inercia: si el score fue alto recientemente, baja más lento
    decay_rate = 0.85 if score_actual > 60 else 0.70
    
    # Score base por los factores del evento actual
    evento_score = (
        anomalia_score * 30 +
        enrichment_score * 40 +
        patron_score * 30
    ) * 100
    
    # Historial limpio baja el score más rápido
    clean_bonus = min(historial_clean_days * 5, 30)
    
    # Nuevo score: mezcla ponderada de actual y nuevo evento
    nuevo = score_actual * decay_rate + evento_score * (1 - decay_rate)
    nuevo = max(0, nuevo - clean_bonus)
    
    return min(100, int(nuevo))
```

Método adicional: get_severidad(score: int) -> tuple[str, str]:
Retorna (nivel, color_hex) según umbrales:
- 80-100: ("critica", "#FF4757")
- 60-79: ("alta", "#FFA502")
- 40-59: ("media", "#FFDD57")
- 20-39: ("baja", "#7BED9F")
- 0-19: ("info", "#70A1FF")

ARCHIVO 2: correlator/honeypot.py

Clase HoneypotManager que define y monitorea los recursos trampa.

HONEYPOTS DEFINIDOS (hardcodeados en la clase, configurables via .env):
```python
HONEYPOTS = {
    "share_financiero": {
        "tipo": "share",
        "indicador": "\\\\fileserver01\\BACKUP_FINANCIERO_2025",
        "descripcion": "Share de red con nombre atractivo — no existe para usuarios reales"
    },
    "ip_fantasma": {
        "tipo": "ip_fantasma", 
        "indicador": "192.168.1.254",
        "descripcion": "IP sin servicios reales — cualquier conexión es sospechosa"
    },
    "usuario_trampa": {
        "tipo": "usuario_ad",
        "indicador": "admin_old",
        "descripcion": "Usuario de AD deshabilitado — login exitoso imposible legítimamente"
    },
    "dns_trampa": {
        "tipo": "dns_interno",
        "indicador": "old-erp.empresa.local",
        "descripcion": "Registro DNS interno que no debería ser consultado"
    }
}
```

Método: async def check_event(self, evento: Evento) -> Optional[HoneypotHit]
- Verifica si el evento involucra alguno de los recursos trampa
- Revisa: externo.valor, interno.ip, cualquier campo que pueda contener el indicador
- Si match: crear HoneypotHit, guardar en MongoDB, publicar alerta CRÍTICA inmediata (usar MongoDB Change Stream)

REGLAS:
- Los honeypot hits son SIEMPRE severidad CRÍTICA, sin excepciones.
- No tienen falsos positivos por definición. Si algo los toca, es alerta.
- El risk_score del involucrado sube inmediatamente a mínimo 85.
```

---

## ⚡ FASE 3 — API y Dashboard

---

### PROMPT 16 — Backend Dev
**Rol:** Backend Developer  
**Componente:** FastAPI — main.py y todos los routers  
**Entregable:** Backend API completamente funcional

```
Sos un Backend Developer Python senior especializado en FastAPI y APIs REST.

Tu tarea es implementar el backend API de CyberPulse LATAM.
Esta API es consumida por el dashboard React via REST y WebSocket.

ARCHIVO: api/main.py

Configurar FastAPI con:
- Título: "CyberPulse LATAM API"
- Versión: "1.0.0"
- CORS habilitado para http://localhost:3000 (y dominio de producción desde .env)
- Lifespan para inicializar conexiones a Redis y MongoDB al arrancar
- Incluir todos los routers con prefijo /api/v1
- Endpoint de salud: GET /health → {"status": "ok", "timestamp": "..."}

ROUTER 1: api/routers/events.py
GET /events
  - Query params: limit=50, offset=0, source=None, desde=None, hasta=None
  - Retorna lista de Evento desde MongoDB ordenados por timestamp DESC
  - Soporte para filtrar por source y rango de fechas

GET /events/{event_id}
  - Retorna un Evento completo con todos sus campos

GET /events/stats
  - Retorna: total eventos hoy, por fuente, por severidad, top 10 dominios maliciosos

ROUTER 2: api/routers/identities.py
GET /identities
  - Lista de todas las identidades con risk_score_actual
  - Ordenadas por risk_score DESC
  - Query param: area=None para filtrar por área

GET /identities/{identidad_id}
  - Retorna Identidad completa con baseline y eventos recientes (últimas 24h)

GET /identities/{identidad_id}/timeline
  - Retorna los últimos 100 eventos de esa identidad ordenados por timestamp

ROUTER 3: api/routers/incidents.py
GET /incidents
  - Lista de incidentes, filtrable por estado y severidad
  - Ordenados por created_at DESC

GET /incidents/{incident_id}
  - Incidente completo con todos los eventos relacionados expandidos

POST /incidents/{incident_id}/estado
  - Body: {"estado": "investigando"|"cerrado"|"falso_positivo"}
  - Actualiza el estado del incidente

ROUTER 4: api/routers/alerts.py
GET /alerts/honeypots
  - Lista de HoneypotHits ordenados por timestamp DESC
  - Siempre criticidad máxima

GET /alerts/summary
  - Resumen ejecutivo: N incidentes abiertos, N críticos, N honeypot hits hoy,
    identidad de mayor riesgo, dominio malicioso más consultado

ROUTER 5: api/routers/simulator.py (solo si LAB_MODE=true)
POST /simulator/scenario
  - Body: {"scenario": "phishing", "target": "ventas.garcia", "intensity": "media"}
  - Dispara un escenario de ataque en el simulador
  - Retorna {"status": "started", "scenario_id": "..."}

GET /simulator/status
  - Estado actual del simulador: personas activas, eventos/min, modo activo

ROUTER 6: api/routers/ai.py
GET /ai/memos
  - Lista de AiMemos ordenados por created_at DESC, limit=20

POST /ai/analyze/{incident_id}
  - Dispara análisis de Claude sobre un incidente
  - Es async: retorna {"status": "processing", "memo_id": "..."} inmediatamente
  - El resultado llega por WebSocket

POST /ai/ceo-view
  - Genera el análisis en lenguaje ejecutivo del estado actual
  - Retorna el memo generado (puede tardar 5-10 segundos, es OK hacer await)

REGLAS:
- Todos los endpoints retornan siempre el mismo formato de respuesta:
  {"data": ..., "total": N (solo en listas), "timestamp": "ISO8601"}
- Errores: {"error": "mensaje", "code": "ERROR_CODE"}
- Paginación en todas las listas
- Ningún endpoint hace operaciones que tarden más de 2 segundos
  (las operaciones lentas son async background tasks)

NO HAGAS:
- No hagas lógica de negocio en los routers. Solo reciben requests,
  llaman a funciones de servicio y retornan respuestas.
- No uses ORM. Queries directas con motor.
- No expongas información sensible como API keys o IPs internas en errores.
- No hagas endpoints sin validación de tipos (usar Pydantic para body y query params).
```

---

### PROMPT 17 — Backend Dev
**Rol:** Backend Developer  
**Componente:** WebSocket — tiempo real al dashboard  
**Entregable:** api/websocket.py con push de eventos en tiempo real

```
Sos un Backend Developer especializado en comunicaciones en tiempo real
con WebSockets y sistemas de eventos.

Tu tarea es implementar el sistema de WebSocket que hace push de eventos
al dashboard React en tiempo real.

ARCHIVO: api/websocket.py

Usar python-socketio con FastAPI (modo ASGI).

EVENTOS QUE EL SERVIDOR EMITE AL CLIENTE:

1. "new_event"
   Payload: Evento enriquecido completo (JSON)
   Cuándo: cada nuevo evento que llega a events:enriched
   Rate limit: máximo 50 eventos/segundo al cliente
   Si hay más: agrupar en batches de hasta 20 eventos

2. "new_alert"
   Payload: Incidente completo (JSON)
   Cuándo: cada vez que el correlator detecta un nuevo incidente
   Sin rate limit: las alertas siempre llegan inmediatamente

3. "honeypot_hit"
   Payload: HoneypotHit completo (JSON)
   Cuándo: cuando se activa cualquier honeypot
   Prioridad máxima: va antes que cualquier otro evento en cola

4. "identity_update"
   Payload: {"identidad_id": "...", "risk_score": N, "delta": N}
   Cuándo: cuando el risk score de una identidad cambia en más de 5 puntos
   Rate limit: máximo 1 update por identidad por segundo

5. "ai_memo"
   Payload: AiMemo completo
   Cuándo: cuando el ai_analyst genera un nuevo memo (autónomo o bajo demanda)

6. "stats_update"
   Payload: {"eventos_por_min": N, "identidades_activas": N, "alertas_abiertas": N}
   Cuándo: cada 30 segundos, automáticamente

EVENTOS QUE EL CLIENTE PUEDE ENVIAR AL SERVIDOR:

1. "subscribe_identity"
   Payload: {"identidad_id": "..."}
   Acción: el cliente recibe todos los eventos de esa identidad específica

2. "request_ceo_view"
   Acción: dispara generación de ceo_view en ai_analyst, retorna en "ai_memo"

ARQUITECTURA INTERNA:
El websocket.py escucha el Redis PubSub channel "dashboard:events"
El correlator y el enricher publican en ese channel cuando tienen algo nuevo.
El websocket distribuye a todos los clientes conectados.

Usar rooms de socket.io para que clientes que se suscriben a una identidad
solo reciban eventos de esa identidad.

REGLAS:
- Soportar múltiples clientes simultáneos (hasta 50 conexiones)
- Al conectar un cliente nuevo: enviarle el estado actual (últimos 10 eventos,
  todas las identidades con risk > 40, últimos 5 memos de AI)
- Heartbeat cada 30 segundos para detectar conexiones muertas
- Reconexión automática en el cliente (implementar en el hook de React)

NO HAGAS:
- No uses polling. Todo debe ser push via WebSocket.
- No envíes eventos al cliente más rápido de lo que puede procesar.
- No olvides limpiar las suscripciones cuando el cliente desconecta.
```

---

### PROMPT 18 — UI/UX Designer
**Rol:** UI/UX Designer  
**Componente:** Sistema de diseño y componentes base  
**Entregable:** Sistema de diseño documentado + componentes base de React

```
Sos un UI/UX Designer especializado en interfaces de seguridad (Security Operations
Centers) y dashboards de datos en tiempo real.

Tu tarea es definir el sistema de diseño de CyberPulse LATAM e implementar
los componentes de UI más básicos y reutilizables.

PALETA DE COLORES (exactamente estos valores, no modificar):
- Background principal: #0D1117
- Background de cards: #161B22
- Background de cards hover: #1A2030
- Border por defecto: #21262D
- Texto principal: #E6EDF3
- Texto secundario: #8B949E
- Acento cyan (primario): #00D4FF
- Acento verde (éxito/limpio): #00FF88
- Acento rojo (crítico): #FF4757
- Acento naranja (advertencia): #FFA502
- Acento purple (info): #7B68EE

TIPOGRAFÍA:
- Fuente: Inter (Google Fonts)
- Tamaños: 11px (label), 13px (body), 15px (subtitle), 20px (title), 28px (hero)
- Monospace (para IPs, dominios, código): JetBrains Mono

SISTEMA DE RIESGO → COLOR:
```javascript
export const RISK_COLORS = {
  critica: { bg: '#FF4757', text: '#FFFFFF', label: 'CRÍTICA' },
  alta:    { bg: '#FFA502', text: '#000000', label: 'ALTA' },
  media:   { bg: '#FFDD57', text: '#000000', label: 'MEDIA' },
  baja:    { bg: '#7BED9F', text: '#000000', label: 'BAJA' },
  info:    { bg: '#70A1FF', text: '#FFFFFF', label: 'INFO' },
}

export const scoreToSeverity = (score) => {
  if (score >= 80) return 'critica'
  if (score >= 60) return 'alta'
  if (score >= 40) return 'media'
  if (score >= 20) return 'baja'
  return 'info'
}
```

IMPLEMENTAR ESTOS COMPONENTES (en dashboard/src/components/ui/):

1. RiskBadge.jsx
Props: score (int 0-100) | severidad (string)
Renderiza: píldora coloreada con el nivel y el score.
Ejemplos: [CRÍTICA 91] [ALTA 67] [MEDIA 43]
Animación: pulse suave si severidad === 'critica'

2. Card.jsx
Props: children, className, glow (bool), glowColor
Renderiza: contenedor con background #161B22, border #21262D, border-radius 8px
Si glow=true: box-shadow con el color del acento

3. StatusDot.jsx
Props: status ("online"|"offline"|"warning")
Renderiza: círculo pequeño coloreado con animación de pulse si "warning"

4. MonoText.jsx
Props: children, color
Renderiza: texto en JetBrains Mono con el color dado
Para IPs, dominios, hashes — siempre usar este componente

5. TimeAgo.jsx
Props: timestamp (ISO8601)
Renderiza: tiempo relativo en español: "hace 3 minutos", "hace 2 horas"
Se actualiza automáticamente cada 30 segundos

6. AreaBadge.jsx
Props: area (string)
Cada área tiene un color consistente (hashear el nombre del área para el color)

7. Skeleton.jsx
Props: width, height
Renderiza: placeholder animado con shimmer effect para estados de carga
Usar background linear-gradient animado con los colores del tema

TAMBIÉN CREAR: dashboard/src/styles/globals.css
- Variables CSS con toda la paleta de colores
- Reset básico
- Scrollbar personalizado (thin, dark)
- Animaciones: pulse, fadeIn, slideInRight

REGLAS:
- Todo en CSS variables para theming consistente.
- No usar Material UI, Chakra, ni ninguna biblioteca de componentes.
  Solo Tailwind utilities y CSS custom cuando Tailwind no alcance.
- Los componentes deben ser dark-mode by default. No hay modo claro.
- Accesibilidad: todos los elementos interactivos tienen aria-label.

NO HAGAS:
- No uses colores fuera de la paleta definida sin justificación.
- No uses animaciones que distraigan en una interfaz de seguridad.
  Solo pulse para críticos y fadeIn para nuevos elementos.
- No hagas componentes que consuman datos directamente.
  Todos reciben props, el fetching es responsabilidad de las views.
```

---

### PROMPT 19 — Frontend Dev
**Rol:** Frontend Developer  
**Componente:** Dashboard — las 4 vistas principales  
**Entregable:** NetworkMap.jsx, Timeline.jsx, Identities.jsx, AttackInjector.jsx

```
Sos un Frontend Developer React senior especializado en dashboards de datos
en tiempo real y visualizaciones de seguridad.

Tu tarea es implementar las 4 vistas principales del dashboard de CyberPulse LATAM.
Usar el sistema de diseño ya definido (componentes de /ui/ y paleta de colores).

ESTADO GLOBAL (Zustand store — dashboard/src/store/index.js):
```javascript
// Ya implementado. Disponible via useStore():
{
  events: [],           // últimos 500 eventos
  identities: {},       // mapa id → Identidad
  incidents: [],        // incidentes abiertos
  alerts: [],           // alertas recientes
  aiMemos: [],          // memos de AI
  stats: {},            // estadísticas generales
  isLabMode: bool,      // si LAB_MODE=true en el servidor
  
  // Acciones:
  addEvent, updateIdentity, addIncident, addAlert, addAiMemo, updateStats
}
```

VISTA 1: NetworkMap.jsx
Grafo interactivo de la red interna usando D3.js o React Flow.

Cada nodo:
- Representa una Identidad (usuario + dispositivo)
- Tamaño: proporcional al riesgo actual
- Color: según scoreToSeverity(risk_score)
- Label: usuario + área
- Al hacer hover: mostrar tooltip con últimas 3 acciones

Cada arista:
- Representa una conexión activa (evento en los últimos 5 minutos)
- Grosor: proporcional al volumen de tráfico
- Color: cyan para conexiones normales, rojo para conexiones sospechosas

Comportamiento en tiempo real:
- Cuando llega un "new_event" por WebSocket: animar el nodo correspondiente
- Cuando llega un "new_alert": el nodo involucrado pulsa en rojo por 5 segundos
- Las aristas aparecen y desaparecen según la actividad reciente

Panel lateral al hacer click en un nodo:
- Nombre, área, IP, hostname
- Risk score con el RiskBadge
- Últimos 5 eventos (con MonoText para dominios)
- Botón: "Ver timeline completo"

VISTA 2: Timeline.jsx
Feed vertical de eventos en tiempo real.

Cada IncidentCard muestra:
- Timestamp (con TimeAgo)
- Usa SVGs acordes según source (DNS:, Proxy:, Firewall: , Wazuh:, Endpoint:)
- Identidad involucrada (con AreaBadge)
- Descripción del evento en una línea
- RiskBadge si tiene risk_score > 40
- Si es un incidente (no solo evento): borde izquierdo coloreado según severidad

Comportamiento:
- Los nuevos eventos se insertan al tope con animación fadeIn
- Scroll automático si el usuario está al tope; si scrolleó hacia abajo, mostrar
  badge "N nuevos eventos" que al hacer click vuelve al tope
- Filtros en la barra superior: por source, por severidad mínima, por área
- Al hacer click en un evento: expandir y mostrar contexto completo + eventos correlacionados

VISTA 3: Identities.jsx
Tabla/grid de todas las identidades ordenadas por risk_score.

Para cada identidad, mostrar:
- Avatar con inicial del nombre
- Nombre completo + área (con AreaBadge)
- Dispositivo y hostname (con MonoText)
- RiskBadge con el score actual
- Mini sparkline de los últimos 24h de risk_score (usar recharts SparkLine)
- StatusDot indicando si está activa ahora (actividad en últimos 30 minutos)
- Delta del score: flecha ↑ si subió, ↓ si bajó en las últimas 2 horas

Al hacer click en una identidad:
- Drawer lateral con:
  * Timeline de los últimos 50 eventos
  * Baseline: horario habitual, dominios frecuentes, volumen típico
  * Desviaciones actuales respecto al baseline

VISTA 4: AttackInjector.jsx (solo visible si isLabMode === true)
Panel flotante en la esquina inferior derecha.

Contenido:
- Botón principal: "Inyectar Ataque"
- Al hacer click: modal con:
  * Dropdown de escenario: phishing | ransomware | dns_tunneling | lateral_movement | exfiltration
  * Dropdown de target: lista de identidades disponibles
  * Radio buttons de intensidad: baja | media | alta
  * Descripción del escenario seleccionado
  * Botón "Ejecutar"
- Feedback: toast de confirmación + indicador "Ataque en progreso..." con timer

También mostrar en este panel:
- Estadísticas del simulador: personas activas, eventos/min
- Log de los últimos 3 ataques inyectados

REGLAS:
- Todas las vistas usan useStore() para leer el estado
- El WebSocket ya está conectado en App.jsx antes de renderizar las vistas
- No hacer fetch() desde las vistas — usar datos del store que llegan por WebSocket
- Sí hacer fetch para datos históricos al montar la vista (useEffect)
- Lazy loading de vistas con React.lazy() para no cargar todo junto

NO HAGAS:
- No rendericés todos los eventos en el DOM (virtualización para listas largas).
  Usar react-window o react-virtual para el Timeline.
- No hagas que el mapa redibuje completamente con cada evento.
  Actualizar solo los nodos afectados con D3 transitions.
- No uses setTimeout en los componentes. Todo timing es manejado por WebSocket.
- No muestres IPs internas en la vista CEO (ofuscar como "Dispositivo #N").
- No uses iconos de emojis ni nada que refiera a hecho por IA, usa SVGs acordes según source (DNS:, Proxy:, Firewall: , Wazuh:, Endpoint:)
```

---

## 🧠 FASE 4 — Inteligencia Artificial

---

### PROMPT 20 — AI Engineer
**Rol:** 🧠 AI / Prompt Engineer  
**Componente:** ai_analyst — todos los archivos  
**Entregable:** Sistema completo de IA integrado

```
Sos un AI Engineer especializado en integración de LLMs en sistemas de producción
y en ingeniería de prompts para aplicaciones de seguridad.

Tu tarea es implementar el módulo completo de IA de CyberPulse LATAM.
La IA es Claude (Anthropic), modelo claude-sonnet-4-20250514.

ARCHIVO 1: ai_analyst/autonomous_analyst.py

El analista autónomo corre en background y genera memos proactivos.

```python
class AutonomousAnalyst:
    ANALYSIS_INTERVAL = 900  # cada 15 minutos
    
    async def run(self) -> None:
        """Loop infinito que corre el análisis cada ANALYSIS_INTERVAL segundos"""
    
    async def analyze_current_state(self) -> Optional[AiMemo]:
        """
        1. Recopilar contexto: últimos 500 eventos (últimos 15 min),
           identidades con risk_score > 40, incidentes abiertos,
           honeypot hits de las últimas 24h.
        
        2. Si no hay nada interesante (todos los scores < 30, sin incidentes):
           no generar memo (retornar None). Ahorrar tokens.
        
        3. Llamar a Claude con el prompt de autonomous.txt + el contexto.
        
        4. Parsear la respuesta (ver formato más abajo).
        
        5. Guardar en MongoDB y publicar en WebSocket.
        """
    
    def _build_context_summary(self, eventos, identidades, incidentes) -> str:
        """
        Construye un resumen compacto del estado actual para incluir en el prompt.
        Formato diseñado para ser informativo pero no desperdiciar tokens.
        Máximo 2000 tokens de contexto.
        """
```

ARCHIVO 2: ai_analyst/incident_analyzer.py

Analiza un incidente específico bajo demanda.

```python
class IncidentAnalyzer:
    
    async def analyze(self, incident_id: str) -> AiMemo:
        """
        1. Cargar el incidente con todos sus eventos relacionados
        2. Cargar el baseline de la identidad involucrada
        3. Cargar los últimos 7 días de historia de esa identidad
        4. Llamar a Claude con prompt de incident.txt + contexto del incidente
        5. Retornar AiMemo con tipo="incidente"
        """
```

ARCHIVO 3: ai_analyst/ceo_translator.py

Genera el resumen ejecutivo del estado actual.

```python
class CeoTranslator:
    
    async def generate(self) -> AiMemo:
        """
        1. Recopilar: incidentes abiertos críticos y altos, risk scores actuales,
           honeypot hits, principales amenazas detectadas.
        2. Llamar a Claude con prompt de ceo_view.txt
        3. La respuesta debe estar en lenguaje de negocio, sin términos técnicos.
        4. Retornar AiMemo con tipo="ceo"
        """
```

ARCHIVO 4: ai_analyst/prompts/autonomous.txt

```
Sos el analista de seguridad de CyberPulse, un sistema de monitoreo de
ciberseguridad para una empresa latinoamericana.

Tu tarea es analizar el estado actual de la red y determinar si hay algo
que merezca atención. No sos un sistema de alertas automáticas — sos un analista
que razona sobre patrones, correlaciones y contexto.

CONTEXTO ACTUAL DE LA RED:
{context}

INSTRUCCIONES:
1. Si no hay nada relevante, respondé SOLO con: {"prioridad": "ninguna"}
2. Si hay algo relevante, respondé en JSON con este formato exacto:
{
  "prioridad": "critica|alta|media|info",
  "titulo": "Una línea descriptiva del hallazgo",
  "contenido": "Análisis detallado en español. Explicá: qué detectaste,
    por qué es relevante, qué podría significar, qué recomendás hacer.
    Máximo 3 párrafos. Lenguaje técnico pero claro.",
  "eventos_clave": ["evt_id_1", "evt_id_2"],
  "accion_inmediata": "Una sola acción concreta y específica que hay que hacer ahora."
}

REGLAS:
- No inventés datos que no están en el contexto.
- No repitas información que el sistema ya alertó (está en incidentes abiertos).
- Priorizá la originalidad del análisis sobre la completitud.
- Si ves un patrón que los detectores automáticos no marcaron, eso es valioso.
- Respondé SOLO JSON. Sin texto antes ni después.
```

ARCHIVO 5: ai_analyst/prompts/incident.txt

```
Sos el analista de seguridad de CyberPulse analizando un incidente específico.

DATOS DEL INCIDENTE:
{incident}

BASELINE DE LA IDENTIDAD INVOLUCRADA:
{baseline}

HISTORIA DE ACTIVIDAD (últimos 7 días):
{history}

Tu análisis debe cubrir:
1. CRONOLOGÍA: Cómo empezó el incidente, qué eventos lo componen en orden temporal.
2. TÉCNICA: Qué tipo de ataque o comportamiento representa (en términos de MITRE ATT&CK si aplica).
3. IMPACTO POTENCIAL: Qué datos o sistemas podrían estar en riesgo.
4. CERTEZA: ¿Estás seguro de que es un incidente real? ¿Podría ser un falso positivo?
5. PRÓXIMOS PASOS: Lista de 3-5 acciones concretas ordenadas por prioridad.

Respondé en JSON:
{
  "titulo": "...",
  "cronologia": "...",
  "tecnica": "...",
  "impacto": "...",
  "certeza": "alta|media|baja",
  "razon_certeza": "...",
  "pasos": ["paso 1", "paso 2", "paso 3"]
}

Respondé SOLO JSON. Sin texto adicional.
```

ARCHIVO 6: ai_analyst/prompts/ceo_view.txt

```
Sos el asesor de seguridad de una empresa. Tu audiencia es el CEO o Director General,
que no tiene conocimientos técnicos de ciberseguridad.

ESTADO ACTUAL DE SEGURIDAD:
{estado}

Escribí un resumen ejecutivo que:
- Use lenguaje de negocio. NUNCA uses: CVE, IP, puerto, CIDR, payload, exploit,
  hash, IOC, TTPs, SIEM, ASN. Si necesitás mencionar un sistema, usá su nombre
  comercial o describilo ("el servidor de archivos de RRHH").
- Tenga máximo 3 párrafos.
- Párrafo 1: Estado general (¿estamos bien o hay algo preocupante?).
- Párrafo 2: Lo más importante que está pasando ahora (si hay algo).
- Párrafo 3: Qué debe hacer el equipo de IT hoy.

Si no hay nada relevante, decilo directamente: "La red opera con normalidad."

Respondé solo con el texto de los párrafos, sin JSON, sin bullets, sin títulos.
```

REGLAS DE IMPLEMENTACIÓN:
- Usar anthropic Python SDK oficial (pip install anthropic)
- Siempre manejar: RateLimitError, APIError, timeout (30 segundos máximo)
- Si Claude falla, loggear el error y retornar None (el sistema sigue operando)
- No hacer más de 10 llamadas a Claude por hora en total (entre todos los analistas)
- Loggear: timestamp, tipo de análisis, tokens usados (input + output), latencia

NO HAGAS:
- No pases el historial completo de eventos a Claude. Resumir primero.
- No hagas llamadas síncronas a Claude. Siempre async.
- No reintentar más de 1 vez si Claude falla.
- No loggees el contenido de los prompts completos (pueden contener datos sensibles).
```

---

## 🧪 FASE 5 — Testing y Calidad

---

### PROMPT 21 — QA Engineer
**Rol:** 🧪 QA Engineer  
**Componente:** Suite de tests — collector y enricher  
**Entregable:** tests/ con cobertura mínima del 80%

```
Sos un QA Engineer especializado en testing de sistemas de seguridad y
pipelines de datos en tiempo real.

Tu tarea es crear la suite de tests para el collector y el enricher.
Usar pytest + pytest-asyncio. No usar unittest.

ESTRUCTURA DE ARCHIVOS A CREAR:
tests/
├── conftest.py            (fixtures compartidas)
├── test_normalizer.py
├── test_dns_parser.py
├── test_enricher.py
├── test_cache.py
└── test_feeds.py

CONFTEST.PY — Fixtures necesarias:
```python
@pytest.fixture
def evento_dns_sample():
    """Retorna un Evento DNS válido de ejemplo para tests"""

@pytest.fixture
def evento_proxy_sample():
    """Retorna un Evento de proxy válido"""

@pytest.fixture
async def redis_mock():
    """Mock de RedisBus para tests unitarios (no necesita Redis real)"""

@pytest.fixture
async def redis_real():
    """Conexión real a Redis para tests de integración (usa Redis local)"""
    # Marcar con @pytest.mark.integration
```

TEST_NORMALIZER.PY — Tests del normalizer:

Casos a cubrir:
- normalize_dns_valido: log de PiHole válido → Evento correcto
- normalize_dns_dominio_interno: dominio .local → retorna None
- normalize_dns_timestamp_formats: probar los 5 formatos de timestamp
- normalize_proxy_url_valida: log Squid → extrae dominio correctamente
- normalize_proxy_url_malformada: URL sin scheme → maneja sin crash
- normalize_firewall_ip_interna_src: origen interno, destino externo
- normalize_firewall_ip_interna_dst: destino interno, origen externo
- normalize_wazuh_level_bajo: level 2 → retorna None (bajo umbral)
- normalize_wazuh_level_alto: level 10 → retorna Evento con risk_score base correcto
- normalize_campos_faltantes: raw_log sin campos opcionales → no crashea
- normalize_ip_invalida: IP malformada → retorna None
- evento_tiene_id_unico: dos normalizaciones del mismo raw_log → IDs distintos
- evento_timestamp_utc: timestamp resultado siempre tiene timezone UTC

TEST_DNS_PARSER.PY:
- parse_line_query_a: línea tipo "query[A]" → dict correcto
- parse_line_query_aaaa: línea tipo "query[AAAA]" → dict correcto
- parse_line_blocked: línea "gravity blocked" → dict con blocked=True
- parse_line_reply: línea "reply" → retorna None (no es query)
- parse_line_cached: línea "cached" → retorna None
- parse_line_dominio_arpa: PTR query → retorna None (dominio interno)
- parse_line_formato_invalido: línea random → retorna None sin crashear
- is_internal_domain_local: "server.empresa.local" → True
- is_internal_domain_arpa: "47.101.220.185.in-addr.arpa" → True
- is_internal_domain_externo: "google.com" → False

TEST_ENRICHER.PY (con mocks de APIs externas):
- enrich_ip_en_cache: IP ya en caché → no llama a ninguna API
- enrich_ip_en_blocklist: IP en Spamhaus → retorna malicioso sin llamar API
- enrich_ip_limpia: IP limpia → llama a AbuseIPDB (mock), retorna limpio
- enrich_dominio_urlhaus: dominio en URLhaus → retorna malicioso
- enrich_con_api_rate_limit: API retorna 429 → no falla, usa siguiente API
- enrich_todas_apis_fallan: timeout en todas → retorna desconocido
- enrich_guarda_en_cache: enriquecimiento exitoso → guardado en Redis
- enrich_cache_expira: TTL 1 segundo → después de 1 seg ya no está en caché

TEST_CACHE.PY:
- cache_set_get: guardar y recuperar Enrichment
- cache_miss: key que no existe → retorna None
- cache_ttl: after TTL → key expirada → retorna None
- cache_stats: hit_rate correcto después de N hits y M misses

REGLAS:
- Todos los tests que necesiten Redis usan redis_mock por default.
  Los tests marcados @pytest.mark.integration usan redis_real.
- Correr tests con: pytest tests/ -v --ignore-integration
- Correr integration con: pytest tests/ -v -m integration
- Cada test debe ser independiente. Limpiar estado después de cada uno.
- Los mocks de APIs usan respuestas reales capturadas (fixtures JSON).
  No inventar respuestas de APIs que no coincidan con la realidad.

NO HAGAS:
- No testees la lógica de negocio de las APIs externas (eso es su responsabilidad).
- No hagas tests que dependan del orden de ejecución.
- No uses time.sleep() en tests. Usar pytest-asyncio con asyncio.sleep() si es necesario.
- No muevas los tests a la misma carpeta que el código fuente.
```

---

### PROMPT 22 — Tester
**Rol:** 🧪 Integration Tester / Red Team  
**Componente:** Tests end-to-end de escenarios de ataque  
**Entregable:** tests/e2e/ con tests de escenarios completos

```
Sos un Integration Tester y Red Teamer especializado en verificar que los
sistemas de detección funcionan correctamente de punta a punta.

Tu tarea es crear los tests end-to-end que verifican que cada escenario
de ataque del simulador es correctamente detectado por el correlator.

ESTRUCTURA:
tests/e2e/
├── conftest_e2e.py         (fixtures que levantan el stack completo)
├── test_e2e_beaconing.py
├── test_e2e_phishing.py
├── test_e2e_ransomware.py
├── test_e2e_dns_tunneling.py
└── test_e2e_false_positives.py

CONFTEST_E2E.PY:
Fixtures que usan el stack real (Redis + MongoDB + todos los servicios).
Marcar todos como @pytest.mark.e2e.

```python
@pytest.fixture(scope="session")
async def full_stack():
    """
    Levanta el stack completo via docker-compose --profile lab.
    Espera a que todos los servicios estén healthy.
    Al finalizar la sesión de tests, limpia todos los datos creados.
    """

@pytest.fixture
async def clean_state(full_stack):
    """Limpia Redis y MongoDB antes de cada test e2e."""
```

TEST_E2E_BEACONING.PY:
```python
async def test_beaconing_detectado(full_stack, clean_state):
    """
    1. Inyectar escenario de beaconing: 10 consultas al mismo dominio
       cada 5 minutos exactos para la identidad "ventas.garcia"
    2. Esperar hasta 120 segundos (timeout)
    3. Verificar en MongoDB: existe un documento en la colección incidents con:
       - titulo que contiene "beaconing" o "C2" o "beacon"
       - identidad involucrada: "ventas.garcia"
       - severidad: "alta" o "critica"
    4. Verificar en Redis: risk_score de ventas.garcia > 60
    """

async def test_beaconing_no_dispara_en_trafico_normal(full_stack, clean_state):
    """
    Inyectar 5 consultas al mismo dominio con intervalos IRREGULARES (navegación normal).
    Verificar que NO se genera un incidente de beaconing.
    Esperar 60 segundos y confirmar que el correlator no creó incidente.
    """
```

TEST_E2E_PHISHING.PY:
```python
async def test_phishing_correlacionado(full_stack, clean_state):
    """
    1. Inyectar phishing a 3 usuarios del área de RRHH simultáneamente.
    2. Verificar que los 3 eventos se correlacionan en UN SOLO incidente
       (no 3 incidentes separados).
    3. El incidente debe referenciar los 3 eventos como correlaciones.
    """
```

TEST_E2E_FALSE_POSITIVES.PY — CRÍTICO:
```python
async def test_reunion_equipo_no_es_phishing(full_stack, clean_state):
    """
    3 usuarios del mismo área consultan youtube.com en 30 minutos.
    (Están viendo un video juntos en la sala de reuniones).
    Verificar que NO se genera incidente de phishing.
    youtube.com está en la categoría de dominios conocidos.
    """

async def test_backup_nocturno_no_es_exfiltracion(full_stack, clean_state):
    """
    El servidor de backup genera 2GB de tráfico a las 2am (backup programado).
    Verificar que el sistema NO lo trata como exfiltración
    si la identidad del servidor tiene ese patrón en su baseline.
    """

async def test_desarrollador_it_accediendo_servidores(full_stack, clean_state):
    """
    Usuario de IT accede a dc01.local, fileserver01, y backup01 en 10 minutos.
    Su baseline incluye esos servidores.
    Verificar que NO se genera alerta de movimiento lateral.
    """
```

MÉTRICAS DE ÉXITO QUE DEBEN PASAR:
- Tasa de detección de ataques simulados: >= 90%
- Falsos positivos en tráfico normal: <= 5%
- Tiempo desde evento hasta alerta: <= 60 segundos (p95)
- Tiempo desde evento hasta memo de AI: <= 20 minutos

REGLAS:
- Cada test e2e tiene un timeout máximo de 3 minutos.
- Los tests e2e corren en el CI solo en la rama main.
- Si un test e2e falla, se guarda el log completo de eventos como artefacto.
- Los tests de falsos positivos son TAN importantes como los de detección.

NO HAGAS:
- No mockees nada en los tests e2e. Debe ser el sistema real completo.
- No dependas del orden de ejecución de los tests.
- No hagas aserciones sobre el TEXTO exacto de las alertas (puede cambiar).
  Verificar campos estructurales: severidad, identidad, eventos_ids.
```

---

## 🚀 FASE 6 — Producción

---

### PROMPT 23 — DevOps Engineer
**Rol:** 🚀 DevOps / Production Engineer  
**Componente:** docker-compose.prod.yml y hardening  
**Entregable:** Configuración lista para producción

```
Sos un DevOps Engineer especializado en seguridad de infraestructura y
deployment de aplicaciones de seguridad en entornos productivos.

Tu tarea es crear la configuración de producción de CyberPulse LATAM,
diferente del laboratorio en varios aspectos clave.

ARCHIVO: docker-compose.prod.yml

Diferencias respecto al laboratorio:
1. Sin el servicio "simulator" (usa perfil --profile lab que no se activa en prod)
2. Sin el pihole de Docker (la red real ya tiene su propio DNS)
3. El collector monta los logs REALES de la empresa (rutas configurables via .env)
4. Recursos limitados explícitamente (memory limits, cpu shares)
5. Logging configurado para enviar a archivo rotativo + syslog
6. Sin puertos mapeados al exterior excepto dashboard (3000) y api (8000)
7. Red privada más restrictiva

VARIABLES DE ENTORNO ADICIONALES PARA PRODUCCIÓN:
- DNS_LOG_PATH: ruta al log real del DNS interno de la empresa
- PROXY_LOG_PATH: ruta al log de Squid/NGINX real
- FIREWALL_LOG_PATH: ruta al log del firewall real
- WAZUH_API_URL: URL de la API de Wazuh self-hosted
- WAZUH_API_USER / WAZUH_API_PASS: credenciales de la API de Wazuh
- AD_SERVER: servidor de Active Directory para resolución de usuarios
- AD_USER / AD_PASS: credenciales de lectura para AD

ARCHIVO: collector/parsers/wazuh_api_poller.py (NUEVO para producción)
En producción, además del webhook, hacer polling a la API de Wazuh cada 60 segundos
para no depender solo de los webhooks (que pueden perderse).

GET /security/events?limit=100&offset=0 (Wazuh API v4)
Guardar el timestamp del último evento procesado en Redis.

ARCHIVO: api/middleware/auth.py
Agregar autenticación básica al dashboard:
- API key en header X-API-Key para endpoints de la API
- Leer la key válida desde variable de entorno DASHBOARD_API_KEY
- Sin autenticación: retornar 401 en todos los endpoints excepto /health
- Rate limiting: máximo 100 requests/minuto por IP (usando Redis como backend)

HARDENING CHECKLIST (como comentarios en el docker-compose.prod.yml):
- [ ] No correr contenedores como root (user: "1000:1000")
- [ ] read_only: true en los contenedores que no necesitan escribir
- [ ] security_opt: no-new-privileges:true en todos
- [ ] Limitar capabilities: cap_drop: ALL
- [ ] Volúmenes de datos no accesibles desde el exterior
- [ ] MongoDB sin mapeo de puertos al host
- [ ] Redis sin mapeo de puertos al host
- [ ] CORS restringido al dominio de producción
- [ ] Logs rotados y comprimidos automáticamente

REGLAS:
- El comando para iniciar producción es: docker-compose -f docker-compose.prod.yml up -d
- Debe funcionar sin LAB_MODE=true
- El sistema debe sobrevivir el reinicio de cualquier contenedor individual
- Los volúmenes de datos deben persistir entre actualizaciones del sistema

NO HAGAS:
- No uses :latest en producción. Fijar versiones específicas de imágenes.
- No mapees el puerto de MongoDB ni Redis al exterior.
- No dejes el DASHBOARD_API_KEY en el docker-compose.prod.yml.
  Debe venir de un archivo .env.prod que no se sube al repositorio.
- No uses el mismo .env del laboratorio para producción.
```

---

### PROMPT 24 — Tech Writer
**Rol:** 📖 Technical Writer  
**Componente:** README.md completo del proyecto  
**Entregable:** README.md que sea la documentación principal del proyecto

```
Sos un Technical Writer especializado en documentación de proyectos
de software open source de seguridad.

Tu tarea es escribir el README.md final del proyecto CyberPulse LATAM.
Este README es lo primero que ve alguien que llega al repositorio.
Debe ser completo, claro, y dar ganas de instalarlo.

SECCIONES DEL README (en este orden):

1. HEADER
   - Badge de estado (en construcción / stable)
   - Logo ASCII art o descripción visual del nombre
   - Tagline: "Motor de decisión de ciberseguridad para Latinoamérica"
   - Badges: Python 3.12, React 18, Docker, License: MIT

2. ¿QUÉ ES CYBERPULSE LATAM?
   2 párrafos. El problema que resuelve. Sin palabras de marketing vacías.

3. DIFERENCIAS CON OTRAS SOLUCIONES
   Tabla comparativa con Splunk, Darktrace, SIEM genérico, etc.

4. ARQUITECTURA EN 30 SEGUNDOS
   Diagrama ASCII de las capas del sistema.
   Un párrafo explicando el flujo de datos.

5. QUICK START — LABORATORIO
   Comandos exactos, copiables, que funcionan:
   ```bash
   git clone https://github.com/tu-org/cyber-pulse-lab
   cd cyber-pulse-lab
   cp .env.example .env
   # Editar .env con tus API keys (ver sección de API Keys)
   docker-compose --profile lab up --build
   # Dashboard en: http://localhost:3000
   # Inyectar primer ataque de prueba:
   curl -X POST http://localhost:8000/api/v1/simulator/scenario \
     -H "Content-Type: application/json" \
     -d '{"scenario": "phishing", "target": "ventas.garcia", "intensity": "media"}'
   ```

6. OBTENER API KEYS GRATUITAS
   Lista de cada API con link directo al registro:
   - AbuseIPDB: link + tiempo estimado de registro (2 minutos)
   - AlienVault OTX: link + tiempo
   - VirusTotal: link + tiempo
   Aclarar: el sistema funciona sin estas keys (usa solo blocklists locales).

7. CONFIGURACIÓN
   Tabla con todas las variables del .env.example,
   con descripción, si es requerida u opcional, y valor de ejemplo.

8. DEPLOYMENT EN PRODUCCIÓN
   Requisitos mínimos de hardware.
   Diferencias respecto al laboratorio.
   Comando de inicio en producción.

9. FUENTES DE THREAT INTEL
   Lista de todas las blocklists y APIs integradas con descripción y frecuencia de sync.

10. CONTRIBUIR
    Cómo abrir un issue, cómo hacer un PR.
    Estándares de código (black, ruff para Python; ESLint para JS).

11. LICENCIA
    MIT. Con aclaración de uso responsable.

REGLAS:
- Todos los comandos deben funcionar en macOS, Linux y Windows (WSL2).
- Los snippets de código deben tener el lenguaje especificado para syntax highlighting.
- No uses capturas de pantalla (no tenemos). Usar diagramas ASCII si es necesario.
- El README debe poder leerse en 5 minutos y dar una comprensión completa del proyecto.
- Incluir emojis con moderación: solo en títulos de secciones.

NO HAGAS:
- No pongas información de instalación de dependencias individuales.
  Docker lo maneja todo.
- No menciones precios de APIs (pueden cambiar).
- No pongas warnings de seguridad alarmistas. El sistema es legítimo.
- No dejes secciones con "TODO" o "Coming soon" visibles.
```

---

## 📌 Guía de uso de estos prompts en Cursor

### Flujo recomendado

```
1. Abrir Cursor en la carpeta del proyecto
2. Abrir el panel de Chat (Cmd+L / Ctrl+L)
3. Seleccionar el modelo: claude-sonnet o gpt-4o
4. Pegar primero el CONTEXTO GLOBAL (ver arriba)
5. Pegar el prompt del número que corresponde
6. Revisar el output ANTES de aceptar cambios
7. Correr los tests del módulo implementado
8. Solo si los tests pasan → pasar al siguiente prompt
```

### Señales de que un agente se está yendo por las ramas ("delirio técnico")

⚠️ Agregar dependencias que no están en requirements.txt  
⚠️ Crear archivos que no están en la estructura definida  
⚠️ Usar patrones de código diferentes al establecido en el módulo anterior  
⚠️ Hacer operaciones síncronas donde se pidió async  
⚠️ Escribir lógica de negocio en archivos de configuración  
⚠️ Agregar logging excesivo o insuficiente  
⚠️ Ignorar el manejo de errores  
⚠️ Hacer una clase que hace más de una cosa  

### Si el agente se desvía

Pegá este recordatorio al inicio del próximo mensaje:

```
STOP. Recordá las restricciones del sistema:
- Stack fijo: Python 3.12, FastAPI, Redis, MongoDB 7, React 18
- Driver MongoDB: motor (async). NUNCA pymongo síncrono, NUNCA MongoEngine
- Sin dependencias nuevas sin justificación explícita
- Cada módulo hace UNA sola cosa
- Todo es async/await
- Ningún secreto hardcodeado
- El schema de Evento es inmutable
- Los eventos van a la Time Series Collection "events" en MongoDB

¿Podés continuar dentro de estas restricciones?
```

---

*CyberPulse LATAM — Prompts de desarrollo v1.0 — 2026*
