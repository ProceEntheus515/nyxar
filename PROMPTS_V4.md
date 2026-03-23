# 🔌 NYXAR — PROMPTS_V4.md
## Contratos de Integración — Cómo todo se conecta

> **Propósito de este archivo:**
> Los PROMPTS V1, V2 y V3 construyen piezas. Este archivo las conecta.
> Cada prompt certifica que dos componentes ya construidos se comunican
> correctamente. No hay código nuevo de lógica de negocio aquí.
> Solo integración, wiring y verificación de contratos.
>
> **Cuándo usar este archivo:**
> Después de terminar cada módulo, antes de avanzar al siguiente.
> Si Cursor pregunta "¿cómo conecto esto con el dashboard?" —
> la respuesta está en un prompt de este archivo.

---

## 📋 Índice — Contratos de Integración

| # | De | Hacia | Canal | Estado |
|---|----|----|-------|--------|
| I01 | Collector | Redis Bus | Stream publish | Fase 1 |
| I02 | Enricher | Redis Bus | Stream consume/publish | Fase 1 |
| I03 | Correlator | Redis Bus + MongoDB | Stream + write | Fase 1 |
| I04 | API FastAPI | MongoDB + Redis | Read + subscribe | Fase 1 |
| I05 | WebSocket Server | API + Redis PubSub | Push al browser | Fase 1 |
| I06 | Dashboard → API | HTTP REST | Fetch inicial | Fase 1 |
| I07 | Dashboard ← WebSocket | socket.io | Eventos en tiempo real | Fase 1 |
| I08 | Zustand Store | WebSocket + API | Estado global del cliente | Fase 1 |
| I09 | AI Analyst | MongoDB + Redis + API | Background loop | Fase 2 |
| I10 | MISP Connector | Redis Blocklists | Enriquecer desde MISP | V2 |
| I11 | AD Connector | Redis + MongoDB | Resolver identidades | V2 |
| I12 | Auto Response | MongoDB + API + Dashboard | Proposals en tiempo real | V2 |
| I13 | Notifier | Redis PubSub | Consumir alertas | V2 |
| I14 | Reporter | MongoDB + API | Generar y servir PDFs | V2 |
| I15 | Observability | Redis + MongoDB + API | Métricas y health | V2 |
| I16 | Simulator → Collector | Redis Stream | Lab mode only | Lab |
| I17 | Verificación End-to-End | Todo el pipeline | Test de humo completo | Final |

---

## ⚙️ CONTEXTO DE INTEGRACIÓN
> Pegar al inicio de cualquier sesión de integración en Cursor.

```
Estás verificando y completando las integraciones entre los microservicios
de NYXAR. Todo el código de cada servicio ya fue escrito
(siguiendo PROMPTS V1, V2 y V3). Este archivo solo conecta las piezas.

REGLA FUNDAMENTAL DE INTEGRACIÓN:
Ningún servicio importa código de otro servicio directamente.
La comunicación es SOLO a través de:
1. Redis Streams (eventos en tiempo real)
2. Redis PubSub (notificaciones point-to-point)
3. Redis caché (datos compartidos con TTL)
4. MongoDB (persistencia compartida de largo plazo)
5. HTTP REST (dashboard → API, API → servicios)
6. WebSocket (API → dashboard, unidireccional desde servidor)

NUNCA: from enricher.models import X dentro del correlator.
SIEMPRE: leer el evento como dict desde Redis y parsear con Pydantic local.

FORMATO DE EVENTO COMPARTIDO (inmutable, todos los servicios lo conocen):
{
  "id": "evt_{timestamp}_{uuid4[:4]}",
  "timestamp": "ISO8601 UTC",
  "source": "dns|proxy|firewall|wazuh|endpoint",
  "tipo": "query|request|block|alert|process",
  "interno": { "ip", "hostname", "usuario", "area" },
  "externo": { "valor", "tipo" },
  "enrichment": null | { "reputacion", "fuente", "categoria", "pais_origen",
                          "asn", "registrado_hace_dias", "virustotal_detecciones", "tags" },
  "risk_score": null | int(0-100),
  "correlaciones": []
}
```

---

## FASE 1 — Integraciones del Pipeline Principal

---

### PROMPT I01 — Collector → Redis Bus
**Verifica:** Que los parsers del collector publiquen eventos en el formato correcto

```
Sos un Integration Engineer verificando que el Collector publica
correctamente en Redis.

CONTRATO A VERIFICAR:
- Canal de publicación: Redis Stream "events:raw"
- Formato del mensaje: Evento JSON completo (ver schema en contexto)
- Quién publica: todos los parsers (dns_parser, proxy_parser, etc.)
- Quién consume: el enricher

TAREA 1 — Verificar que el collector/normalizer.py usa RedisBus correctamente:

Abrir collector/normalizer.py y verificar que:
1. Importa RedisBus desde shared/redis_bus.py
2. Llama a redis_bus.publish_event("events:raw", evento.to_redis_dict())
3. El método to_redis_dict() en el modelo Evento serializa datetime como ISO string
   (Redis no puede almacenar objetos datetime nativos de Python)
4. El campo "id" se genera antes de publicar, no después

Si alguno de estos puntos falta, implementarlo ahora.

TAREA 2 — Crear un script de verificación manual:

Crear el archivo scripts/verify_collector.py:

```python
"""
Script de verificación: Collector → Redis
Uso: python scripts/verify_collector.py
Requiere que el stack esté corriendo: docker-compose --profile lab up
"""
import asyncio
import redis.asyncio as aioredis
import json

async def main():
    r = aioredis.from_url("redis://localhost:6379")
    
    print("=== Verificando Collector → Redis ===\n")
    
    # Leer los últimos 10 mensajes del stream events:raw
    messages = await r.xrevrange("events:raw", count=10)
    
    if not messages:
        print("❌ FALLO: No hay mensajes en events:raw")
        print("   Verificar que el collector y el simulador estén corriendo")
        return
    
    print(f"✓ {len(messages)} mensajes encontrados en events:raw\n")
    
    # Verificar el formato del último mensaje
    latest_id, latest_data = messages[0]
    event_str = latest_data.get(b"data", b"{}").decode()
    event = json.loads(event_str)
    
    REQUIRED_FIELDS = ["id", "timestamp", "source", "tipo", "interno", "externo"]
    missing = [f for f in REQUIRED_FIELDS if f not in event]
    
    if missing:
        print(f"❌ FALLO: Faltan campos requeridos: {missing}")
        return
    
    print(f"✓ Formato correcto. Campos presentes: {list(event.keys())}")
    print(f"  - source: {event['source']}")
    print(f"  - tipo: {event['tipo']}")
    print(f"  - interno.usuario: {event['interno'].get('usuario', 'N/A')}")
    print(f"  - externo.valor: {event['externo'].get('valor', 'N/A')}")
    print(f"  - enrichment: {'presente' if event.get('enrichment') else 'null (esperado)'}")
    print(f"  - risk_score: {event.get('risk_score', 'null (esperado)')}")
    
    # Verificar que hay variedad de fuentes
    sources = set()
    for msg_id, msg_data in messages:
        ev = json.loads(msg_data.get(b"data", b"{}"))
        sources.add(ev.get("source", "unknown"))
    
    print(f"\n✓ Fuentes detectadas: {sources}")
    
    if len(sources) >= 2:
        print("✓ Múltiples fuentes activas — collector funcionando correctamente")
    else:
        print("⚠ Solo una fuente activa — verificar que todos los parsers estén corriendo")
    
    await r.aclose()
    print("\n=== Verificación I01 COMPLETADA ===")

asyncio.run(main())
```

RESULTADO ESPERADO AL CORRER EL SCRIPT:
```
=== Verificando Collector → Redis ===

✓ 10 mensajes encontrados en events:raw

✓ Formato correcto. Campos presentes: ['id', 'timestamp', 'source', 'tipo', 'interno', 'externo', 'enrichment', 'risk_score', 'correlaciones']
  - source: dns
  - tipo: query
  - interno.usuario: maria.gomez
  - externo.valor: drive.google.com
  - enrichment: null (esperado)
  - risk_score: null (esperado)

✓ Fuentes detectadas: {'dns', 'proxy', 'wazuh'}
✓ Múltiples fuentes activas — collector funcionando correctamente

=== Verificación I01 COMPLETADA ===
```

NO AVANZAR AL SIGUIENTE PROMPT hasta que este script pase sin errores.
```

---

### PROMPT I02 — Enricher: consume events:raw, publica events:enriched
**Verifica:** Que el enricher consuma del bus, enriquezca, y publique en el canal correcto

```
Sos un Integration Engineer verificando la integración del Enricher.

CONTRATO A VERIFICAR:
- Consume de: Redis Stream "events:raw" (consumer group: "enricher-group")
- Publica en: Redis Stream "events:enriched"
- El evento publicado tiene el campo "enrichment" completado (no null)
- El campo "risk_score" tiene un valor int entre 0 y 100

TAREA 1 — Verificar enricher/main.py:

El loop del enricher debe:
1. Crear el consumer group si no existe:
   ```python
   try:
       await redis_bus.create_consumer_group("events:raw", "enricher-group")
   except Exception:
       pass  # el grupo ya existe
   ```
2. Consumir con XREADGROUP, no XREAD
3. Hacer ACK después de procesar exitosamente
4. Publicar en "events:enriched" con el evento enriquecido

Si alguno de estos puntos falta, implementarlo ahora.

TAREA 2 — Agregar estos métodos a shared/redis_bus.py si no existen:

```python
async def create_consumer_group(
    self, stream: str, group: str, start_id: str = "0"
) -> None:
    """Crea el consumer group. Si ya existe, no hace nada."""
    try:
        await self.client.xgroup_create(stream, group, start_id, mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            raise

async def get_stream_length(self, stream: str) -> int:
    """Retorna cuántos mensajes hay en el stream."""
    return await self.client.xlen(stream)

async def get_consumer_group_info(self, stream: str, group: str) -> dict:
    """Retorna info del consumer group: pending messages, last id, etc."""
    groups = await self.client.xinfo_groups(stream)
    for g in groups:
        if g["name"].decode() == group:
            return g
    return {}
```

TAREA 3 — Crear scripts/verify_enricher.py:

```python
"""
Script de verificación: Enricher pipeline
Uso: python scripts/verify_enricher.py
Requiere que collector + enricher estén corriendo.
"""
import asyncio
import redis.asyncio as aioredis
import json
import time

async def main():
    r = aioredis.from_url("redis://localhost:6379")
    
    print("=== Verificando Enricher ===\n")
    
    # 1. Verificar que events:enriched tiene mensajes
    enriched_len = await r.xlen("events:enriched")
    if enriched_len == 0:
        print("⚠ events:enriched está vacío — esperando 5 segundos...")
        await asyncio.sleep(5)
        enriched_len = await r.xlen("events:enriched")
    
    if enriched_len == 0:
        print("❌ FALLO: events:enriched sigue vacío.")
        print("   Verificar que el enricher esté corriendo y consumiendo de events:raw")
        return
    
    print(f"✓ {enriched_len} mensajes en events:enriched")
    
    # 2. Verificar que los eventos tienen enrichment completado
    messages = await r.xrevrange("events:enriched", count=20)
    
    with_enrichment = 0
    with_risk_score = 0
    reputations = {}
    
    for msg_id, msg_data in messages:
        ev = json.loads(msg_data.get(b"data", b"{}"))
        
        if ev.get("enrichment") is not None:
            with_enrichment += 1
            rep = ev["enrichment"].get("reputacion", "desconocido")
            reputations[rep] = reputations.get(rep, 0) + 1
        
        if ev.get("risk_score") is not None:
            with_risk_score += 1
    
    print(f"✓ {with_enrichment}/{len(messages)} eventos tienen enrichment completo")
    print(f"✓ {with_risk_score}/{len(messages)} eventos tienen risk_score asignado")
    print(f"  Distribución de reputaciones: {reputations}")
    
    # 3. Verificar el consumer group
    groups = await r.xinfo_groups("events:raw")
    enricher_group = None
    for g in groups:
        if g[b"name"] == b"enricher-group":
            enricher_group = g
            break
    
    if not enricher_group:
        print("❌ FALLO: consumer group 'enricher-group' no existe en events:raw")
        return
    
    pending = enricher_group.get(b"pending", 0)
    print(f"\n✓ Consumer group 'enricher-group' existe")
    print(f"  - Mensajes pendientes sin ACK: {pending}")
    if pending > 100:
        print(f"  ⚠ Muchos mensajes pendientes — el enricher puede estar lento")
    
    # 4. Verificar latencia de enriquecimiento
    raw_messages = await r.xrevrange("events:raw", count=1)
    enriched_messages = await r.xrevrange("events:enriched", count=1)
    
    if raw_messages and enriched_messages:
        raw_id = raw_messages[0][0].decode()
        enriched_id = enriched_messages[0][0].decode()
        raw_ms = int(raw_id.split("-")[0])
        enriched_ms = int(enriched_id.split("-")[0])
        latency_ms = enriched_ms - raw_ms
        print(f"\n✓ Latencia aproximada de enriquecimiento: {latency_ms}ms")
        if latency_ms > 2000:
            print("  ⚠ Latencia alta — verificar APIs externas o caché")
    
    await r.aclose()
    print("\n=== Verificación I02 COMPLETADA ===")

asyncio.run(main())
```

NO AVANZAR hasta que este script pase. El enricher es el cuello de botella
del pipeline — si está roto, todo lo demás falla silenciosamente.
```

---

### PROMPT I03 — Correlator: consume events:enriched, escribe en MongoDB
**Verifica:** Que el correlator detecte patrones y persista incidentes

```
Sos un Integration Engineer verificando la integración del Correlator.

CONTRATO A VERIFICAR:
- Consume de: Redis Stream "events:enriched" (consumer group: "correlator-group")
- Escribe incidentes en: MongoDB colección "incidents"
- Actualiza risk scores en: MongoDB colección "identities"
- Publica alertas en: Redis PubSub canal "dashboard:alerts"

TAREA 1 — Verificar que el correlator/main.py hace las 4 operaciones:

```python
# Pseudocódigo del loop principal que DEBE estar en correlator/main.py:

async def run():
    # 1. Crear consumer group
    await redis_bus.create_consumer_group("events:enriched", "correlator-group")
    
    while True:
        # 2. Consumir batch de eventos enriquecidos
        events = await redis_bus.consume_events(
            "events:enriched", "correlator-group", "correlator-1", count=10
        )
        
        for redis_id, event_data in events:
            evento = Evento(**event_data)
            
            # 3. Correr todos los patrones en paralelo
            results = await asyncio.gather(
                beaconing.check(evento, context),
                dns_tunneling.check(evento, context),
                lateral_movement.check(evento, context),
                volume_anomaly.check(evento, context),
                time_anomaly.check(evento, context),
                return_exceptions=True
            )
            
            # 4. Si algún patrón detectó algo → guardar incidente en MongoDB
            for result in results:
                if isinstance(result, Incidente):
                    await mongo.db.incidents.insert_one(result.to_mongo_dict())
                    # 5. Publicar en PubSub para el dashboard
                    await redis_bus.publish_alert(
                        "dashboard:alerts",
                        {"tipo": "new_incident", "data": result.dict()}
                    )
            
            # 6. Actualizar risk score de la identidad en MongoDB
            await mongo.db.identities.update_one(
                {"id": evento.interno.usuario},
                {"$set": {"risk_score_actual": nuevo_score,
                          "ultima_actividad": evento.timestamp}},
                upsert=True
            )
            
            # 7. ACK del mensaje
            await redis_bus.acknowledge("events:enriched", "correlator-group", redis_id)
```

Si alguna de estas operaciones falta en el código actual, implementarla.

TAREA 2 — Crear scripts/verify_correlator.py:

```python
"""
Script de verificación: Correlator
Uso: python scripts/verify_correlator.py
"""
import asyncio
import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient
import json
import os

MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/NYXAR")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

async def main():
    r = aioredis.from_url(REDIS_URL)
    mongo = AsyncIOMotorClient(MONGO_URL)
    db = mongo.NYXAR
    
    print("=== Verificando Correlator ===\n")
    
    # 1. Verificar consumer group en events:enriched
    groups = await r.xinfo_groups("events:enriched")
    correlator_group = next(
        (g for g in groups if g[b"name"] == b"correlator-group"), None
    )
    
    if not correlator_group:
        print("❌ FALLO: consumer group 'correlator-group' no existe")
        return
    print(f"✓ Consumer group 'correlator-group' activo")
    print(f"  Pending: {correlator_group.get(b'pending', 0)} mensajes")
    
    # 2. Verificar que hay identidades en MongoDB
    identity_count = await db.identities.count_documents({})
    print(f"\n✓ {identity_count} identidades en MongoDB")
    
    if identity_count == 0:
        print("⚠ No hay identidades — el correlator puede no estar procesando")
    else:
        # Mostrar muestra
        sample = await db.identities.find_one(
            {}, {"id": 1, "risk_score_actual": 1, "area": 1}
        )
        print(f"  Ejemplo: {sample.get('id')} — score: {sample.get('risk_score_actual')}")
    
    # 3. Verificar incidentes (puede estar vacío si no hubo ataques)
    incident_count = await db.incidents.count_documents({})
    print(f"\n✓ {incident_count} incidentes en MongoDB")
    if incident_count > 0:
        latest = await db.incidents.find_one({}, sort=[("created_at", -1)])
        print(f"  Último: {latest.get('titulo')} — {latest.get('severidad')}")
    
    # 4. Verificar que el PubSub funciona (enviar y recibir un mensaje de prueba)
    print("\nVerificando PubSub canal 'dashboard:alerts'...")
    pubsub = r.pubsub()
    await pubsub.subscribe("dashboard:alerts")
    
    # Publicar un mensaje de prueba
    test_payload = json.dumps({"tipo": "test", "data": {"msg": "verify_correlator"}})
    await r.publish("dashboard:alerts", test_payload)
    
    # Intentar recibirlo
    await asyncio.sleep(0.2)
    msg = await pubsub.get_message(ignore_subscribe_messages=True)
    
    if msg and msg.get("data"):
        received = json.loads(msg["data"])
        if received.get("tipo") == "test":
            print("✓ PubSub 'dashboard:alerts' funcionando correctamente")
        else:
            print(f"⚠ Mensaje recibido pero con contenido inesperado: {received}")
    else:
        print("⚠ No se recibió el mensaje de prueba en PubSub")
        print("  Verificar que el canal está activo")
    
    await pubsub.unsubscribe("dashboard:alerts")
    await r.aclose()
    mongo.close()
    print("\n=== Verificación I03 COMPLETADA ===")

asyncio.run(main())
```

---

### PROMPT I04 — API FastAPI: conecta MongoDB y Redis
**Verifica:** Que todos los routers lean de MongoDB correctamente y el startup inicialice las conexiones

```
Sos un Integration Engineer verificando que la API FastAPI
tiene las conexiones correctas a MongoDB y Redis.

TAREA 1 — Verificar api/main.py tiene el lifespan correcto:

El lifespan de FastAPI DEBE inicializar las conexiones al arrancar
y cerrarlas al apagar. Si no está implementado así, hacerlo ahora:

```python
# api/main.py — patrón CORRECTO de lifespan

from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as aioredis

# Singletons de conexión — accesibles desde todos los routers
mongo_client: AsyncIOMotorClient = None
redis_client: aioredis.Redis = None
db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    global mongo_client, redis_client, db
    
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
    redis_client = aioredis.from_url(settings.REDIS_URL)
    db = mongo_client.NYXAR
    
    # Verificar conexiones
    await mongo_client.admin.command("ping")
    await redis_client.ping()
    
    logger.info("✓ Conexiones a MongoDB y Redis establecidas")
    
    yield  # La app corre aquí
    
    # SHUTDOWN
    mongo_client.close()
    await redis_client.aclose()
    logger.info("Conexiones cerradas")

app = FastAPI(lifespan=lifespan)
```

TAREA 2 — Crear api/dependencies.py con las dependencias de FastAPI:

```python
# api/dependencies.py
# Las dependencias permiten a los routers acceder a db y redis
# sin importar los singletons directamente.

from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase
import redis.asyncio as aioredis

def get_db(request: Request) -> AsyncIOMotorDatabase:
    """Inyecta la conexión a MongoDB en los routers."""
    return request.app.state.db

def get_redis(request: Request) -> aioredis.Redis:
    """Inyecta la conexión a Redis en los routers."""
    return request.app.state.redis
```

Y en api/main.py agregar después del yield del lifespan:
```python
app.state.db = db
app.state.redis = redis_client
```

TAREA 3 — Verificar que los routers usan las dependencias:

Abrir api/routers/events.py y verificar que el endpoint GET /events
se ve así (con Depends):

```python
from fastapi import APIRouter, Depends, Query
from api.dependencies import get_db
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter()

@router.get("/events")
async def get_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source: str = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    query = {}
    if source:
        query["meta.source"] = source
    
    cursor = db.events.find(query).sort("timestamp", -1).skip(offset).limit(limit)
    events = await cursor.to_list(length=limit)
    total = await db.events.count_documents(query)
    
    # Convertir ObjectId a string para JSON serialization
    for ev in events:
        ev["_id"] = str(ev["_id"])
    
    return {"data": events, "total": total, "timestamp": datetime.utcnow().isoformat()}
```

Si algún router usa mongo_client directamente (en lugar de Depends), corregirlo.

TAREA 4 — Crear scripts/verify_api.py:

```python
"""
Script de verificación: API FastAPI
Uso: python scripts/verify_api.py
Requiere que la API esté corriendo en localhost:8000
"""
import httpx
import asyncio
import json

BASE_URL = "http://localhost:8000"

async def main():
    print("=== Verificando API FastAPI ===\n")
    
    async with httpx.AsyncClient() as client:
        # 1. Health check
        r = await client.get(f"{BASE_URL}/health")
        assert r.status_code == 200, f"❌ /health falló: {r.status_code}"
        print(f"✓ GET /health → {r.json()}")
        
        # 2. Eventos
        r = await client.get(f"{BASE_URL}/api/v1/events?limit=5")
        assert r.status_code == 200, f"❌ /events falló: {r.status_code}"
        data = r.json()
        assert "data" in data, "❌ Respuesta de /events no tiene campo 'data'"
        assert "total" in data, "❌ Respuesta de /events no tiene campo 'total'"
        print(f"✓ GET /events → {data['total']} eventos totales, retornó {len(data['data'])}")
        
        # 3. Identidades
        r = await client.get(f"{BASE_URL}/api/v1/identities")
        assert r.status_code == 200, f"❌ /identities falló: {r.status_code}"
        data = r.json()
        print(f"✓ GET /identities → {data.get('total', '?')} identidades")
        
        # 4. Incidentes
        r = await client.get(f"{BASE_URL}/api/v1/incidents")
        assert r.status_code == 200, f"❌ /incidents falló: {r.status_code}"
        data = r.json()
        print(f"✓ GET /incidents → {data.get('total', '?')} incidentes")
        
        # 5. Verificar formato de un evento
        r = await client.get(f"{BASE_URL}/api/v1/events?limit=1")
        events = r.json()["data"]
        if events:
            ev = events[0]
            required = ["id", "timestamp", "source", "tipo", "interno", "externo"]
            missing = [f for f in required if f not in ev]
            if missing:
                print(f"❌ Evento sin campos requeridos: {missing}")
            else:
                print(f"✓ Formato de evento correcto: {list(ev.keys())}")
        
        # 6. CORS headers (importante para el dashboard)
        r = await client.options(
            f"{BASE_URL}/api/v1/events",
            headers={"Origin": "http://localhost:3000",
                     "Access-Control-Request-Method": "GET"}
        )
        cors_header = r.headers.get("access-control-allow-origin", "")
        if "localhost:3000" in cors_header or cors_header == "*":
            print(f"✓ CORS habilitado para el dashboard: {cors_header}")
        else:
            print(f"⚠ CORS puede no estar configurado para localhost:3000")
            print(f"  Header recibido: {cors_header}")
    
    print("\n=== Verificación I04 COMPLETADA ===")

asyncio.run(main())
```

---

### PROMPT I05 — WebSocket Server: Redis PubSub → Browser
**Verifica:** Que el servidor WebSocket distribuya eventos al dashboard correctamente

```
Sos un Integration Engineer verificando la integración del WebSocket server.

CONTRATO A VERIFICAR:
- Escucha en: Redis PubSub canal "dashboard:events" y "dashboard:alerts"
- Emite al browser: eventos socket.io nombrados correctamente
- Los nombres de eventos deben coincidir EXACTAMENTE con los que
  el dashboard (useWebSocket.js) espera

TAREA 1 — Definir el contrato de eventos WebSocket:

Este es el contrato EXACTO entre server y client.
Si el server emite "new_event" y el client escucha "newEvent",
nada funciona. Deben coincidir.

Crear api/websocket_contract.py (solo documentación, sin lógica):

```python
"""
CONTRATO DE EVENTOS WEBSOCKET — NYXAR
Este archivo es la fuente de verdad de todos los eventos socket.io.
Tanto el server (api/websocket.py) como el client (useWebSocket.js)
DEBEN usar exactamente estos nombres.

Cualquier cambio acá requiere cambio en ambos lados.
"""

# Eventos que el SERVER emite al CLIENT
SERVER_EVENTS = {
    "new_event":       "Nuevo evento enriquecido del pipeline",
    "new_alert":       "Nuevo incidente detectado por el correlator",
    "honeypot_hit":    "Activación de un honeypot interno",
    "identity_update": "Cambio de risk_score de una identidad",
    "ai_memo":         "Nuevo análisis generado por Claude",
    "stats_update":    "Actualización de estadísticas generales (cada 30s)",
    "health_update":   "Estado de salud del sistema (cada 60s)",
    "response_proposal": "Nueva propuesta de acción automatizada",
}

# Eventos que el CLIENT envía al SERVER
CLIENT_EVENTS = {
    "subscribe_identity": "Cliente quiere recibir todos los eventos de una identidad",
    "unsubscribe_identity": "Cliente deja de seguir una identidad",
    "request_ceo_view": "Cliente solicita análisis CEO",
    "ping": "Keepalive desde el cliente",
}

# Payload de cada evento (para validación)
EVENT_PAYLOADS = {
    "new_event": {
        "schema": "Evento completo serializado como dict",
        "example": {"id": "evt_...", "source": "dns", "risk_score": 45, "...": "..."}
    },
    "new_alert": {
        "schema": "Incidente completo serializado como dict",
        "example": {"id": "inc_...", "titulo": "...", "severidad": "critica"}
    },
    "honeypot_hit": {
        "schema": "HoneypotHit completo serializado como dict",
        "example": {"id": "hp_...", "recurso": "BACKUP_FINANCIERO_2025", "ip_interna": "..."}
    },
    "identity_update": {
        "schema": "Dict con id, risk_score actual y delta",
        "example": {"identidad_id": "ventas.garcia", "risk_score": 67, "delta": +12}
    },
    "ai_memo": {
        "schema": "AiMemo completo serializado como dict",
        "example": {"id": "memo_...", "tipo": "autonomo", "prioridad": "alta", "contenido": "..."}
    },
    "stats_update": {
        "schema": "Dict con estadísticas del pipeline",
        "example": {"eventos_por_min": 14.5, "identidades_activas": 12, "alertas_abiertas": 2}
    },
}
```

TAREA 2 — Verificar api/websocket.py usa los nombres del contrato:

Abrir api/websocket.py y verificar que:
1. Todos los sio.emit() usan las keys de SERVER_EVENTS
2. Todos los @sio.on() usan las keys de CLIENT_EVENTS
3. El background task que escucha Redis PubSub está corriendo

Si hay discrepancias, corregirlas ahora alineando con el contrato.

TAREA 3 — Verificar dashboard/src/hooks/useWebSocket.js usa el mismo contrato:

Abrir el hook y verificar que los event listeners coinciden:

```javascript
// dashboard/src/hooks/useWebSocket.js — DEBE verse así:

import { useEffect } from 'react'
import { io } from 'socket.io-client'
import { useStore } from '../store'

const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:8000'

let socket = null

export function useWebSocket() {
  const { addEvent, addAlert, addHoneypotHit, updateIdentity,
          addAiMemo, updateStats, updateHealth, addProposal } = useStore()
  
  useEffect(() => {
    socket = io(WS_URL, {
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: Infinity,
    })
    
    socket.on('connect', () => {
      console.log('WebSocket conectado:', socket.id)
      useStore.getState().setConnected(true)
    })
    
    socket.on('disconnect', () => {
      useStore.getState().setConnected(false)
    })
    
    // ESTOS NOMBRES DEBEN COINCIDIR CON SERVER_EVENTS en websocket_contract.py
    socket.on('new_event', addEvent)
    socket.on('new_alert', addAlert)
    socket.on('honeypot_hit', addHoneypotHit)
    socket.on('identity_update', updateIdentity)
    socket.on('ai_memo', addAiMemo)
    socket.on('stats_update', updateStats)
    socket.on('health_update', updateHealth)
    socket.on('response_proposal', addProposal)
    
    return () => {
      socket.removeAllListeners()
      socket.disconnect()
    }
  }, [])
  
  return socket
}
```

Si hay nombres distintos entre el server y el client, este prompt
es la oportunidad de alinearlos. Usar SIEMPRE los nombres de websocket_contract.py.

TAREA 4 — Crear scripts/verify_websocket.js:

```javascript
/**
 * Script de verificación: WebSocket Server
 * Uso: node scripts/verify_websocket.js
 * Requiere: npm install socket.io-client (solo para el script)
 */
const { io } = require('socket.io-client')

const socket = io('http://localhost:8000', { transports: ['websocket'] })

const received = {}
const TIMEOUT_MS = 15000

console.log('=== Verificando WebSocket Server ===\n')
console.log('Conectando a http://localhost:8000...')

socket.on('connect', () => {
  console.log(`✓ Conectado. Socket ID: ${socket.id}\n`)
  console.log('Esperando eventos (máximo 15 segundos)...\n')
})

socket.on('disconnect', () => {
  console.log('✗ Desconectado')
})

// Escuchar todos los eventos del contrato
const EXPECTED_EVENTS = ['new_event', 'stats_update']

EXPECTED_EVENTS.forEach(eventName => {
  socket.on(eventName, (data) => {
    if (!received[eventName]) {
      received[eventName] = data
      console.log(`✓ Recibido: ${eventName}`)
      if (eventName === 'new_event') {
        console.log(`  source: ${data.source}`)
        console.log(`  usuario: ${data.interno?.usuario}`)
        console.log(`  risk_score: ${data.risk_score}`)
      }
      if (eventName === 'stats_update') {
        console.log(`  eventos/min: ${data.eventos_por_min}`)
        console.log(`  identidades activas: ${data.identidades_activas}`)
      }
    }
  })
})

setTimeout(() => {
  const missing = EXPECTED_EVENTS.filter(e => !received[e])
  
  console.log('\n=== Resultado ===')
  if (missing.length === 0) {
    console.log('✓ Todos los eventos esperados fueron recibidos')
    console.log('✓ WebSocket Server funcionando correctamente')
  } else {
    console.log(`❌ Eventos no recibidos: ${missing.join(', ')}`)
    console.log('  Verificar que el pipeline esté corriendo y generando eventos')
  }
  
  socket.disconnect()
  process.exit(missing.length > 0 ? 1 : 0)
}, TIMEOUT_MS)
```

NO AVANZAR hasta que este script confirme que los eventos llegan al browser.
Este es el punto de integración más crítico de todo el sistema.
```

---

### PROMPT I06 — Dashboard → API: HTTP client configurado
**Verifica:** Que el dashboard tenga un cliente HTTP correctamente configurado para llamar a la API

```
Sos un Integration Engineer verificando la capa HTTP del dashboard.

TAREA 1 — Crear dashboard/src/api/client.js:

Este archivo centraliza TODAS las llamadas HTTP del dashboard.
Ningún componente hace fetch() directamente. Todo pasa por acá.

```javascript
// dashboard/src/api/client.js

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

/**
 * Cliente HTTP base con manejo de errores centralizado.
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  }
  
  try {
    const response = await fetch(url, config)
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }))
      throw new ApiError(response.status, error.error || 'Request failed', endpoint)
    }
    
    return response.json()
  } catch (err) {
    if (err instanceof ApiError) throw err
    throw new ApiError(0, 'Network error — verificar que la API esté corriendo', endpoint)
  }
}

class ApiError extends Error {
  constructor(status, message, endpoint) {
    super(message)
    this.status = status
    this.endpoint = endpoint
    this.name = 'ApiError'
  }
}

/**
 * API de eventos
 */
export const eventsApi = {
  getAll: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/events${qs ? '?' + qs : ''}`)
  },
  getById: (id) => request(`/events/${id}`),
  getStats: () => request('/events/stats'),
}

/**
 * API de identidades
 */
export const identitiesApi = {
  getAll: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/identities${qs ? '?' + qs : ''}`)
  },
  getById: (id) => request(`/identities/${id}`),
  getTimeline: (id) => request(`/identities/${id}/timeline`),
}

/**
 * API de incidentes
 */
export const incidentsApi = {
  getAll: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/incidents${qs ? '?' + qs : ''}`)
  },
  getById: (id) => request(`/incidents/${id}`),
  updateEstado: (id, estado, comentario = '') =>
    request(`/incidents/${id}/estado`, {
      method: 'POST',
      body: JSON.stringify({ estado, comentario })
    }),
}

/**
 * API de alertas
 */
export const alertsApi = {
  getHoneypots: () => request('/alerts/honeypots'),
  getSummary: () => request('/alerts/summary'),
}

/**
 * API de IA
 */
export const aiApi = {
  getMemos: () => request('/ai/memos'),
  analyzeIncident: (id) => request(`/ai/analyze/${id}`, { method: 'POST' }),
  getCeoView: () => request('/ai/ceo-view', { method: 'POST' }),
}

/**
 * API del simulador (solo en lab mode)
 */
export const simulatorApi = {
  runScenario: (scenario, target, intensity) =>
    request('/simulator/scenario', {
      method: 'POST',
      body: JSON.stringify({ scenario, target, intensity })
    }),
  getStatus: () => request('/simulator/status'),
}

/**
 * API de respuestas automáticas
 */
export const responseApi = {
  getProposals: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/response/proposals${qs ? '?' + qs : ''}`)
  },
  approve: (id, comentario = '') =>
    request(`/response/proposals/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ comentario })
    }),
  reject: (id, motivo) =>
    request(`/response/proposals/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ motivo })
    }),
}
```

TAREA 2 — Crear dashboard/.env.local con las URLs:

```
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=http://localhost:8000
VITE_LAB_MODE=true
```

Y dashboard/.env.production:
```
VITE_API_URL=http://tu-servidor:8000/api/v1
VITE_WS_URL=http://tu-servidor:8000
VITE_LAB_MODE=false
```

TAREA 3 — Verificar que ninguna vista hace fetch() directamente:

Correr este comando y arreglar cualquier instancia encontrada:
```bash
grep -r "fetch(" dashboard/src/views/ --include="*.jsx"
grep -r "fetch(" dashboard/src/components/ --include="*.jsx"
```

Si encuentran fetch() directo en una vista, reemplazarlo con
la función correspondiente de client.js.

REGLA: Las vistas usan client.js. Nunca fetch() directo.
```

---

### PROMPT I07 — Zustand Store: conecta WebSocket + API
**Verifica:** Que el store de Zustand esté correctamente definido con todas las acciones

```
Sos un Integration Engineer verificando el estado global del dashboard.

El Zustand store es el cerebro del dashboard. Recibe datos del WebSocket
y de la API, y los distribuye a todos los componentes.

TAREA 1 — Implementar dashboard/src/store/index.js completamente:

```javascript
// dashboard/src/store/index.js
import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'

const MAX_EVENTS = 500  // ring buffer — no acumular infinitamente

export const useStore = create(
  subscribeWithSelector((set, get) => ({
    
    // ─── ESTADO DE CONEXIÓN ───────────────────────────────
    connected: false,
    setConnected: (connected) => set({ connected }),
    
    // ─── EVENTOS (ring buffer de MAX_EVENTS) ─────────────
    events: [],
    addEvent: (event) => set((state) => ({
      events: [event, ...state.events].slice(0, MAX_EVENTS)
    })),
    addEvents: (newEvents) => set((state) => ({
      events: [...newEvents, ...state.events].slice(0, MAX_EVENTS)
    })),
    
    // ─── IDENTIDADES (mapa id → Identidad) ───────────────
    identities: {},
    setIdentities: (identities) => {
      const map = {}
      identities.forEach(id => { map[id.id] = id })
      set({ identities: map })
    },
    updateIdentity: (update) => set((state) => ({
      identities: {
        ...state.identities,
        [update.identidad_id]: {
          ...state.identities[update.identidad_id],
          risk_score_actual: update.risk_score,
          _delta: update.delta,
        }
      }
    })),
    
    // ─── INCIDENTES ───────────────────────────────────────
    incidents: [],
    addAlert: (incident) => set((state) => ({
      incidents: [incident, ...state.incidents].slice(0, 100)
    })),
    setIncidents: (incidents) => set({ incidents }),
    updateIncidentEstado: (id, estado) => set((state) => ({
      incidents: state.incidents.map(inc =>
        inc.id === id ? { ...inc, estado } : inc
      )
    })),
    
    // ─── HONEYPOT HITS ────────────────────────────────────
    honeypotHits: [],
    addHoneypotHit: (hit) => set((state) => ({
      honeypotHits: [hit, ...state.honeypotHits].slice(0, 50)
    })),
    
    // ─── AI MEMOS ─────────────────────────────────────────
    aiMemos: [],
    addAiMemo: (memo) => set((state) => ({
      aiMemos: [memo, ...state.aiMemos].slice(0, 50)
    })),
    setAiMemos: (memos) => set({ aiMemos: memos }),
    
    // ─── ESTADÍSTICAS ─────────────────────────────────────
    stats: {
      eventos_por_min: 0,
      identidades_activas: 0,
      alertas_abiertas: 0,
      honeypots_hoy: 0,
    },
    updateStats: (stats) => set({ stats }),
    
    // ─── HEALTH DEL SISTEMA ───────────────────────────────
    systemHealth: null,
    updateHealth: (health) => set({ systemHealth: health }),
    
    // ─── RESPONSE PROPOSALS ──────────────────────────────
    proposals: [],
    addProposal: (proposal) => set((state) => ({
      proposals: [proposal, ...state.proposals]
    })),
    setProposals: (proposals) => set({ proposals }),
    
    // ─── DETAIL PANEL ─────────────────────────────────────
    detailPanel: { isOpen: false, type: null, id: null },
    openDetail: (type, id) => set({ detailPanel: { isOpen: true, type, id } }),
    closeDetail: () => set({ detailPanel: { isOpen: false, type: null, id: null } }),
    
    // ─── LAB MODE ─────────────────────────────────────────
    isLabMode: import.meta.env.VITE_LAB_MODE === 'true',
    
    // ─── FILTROS ACTIVOS EN TIMELINE ──────────────────────
    timelineFilters: {
      source: null,
      minSeverity: null,
      area: null,
      onlyAlerts: false,
    },
    setTimelineFilter: (key, value) => set((state) => ({
      timelineFilters: { ...state.timelineFilters, [key]: value }
    })),
    
    // ─── GETTER: eventos filtrados para el Timeline ───────
    get filteredEvents() {
      const { events, timelineFilters } = get()
      return events.filter(ev => {
        if (timelineFilters.source && ev.source !== timelineFilters.source) return false
        if (timelineFilters.area && ev.interno?.area !== timelineFilters.area) return false
        if (timelineFilters.onlyAlerts && (!ev.risk_score || ev.risk_score < 60)) return false
        return true
      })
    },
  }))
)
```

TAREA 2 — Verificar que el estado inicial se carga al montar App.jsx:

En dashboard/src/App.jsx debe haber un useEffect que carga el estado inicial
llamando a la API para los datos históricos:

```javascript
// dashboard/src/App.jsx
useEffect(() => {
  async function loadInitialState() {
    try {
      // Cargar los últimos eventos
      const eventsData = await eventsApi.getAll({ limit: 50 })
      useStore.getState().addEvents(eventsData.data)
      
      // Cargar identidades
      const identitiesData = await identitiesApi.getAll()
      useStore.getState().setIdentities(identitiesData.data)
      
      // Cargar incidentes abiertos
      const incidentsData = await incidentsApi.getAll({ estado: 'abierto' })
      useStore.getState().setIncidents(incidentsData.data)
      
      // Cargar últimos memos de IA
      const memosData = await aiApi.getMemos()
      useStore.getState().setAiMemos(memosData.data)
      
    } catch (err) {
      console.error('Error cargando estado inicial:', err)
    }
  }
  
  loadInitialState()
}, [])
```

Si este useEffect no existe, crearlo ahora.

TAREA 3 — Crear scripts/verify_store.js (test en browser):

Agregar al dashboard en modo desarrollo este snippet en App.jsx
(rodeado con comentarios para quitar en producción):

```javascript
// SOLO EN DEVELOPMENT — verificar que el store recibe datos del WebSocket
if (import.meta.env.DEV) {
  setTimeout(() => {
    const state = useStore.getState()
    console.group('=== Verificación del Store ===')
    console.log('✓ Conectado:', state.connected)
    console.log('✓ Eventos cargados:', state.events.length)
    console.log('✓ Identidades cargadas:', Object.keys(state.identities).length)
    console.log('✓ Incidentes:', state.incidents.length)
    console.log('✓ AI Memos:', state.aiMemos.length)
    console.log('✓ Lab mode:', state.isLabMode)
    
    if (state.events.length === 0) {
      console.warn('⚠ Sin eventos — verificar WebSocket y API')
    }
    if (Object.keys(state.identities).length === 0) {
      console.warn('⚠ Sin identidades — verificar GET /identities')
    }
    console.groupEnd()
  }, 3000) // esperar 3 segundos para que el WS conecte
}
```

Abrir el browser en http://localhost:3000 y verificar la consola.
```

---

## 🔌 FASE 2 — Integraciones de Módulos Avanzados (V2)

---

### PROMPT I09 — AI Analyst → MongoDB + Redis + WebSocket
**Verifica:** Que el AI Analyst publique sus memos correctamente al dashboard

```
Sos un Integration Engineer verificando la integración del AI Analyst.

CONTRATO:
- El AI Analyst lee datos de: MongoDB (eventos, identidades, incidentes)
- Publica memos en: MongoDB colección "ai_memos"
- Notifica al dashboard via: Redis PubSub "dashboard:events"
  con evento tipo "ai_memo"

TAREA 1 — Verificar ai_analyst/autonomous_analyst.py publica correctamente:

El método analyze_current_state() DEBE terminar con:
```python
# Guardar en MongoDB
await mongo.db.ai_memos.insert_one(memo.to_mongo_dict())

# Notificar al dashboard via Redis PubSub
await redis_bus.publish_alert(
    "dashboard:events",
    {
        "tipo": "ai_memo",     # DEBE ser "ai_memo" — coincide con el contrato WS
        "data": memo.dict()
    }
)

logger.info(f"Memo publicado: {memo.prioridad} — {memo.titulo}")
```

TAREA 2 — Verificar api/routers/ai.py retorna el formato correcto:

```python
# GET /ai/memos debe retornar:
{
  "data": [
    {
      "id": "memo_...",
      "tipo": "autonomo",
      "contenido": "texto del análisis...",
      "prioridad": "alta",
      "eventos_relacionados": ["evt_..."],
      "created_at": "ISO8601"
    }
  ],
  "total": N,
  "timestamp": "ISO8601"
}
```

TAREA 3 — Verificar que el store de React actualiza al recibir un memo:

En useWebSocket.js, el handler de "ai_memo" llama a:
```javascript
socket.on('ai_memo', (data) => {
  useStore.getState().addAiMemo(data)
  // También mostrar una notificación toast si prioridad === "critica" o "alta"
  if (data.prioridad === 'critica' || data.prioridad === 'alta') {
    showToast({
      type: 'warning',
      title: 'Nuevo análisis IA',
      message: data.titulo || data.contenido.slice(0, 80) + '...'
    })
  }
})
```

Si el showToast no existe, implementar un sistema de toasts simple
en dashboard/src/components/ui/Toast.jsx.

TAREA 4 — Verificar que AiMemo.jsx muestra el contenido:

El componente AiMemo.jsx debe:
1. Leer de useStore().aiMemos
2. Mostrar los últimos 5 memos
3. Cada memo con: prioridad (badge), contenido, timestamp (TimeAgo)
4. Si prioridad=critica: borde rojo
```

---

### PROMPT I10 — MISP Connector → Redis Blocklists → Enricher
**Verifica:** Que los IOCs de MISP lleguen correctamente al enricher

```
Sos un Integration Engineer verificando la integración MISP → Enricher.

CONTRATO:
- MISP Connector escribe en: Redis sets "blocklist:misp_ips", 
  "blocklist:misp_domains", etc.
- MISP Connector escribe metadata en: Redis keys "misp:meta:{valor}"
- Enricher lee de: esos mismos sets y keys

TAREA 1 — Verificar que FeedDownloader en el enricher conoce las blocklists de MISP:

En enricher/feeds/downloader.py, el método check_ip() y check_domain()
deben incluir los sets de MISP además de los feeds estáticos:

```python
ALL_IP_BLOCKLISTS = [
    "blocklist:spamhaus_drop",
    "blocklist:spamhaus_edrop", 
    "blocklist:feodo",
    "blocklist:misp_ips",      # ← MISP agregado
]

ALL_DOMAIN_BLOCKLISTS = [
    "blocklist:urlhaus",
    "blocklist:misp_domains",  # ← MISP agregado
]
```

TAREA 2 — Verificar que cuando el enricher detecta un hit de MISP,
busca el contexto de metadata:

En enricher/main.py, después de detectar hit en blocklist:
```python
hit_lista = await feed_downloader.check_ip(valor)

if hit_lista:
    # Si el hit es de MISP, buscar contexto adicional
    enrichment_data = {
        "reputacion": "malicioso",
        "fuente": hit_lista,
    }
    
    if "misp" in hit_lista:
        misp_meta_key = f"misp:meta:{valor}"
        misp_context = await redis_bus.cache_get(misp_meta_key)
        if misp_context:
            enrichment_data["categoria"] = misp_context.get("event_name")
            enrichment_data["tags"] = misp_context.get("tags", [])
```

TAREA 3 — Crear scripts/verify_misp_integration.py:

```python
"""
Script de verificación: MISP → Redis → Enricher
"""
import asyncio
import redis.asyncio as aioredis

async def main():
    r = aioredis.from_url("redis://localhost:6379")
    
    print("=== Verificando MISP Integration ===\n")
    
    # Verificar que las blocklists de MISP existen
    misp_lists = ["blocklist:misp_ips", "blocklist:misp_domains", 
                  "blocklist:misp_hashes", "blocklist:misp_urls"]
    
    for lista in misp_lists:
        size = await r.scard(lista)
        print(f"  {lista}: {size} IOCs")
    
    total = sum([await r.scard(l) for l in misp_lists])
    
    if total == 0:
        print("\n⚠ No hay IOCs de MISP en Redis")
        print("  Verificar que MISP_URL y MISP_API_KEY están configurados")
        print("  y que el misp_connector esté corriendo")
    else:
        print(f"\n✓ Total IOCs de MISP: {total}")
        
        # Verificar que hay metadata para algunos IOCs
        keys = await r.keys("misp:meta:*")
        print(f"✓ Metadata de MISP disponible para {len(keys)} IOCs")
    
    await r.aclose()
    print("\n=== Verificación I10 COMPLETADA ===")

asyncio.run(main())
```

---

### PROMPT I11 — AD Connector → Redis + Normalizer
**Verifica:** Que la resolución de identidades de AD llegue al normalizer

```
Sos un Integration Engineer verificando la integración AD → Collector.

CONTRATO:
- AD Connector escribe en Redis: keys "identity:{ip}" → {usuario, hostname, area}
- Normalizer lee de Redis: esas mismas keys para resolver identidades

TAREA 1 — Verificar que ad_connector/resolver.py escribe en Redis el formato correcto:

El formato de la key debe ser EXACTAMENTE:
```python
# En ad_connector/resolver.py
key = f"identity:{ip}"
value = {
    "ip": ip,
    "usuario": sAMAccountName,
    "nombre_completo": displayName,
    "hostname": hostname,
    "area": department,
    "cargo": title,
    "es_privilegiado": es_privilegiado,
    "fuente_resolucion": "ad_sync"
}
await redis_bus.cache_set(key, value, ttl=300)
```

TAREA 2 — Verificar que collector/normalizer.py lee con ese mismo formato:

```python
# En collector/normalizer.py
async def _resolve_internal(self, ip: str) -> dict:
    identity = await self.redis_bus.cache_get(f"identity:{ip}")
    
    if identity:
        return {
            "hostname": identity.get("hostname", "desconocido"),
            "usuario": identity.get("usuario", "desconocido"),
            "area": identity.get("area", "desconocido")
        }
    
    # Fallback si AD no está disponible
    return {
        "hostname": "desconocido",
        "usuario": "desconocido", 
        "area": "desconocido"
    }
```

Si el normalizer aún usa la tabla manual del simulador, reemplazarlo con este código.

TAREA 3 — Crear scripts/verify_ad_integration.py:

```python
import asyncio
import redis.asyncio as aioredis

async def main():
    r = aioredis.from_url("redis://localhost:6379")
    
    print("=== Verificando AD Integration ===\n")
    
    # Buscar keys de identidad en Redis
    keys = await r.keys("identity:*")
    print(f"✓ {len(keys)} identidades resueltas en Redis")
    
    if len(keys) == 0:
        print("⚠ Sin identidades — verificar AD connector o simulador")
    else:
        # Mostrar algunas
        for key in keys[:3]:
            identity = await r.get(key)
            import json
            data = json.loads(identity)
            print(f"  {key.decode()}: {data.get('usuario')} ({data.get('area')})")
    
    await r.aclose()
    print("\n=== Verificación I11 COMPLETADA ===")

asyncio.run(main())
```

---

### PROMPT I12 — Auto Response → MongoDB + API + Dashboard
**Verifica:** Que los proposals lleguen al dashboard para aprobación

```
Sos un Integration Engineer verificando la integración del módulo
de respuesta automatizada con el dashboard.

CONTRATO COMPLETO DE AUTO RESPONSE:
1. Correlator detecta incidente → guarda en MongoDB incidents
2. Auto Response escucha via MongoDB Change Stream → crea proposal
3. Proposal guardado en MongoDB response_proposals
4. Auto Response publica en Redis PubSub "dashboard:events" con tipo "response_proposal"
5. WebSocket server recibe del PubSub → emite "response_proposal" al browser
6. Dashboard recibe → store.addProposal() → ResponseView muestra el proposal
7. Operador aprueba → POST /response/proposals/{id}/approve → engine ejecuta

TAREA 1 — Verificar que auto_response/engine.py publica en el canal correcto:

```python
# En propose_actions() después de guardar en MongoDB:
await redis_bus.publish_alert(
    "dashboard:events",  # MISMO canal que el WebSocket escucha
    {
        "tipo": "response_proposal",  # DEBE ser "response_proposal"
        "data": {
            "id": proposal_id,
            "incident_id": incident["id"],
            "acciones": [a.dict() for a in plan.acciones],
            "justificacion": plan.justificacion,
            "urgencia": plan.urgencia,
        }
    }
)
```

TAREA 2 — Verificar que api/routers/response.py tiene los endpoints correctos
y que el store del dashboard los llama correctamente.

En dashboard/src/views/ResponseView.jsx, el botón de aprobación debe llamar a:
```javascript
import { responseApi } from '../api/client'

const handleApprove = async (proposalId) => {
  await responseApi.approve(proposalId, comentario)
  useStore.getState().setProposals(
    useStore.getState().proposals.filter(p => p.id !== proposalId)
  )
}
```

TAREA 3 — Crear scripts/verify_response_flow.py:

```python
"""
Simula el flujo completo: incidente → proposal → aprobación
"""
import asyncio
import httpx
import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient
import json
import os

async def main():
    r = aioredis.from_url("redis://localhost:6379")
    mongo = AsyncIOMotorClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017/NYXAR"))
    db = mongo.NYXAR
    
    print("=== Verificando Auto Response Flow ===\n")
    
    # 1. Verificar que la colección response_proposals existe
    collections = await db.list_collection_names()
    if "response_proposals" not in collections:
        print("❌ Colección response_proposals no existe")
        print("   Verificar que auto_response esté corriendo y haya procesado al menos un incidente")
    else:
        count = await db.response_proposals.count_documents({})
        pending = await db.response_proposals.count_documents({"estado": "pendiente_aprobacion"})
        print(f"✓ response_proposals existe: {count} total, {pending} pendientes")
    
    # 2. Verificar que la API retorna proposals
    async with httpx.AsyncClient() as client:
        r_http = await client.get("http://localhost:8000/api/v1/response/proposals")
        if r_http.status_code == 200:
            data = r_http.json()
            print(f"✓ GET /response/proposals → {data.get('total', '?')} proposals")
        else:
            print(f"❌ GET /response/proposals falló: {r_http.status_code}")
    
    await r.aclose()
    mongo.close()
    print("\n=== Verificación I12 COMPLETADA ===")

asyncio.run(main())
```

---

### PROMPT I13 — Notifier: consume de Redis PubSub
**Verifica:** Que el notifier esté correctamente suscripto a los canales de alertas

```
Sos un Integration Engineer verificando la integración del Notifier.

CONTRATO:
El notifier escucha en estos canales de Redis PubSub:
- "notifications:urgent"  → alertas críticas de alta prioridad
- "notifications:reports" → reportes listos para enviar
- "dashboard:alerts"      → todos los incidentes nuevos (para filtrar)

TAREA 1 — Verificar notifier/engine.py tiene las suscripciones correctas:

```python
# En NotificationEngine.start():
async def start(self):
    pubsub = self.redis.pubsub()
    
    # Suscribirse a todos los canales relevantes
    await pubsub.subscribe(
        "notifications:urgent",
        "notifications:reports", 
        "dashboard:alerts",       # también escucha los incidentes
    )
    
    # También escuchar MongoDB Change Stream para honeypot_hits
    asyncio.create_task(self._watch_honeypots())
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            canal = message["channel"].decode()
            payload = json.loads(message["data"])
            await self.process_event(canal, payload)
```

TAREA 2 — Verificar que process_event() enruta correctamente:

```python
async def process_event(self, canal: str, payload: dict):
    tipo = payload.get("tipo")
    data = payload.get("data", {})
    
    # Mapeo canal/tipo → qué notificar
    if canal == "notifications:urgent" or (
        canal == "dashboard:alerts" and 
        data.get("severidad") in ("critica", "alta")
    ):
        await self._handle_incident_alert(data)
    
    elif canal == "notifications:reports":
        await self._handle_report_ready(data)
    
    # Los honeypot hits vienen del Change Stream, no de PubSub
```

TAREA 3 — Crear scripts/verify_notifier.py:

```python
"""
Verifica que el notifier está activo y suscripto a los canales
"""
import asyncio
import redis.asyncio as aioredis
import json

async def main():
    r = aioredis.from_url("redis://localhost:6379")
    
    print("=== Verificando Notifier ===\n")
    
    # Verificar heartbeat del notifier
    heartbeat = await r.get("heartbeat:notifier")
    if heartbeat:
        data = json.loads(heartbeat)
        print(f"✓ Notifier activo. Último heartbeat: {data.get('ts')}")
    else:
        print("❌ Notifier no activo (sin heartbeat)")
        return
    
    # Enviar una notificación de prueba y verificar que el log la registra
    test_notification = json.dumps({
        "tipo": "test",
        "data": {
            "severidad": "info",
            "titulo": "Test de verificación",
            "mensaje": "Este es un test de integración"
        }
    })
    
    await r.publish("notifications:urgent", test_notification)
    print("✓ Notificación de prueba publicada en 'notifications:urgent'")
    
    await asyncio.sleep(1)
    
    # Verificar en MongoDB que se registró
    from motor.motor_asyncio import AsyncIOMotorClient
    import os
    mongo = AsyncIOMotorClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017/NYXAR"))
    db = mongo.NYXAR
    
    recent = await db.notifications_log.find_one(
        {"tipo": "test"},
        sort=[("enviado_at", -1)]
    )
    
    if recent:
        print(f"✓ Notificación procesada y registrada en MongoDB")
    else:
        print("⚠ Notificación no encontrada en notifications_log")
        print("  Puede estar procesando o el log no está habilitado")
    
    mongo.close()
    await r.aclose()
    print("\n=== Verificación I13 COMPLETADA ===")

asyncio.run(main())
```

---

### PROMPT I16 — Simulator → Collector (Lab Mode)
**Verifica:** Que el simulador publique eventos que el collector puede parsear

```
Sos un Integration Engineer verificando la integración del Simulador
en modo laboratorio.

Esta es la integración más importante para el desarrollo:
si el simulador no genera eventos que el collector parsea correctamente,
ninguna prueba del sistema tiene sentido.

TAREA 1 — Verificar que el generator.py del simulador publica en el formato
que el normalizer puede parsear:

El simulador NO publica eventos normalizados — publica logs RAW
exactamente como lo haría un sistema real. El collector normaliza.

Para eventos DNS, el simulador debe publicar:
```python
# simulator/generator.py — formato de log DNS a publicar

raw_dns_log = {
    "timestamp": datetime.utcnow().isoformat(),
    "client": persona["dispositivo"],       # IP interna
    "domain": dominio,
    "type": "A",
    "status": "NOERROR",
    "blocked": False
}

# Publicar en el mismo stream que el dns_parser produciría
await redis_bus.publish_event("events:raw", {
    # El simulador normaliza directamente (no tiene archivo de log)
    "id": generate_event_id(),
    "timestamp": datetime.utcnow().isoformat(),
    "source": "dns",
    "tipo": "query",
    "interno": {
        "ip": persona["dispositivo"],
        "hostname": persona["hostname"],
        "usuario": persona["id"],
        "area": persona["area"]
    },
    "externo": {
        "valor": dominio,
        "tipo": "dominio"
    },
    "enrichment": None,
    "risk_score": None,
    "correlaciones": []
})
```

NOTA IMPORTANTE: En modo lab, el simulador publica DIRECTAMENTE en events:raw
(ya normalizado), porque no tiene archivos de log físicos.
En producción, el collector lee archivos físicos y normaliza.
Esta diferencia es esperada y correcta.

TAREA 2 — Verificar que el simulador usa el heartbeat:

```python
# En simulator/main.py agregar:
asyncio.create_task(_heartbeat_loop(redis_bus, "simulator"))
```

TAREA 3 — Crear scripts/verify_lab_pipeline.py:

```python
"""
Verifica el pipeline completo en modo lab.
Inyecta un evento de prueba y lo rastrea hasta MongoDB.
"""
import asyncio
import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient
import json
import os
import uuid
import time

async def main():
    r = aioredis.from_url("redis://localhost:6379")
    mongo = AsyncIOMotorClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017/NYXAR"))
    db = mongo.NYXAR
    
    print("=== Verificando Pipeline Completo (Lab Mode) ===\n")
    
    # Generar un evento de prueba con ID único para rastrearlo
    test_id = f"evt_test_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    test_domain = f"verify-{uuid.uuid4().hex[:8]}.test.com"
    
    test_event = {
        "id": test_id,
        "timestamp": asyncio.get_event_loop().time(),
        "source": "dns",
        "tipo": "query",
        "interno": {
            "ip": "192.168.1.45",
            "hostname": "PC-TEST-01",
            "usuario": "test.verify",
            "area": "testing"
        },
        "externo": {
            "valor": test_domain,
            "tipo": "dominio"
        },
        "enrichment": None,
        "risk_score": None,
        "correlaciones": []
    }
    
    # Paso 1: Publicar en events:raw
    await r.xadd("events:raw", {"data": json.dumps(test_event)})
    print(f"✓ Paso 1: Evento publicado en events:raw (id: {test_id})")
    
    # Esperar que el enricher lo procese
    print("  Esperando que el enricher procese...")
    await asyncio.sleep(3)
    
    # Paso 2: Verificar que llegó a events:enriched
    enriched_msgs = await r.xrevrange("events:enriched", count=20)
    found_enriched = False
    for msg_id, msg_data in enriched_msgs:
        ev = json.loads(msg_data.get(b"data", b"{}"))
        if ev.get("id") == test_id:
            found_enriched = True
            print(f"✓ Paso 2: Evento encontrado en events:enriched")
            print(f"  enrichment: {ev.get('enrichment', {}).get('reputacion', 'none')}")
            print(f"  risk_score: {ev.get('risk_score')}")
            break
    
    if not found_enriched:
        print("❌ Paso 2: Evento NO encontrado en events:enriched")
        print("  El enricher puede no estar corriendo o estar muy lento")
    
    # Paso 3: Verificar que llegó a MongoDB
    await asyncio.sleep(3)
    mongo_event = await db.events.find_one({"id": test_id})
    if mongo_event:
        print(f"✓ Paso 3: Evento persistido en MongoDB")
    else:
        print(f"⚠ Paso 3: Evento no en MongoDB todavía (puede tardar más)")
    
    # Resumen
    print(f"\n{'✓ Pipeline funcional' if found_enriched else '❌ Pipeline roto — revisar enricher'}")
    
    await r.aclose()
    mongo.close()
    print("\n=== Verificación I16 COMPLETADA ===")

asyncio.run(main())
```

---

## 🔍 PROMPT I17 — Verificación End-to-End Completa

```
Sos un Integration Engineer realizando la verificación final de todo el sistema.

Este es el "test de humo" completo: verificar que un evento generado por el
simulador llega correctamente hasta el dashboard del browser.

CREAR: scripts/verify_e2e.py

```python
"""
Verificación End-to-End de NYXAR
Rastrea un evento desde el simulador hasta el dashboard.

Uso: python scripts/verify_e2e.py
Requiere: Stack completo corriendo (docker-compose --profile lab up)
"""
import asyncio
import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient
import httpx
import json
import os
import uuid
import time

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/NYXAR")
API_URL = "http://localhost:8000"

async def check_service_heartbeats(r):
    print("─── Servicios activos ───")
    services = ["collector", "enricher", "correlator", "ai_analyst", "notifier"]
    all_ok = True
    for svc in services:
        heartbeat = await r.get(f"heartbeat:{svc}")
        if heartbeat:
            print(f"  ✓ {svc}")
        else:
            print(f"  ❌ {svc} — sin heartbeat")
            all_ok = False
    return all_ok

async def check_pipeline_flow(r, db):
    print("\n─── Flujo del pipeline ───")
    
    raw_len = await r.xlen("events:raw")
    enriched_len = await r.xlen("events:enriched")
    mongo_count = await db.events.count_documents({})
    
    print(f"  events:raw: {raw_len} mensajes")
    print(f"  events:enriched: {enriched_len} mensajes")
    print(f"  MongoDB events: {mongo_count} documentos")
    
    if raw_len > 0 and enriched_len > 0:
        print("  ✓ Pipeline activo")
        return True
    else:
        print("  ❌ Pipeline inactivo")
        return False

async def check_api_endpoints(session):
    print("\n─── Endpoints de la API ───")
    endpoints = [
        ("/health", "GET"),
        ("/api/v1/events?limit=1", "GET"),
        ("/api/v1/identities", "GET"),
        ("/api/v1/incidents", "GET"),
        ("/api/v1/alerts/summary", "GET"),
    ]
    all_ok = True
    for path, method in endpoints:
        r = await session.request(method, f"{API_URL}{path}")
        status = "✓" if r.status_code == 200 else "❌"
        print(f"  {status} {method} {path} → {r.status_code}")
        if r.status_code != 200:
            all_ok = False
    return all_ok

async def check_identities(db):
    print("\n─── Identidades ───")
    count = await db.identities.count_documents({})
    print(f"  Total identidades en MongoDB: {count}")
    
    if count > 0:
        high_risk = await db.identities.count_documents({"risk_score_actual": {"$gt": 60}})
        print(f"  Con risk score > 60: {high_risk}")
        print("  ✓ Identidades disponibles")
        return True
    else:
        print("  ⚠ Sin identidades — el correlator puede no estar actualizando")
        return False

async def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║     NYXAR — VERIFICACIÓN END-TO-END      ║")
    print("╚══════════════════════════════════════════════════════╝\n")
    
    r = aioredis.from_url(REDIS_URL)
    mongo = AsyncIOMotorClient(MONGO_URL)
    db = mongo.NYXAR
    
    results = {}
    
    async with httpx.AsyncClient(timeout=10) as session:
        results["heartbeats"] = await check_service_heartbeats(r)
        results["pipeline"] = await check_pipeline_flow(r, db)
        results["api"] = await check_api_endpoints(session)
        results["identities"] = await check_identities(db)
    
    # Resumen final
    print("\n╔══════════════════════════════════════════╗")
    print("║              RESUMEN FINAL               ║")
    print("╠══════════════════════════════════════════╣")
    
    all_passed = all(results.values())
    for check, passed in results.items():
        icon = "✓" if passed else "❌"
        print(f"║  {icon}  {check:<35} ║")
    
    print("╠══════════════════════════════════════════╣")
    if all_passed:
        print("║  ✓  SISTEMA OPERATIVO — Todo funcional   ║")
    else:
        print("║  ❌  REVISAR COMPONENTES CON FALLO        ║")
    print("╚══════════════════════════════════════════╝")
    
    await r.aclose()
    mongo.close()
    
    return 0 if all_passed else 1

asyncio.run(main())
```

INSTRUCCIONES FINALES PARA EL DESARROLLADOR:

Antes de declarar el sistema como "listo para mostrar", correr:
```bash
# 1. Levantar el stack completo
docker-compose --profile lab up -d

# 2. Esperar 30 segundos para que todo inicialice
sleep 30

# 3. Correr verificaciones en orden
python scripts/verify_collector.py
python scripts/verify_enricher.py
python scripts/verify_correlator.py
python scripts/verify_api.py
node scripts/verify_websocket.js

# 4. Verificación final
python scripts/verify_e2e.py
```

Si TODOS pasan: el sistema está integrado correctamente.
Si alguno falla: el output del script indica exactamente qué revisar.
```

---

## 📋 Checklist de Integración por Fase

### Fase 1 — Pipeline Principal
```
□ I01: Collector publica en events:raw con formato correcto
□ I02: Enricher consume y publica en events:enriched con enrichment
□ I03: Correlator persiste incidentes en MongoDB y publica en PubSub
□ I04: API FastAPI lee de MongoDB y responde con formato estándar
□ I05: WebSocket emite eventos al browser con nombres correctos
□ I06: Dashboard tiene cliente HTTP centralizado (api/client.js)
□ I07: Zustand store conectado a WebSocket y API
□ Verificación E2E pasa sin errores
```

### Fase 2 — Módulos V2
```
□ I09: AI Analyst publica memos en MongoDB y PubSub
□ I10: MISP IOCs llegan a blocklists de Redis y el enricher los usa
□ I11: AD identidades resueltas en Redis, normalizer las usa
□ I12: Auto Response proposals visibles en el dashboard
□ I13: Notifier suscripto a canales correctos y procesando alertas
□ I14: Reporter genera PDFs y los sirve via API
□ I15: Observability reporta health de todos los servicios
```

### Regla de oro
> Si Cursor pregunta "¿cómo conecto X con Y?",
> la respuesta es siempre: "Usá el script de verificación del PROMPTS_V4.md
> que corresponde a esa integración. Si el script pasa, está conectado."

---

*NYXAR — PROMPTS_V4.md — Contratos de Integración — v1.0 — 2026*
