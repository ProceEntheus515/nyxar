# 🧠 NYXAR — PROMPTS_V2.md
## Módulos Avanzados — Segunda Entrega

> **Prerequisito:** Tener el PROMPTS.md (v1) completamente implementado y con tests pasando.
> Este archivo extiende el sistema con 7 módulos nuevos. Seguir el mismo contrato:
> un prompt a la vez, tests antes de avanzar, stack inmutable.
>
> **Stack heredado (no modificar):**
> Python 3.12 · FastAPI · Redis 7 · MongoDB 7 + motor · React 18 · Docker

---

## 📋 Índice de Prompts V2

| # | Rol | Componente | Módulo |
|---|-----|-----------|--------|
| V01 | Security Dev | MISP — cliente async e ingesta de IOCs | MISP |
| V02 | Security Dev | MISP — contribución de IOCs propios | MISP |
| V03 | Security Dev | MISP — sync automático y correlación | MISP |
| V04 | Integration Dev | AD/LDAP — conector de identidades | AD/LDAP |
| V05 | Integration Dev | AD/LDAP — sincronización y resolución en tiempo real | AD/LDAP |
| V06 | Automation Dev | Respuesta automatizada — motor de acciones | AUTO-RESPONSE |
| V07 | Automation Dev | Respuesta automatizada — playbooks por escenario | AUTO-RESPONSE |
| V08 | Automation Dev | Respuesta automatizada — aprobación humana y auditoría | AUTO-RESPONSE |
| V09 | AI Engineer | Threat Hunting — motor de hipótesis con Claude | HUNTING |
| V10 | AI Engineer | Threat Hunting — queries sobre MongoDB | HUNTING |
| V11 | AI Engineer | Threat Hunting — interfaz de investigación en dashboard | HUNTING |
| V12 | Report Dev | Sistema de reportes — generador PDF automático | REPORTS |
| V13 | Report Dev | Sistema de reportes — scheduler y plantillas | REPORTS |
| V14 | Integration Dev | Notificaciones — motor central de alertas | NOTIFY |
| V15 | Integration Dev | Notificaciones — conectores Slack, Email, WhatsApp | NOTIFY |
| V16 | Integration Dev | Notificaciones — reglas y preferencias por usuario | NOTIFY |
| V17 | DevOps Engineer | Observabilidad — métricas internas del sistema | OBS |
| V18 | DevOps Engineer | Observabilidad — dashboard de salud del sistema | OBS |
| V19 | QA Engineer | Tests de integración para todos los módulos V2 | TESTING |

---

## CONTEXTO ADICIONAL V2
> Agregar esto al CONTEXTO GLOBAL al iniciar cualquier sesión de V2 en Cursor.

```
MÓDULOS NUEVOS EN V2 (agregados a la estructura existente):

nyxar/
├── misp_connector/          # integración con MISP Community
│   ├── Dockerfile
│   ├── requirements.txt     (pymisp, httpx, motor, redis)
│   ├── main.py
│   ├── client.py            # cliente async para API de MISP
│   ├── ingestor.py          # ingesta IOCs de MISP al enricher
│   ├── contributor.py       # publica IOCs propios a MISP
│   └── sync.py              # sincronización periódica
│
├── ad_connector/            # integración con Active Directory / LDAP
│   ├── Dockerfile
│   ├── requirements.txt     (ldap3, motor, redis)
│   ├── main.py
│   ├── client.py            # cliente LDAP async
│   ├── identity_sync.py     # sync de usuarios/grupos a MongoDB
│   └── resolver.py          # resolución ip→usuario en tiempo real
│
├── auto_response/           # respuesta automatizada con aprobación humana
│   ├── Dockerfile
│   ├── requirements.txt     (motor, redis, httpx)
│   ├── main.py
│   ├── engine.py            # motor de decisión de respuesta
│   ├── playbooks/
│   │   ├── __init__.py
│   │   ├── quarantine.py    # aislar dispositivo de la red
│   │   ├── block_ip.py      # bloquear IP en firewall
│   │   ├── disable_user.py  # deshabilitar usuario en AD
│   │   └── notify_only.py   # solo notificar, sin acción
│   ├── approval.py          # flujo de aprobación humana
│   └── audit.py             # log de auditoría de acciones
│
├── threat_hunting/          # hunting proactivo guiado por IA
│   ├── Dockerfile
│   ├── requirements.txt     (anthropic, motor, redis)
│   ├── main.py
│   ├── hypothesis_engine.py # generación de hipótesis con Claude
│   ├── query_builder.py     # traduce hipótesis a queries MongoDB
│   ├── hunter.py            # ejecuta las búsquedas
│   └── prompts/
│       ├── hypothesis.txt
│       └── findings.txt
│
├── reporter/                # generación de reportes PDF automáticos
│   ├── Dockerfile
│   ├── requirements.txt     (reportlab, motor, redis, schedule)
│   ├── main.py
│   ├── generator.py         # genera el PDF
│   ├── scheduler.py         # programa generación automática
│   └── templates/
│       ├── daily.py         # reporte diario
│       ├── weekly.py        # reporte semanal
│       └── incident.py      # reporte de incidente específico
│
├── notifier/                # motor central de notificaciones
│   ├── Dockerfile
│   ├── requirements.txt     (httpx, motor, redis, jinja2)
│   ├── main.py
│   ├── engine.py            # evalúa qué notificar y a quién
│   ├── channels/
│   │   ├── __init__.py
│   │   ├── slack.py
│   │   ├── email.py         # SMTP async
│   │   └── whatsapp.py      # via API de WhatsApp Business o Twilio
│   ├── templates/           # plantillas Jinja2 por canal y tipo
│   └── preferences.py       # reglas por usuario/área/severidad
│
└── observability/           # monitoreo interno del sistema
    ├── Dockerfile
    ├── requirements.txt     (prometheus-client, motor, redis, fastapi)
    ├── main.py
    ├── metrics.py           # definición de métricas Prometheus
    ├── collectors/
    │   ├── redis_collector.py
    │   ├── mongo_collector.py
    │   └── pipeline_collector.py
    └── health.py            # endpoints de salud detallados

PRINCIPIOS ADICIONALES V2:
8. Las acciones automatizadas SIEMPRE requieren aprobación humana explícita
   (excepto las configuradas como "auto-approve" por el administrador).
9. Toda acción ejecutada se loggea en la colección audit_log de MongoDB.
10. Las notificaciones tienen deduplicación: el mismo evento no genera
    dos notificaciones en menos de 15 minutos al mismo destinatario.
11. El sistema de hunting no modifica datos — solo lee y analiza.
12. Los reportes PDF se generan en background, nunca bloquean la API.
```

---

## MÓDULO MISP — Integración con MISP Community

---

### PROMPT V01 — Security Dev
**Rol:** Security Engineer  
**Componente:** MISP — cliente async y estructura base  
**Entregable:** `misp_connector/client.py` y `misp_connector/main.py`

```
Sos un Security Engineer especializado en threat intelligence y plataformas
de sharing de IOCs como MISP (Malware Information Sharing Platform).

Tu tarea es implementar el cliente async para la API de MISP.

CONTEXTO DE MISP:
MISP es una plataforma open source de threat intelligence sharing.
La instancia a conectar puede ser:
a) Una instancia propia auto-hosteada (recomendado a futuro)
b) MISP Community / CIRCL: https://www.misp-project.org/communities/
c) Cualquier instancia pública con API key

ARCHIVO: misp_connector/client.py

```python
class MISPClient:
    """
    Cliente async para la API REST de MISP v2.4+.
    Documentación: https://www.misp-project.org/openapi/
    
    Autenticación: header Authorization: {API_KEY}
    Base URL: configurable via MISP_URL en .env
    """
    
    async def connect(self) -> bool:
        """
        Verifica conectividad con GET /servers/getPyMISPVersion.json
        Retorna True si la instancia responde y la API key es válida.
        Loggear versión de MISP al conectar.
        """
    
    async def get_events(
        self,
        last: str = "1d",          # "1h", "1d", "7d" — eventos recientes
        tags: list[str] = None,     # filtrar por tags
        threat_level: int = None,   # 1=High, 2=Medium, 3=Low, 4=Undefined
        limit: int = 100
    ) -> list[dict]:
        """
        GET /events/restSearch
        Retorna lista de eventos MISP con sus atributos (IOCs).
        Un evento MISP puede contener decenas de IOCs.
        """
    
    async def get_attributes(
        self,
        event_id: str = None,
        type_filter: list[str] = None,  # ["ip-dst", "domain", "md5", "sha256", "url"]
        last: str = "1d",
        limit: int = 1000
    ) -> list[dict]:
        """
        GET /attributes/restSearch
        Más granular que get_events: retorna IOCs individuales directamente.
        Tipos de atributo MISP más relevantes:
        - ip-dst, ip-src: IPs maliciosas
        - domain, hostname: dominios maliciosos
        - md5, sha256: hashes de malware
        - url: URLs maliciosas
        - email-src: emails de phishing
        """
    
    async def create_event(self, event_data: dict) -> Optional[str]:
        """
        POST /events/add
        Crea un nuevo evento MISP con IOCs propios.
        Retorna el event_id generado por MISP.
        Solo si MISP_CONTRIBUTE=true en .env (opt-in explícito).
        """
    
    async def add_attribute(self, event_id: str, attribute: dict) -> bool:
        """
        POST /attributes/add/{event_id}
        Agrega un IOC a un evento existente.
        """
    
    async def search_attribute(self, valor: str) -> list[dict]:
        """
        Busca un valor específico (IP, dominio, hash) en todos los atributos.
        GET /attributes/restSearch con value={valor}
        Retorna lista de atributos que matchean con contexto del evento padre.
        """
```

VARIABLES DE ENTORNO REQUERIDAS:
```
MISP_URL=https://misp.tu-instancia.com
MISP_API_KEY=tu_api_key_aqui
MISP_VERIFY_SSL=true
MISP_CONTRIBUTE=false    # opt-in: si true, el sistema puede publicar IOCs
MISP_ORG_NAME=NYXAR
```

MANEJO DE ERRORES ESPECÍFICO DE MISP:
- 403: API key inválida o sin permisos → log crítico, no reintentar
- 404: evento/atributo no encontrado → retornar None, no es error
- 429: rate limit → backoff exponencial, máximo 3 reintentos
- SSL errors: si MISP_VERIFY_SSL=false, deshabilitar verificación
  (útil para instancias internas con certificados self-signed)
- Timeout: 30 segundos por request

TAMBIÉN CREAR: misp_connector/main.py
Orquestador que inicia todos los componentes del módulo MISP:
```python
async def main():
    client = MISPClient()
    if not await client.connect():
        logger.error("No se pudo conectar a MISP. Revisar MISP_URL y MISP_API_KEY.")
        return
    
    await asyncio.gather(
        ingestor.start(client),   # ingesta continua de IOCs
        contributor.start(client) # contribución de IOCs propios (si está habilitado)
    )
```

REGLAS:
- Usar httpx.AsyncClient con timeout=30 y verify=MISP_VERIFY_SSL
- Todas las respuestas de MISP son JSON — parsear siempre, nunca asumir estructura
- El cliente no tiene estado entre llamadas — cada método crea su request
- Loggear latencia de cada llamada a la API de MISP a nivel DEBUG

NO HAGAS:
- No uses la librería pymisp síncrona. Implementar el cliente HTTP directamente con httpx.
- No hardcodees el tipo de instancia MISP. Debe funcionar con cualquier v2.4+.
- No falles si MISP no está disponible al arrancar. Reintentar cada 5 minutos.
- No envíes IOCs a MISP si MISP_CONTRIBUTE=false (default).
```

---

### PROMPT V02 — Security Dev
**Rol:** Security Engineer  
**Componente:** MISP — ingestor de IOCs al enricher  
**Entregable:** `misp_connector/ingestor.py`

```
Sos un Security Engineer especializado en pipelines de threat intelligence.

Tu tarea es implementar el ingestor que trae IOCs de MISP y los integra
al sistema de enrichment de NYXAR (blocklists en Redis).

ARCHIVO: misp_connector/ingestor.py

```python
class MISPIngestor:
    """
    Consume IOCs de MISP y los carga en las blocklists de Redis
    del enricher, exactamente en el mismo formato que los feeds
    de Spamhaus, URLhaus, etc.
    
    Ventaja sobre feeds estáticos: los IOCs de MISP se actualizan
    en minutos, no en horas. Y tienen contexto (tags, threat level,
    nombre del evento, organización que lo reportó).
    """
    
    SYNC_INTERVAL = 300  # cada 5 minutos (MISP tiene datos muy frescos)
    
    async def start(self, client: MISPClient) -> None:
        """Loop de sincronización. Primera corrida inmediata."""
    
    async def sync_once(self, client: MISPClient) -> dict:
        """
        Descarga IOCs nuevos desde la última sincronización y los
        carga en Redis. Retorna estadísticas: {nuevos, actualizados, total}.
        
        Guardar timestamp de última sync en Redis:
        key: "misp:last_sync" → ISO8601 timestamp
        
        En la primera corrida: traer los últimos 7 días.
        En corridas siguientes: traer solo desde last_sync.
        """
    
    async def _ingest_attributes(
        self, 
        attributes: list[dict], 
        redis_bus: RedisBus
    ) -> tuple[int, int]:
        """
        Procesa lista de atributos MISP y los carga en Redis.
        
        Para cada atributo:
        1. Determinar el tipo: ip-dst/src → blocklist:misp_ips
                              domain/hostname → blocklist:misp_domains
                              md5/sha256 → blocklist:misp_hashes
                              url → blocklist:misp_urls
        
        2. Extraer metadatos del contexto:
           - event.info: nombre del evento (descripción del ataque)
           - event.threat_level_id: 1=High, 2=Medium, 3=Low
           - attribute.tags: lista de tags (malware family, etc.)
           - org.name: organización que lo reportó
        
        3. Guardar en Redis con metadata enriquecida:
           key: "misp:meta:{valor}" → JSON con contexto
           (para que el enricher pueda mostrar contexto de MISP en el enrichment)
        
        4. Agregar al set de blocklist correspondiente:
           redis SADD blocklist:misp_ips {ip}
        
        Retornar (nuevos_insertados, ya_existentes)
        """
    
    def _map_threat_level(self, level_id: int) -> str:
        """
        MISP threat levels → reputacion del enrichment:
        1 (High) → "malicioso"
        2 (Medium) → "malicioso"
        3 (Low) → "sospechoso"
        4 (Undefined) → "sospechoso"
        """
    
    async def get_context_for_ioc(
        self, 
        valor: str, 
        redis_bus: RedisBus
    ) -> Optional[dict]:
        """
        Recupera el contexto MISP de un IOC específico.
        Usado por el enricher cuando detecta un hit en blocklist:misp_*.
        Retorna el metadata guardado en "misp:meta:{valor}".
        """
    
    async def get_stats(self) -> dict:
        """
        Total de IOCs por tipo, timestamp de última sync,
        cantidad de hits en las blocklists de MISP en las últimas 24h.
        """
```

INTEGRACIÓN CON EL ENRICHER EXISTENTE:
El enricher ya tiene un método check_ip() y check_domain() que verifican
los sets de Redis. Agregar al FeedDownloader las nuevas blocklists de MISP:

```python
# En enricher/feeds/downloader.py — agregar a la verificación:
MISP_BLOCKLISTS = [
    "blocklist:misp_ips",
    "blocklist:misp_domains",
    "blocklist:misp_urls",
    "blocklist:misp_hashes",
]
```

Cuando el enricher encuentra un hit en una blocklist de MISP,
consultar el contexto de MISP en Redis y agregarlo al Enrichment:
```python
enrichment.fuente = "misp"
enrichment.tags = misp_context.get("tags", [])
enrichment.categoria = misp_context.get("event_name", "MISP IOC")
```

REGLAS:
- Los IOCs de MISP tienen TTL en Redis de 48 horas (se renuevan con cada sync).
  Si MISP deja de estar disponible, los IOCs persisten 48h antes de expirar.
- No sobreescribir un IOC existente con datos de menor calidad
  (threat_level más alto = mayor prioridad).
- Loggear estadísticas de sync: N nuevos IOCs, N tipos distintos, latencia total.

NO HAGAS:
- No cargues los IOCs de MISP en la misma blocklist que los feeds estáticos.
  Mantener sets separados (blocklist:misp_*) para poder rastrear la fuente.
- No sincronices más de una vez cada 5 minutos (respetar rate limits de MISP).
- No elimines IOCs de MISP al hacer sync — solo agregar. La eliminación es
  manual o cuando el TTL expira.
```

---

### PROMPT V03 — Security Dev
**Rol:** Security Engineer  
**Componente:** MISP — contribución de IOCs propios  
**Entregable:** `misp_connector/contributor.py`

```
Sos un Security Engineer especializado en threat intelligence sharing
y en el modelo de inteligencia colectiva de comunidades de seguridad.

Tu tarea es implementar el módulo que publica IOCs detectados por
NYXAR de vuelta a la comunidad MISP.

FILOSOFÍA:
Este módulo implementa el modelo de "dar para recibir" de la comunidad
de threat intelligence. Cuando NYXAR detecta un IOC nuevo que no
estaba en ningún feed conocido, puede contribuirlo a MISP para que
otras organizaciones se beneficien. Es opt-in: MISP_CONTRIBUTE=true.

ARCHIVO: misp_connector/contributor.py

```python
class MISPContributor:
    """
    Publica IOCs nuevos y validados de NYXAR a MISP.
    
    Un IOC es elegible para contribución si:
    1. No estaba en ninguna blocklist conocida al momento de detección
    2. Fue confirmado como malicioso (incidente cerrado, no falso positivo)
    3. Tiene suficiente contexto para ser útil (al menos tipo + valor + descripción)
    4. MISP_CONTRIBUTE=true en .env
    """
    
    async def start(self, client: MISPClient) -> None:
        """
        Escucha la colección incidents de MongoDB (Change Stream).
        Cuando un incidente pasa a estado "cerrado" (no "falso_positivo"):
        evaluar si los IOCs del incidente son elegibles para contribución.
        """
    
    async def evaluate_incident(self, incident: dict) -> list[dict]:
        """
        Analiza un incidente cerrado y extrae IOCs contribuibles.
        
        Criterios de elegibilidad:
        - El IOC no está en ninguna blocklist existente
        - El IOC aparece en al menos 2 eventos del incidente (no es ruido)
        - El incidente tiene severidad "alta" o "critica"
        - El incidente NO es de tipo "falso_positivo"
        
        Retorna lista de dicts con estructura MISP:
        {
          "type": "ip-dst" | "domain" | "md5" | "url",
          "value": "185.220.101.47",
          "comment": "Detectado como C2 de beaconing — NYXAR",
          "to_ids": True,           # marcar como útil para detección IDS
          "tags": ["NYXAR", "latam", "c2", "beaconing"]
        }
        """
    
    async def publish_iocs(
        self, 
        iocs: list[dict], 
        incident: dict,
        client: MISPClient
    ) -> Optional[str]:
        """
        Crea un evento MISP con los IOCs del incidente.
        
        Estructura del evento MISP a crear:
        {
          "info": f"[NYXAR] {incident['titulo']}",
          "threat_level_id": mapear_severidad(incident['severidad']),
          "analysis": 2,          # 0=Initial, 1=Ongoing, 2=Completed
          "distribution": 1,      # 0=Org only, 1=Community, 2=Connected, 3=All
          "tags": [
            "tlp:white",          # o tlp:green según política de la empresa
            "NYXAR:latam",
            f"sector:latam"
          ],
          "Attribute": iocs       # lista de IOCs
        }
        
        Guardar el MISP event_id en el incidente de MongoDB:
        db.incidents.update_one({"id": incident_id}, 
                                {"$set": {"misp_event_id": event_id}})
        
        Retornar event_id o None si falló.
        """
    
    def _map_severidad_to_threat_level(self, severidad: str) -> int:
        """
        critica → 1 (High)
        alta    → 1 (High)
        media   → 2 (Medium)
        baja    → 3 (Low)
        """
```

POLÍTICA DE PRIVACIDAD AL CONTRIBUIR:
Antes de publicar, el contributor debe sanitizar los IOCs:
- Remover IPs internas (RFC1918) — NUNCA contribuir IPs de la red interna
- Remover nombres de usuarios o dispositivos internos de los comentarios
- Remover nombres de dominio .local o .internal
- Los comentarios deben describir el comportamiento, no la identidad

REGLAS:
- La contribución es asíncrona y no bloqueante. Si falla, loggear y continuar.
- Guardar en MongoDB todos los IOCs contribuidos con timestamp y event_id de MISP.
- No contribuir el mismo IOC dos veces (verificar en MongoDB antes de publicar).
- Respetar la política de TLP (Traffic Light Protocol):
  TLP:WHITE por defecto. Configurable via MISP_TLP en .env.

NO HAGAS:
- No contribuyas automáticamente al cerrar un incidente. Hacer una evaluación
  explícita de elegibilidad primero.
- No incluyas información identificatoria de la empresa en los IOCs publicados.
- No uses distribution=3 (All Communities) sin confirmación explícita.
  Default: distribution=1 (Community only).
- No contribuyas si MISP_CONTRIBUTE no está explícitamente en "true".
```

---

## MÓDULO AD/LDAP — Integración con Active Directory

---

### PROMPT V04 — Integration Dev
**Rol:** Integration Developer  
**Componente:** AD/LDAP — cliente y sincronización inicial  
**Entregable:** `ad_connector/client.py` y `ad_connector/identity_sync.py`

```
Sos un Integration Developer especializado en Active Directory, LDAP
y gestión de identidades empresariales.

Tu tarea es implementar el conector con Active Directory / LDAP para
enriquecer automáticamente las identidades de NYXAR con datos reales
de la organización.

PROBLEMA QUE RESUELVE:
Hoy el sistema resuelve ip→usuario desde una tabla manual que el simulador
puebla. En producción, esa tabla viene de Active Directory: quién está
logueado en qué máquina, a qué grupos pertenece, cuál es su cargo.

ARCHIVO: ad_connector/client.py

```python
class ADClient:
    """
    Cliente LDAP async usando la librería ldap3.
    Soporta tanto Active Directory (Windows) como OpenLDAP (Linux).
    
    Configuración via .env:
    AD_SERVER=192.168.1.10
    AD_PORT=389              # 636 para LDAPS
    AD_USE_SSL=false         # true para LDAPS
    AD_DOMAIN=empresa.local
    AD_BASE_DN=DC=empresa,DC=local
    AD_USER=CN=NYXAR,CN=Users,DC=empresa,DC=local
    AD_PASSWORD=...
    AD_SYNC_INTERVAL=300     # segundos entre sincronizaciones
    """
    
    async def connect(self) -> bool:
        """
        Conectar al servidor LDAP.
        Usar ldap3 con Connection(auto_bind=AUTO_BIND_NO_TLS para LDAP,
        AUTO_BIND_TLS_BEFORE_BIND para LDAPS).
        Retornar True si la conexión y bind son exitosos.
        """
    
    async def get_all_users(self) -> list[dict]:
        """
        Query LDAP para traer todos los usuarios activos.
        
        Base: AD_BASE_DN
        Filtro: (&(objectClass=user)(objectCategory=person)
                  (!(userAccountControl:1.2.840.113556.1.4.803:=2)))
        # El filtro excluye cuentas deshabilitadas
        
        Atributos a recuperar:
        - sAMAccountName (username)
        - displayName (nombre completo)
        - mail (email)
        - department (área/departamento)
        - title (cargo)
        - manager (DN del gerente)
        - memberOf (grupos a los que pertenece)
        - lastLogon (último login — timestamp LDAP, convertir a datetime)
        - userWorkstations (máquinas habilitadas para este usuario)
        - whenCreated (fecha de creación de la cuenta)
        """
    
    async def get_computers(self) -> list[dict]:
        """
        Traer todos los equipos del dominio.
        
        Filtro: (&(objectClass=computer)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))
        
        Atributos:
        - cn (hostname)
        - dNSHostName (FQDN)
        - operatingSystem
        - lastLogonTimestamp
        - description
        """
    
    async def get_groups(self) -> list[dict]:
        """
        Traer grupos de seguridad relevantes.
        Filtro: (&(objectClass=group)(groupType:1.2.840.113556.1.4.803:=2147483648))
        # Solo grupos de seguridad, no de distribución
        
        Atributos: cn, description, member
        """
    
    async def get_logged_on_users(self) -> list[dict]:
        """
        IMPORTANTE: AD no expone directamente "IP → usuario logueado ahora".
        Esta información viene de los eventos de Security del Event Log de Windows
        (Event ID 4624 — Logon) que Wazuh ya recolecta.
        
        Este método consulta los últimos eventos de logon en MongoDB
        (parseados por el wazuh_parser) y construye el mapa ip→usuario actual.
        
        Retorna: [{"ip": "192.168.1.45", "usuario": "maria.gomez", 
                   "hostname": "PC-CONT-03", "desde": datetime}]
        """
```

ARCHIVO: ad_connector/identity_sync.py

```python
class IdentitySync:
    """
    Sincroniza usuarios y equipos de AD a la colección identities de MongoDB.
    Enriquece los perfiles de identidad con datos reales de la organización.
    """
    
    async def full_sync(self, client: ADClient) -> dict:
        """
        Sincronización completa: usuarios + equipos + grupos.
        Usar MongoDB upsert (update con upsert=True) para cada identidad.
        
        Por cada usuario de AD, crear/actualizar en MongoDB:
        {
          "id": "{area}.{username}",     # ej: "contabilidad.mgarcia"
          "usuario": sAMAccountName,
          "nombre_completo": displayName,
          "email": mail,
          "area": department,
          "cargo": title,
          "grupos_ad": [lista de CNs de grupos],
          "es_admin": True si es miembro de "Domain Admins" o "Administrators",
          "manager_id": id del manager (si existe en el sistema),
          "ad_sincronizado": True,
          "ad_ultima_sync": datetime.utcnow(),
          # Preservar baseline y risk_score_actual si ya existen
        }
        
        Retornar: {sincronizados, nuevos, actualizados, errores}
        """
    
    async def incremental_sync(self, client: ADClient, desde: datetime) -> dict:
        """
        Sync incremental: solo usuarios modificados desde {desde}.
        Usar el atributo whenChanged de AD para filtrar.
        Más eficiente para el sync periódico.
        """
    
    async def flag_high_privilege_users(self) -> None:
        """
        Marcar en MongoDB los usuarios con privilegios altos.
        Estos usuarios tienen umbrales de alerta más sensibles
        (un admin que hace algo raro es más crítico que un usuario normal).
        
        Grupos que implican privilegio alto:
        - Domain Admins, Enterprise Admins, Schema Admins
        - Backup Operators, Server Operators
        - Cualquier grupo con "admin" en el nombre (configurable)
        
        Setear en MongoDB: identidad.es_privilegiado = True
        El correlator usa este campo para ajustar el risk score.
        """
```

REGLAS:
- La conexión LDAP se restablece automáticamente si se cae.
- El sync completo corre al iniciar. Luego sync incremental cada AD_SYNC_INTERVAL segundos.
- Si AD no está disponible, el sistema sigue funcionando con los datos del último sync.
- Los timestamps de AD (filetime de Windows) deben convertirse a datetime UTC:
  `datetime(1601, 1, 1) + timedelta(microseconds=filetime // 10)`

NO HAGAS:
- No almacenes la contraseña de AD en MongoDB ni en logs.
- No hagas queries LDAP sin timeout (usar receive_timeout=10 en ldap3).
- No sincronices cuentas deshabilitadas de AD.
- No uses LDAP síncrono en el loop principal — wrappear con asyncio.to_thread().
```

---

### PROMPT V05 — Integration Dev
**Rol:** Integration Developer  
**Componente:** AD/LDAP — resolución de identidades en tiempo real  
**Entregable:** `ad_connector/resolver.py` y actualización del normalizer

```
Sos un Integration Developer especializado en resolución de identidades
en sistemas de seguridad de red en tiempo real.

Tu tarea es implementar el resolver que reemplaza la tabla manual
ip→usuario del simulador por datos reales de AD y logs de Wazuh.

ARCHIVO: ad_connector/resolver.py

```python
class IdentityResolver:
    """
    Resuelve ip → {usuario, hostname, area, cargo} en tiempo real.
    
    Fuentes de resolución en orden de prioridad:
    1. Caché Redis (TTL 5 minutos) — más rápido
    2. Logs de logon de Wazuh en MongoDB (Event ID 4624) — más preciso
    3. Tabla de identidades de MongoDB (sincronizada desde AD) — fallback
    4. Tabla de equipos de AD (hostname → área) — último recurso
    """
    
    CACHE_TTL = 300  # 5 minutos — una sesión típica dura más que esto
    
    async def resolve(self, ip: str) -> dict:
        """
        Punto de entrada principal.
        Retorna siempre un dict (nunca None):
        {
          "ip": "192.168.1.45",
          "usuario": "mgarcia" | "desconocido",
          "nombre_completo": "María García" | None,
          "hostname": "PC-CONT-03" | "desconocido",
          "area": "contabilidad" | "desconocido",
          "cargo": "Contadora" | None,
          "es_privilegiado": False,
          "fuente_resolucion": "cache" | "wazuh_logon" | "ad_sync" | "desconocido"
        }
        """
    
    async def _resolve_from_wazuh_logons(self, ip: str) -> Optional[dict]:
        """
        Busca en MongoDB el último evento de logon exitoso
        (Wazuh Event ID 4624) para esta IP.
        
        Query MongoDB:
        db.events.find_one(
          {
            "meta.source": "wazuh",
            "interno.ip": ip,
            "externo.valor": {"$regex": "4624"},  # Event ID en la descripción
          },
          sort=[("timestamp", -1)]   # el más reciente
        )
        """
    
    async def _update_cache(self, ip: str, identity: dict) -> None:
        """Guarda la resolución en Redis con TTL de 5 minutos."""
    
    async def invalidate(self, ip: str) -> None:
        """
        Invalida la caché para una IP específica.
        Llamar cuando Wazuh detecta un logoff (Event ID 4634)
        para que la próxima consulta resuelva al nuevo usuario.
        """
    
    async def get_all_active_sessions(self) -> list[dict]:
        """
        Retorna todas las sesiones activas actuales (IP → usuario).
        Útil para el dashboard de identidades.
        Se construye desde Redis (todas las keys "identity:session:*").
        """
```

MODIFICACIÓN AL COLLECTOR/NORMALIZER.PY:
Reemplazar la resolución manual por el IdentityResolver:

```python
# En normalizer.py — reemplazar los métodos:
# resolver_hostname(ip) y resolver_usuario(ip) por:

from ad_connector.resolver import IdentityResolver

class Normalizer:
    def __init__(self, resolver: IdentityResolver):
        self.resolver = resolver
    
    async def _resolve_internal(self, ip: str) -> dict:
        """Llama al resolver y extrae hostname/usuario para el evento."""
        identity = await self.resolver.resolve(ip)
        return {
            "hostname": identity["hostname"],
            "usuario": identity["usuario"],
            "area": identity["area"]
        }
```

EVENTO ESPECIAL — WAZUH LOGON (Event ID 4624):
Cuando el wazuh_parser recibe un evento con rule relacionado a logon exitoso,
debe disparar una actualización del resolver:

```python
# En wazuh_parser.py — agregar después de publicar el evento:
if "4624" in raw.get("rule", {}).get("id", ""):
    await resolver.invalidate(agent_ip)  # forzar refresh de caché para esta IP
```

REGLAS:
- La resolución nunca debe tardar más de 50ms. Si tarda más, usar el fallback.
- Una IP desconocida no es un error — es información ("dispositivo no gestionado").
- Las IPs de servidores (siempre activos, sin sesión de usuario) deben resolverse
  al hostname del servidor, no a "desconocido".

NO HAGAS:
- No hagas una query a MongoDB por cada evento (usar caché Redis).
- No asumas que una IP siempre tiene el mismo usuario (las IPs se reasignan por DHCP).
- No falles si AD no está disponible — usar datos del último sync.
```

---

## MÓDULO RESPUESTA AUTOMATIZADA

---

### PROMPT V06 — Automation Dev
**Rol:** Automation Developer  
**Componente:** Motor de respuesta automatizada  
**Entregable:** `auto_response/engine.py` y estructura base

```
Sos un Automation Developer especializado en SOAR (Security Orchestration,
Automation and Response) y en diseño de sistemas de respuesta a incidentes.

Tu tarea es implementar el motor de respuesta automatizada de NYXAR.
PRINCIPIO FUNDAMENTAL: Las máquinas proponen, los humanos aprueban.

FILOSOFÍA DE DISEÑO:
Este no es un sistema de respuesta completamente automático.
Es un sistema de ASISTENCIA a la respuesta. Por defecto, todas las acciones
requieren aprobación humana explícita. El operador puede configurar
ciertas acciones como "auto-approve" para incidentes muy críticos,
pero eso es una decisión consciente y documentada.

ARCHIVO: auto_response/engine.py

```python
class ResponseEngine:
    """
    Motor central que:
    1. Escucha nuevos incidentes via MongoDB Change Stream
    2. Evalúa qué playbook aplica
    3. Propone acciones al operador
    4. Ejecuta las aprobadas
    5. Registra todo en el audit log
    """
    
    async def start(self) -> None:
        """
        Escucha la colección incidents de MongoDB via Change Stream.
        Por cada incidente nuevo o actualizado a estado "abierto":
        evaluar y proponer respuesta.
        """
    
    async def evaluate_incident(self, incident: dict) -> Optional[ResponsePlan]:
        """
        Determina qué acciones proponer para un incidente.
        
        Lógica de selección de playbook:
        - severidad=critica + patron=ransomware → QuarantinePlaybook
        - severidad=critica + patron=lateral_movement → QuarantinePlaybook
        - severidad=alta + patron=beaconing → BlockIPPlaybook + NotifyPlaybook
        - severidad=alta + patron=exfiltration → BlockIPPlaybook + NotifyPlaybook
        - honeypot_hit → DisableUserPlaybook + NotifyPlaybook (si hay usuario)
        - cualquier_critico → NotifyPlaybook (siempre, como mínimo)
        
        Retornar None si no hay playbook aplicable.
        """
    
    async def propose_actions(
        self, 
        incident: dict, 
        plan: ResponsePlan
    ) -> str:
        """
        Registra el plan propuesto en MongoDB y notifica al operador.
        
        Guardar en nueva colección response_proposals:
        {
          "id": generate_id(),
          "incident_id": incident["id"],
          "acciones": [lista de acciones propuestas],
          "estado": "pendiente_aprobacion",
          "auto_approve": False,    # default
          "propuesto_at": datetime,
          "aprobado_by": None,
          "aprobado_at": None,
          "ejecutado_at": None,
          "resultado": None
        }
        
        Si el incidente es severidad=critica Y la acción está configurada
        como auto-approvable en .env (AUTO_RESPONSE_CRITICO=true):
        setear auto_approve=True y ejecutar sin esperar aprobación humana.
        
        Retornar el proposal_id.
        """
    
    async def execute_approved(self, proposal_id: str) -> dict:
        """
        Ejecuta las acciones de un proposal aprobado.
        
        1. Verificar que proposal.estado == "aprobado"
        2. Para cada acción en proposal.acciones:
           a. Instanciar el playbook correspondiente
           b. Ejecutar playbook.execute()
           c. Registrar resultado (éxito/fallo) en MongoDB
        3. Actualizar proposal.estado = "ejecutado"
        4. Actualizar incidente.estado = "investigando"
        
        Retornar {ejecutadas, exitosas, fallidas, resultados}
        """
```

MODELO ResponsePlan:
```python
class AccionPropuesta(BaseModel):
    tipo: Literal["quarantine", "block_ip", "disable_user", "notify_only"]
    objetivo: str          # IP, usuario, o "all" para notificaciones
    descripcion: str       # explicación en español de qué hace esta acción
    reversible: bool       # si la acción se puede deshacer fácilmente
    impacto: str           # descripción del impacto en el negocio
    requiere_aprobacion: bool = True

class ResponsePlan(BaseModel):
    incident_id: str
    playbook_nombre: str
    acciones: list[AccionPropuesta]
    justificacion: str     # por qué se proponen estas acciones
    urgencia: Literal["inmediata", "proxima_hora", "proximo_dia"]
```

NUEVAS VARIABLES .ENV:
```
AUTO_RESPONSE_ENABLED=false       # habilitar el módulo
AUTO_RESPONSE_CRITICO=false       # auto-ejecutar en incidentes críticos
FIREWALL_API_URL=http://fw:8080   # API del firewall para bloquear IPs
AD_WRITE_ENABLED=false            # permitir deshabilitar usuarios en AD
```

REGLAS:
- Si AUTO_RESPONSE_ENABLED=false: el engine solo loggea lo que haría, sin actuar.
- Toda acción ejecutada genera un registro inmutable en audit_log.
- Una acción fallida no cancela las demás acciones del plan.
- El operador puede rechazar un proposal (estado="rechazado") con comentario.

NO HAGAS:
- No ejecutes ninguna acción sin verificar el estado del proposal en MongoDB.
- No caches el estado de approval — siempre leer de MongoDB antes de ejecutar.
- No implementes acciones destructivas (eliminar archivos, formatear discos).
  Solo: aislar, bloquear, deshabilitar, notificar.
- No ejecutes más de una acción por segundo (throttling deliberado).
```

---

### PROMPT V07 — Automation Dev
**Rol:** Automation Developer  
**Componente:** Playbooks de respuesta  
**Entregable:** Los 4 playbooks en `auto_response/playbooks/`

```
Sos un Automation Developer especializado en playbooks de respuesta a
incidentes de ciberseguridad.

Tu tarea es implementar los 4 playbooks de respuesta del sistema.
Cada playbook es una acción concreta y reversible que puede ejecutarse
sobre la infraestructura de la empresa.

INTERFACE COMÚN (todos los playbooks la implementan):

```python
class BasePlaybook:
    nombre: str
    descripcion: str
    reversible: bool
    
    async def execute(
        self, 
        objetivo: str,       # IP, usuario o dominio
        incident_id: str,
        ejecutado_by: str    # "auto" o username del operador
    ) -> PlaybookResult:
        """
        Ejecuta la acción.
        NUNCA lanza excepciones — captura todo y retorna resultado.
        """
    
    async def undo(self, execution_id: str) -> PlaybookResult:
        """Revierte la acción si reversible=True."""
    
    async def check_preconditions(self, objetivo: str) -> tuple[bool, str]:
        """
        Verifica que se puede ejecutar la acción antes de intentarla.
        Retorna (puede_ejecutar, razon_si_no_puede).
        """

class PlaybookResult(BaseModel):
    execution_id: str
    playbook: str
    objetivo: str
    exitoso: bool
    mensaje: str           # descripción del resultado
    detalles: dict         # detalles técnicos del resultado
    ejecutado_at: datetime
    puede_deshacer: bool
```

PLAYBOOK 1: quarantine.py — QuarantinePlaybook
Aisla un dispositivo de la red bloqueando su IP en el firewall
y en todos los switches (si hay API disponible).

```python
class QuarantinePlaybook(BasePlaybook):
    nombre = "Cuarentena de dispositivo"
    reversible = True
    
    async def execute(self, objetivo: str, ...) -> PlaybookResult:
        """
        objetivo = IP interna del dispositivo a aislar.
        
        PASO 1: Verificar que la IP es interna y existe en la red.
        PASO 2: Llamar a la API del firewall para bloquear la IP:
          POST {FIREWALL_API_URL}/rules/quarantine
          Body: {"ip": objetivo, "reason": f"Incidente {incident_id}"}
        PASO 3: Si la IP tiene un hostname, intentar también via
          API de switch (si SWITCH_API_URL está configurado).
        PASO 4: Guardar en MongoDB:
          {"ip": objetivo, "regla_firewall_id": id_retornado,
           "cuarentena_inicio": now, "incident_id": incident_id}
        PASO 5: Notificar al dueño del dispositivo (si se conoce).
        
        Si la API del firewall no está disponible:
        retornar PlaybookResult(exitoso=False, 
          mensaje="Firewall API no disponible. Acción manual requerida.")
        """
    
    async def undo(self, execution_id: str) -> PlaybookResult:
        """Elimina la regla de cuarentena del firewall."""
```

PLAYBOOK 2: block_ip.py — BlockIPPlaybook
Bloquea una IP EXTERNA en el firewall perimetral.

```python
class BlockIPPlaybook(BasePlaybook):
    nombre = "Bloqueo de IP externa"
    reversible = True
    
    async def execute(self, objetivo: str, ...) -> PlaybookResult:
        """
        objetivo = IP externa a bloquear.
        
        Verificar que NO es una IP interna (RFC1918) antes de bloquear.
        Si es interna, retornar error: usar QuarantinePlaybook en su lugar.
        
        POST {FIREWALL_API_URL}/rules/block_external
        Body: {"ip": objetivo, "direction": "both", 
               "comment": f"NYXAR: Incidente {incident_id}"}
        
        También agregar a la blocklist local de Redis
        para que el enricher la marque como maliciosa en futuros eventos.
        """
```

PLAYBOOK 3: disable_user.py — DisableUserPlaybook
Deshabilita un usuario en Active Directory.

```python
class DisableUserPlaybook(BasePlaybook):
    nombre = "Deshabilitar usuario en AD"
    reversible = True
    
    async def check_preconditions(self, objetivo: str) -> tuple[bool, str]:
        """
        Verificar:
        1. AD_WRITE_ENABLED=true en .env
        2. El usuario existe en AD y está habilitado
        3. El usuario NO es Domain Admin (nunca deshabilitar admins automáticamente)
        4. El usuario NO es la cuenta de servicio de NYXAR (ciclo infinito)
        """
    
    async def execute(self, objetivo: str, ...) -> PlaybookResult:
        """
        objetivo = sAMAccountName del usuario.
        
        Usar ldap3 para modificar el atributo userAccountControl:
        Setear el bit 0x0002 (ACCOUNTDISABLE) en el valor actual.
        
        Guardar el valor anterior de userAccountControl en MongoDB
        para poder revertir con undo().
        
        También: invalidar la caché del resolver para todas las IPs
        donde este usuario estaba activo.
        """
```

PLAYBOOK 4: notify_only.py — NotifyOnlyPlaybook
No ejecuta acciones en la infraestructura — solo notifica.

```python
class NotifyOnlyPlaybook(BasePlaybook):
    nombre = "Notificación de incidente"
    reversible = False
    
    async def execute(self, objetivo: str, ...) -> PlaybookResult:
        """
        objetivo = lista de destinatarios separados por coma,
                   o "responsable_area" para notificar al responsable del área.
        
        Publicar en Redis canal "notifications:urgent" para que
        el notifier lo procese y envíe por los canales configurados.
        
        Este playbook siempre retorna exitoso=True
        (el éxito real del envío lo maneja el notifier).
        """
```

REGLAS:
- Cada playbook debe poder ejecutarse de forma idempotente
  (ejecutarlo dos veces no genera duplicados ni errores).
- Los errores de APIs externas (firewall, AD) se loggean como WARNING,
  no como ERROR crítico. El sistema sigue funcionando.
- check_preconditions() siempre se llama antes de execute().

NO HAGAS:
- No implementes acciones sobre servidores de producción críticos sin
  una verificación adicional (lista de IPs protegidas en .env: PROTECTED_IPS).
- No ejecutes más de un playbook por segundo en el mismo objetivo.
- No uses las credenciales de AD del lector para escribir
  si AD_WRITE_ENABLED=false.
```

---

### PROMPT V08 — Automation Dev
**Rol:** Automation Developer  
**Componente:** Flujo de aprobación humana y auditoría  
**Entregable:** `auto_response/approval.py` y `auto_response/audit.py`

```
Sos un Automation Developer especializado en flujos de aprobación
y sistemas de auditoría para entornos regulados de seguridad.

ARCHIVO 1: auto_response/approval.py

```python
class ApprovalManager:
    """
    Gestiona el flujo de aprobación/rechazo de acciones propuestas.
    
    El flujo es:
    engine propone → notifier avisa al operador → operador aprueba/rechaza
    → engine ejecuta → audit registra
    """
    
    async def approve(
        self,
        proposal_id: str,
        aprobado_by: str,    # username del operador
        comentario: str = ""
    ) -> bool:
        """
        Aprueba un proposal pendiente.
        1. Verificar que existe y está en estado "pendiente_aprobacion"
        2. Actualizar en MongoDB:
           {estado: "aprobado", aprobado_by, aprobado_at, comentario}
        3. Publicar en Redis canal "approvals:ready" para que
           el engine ejecute inmediatamente.
        4. Retornar True si se aprobó correctamente.
        """
    
    async def reject(
        self,
        proposal_id: str,
        rechazado_by: str,
        motivo: str
    ) -> bool:
        """
        Rechaza un proposal. La acción no se ejecuta.
        Actualizar estado: "rechazado". Loggear motivo.
        """
    
    async def get_pending(self) -> list[dict]:
        """
        Lista todos los proposals pendientes de aprobación.
        Ordenados por urgencia DESC, created_at ASC.
        Para el dashboard: badge de "N acciones pendientes".
        """
    
    async def auto_expire(self) -> int:
        """
        Expira proposals que llevan más de APPROVAL_TIMEOUT horas
        sin ser aprobados o rechazados.
        Default: 24 horas. Configurable via APPROVAL_TIMEOUT en .env.
        Estado final: "expirado".
        Retorna cantidad de proposals expirados.
        """
```

ENDPOINT EN LA API (agregar a api/routers/):
```python
# api/routers/response.py

GET /response/proposals
  - Lista todos los proposals (filtrable por estado)
  - Para el panel de "Acciones pendientes" del dashboard

GET /response/proposals/{proposal_id}
  - Detalle completo: incidente, acciones, justificación

POST /response/proposals/{proposal_id}/approve
  - Body: {"comentario": "..."}
  - Aprueba y dispara ejecución inmediata

POST /response/proposals/{proposal_id}/reject
  - Body: {"motivo": "..."}

GET /response/audit
  - Lista del audit log completo (paginado)
  - Filtrable por: fecha, playbook, operador, resultado
```

ARCHIVO 2: auto_response/audit.py

```python
class AuditLogger:
    """
    Registro inmutable de todas las acciones ejecutadas por el sistema
    de respuesta automatizada. Cumple con requisitos de auditoría.
    
    La colección audit_log de MongoDB es append-only:
    - No se actualiza
    - No se elimina
    - No tiene TTL (retención permanente)
    """
    
    AUDIT_COLLECTION = "audit_log"
    
    async def log_action(
        self,
        tipo: str,               # "propuesta", "aprobacion", "rechazo", 
                                 # "ejecucion", "resultado", "reversion"
        proposal_id: str,
        actor: str,              # username o "sistema_automatico"
        incident_id: str,
        playbook: str,
        objetivo: str,
        detalle: dict,           # información específica de la acción
        exitoso: bool = None     # None si es una propuesta (aún no ejecutada)
    ) -> str:
        """
        Registra una entrada en el audit log.
        Retorna el ID del registro creado.
        
        Estructura del documento:
        {
          "_id": ObjectId(),
          "tipo": tipo,
          "timestamp": datetime.utcnow(),
          "proposal_id": proposal_id,
          "actor": actor,
          "incident_id": incident_id,
          "playbook": playbook,
          "objetivo": objetivo,      # IP o usuario (no nombres internos)
          "detalle": detalle,
          "exitoso": exitoso,
          "ip_del_actor": None       # a futuro: IP desde donde aprobó el operador
        }
        """
    
    async def get_audit_trail(self, incident_id: str) -> list[dict]:
        """
        Retorna toda la cadena de acciones para un incidente:
        propuesta → aprobación → ejecución → resultado.
        Útil para reportes de auditoría y forensics.
        """
    
    async def export_period(
        self, 
        desde: datetime, 
        hasta: datetime,
        formato: Literal["json", "csv"]
    ) -> bytes:
        """
        Exporta el audit log de un período para revisiones de auditoría.
        Usado por el reporter para incluir en reportes de compliance.
        """
```

REGLAS:
- El audit log usa MongoDB con writeConcern: majority para garantizar
  que cada entrada fue escrita en la mayoría de los nodos (si hay replica set).
  En una instancia single: writeConcern: 1 es suficiente.
- Nunca editar ni eliminar entradas del audit log una vez creadas.
- El actor "sistema_automatico" solo aplica cuando AUTO_RESPONSE_CRITICO=true.
- Incluir en el detalle el estado del sistema en el momento de la acción:
  risk_score de la identidad, severidad del incidente, hora del día.

NO HAGAS:
- No uses el audit log para debug o logging técnico.
  Solo para acciones de respuesta con impacto real.
- No guardes datos sensibles (passwords, tokens) en el detalle.
- No permitas que la API modifique entradas existentes del audit log.
```

---

## MÓDULO THREAT HUNTING

---

### PROMPT V09 — AI Engineer
**Rol:** AI Engineer / Threat Hunter  
**Componente:** Motor de hipótesis de hunting  
**Entregable:** `threat_hunting/hypothesis_engine.py` y prompts

```
Sos un AI Engineer especializado en Threat Hunting y en el uso de LLMs
para generar hipótesis de investigación en sistemas de seguridad.

CONCEPTO:
Threat Hunting es la práctica de buscar proactivamente amenazas que
los sistemas automáticos NO detectaron. La IA genera hipótesis
("¿Y si hay un atacante que...?") y el sistema las investiga.

A diferencia de las alertas automáticas:
- El hunting empieza con una pregunta, no con un evento
- Busca patrones que los detectores no conocen
- El analista humano guía la investigación

ARCHIVO: threat_hunting/hypothesis_engine.py

```python
class HypothesisEngine:
    """
    Genera hipótesis de hunting usando Claude.
    Una hipótesis es una pregunta investigable sobre la red:
    "¿Hay dispositivos que se comunican regularmente fuera del horario laboral
    y que no están en ninguna blocklist pero tienen dominios registrados recientemente?"
    """
    
    async def generate_hypotheses(
        self,
        context: HuntingContext
    ) -> list[Hypothesis]:
        """
        Llama a Claude con el contexto actual de la red y genera
        3-5 hipótesis de hunting priorizadas.
        
        El contexto incluye:
        - Últimas 24h de estadísticas: eventos por tipo, IPs únicas, dominios únicos
        - Incidentes abiertos y cerrados de la última semana
        - Threat intel reciente de MISP y feeds
        - IOCs más frecuentes que NO dispararon alertas
        - Identidades con comportamiento limpio pero ligeramente anómalo
          (risk_score entre 15 y 35 — debajo del umbral de alerta)
        
        Retornar lista de Hypothesis ordenadas por prioridad estimada.
        """
    
    async def refine_hypothesis(
        self,
        hypothesis: Hypothesis,
        resultados_parciales: list[dict]
    ) -> Hypothesis:
        """
        Dado resultados parciales de una búsqueda, Claude refina
        la hipótesis: ¿los datos apoyan o refutan la teoría?
        ¿Qué buscar a continuación?
        """
    
    async def conclude_hunt(
        self,
        hypothesis: Hypothesis,
        todos_los_resultados: list[dict]
    ) -> HuntConclusion:
        """
        Claude analiza todos los resultados y concluye:
        - ¿Se encontró evidencia de amenaza?
        - ¿Qué tan confiable es la evidencia?
        - ¿Se debe crear un incidente formal?
        - ¿Qué IOCs nuevos se descubrieron?
        """
```

MODELOS DE DATOS:
```python
class Hypothesis(BaseModel):
    id: str
    titulo: str                  # "Posible C2 no detectado en cuentas privilegiadas"
    descripcion: str             # descripción detallada de la hipótesis
    tecnica_mitre: str           # técnica MITRE que investiga
    prioridad: int               # 1-5, 5 = más urgente
    queries_sugeridas: list[str] # descripciones en lenguaje natural de qué buscar
    estado: Literal["nueva", "investigando", "confirmada", "descartada"]
    creada_at: datetime
    hunter: str                  # "claude_autonomo" o username del analista

class HuntConclusion(BaseModel):
    hypothesis_id: str
    encontrado: bool
    evidencia: list[dict]        # eventos que apoyan la hipótesis
    confianza: Literal["alta", "media", "baja"]
    iocs_nuevos: list[str]       # IOCs descubiertos durante el hunt
    crear_incidente: bool
    resumen: str                 # conclusión en español
```

ARCHIVO: threat_hunting/prompts/hypothesis.txt

```
Sos un Threat Hunter experto trabajando con NYXAR.
Tu trabajo es generar hipótesis de investigación proactivas.

CONTEXTO DE LA RED (últimas 24 horas):
{context}

THREAT INTEL RECIENTE:
{threat_intel}

INCIDENTES RECIENTES (para no repetir):
{recent_incidents}

Generá entre 3 y 5 hipótesis de hunting. Para cada una:
- Debe ser investigable con los datos disponibles en el sistema
- No debe repetir lo que ya fue detectado como incidente
- Debe representar una técnica de ataque real (referenciá MITRE ATT&CK si aplica)
- Debe tener valor diferencial: buscar lo que los detectores automáticos pueden perder

Respondé SOLO en JSON:
[
  {
    "titulo": "...",
    "descripcion": "...",
    "tecnica_mitre": "T1XXX",
    "prioridad": 1-5,
    "razon_prioridad": "...",
    "queries_sugeridas": [
      "Buscar dispositivos que...",
      "Verificar si existen comunicaciones entre..."
    ]
  }
]
```

ARCHIVO: threat_hunting/prompts/findings.txt

```
Sos un Threat Hunter analizando resultados de una investigación.

HIPÓTESIS INVESTIGADA:
{hypothesis}

RESULTADOS ENCONTRADOS:
{results}

Analizá los resultados y respondé en JSON:
{
  "encontrado": true/false,
  "confianza": "alta/media/baja",
  "razon_confianza": "...",
  "evidencia_clave": ["descripción de los hallazgos más importantes"],
  "iocs_nuevos": ["lista de nuevos indicadores descubiertos"],
  "crear_incidente": true/false,
  "justificacion": "...",
  "proximos_pasos": ["qué buscar si se quiere profundizar"]
}
```

REGLAS:
- Generar hipótesis nuevas solo si no hay una activa con título similar (deduplicar).
- El hunting autónomo corre una vez por día (a las 6am, fuera de horario pico).
- Un analista humano puede iniciar una sesión de hunting manual en cualquier momento.
- Las hipótesis descartadas se guardan igualmente — son valiosas como historial.

NO HAGAS:
- No generes hipótesis que ya son cubiertas por los patrones del correlator.
  El hunting busca lo desconocido, no lo conocido.
- No ejecutes queries destructivas (write operations) durante el hunting.
- No crees incidentes automáticamente sin pasar por el flujo de aprobación normal.
```

---

### PROMPT V10 — AI Engineer
**Rol:** AI Engineer  
**Componente:** Threat Hunting — query builder y hunter  
**Entregable:** `threat_hunting/query_builder.py` y `threat_hunting/hunter.py`

```
Sos un AI Engineer especializado en traducir hipótesis de lenguaje natural
a queries de MongoDB Aggregation Pipeline.

ARCHIVO: threat_hunting/query_builder.py

```python
class QueryBuilder:
    """
    Traduce hipótesis de hunting (lenguaje natural) a queries
    ejecutables sobre MongoDB.
    
    Usa Claude para la traducción, con validación posterior.
    """
    
    ALLOWED_COLLECTIONS = ["events", "identities", "incidents", "honeypot_hits"]
    MAX_QUERY_DURATION_SECONDS = 30
    MAX_RESULTS = 1000
    
    async def build_queries(
        self,
        hypothesis: Hypothesis
    ) -> list[MongoQuery]:
        """
        Para cada query_sugerida en la hipótesis,
        construir la query de MongoDB correspondiente.
        
        Proceso:
        1. Enviar la query sugerida a Claude con el schema de MongoDB
        2. Claude retorna el aggregation pipeline en JSON
        3. Validar que solo usa colecciones permitidas (ALLOWED_COLLECTIONS)
        4. Validar que no tiene operaciones de escritura ($set, $unset, $delete)
        5. Agregar $limit: MAX_RESULTS automáticamente si no está presente
        6. Retornar lista de MongoQuery validadas
        """
    
    async def _validate_pipeline(self, pipeline: list[dict]) -> tuple[bool, str]:
        """
        Validaciones de seguridad sobre el aggregation pipeline:
        - No contiene $out ni $merge (no escribe a disco)
        - No contiene $lookup a colecciones no permitidas
        - No contiene operadores de escritura
        - Tiene al menos un stage de filtro ($match) para evitar full scans
        Retorna (es_valida, razon_si_invalida)
        """
    
    CLAUDE_QUERY_PROMPT = """
    Sos un experto en MongoDB Aggregation Pipeline.
    
    Schema de la colección events (Time Series):
    - timestamp: Date
    - meta: {source, ip, usuario, area}
    - interno: {ip, hostname, usuario, area}
    - externo: {valor, tipo}
    - enrichment: {reputacion, fuente, categoria, tags}
    - risk_score: Number
    - correlaciones: Array<String>
    
    Schema de identities:
    - id: String
    - usuario: String
    - area: String
    - risk_score_actual: Number
    - baseline: {horario_inicio, horario_fin, dominios_habituales, volumen_mb_dia_media}
    - es_privilegiado: Boolean
    
    QUERY EN LENGUAJE NATURAL:
    {query_natural}
    
    Rango de tiempo a considerar: últimas {horas} horas.
    
    Respondé SOLO con el aggregation pipeline como JSON array.
    Sin texto adicional. Sin markdown. Solo el array JSON.
    Ejemplo: [{"$match": {...}}, {"$group": {...}}, {"$limit": 100}]
    """
```

ARCHIVO: threat_hunting/hunter.py

```python
class Hunter:
    """
    Ejecuta queries de hunting sobre MongoDB y compila los resultados.
    """
    
    async def run_hunt(self, hypothesis: Hypothesis) -> HuntSession:
        """
        Ejecuta una sesión de hunting completa para una hipótesis.
        
        1. QueryBuilder.build_queries(hypothesis)
        2. Para cada query:
           a. Ejecutar en MongoDB con timeout MAX_QUERY_DURATION_SECONDS
           b. Si tarda más: cancelar y marcar como "timeout"
           c. Guardar resultados parciales
        3. HypothesisEngine.conclude_hunt(hypothesis, todos_resultados)
        4. Guardar HuntSession en MongoDB (colección hunt_sessions)
        5. Si conclusion.crear_incidente: llamar al flujo normal de incidentes
        
        Retornar HuntSession completa.
        """
    
    async def run_query(
        self,
        collection: str,
        pipeline: list[dict],
        timeout: int = 30
    ) -> list[dict]:
        """
        Ejecuta un aggregation pipeline con timeout estricto.
        Usar asyncio.wait_for con timeout.
        Si hay timeout: loggear warning y retornar lista vacía.
        """
    
    async def get_sessions(
        self,
        estado: str = None,
        limit: int = 20
    ) -> list[dict]:
        """
        Lista sesiones de hunting pasadas.
        Para el dashboard de hunting.
        """
```

MODELO HuntSession:
```python
class HuntSession(BaseModel):
    id: str
    hypothesis_id: str
    inicio: datetime
    fin: Optional[datetime]
    estado: Literal["corriendo", "completado", "timeout", "error"]
    queries_ejecutadas: int
    resultados_totales: int
    conclusion: Optional[HuntConclusion]
    iniciado_by: str    # "sistema_autonomo" o username
```

NUEVOS ENDPOINTS EN API:
```python
# api/routers/hunting.py

GET /hunting/hypotheses
  - Lista hipótesis activas ordenadas por prioridad

POST /hunting/hypotheses
  - Body: {"descripcion": "Quiero investigar..."} — el analista da una hipótesis manual
  - Claude la formaliza y crea el objeto Hypothesis

POST /hunting/hypotheses/{id}/run
  - Inicia una sesión de hunting para esa hipótesis

GET /hunting/sessions
  - Lista sesiones de hunting pasadas con sus conclusiones

GET /hunting/sessions/{id}
  - Detalle completo: hipótesis, queries ejecutadas, resultados, conclusión
```

REGLAS:
- Las queries de hunting tienen prioridad BAJA en MongoDB. No deben
  competir con el pipeline principal de eventos.
  Usar `maxTimeMS` en todas las queries.
- El hunting autónomo no corre si hay más de 5 incidentes críticos abiertos
  (el sistema está bajo ataque real, no es momento de hunting).
- Guardar todas las queries ejecutadas para poder auditarlas.

NO HAGAS:
- No ejecutes queries sin el timeout MAX_QUERY_DURATION_SECONDS.
- No le des a Claude acceso directo a MongoDB. QueryBuilder valida todo.
- No uses $where (JavaScript en MongoDB) — es un vector de inyección.
- No hagas full collection scans. Toda query debe usar al menos un índice.
```

---

### PROMPT V11 — Frontend Dev
**Rol:** Frontend Developer  
**Componente:** Vista de Threat Hunting en el dashboard  
**Entregable:** `dashboard/src/views/HuntingView.jsx`

```
Sos un Frontend Developer React especializado en interfaces de investigación
y análisis forense para analistas de seguridad.

Tu tarea es implementar la vista de Threat Hunting del dashboard.
Es la vista más "analista" del sistema — diseñada para investigación
activa, no para monitoreo pasivo.

ARCHIVO: dashboard/src/views/HuntingView.jsx

LAYOUT:
Panel dividido en dos columnas:
- Izquierda (35%): lista de hipótesis + botón para nueva hipótesis manual
- Derecha (65%): detalle de la sesión de hunting activa o seleccionada

COLUMNA IZQUIERDA — Lista de hipótesis:
Para cada hipótesis mostrar:
- Prioridad (1-5 con estrellas o números coloreados)
- Título (con badge de técnica MITRE si está disponible)
- Estado: nueva | investigando | confirmada | descartada
- Si estado="confirmada": badge rojo "AMENAZA CONFIRMADA"
- Si estado="descartada": texto tachado, opacidad reducida
- Timestamp de creación
- Botón "Investigar" si estado="nueva"

Sección inferior del panel izquierdo:
- Botón "Nueva hipótesis manual"
- Al hacer click: textarea donde el analista escribe en lenguaje natural
  lo que quiere investigar. POST /hunting/hypotheses.
  Claude formaliza la hipótesis y aparece en la lista.

COLUMNA DERECHA — Detalle de sesión:
Cuando el analista hace click en "Investigar" o en una sesión pasada:

1. Header: título de la hipótesis + descripción + técnica MITRE
2. Sección "Queries ejecutadas":
   - Cada query con su descripción en lenguaje natural
   - Indicador de estado: ✓ completada / ⚠ timeout / ⟳ corriendo
   - Cantidad de resultados encontrados
3. Sección "Resultados":
   - Si hay resultados: tabla/lista de los documentos encontrados
   - Cada resultado tiene: timestamp, identidad, valor anómalo, contexto
   - Botón "Ver evento completo" abre el incidente/evento en el Timeline
4. Sección "Conclusión de Claude":
   - Card con el análisis: encontrado o no, confianza, evidencia clave
   - Si crear_incidente=true: botón "Crear incidente formal"
   - Lista de IOCs nuevos descubiertos (si hay)

ESTADO EN TIEMPO REAL:
Una sesión corriendo muestra:
- Spinner animado en la query activa
- Contador de resultados actualizándose en tiempo real (via WebSocket)
- Estimación de tiempo restante

REGLAS:
- Esta vista solo es visible si el usuario tiene rol "analyst" o "admin"
  (verificar via endpoint GET /auth/me cuando se implemente auth).
- Por ahora: visible para todos, pero con badge "Función avanzada".
- El textarea de hipótesis manual tiene un placeholder orientativo:
  "Ej: Quiero investigar si hay dispositivos que se comunican con
  infraestructura de Tor o proxies anónimos..."
- Máximo 3 sesiones de hunting corriendo simultáneamente.

NO HAGAS:
- No rendericés los resultados completos de las queries en el DOM.
  Virtualizar si hay más de 50 resultados.
- No hagas que el analista escriba MongoDB directamente.
  Solo lenguaje natural — Claude hace la traducción.
- No muestres los pipelines de MongoDB generados en la UI del analista.
  Son detalles de implementación.
```

---

## 📊 MÓDULO REPORTES AUTOMÁTICOS

---

### PROMPT V12 — Report Dev
**Rol:** 📊 Report Developer  
**Componente:** Generador de reportes PDF  
**Entregable:** `reporter/generator.py` y templates

```
Sos un Report Developer especializado en generación automática de reportes
de seguridad ejecutivos y técnicos.

Tu tarea es implementar el generador de reportes PDF de NYXAR.
Usar reportlab (ya usado en el sistema — mantener coherencia visual).

ARCHIVO: reporter/generator.py

```python
class ReportGenerator:
    """
    Genera reportes PDF profesionales a partir de datos de MongoDB.
    Los reportes son el producto final tangible del sistema:
    documentan lo que pasó y qué se hizo al respecto.
    """
    
    async def generate(
        self,
        tipo: Literal["diario", "semanal", "incidente"],
        parametros: dict,
        output_path: str
    ) -> str:
        """
        Genera el PDF y lo guarda en output_path.
        Retorna la ruta del archivo generado.
        
        parametros para cada tipo:
        - diario: {"fecha": "2026-03-20"}
        - semanal: {"semana_inicio": "2026-03-16"}
        - incidente: {"incident_id": "inc_xxx"}
        """
    
    async def _collect_daily_data(self, fecha: date) -> dict:
        """
        Recolecta de MongoDB todos los datos para el reporte diario:
        - Total de eventos por fuente y tipo
        - Incidentes abiertos, cerrados y nuevos en ese día
        - Top 10 IPs externas más consultadas y su reputación
        - Top 10 dominios maliciosos detectados
        - Identidades con mayor risk_score al final del día
        - Acciones de respuesta ejecutadas
        - Memos de IA generados
        - Estadísticas de enrichment: % de caché hits, APIs consultadas
        - Alertas de honeypots
        """
    
    async def _collect_incident_data(self, incident_id: str) -> dict:
        """
        Recolecta todo el contexto de un incidente específico:
        - El incidente completo con todos sus eventos
        - Timeline cronológico de los eventos
        - Identidad involucrada con su baseline
        - Análisis de Claude (memo de incidente)
        - Acciones de respuesta tomadas (del audit log)
        - IOCs involucrados y su contexto de threat intel
        """
```

DISEÑO VISUAL DE LOS REPORTES:
Usar la misma paleta y estilo que el PDF de arquitectura ya generado:
- Background oscuro (#0D1117) para portada
- Cards con bordes cyan para secciones importantes
- Tablas con alternado de colores oscuros
- Risk scores con colores semáforo

ESTRUCTURA DEL REPORTE DIARIO:
```
1. Portada: Logo + "Reporte Diario de Seguridad — {fecha}"
            + clasificación (CONFIDENCIAL)
2. Resumen ejecutivo (media página): 
   - ¿Fue un día tranquilo o con incidentes?
   - 3 puntos más importantes del día
   - Generado por Claude con los datos del día
3. Estadísticas del día:
   - Cards con métricas: total eventos, incidentes, alertas, honeypots
   - Gráfico de barras ASCII: eventos por hora del día (usando reportlab)
4. Incidentes del día:
   - Tabla con todos los incidentes: severidad, título, estado, identidad
   - Para cada incidente crítico o alto: párrafo de descripción
5. Top amenazas detectadas:
   - Tabla de IPs/dominios maliciosos más frecuentes
6. Acciones tomadas:
   - Lista de respuestas ejecutadas (del audit log)
7. Identidades en alerta:
   - Tabla de usuarios con risk_score > 60 al cierre del día
8. Pie de página: generado automáticamente, no revisado por humanos
```

ESTRUCTURA DEL REPORTE DE INCIDENTE:
```
1. Portada: "Reporte de Incidente — {titulo}" + severidad en color
2. Resumen ejecutivo: análisis de Claude en lenguaje ejecutivo
3. Timeline: línea de tiempo cronológica con los eventos del incidente
4. Análisis técnico: detalles de los eventos, IOCs, técnica MITRE
5. Impacto potencial: sistemas y datos afectados
6. Acciones tomadas: del audit log, con timestamps
7. Recomendaciones: próximos pasos sugeridos
8. IOCs para bloquear: tabla de IPs/dominios/hashes para otros equipos
```

REGLAS:
- Los reportes se guardan en ./data/reports/{tipo}/{fecha}_{id}.pdf
- Cada reporte generado se registra en MongoDB (colección reports).
- El resumen ejecutivo de cada reporte es generado por Claude
  con los datos recolectados. Máximo 300 tokens para el resumen.
- Si Claude no está disponible: generar el reporte sin el resumen ejecutivo,
  con una nota indicando que el análisis automático no está disponible.

NO HAGAS:
- No generes reportes síncronamente en el request HTTP.
  Siempre en background task.
- No incluyas contraseñas, API keys ni datos internos sensibles en los reportes.
- No incluyas IPs internas RFC1918 en reportes que puedan salir de la organización.
- No uses imágenes externas en los PDFs (deben funcionar offline).
```

---

### PROMPT V13 — Report Dev
**Rol:** 📊 Report Developer  
**Componente:** Scheduler de reportes y endpoints  
**Entregable:** `reporter/scheduler.py` y endpoints de API

```
Sos un Report Developer especializado en automatización y scheduling
de generación de contenido periódico.

ARCHIVO: reporter/scheduler.py

```python
class ReportScheduler:
    """
    Programa la generación automática de reportes.
    Usa asyncio puro para el scheduling (sin Celery ni APScheduler).
    """
    
    async def start(self) -> None:
        """
        Inicia todos los loops de scheduling en paralelo:
        - daily_loop: genera el reporte diario
        - weekly_loop: genera el reporte semanal
        """
    
    async def daily_loop(self) -> None:
        """
        Genera el reporte del día anterior todos los días a las 06:00 AM.
        
        Lógica:
        1. Calcular segundos hasta las 06:00 del día siguiente
        2. asyncio.sleep(segundos)
        3. Generar reporte del día anterior
        4. Notificar por los canales configurados (REPORT_NOTIFY_CHANNELS en .env)
        5. Repetir
        """
    
    async def weekly_loop(self) -> None:
        """
        Genera el reporte semanal todos los lunes a las 07:00 AM.
        Cubre la semana anterior (lunes a domingo).
        """
    
    async def generate_on_demand(
        self,
        tipo: str,
        parametros: dict,
        solicitado_by: str
    ) -> str:
        """
        Genera un reporte a demanda.
        Retorna el ID del reporte en MongoDB (disponible en segundos).
        La generación es async — el caller recibe el ID y puede
        consultar el estado via GET /reports/{id}.
        """
```

NUEVOS ENDPOINTS EN API:
```python
# api/routers/reports.py

GET /reports
  - Lista de reportes generados, paginados, ordenados por fecha DESC
  - Filtrable por tipo: diario | semanal | incidente

GET /reports/{report_id}
  - Metadata del reporte: tipo, fecha, estado (generando | listo | error)
  - Si estado=listo: incluir URL de descarga

GET /reports/{report_id}/download
  - Descarga el PDF directamente (Content-Type: application/pdf)
  - Si aún está generando: 202 Accepted con header Retry-After: 10

POST /reports/generate
  - Body: {"tipo": "incidente", "incident_id": "inc_xxx"}
  - Genera un reporte a demanda
  - Retorna: {"report_id": "...", "estado": "generando"}

POST /reports/schedule
  - Configura el horario de generación automática
  - Body: {"diario_hora": "06:00", "semanal_dia": "lunes",
           "notify_channels": ["slack", "email"]}
```

INTEGRACIÓN CON EL NOTIFIER:
Cuando un reporte está listo, publicar en Redis canal "notifications:reports"
con el payload:
```json
{
  "tipo": "reporte_listo",
  "report_id": "...",
  "report_tipo": "diario",
  "fecha": "2026-03-20",
  "download_url": "http://api:8000/api/v1/reports/{id}/download"
}
```

REGLAS:
- Los reportes se generan en un proceso separado para no bloquear la API.
  Usar asyncio.create_task() para generación en background.
- Si la generación falla, reintentar una vez. Si falla de nuevo: estado="error".
- Retener reportes en disco por 90 días. Después, eliminar el PDF
  pero mantener el registro en MongoDB.
- Comprimir PDFs grandes con gzip antes de guardar a disco.

NO HAGAS:
- No uses Celery, RQ ni ningún worker externo. Solo asyncio.
- No bloquees la generación de reportes si hay muchos incidentes.
  Paginar las queries a MongoDB dentro del generator.
- No generes más de un reporte del mismo tipo/fecha simultáneamente
  (deduplicación por tipo+fecha).
```

---

## 🔔 MÓDULO NOTIFICACIONES

---

### PROMPT V14 — Integration Dev
**Rol:** 🔔 Integration Developer  
**Componente:** Motor central de notificaciones  
**Entregable:** `notifier/engine.py`

```
Sos un Integration Developer especializado en sistemas de notificaciones
multi-canal para plataformas de seguridad.

FILOSOFÍA:
Las notificaciones son el puente entre el sistema y las personas.
Una notificación mal diseñada es ignorada. Una notificación bien diseñada
es la diferencia entre responder en 5 minutos o en 5 horas.

PRINCIPIOS DE DISEÑO:
1. Deduplicación: el mismo evento no genera dos notificaciones en 15 minutos
2. Prioridad: las críticas van por todos los canales, las informativas solo por email
3. Personalización: cada área puede configurar sus propias preferencias
4. Silencio inteligente: no notificar entre 23hs y 7hs excepto críticos
5. Degradación elegante: si un canal falla, intentar el siguiente

ARCHIVO: notifier/engine.py

```python
class NotificationEngine:
    """
    Motor central que decide qué notificar, a quién, y por qué canal.
    Escucha múltiples canales de Redis y MongoDB Change Streams.
    """
    
    DEDUP_TTL = 900  # 15 minutos — no repetir la misma notificación
    
    async def start(self) -> None:
        """
        Escucha en paralelo:
        1. Redis PubSub canal "notifications:urgent" — alertas críticas
        2. Redis PubSub canal "notifications:reports" — reportes listos
        3. MongoDB Change Stream en incidents — nuevos incidentes
        4. MongoDB Change Stream en honeypot_hits — honeypots activados
        5. Redis PubSub canal "approvals:pending" — acciones esperando aprobación
        """
    
    async def process_event(self, evento_tipo: str, payload: dict) -> None:
        """
        Router principal. Según el tipo de evento determina:
        1. ¿Se debe notificar? (puede estar en período de silencio o dedup)
        2. ¿A quién? (ver _resolve_recipients)
        3. ¿Por qué canal? (ver _select_channels)
        4. ¿Con qué plantilla? (ver _select_template)
        5. Enviar via _send()
        """
    
    def _is_quiet_hours(self) -> bool:
        """
        Retorna True si es horario de silencio (configurable en .env:
        NOTIFY_QUIET_START=23:00, NOTIFY_QUIET_END=07:00).
        En horario de silencio: solo enviar severidad=critica.
        """
    
    async def _is_duplicate(self, evento_tipo: str, objetivo: str) -> bool:
        """
        Verifica si ya se envió una notificación del mismo tipo
        para el mismo objetivo en los últimos DEDUP_TTL segundos.
        Key Redis: "notif:dedup:{evento_tipo}:{objetivo}" con TTL.
        """
    
    async def _resolve_recipients(
        self, 
        evento_tipo: str,
        payload: dict
    ) -> list[Recipient]:
        """
        Determina a quién notificar según el tipo de evento:
        
        - incidente_critico: todos los en NOTIFY_ADMINS + responsable del área afectada
        - incidente_alto: responsable del área afectada + NOTIFY_SECURITY_TEAM
        - honeypot_hit: NOTIFY_ADMINS (siempre, sin excepción)
        - reporte_listo: NOTIFY_REPORT_RECIPIENTS
        - aprobacion_pendiente: NOTIFY_ADMINS
        - incidente_medio/bajo: solo email al responsable del área
        
        Recipients se configuran en .env o en preferences.py
        """
    
    async def _select_channels(
        self,
        severidad: str,
        recipient: Recipient,
        es_horario_silencio: bool
    ) -> list[str]:
        """
        Canales según severidad y preferencias del recipient:
        
        critica: slack + whatsapp + email (siempre, incluso en silencio)
        alta: slack + email (en silencio: solo email)
        media: email
        baja: email (1 por día como resumen, no por evento individual)
        info: solo en el dashboard (no enviar notificaciones externas)
        """
```

MODELO Recipient:
```python
class Recipient(BaseModel):
    id: str
    nombre: str
    email: Optional[str]
    slack_user_id: Optional[str]    # @usuario en Slack
    whatsapp_number: Optional[str]  # con código de país: +5491112345678
    area: Optional[str]
    es_admin: bool = False
    preferencias: NotifPreferences
```

REGLAS:
- Las notificaciones de honeypot van SIEMPRE, sin deduplicación, a cualquier hora.
- Un incidente que escala de severidad media a alta genera una nueva notificación,
  aunque se haya notificado antes (la escalada es información nueva).
- Guardar cada notificación enviada en MongoDB (colección notifications_log).

NO HAGAS:
- No envíes más de 10 notificaciones por minuto en total (throttling global).
- No notifiques por WhatsApp más de 5 veces por hora (límites de las APIs).
- No incluyas datos técnicos (IPs, CVEs) en notificaciones de WhatsApp/SMS.
  Solo texto natural: "Alerta crítica en el sistema. Revisar dashboard."
```

---

### PROMPT V15 — Integration Dev
**Rol:** 🔔 Integration Developer  
**Componente:** Conectores de canales de notificación  
**Entregable:** Los tres conectores en `notifier/channels/`

```
Sos un Integration Developer especializado en APIs de mensajería
(Slack, WhatsApp Business API, SMTP).

ARCHIVO 1: notifier/channels/slack.py

```python
class SlackChannel:
    """
    Envía notificaciones a Slack via Incoming Webhooks o Bot API.
    
    Configuración .env:
    SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...   # para webhooks
    SLACK_BOT_TOKEN=xoxb-...                                  # para Bot API
    SLACK_DEFAULT_CHANNEL=#NYXAR-alerts
    
    Preferir Bot API (SLACK_BOT_TOKEN) si está disponible.
    Fallback a Webhook si no.
    """
    
    async def send(
        self, 
        recipient: Recipient,
        mensaje: NotifMessage
    ) -> bool:
        """
        Envía un mensaje formateado a Slack.
        
        Usar Block Kit de Slack para mensajes ricos:
        - Header con color según severidad (danger=rojo, warning=amarillo, good=verde)
        - Sección con el texto del mensaje
        - Context con timestamp y fuente
        - Botón "Ver en dashboard" con link directo al incidente
        
        Si recipient.slack_user_id está configurado: DM directo.
        Si no: enviar al SLACK_DEFAULT_CHANNEL.
        """
    
    def _build_blocks(self, mensaje: NotifMessage) -> list[dict]:
        """
        Construye el payload de Block Kit según el tipo y severidad.
        
        Para incidentes críticos incluir:
        - Color rojo en attachment
        - Campo "Acción requerida" con el texto de acción inmediata
        - Botón "Aprobar respuesta" si hay proposal pendiente
        
        Para reportes:
        - Botón de descarga del PDF
        """
```

ARCHIVO 2: notifier/channels/email.py

```python
class EmailChannel:
    """
    Envía notificaciones por email via SMTP async.
    Usar aiosmtplib para async nativo.
    
    Configuración .env:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=NYXAR@empresa.com
    SMTP_PASSWORD=...
    SMTP_USE_TLS=true
    EMAIL_FROM=NYXAR <NYXAR@empresa.com>
    """
    
    async def send(
        self,
        recipient: Recipient,
        mensaje: NotifMessage
    ) -> bool:
        """
        Envía email HTML formateado.
        
        El HTML del email debe:
        - Funcionar en clientes de email corporativos (Outlook, Gmail)
        - Usar tablas HTML para layout (no flexbox/grid)
        - Incluir versión plain text como fallback
        - Tener diseño consistente con el dashboard (colores oscuros)
        - Incluir link "Ver en dashboard" con el incident_id en la URL
        - Incluir footer: "Este email fue generado automáticamente por NYXAR"
        
        Para reportes: adjuntar el PDF como attachment.
        Límite de adjuntos: 10MB.
        """
    
    def _build_html(self, mensaje: NotifMessage) -> str:
        """
        Genera el HTML del email desde la plantilla Jinja2.
        Templates en notifier/templates/email/
        Una plantilla por tipo: alerta.html, reporte.html, aprobacion.html
        """
```

ARCHIVO 3: notifier/channels/whatsapp.py

```python
class WhatsAppChannel:
    """
    Envía mensajes de WhatsApp para alertas urgentes.
    
    Soportar dos proveedores (configurar con WHATSAPP_PROVIDER en .env):
    
    A) Twilio (recomendado para empezar):
       WHATSAPP_PROVIDER=twilio
       TWILIO_ACCOUNT_SID=...
       TWILIO_AUTH_TOKEN=...
       TWILIO_WHATSAPP_FROM=whatsapp:+14155238886  # número de Twilio sandbox
    
    B) WhatsApp Business API (para producción, requiere aprobación de Meta):
       WHATSAPP_PROVIDER=meta
       META_WHATSAPP_TOKEN=...
       META_WHATSAPP_PHONE_ID=...
    """
    
    async def send(
        self,
        recipient: Recipient,
        mensaje: NotifMessage
    ) -> bool:
        """
        Envía mensaje de WhatsApp.
        
        CRÍTICO: WhatsApp tiene restricciones de contenido.
        Los mensajes deben ser:
        - Cortos (máximo 200 caracteres para alertas)
        - Sin HTML (solo texto plano)
        - Sin IPs, CVEs ni términos técnicos
        - Formato: "🚨 {severidad} | {descripcion_simple} | Ver: {url_corta}"
        
        Para Twilio: POST a https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json
        Para Meta: POST a https://graph.facebook.com/v18.0/{PHONE_ID}/messages
        """
    
    def _truncate_for_whatsapp(self, texto: str) -> str:
        """
        Simplifica y trunca el mensaje para WhatsApp.
        Eliminar términos técnicos, IPs, puertos.
        Máximo 200 caracteres.
        """
```

MODELO NotifMessage:
```python
class NotifMessage(BaseModel):
    tipo: Literal["alerta", "reporte", "aprobacion", "resolucion"]
    severidad: str
    titulo: str
    cuerpo: str              # texto completo, puede ser largo
    cuerpo_corto: str        # versión corta para WhatsApp (max 200 chars)
    link: Optional[str]      # URL al dashboard
    incident_id: Optional[str]
    proposal_id: Optional[str]
    attachment_path: Optional[str]  # para reportes con PDF adjunto
    metadata: dict = {}
```

REGLAS:
- Si el envío falla: reintentar 1 vez después de 5 segundos.
  Si falla de nuevo: loggear error y continuar (no bloquear otras notificaciones).
- Loggear cada envío: canal, destinatario, tipo, latencia, éxito/fallo.
- Los tokens y passwords de APIs van SIEMPRE desde variables de entorno.

NO HAGAS:
- No pongas el número de WhatsApp en logs (dato personal sensible).
- No envíes archivos adjuntos por WhatsApp (no soportado en modo básico).
- No uses requests síncrono. Todo con httpx.AsyncClient o aiosmtplib.
- No envíes más de 1 mensaje de WhatsApp por minuto al mismo número.
```

---

### PROMPT V16 — Integration Dev
**Rol:** 🔔 Integration Developer  
**Componente:** Preferencias y reglas de notificación  
**Entregable:** `notifier/preferences.py` y endpoints de configuración

```
Sos un Integration Developer especializado en sistemas de preferencias
de usuario y configuración de notificaciones empresariales.

ARCHIVO: notifier/preferences.py

```python
class PreferencesManager:
    """
    Gestiona las preferencias de notificación por usuario, área y sistema.
    
    Jerarquía de preferencias (de mayor a menor prioridad):
    1. Preferencias del usuario individual
    2. Preferencias del área
    3. Configuración global (variables .env)
    """
    
    DEFAULT_PREFERENCES = {
        "critica": {
            "canales": ["slack", "whatsapp", "email"],
            "respetar_silencio": False,   # siempre enviar
            "dedup_minutes": 0             # nunca deduplicar críticos
        },
        "alta": {
            "canales": ["slack", "email"],
            "respetar_silencio": True,
            "dedup_minutes": 30
        },
        "media": {
            "canales": ["email"],
            "respetar_silencio": True,
            "dedup_minutes": 60
        },
        "baja": {
            "canales": ["email"],
            "respetar_silencio": True,
            "agrupar_en_resumen_diario": True  # no enviar individualmente
        },
        "info": {
            "canales": [],  # solo dashboard
            "respetar_silencio": True
        }
    }
    
    async def get_for_recipient(
        self, 
        recipient_id: str,
        severidad: str
    ) -> NotifPreferences:
        """
        Retorna las preferencias efectivas para un recipient y severidad.
        Merge de preferencias individuales + área + default.
        """
    
    async def set_user_preferences(
        self,
        user_id: str,
        prefs: dict
    ) -> None:
        """Guarda preferencias de un usuario en MongoDB."""
    
    async def set_area_preferences(
        self,
        area: str,
        prefs: dict
    ) -> None:
        """Preferencias para todo un área."""
    
    async def get_all_admins(self) -> list[Recipient]:
        """
        Retorna la lista de administradores del sistema.
        Fuentes:
        1. Variable NOTIFY_ADMINS en .env: "admin1@empresa.com,admin2@empresa.com"
        2. Usuarios con is_admin=True en MongoDB (sincronizados desde AD)
        """
    
    async def get_area_responsible(self, area: str) -> Optional[Recipient]:
        """
        Retorna el responsable del área.
        Configurado via NOTIFY_AREA_{AREA}_EMAIL en .env, o via AD (manager del área).
        """
```

NUEVOS ENDPOINTS:
```python
# api/routers/notifications.py

GET /notifications/preferences
  - Preferencias actuales del sistema (globales)

PUT /notifications/preferences/user/{user_id}
  - Actualiza preferencias de un usuario
  - Body: {"alta": {"canales": ["email"]}, "critica": {"whatsapp": "+54911..."}}

PUT /notifications/preferences/area/{area}
  - Actualiza preferencias de un área

GET /notifications/log
  - Historial de notificaciones enviadas (paginado)
  - Filtrable por canal, tipo, estado

POST /notifications/test
  - Body: {"canal": "slack", "severidad": "alta"}
  - Envía una notificación de prueba al canal configurado
  - Útil para verificar que la configuración funciona

GET /notifications/stats
  - Estadísticas: enviadas hoy, tasa de éxito por canal, más frecuentes
```

VARIABLE DE ENTORNO PARA CONFIGURACIÓN RÁPIDA:
```
# Admins del sistema (reciben todas las alertas críticas)
NOTIFY_ADMINS=admin@empresa.com,seguridad@empresa.com

# Responsables por área (para alertas del área)
NOTIFY_AREA_CONTABILIDAD=contabilidad@empresa.com
NOTIFY_AREA_RRHH=rrhh@empresa.com
NOTIFY_AREA_IT=it@empresa.com

# Receptores de reportes automáticos
NOTIFY_REPORT_RECIPIENTS=gerencia@empresa.com,ceo@empresa.com

# Canales habilitados (deshabilitar canales no configurados)
NOTIFY_CHANNELS_ENABLED=slack,email   # whatsapp opcional
```

REGLAS:
- Las preferencias se cachean en Redis por 5 minutos (se actualizan poco).
- Un usuario puede optar por no recibir notificaciones de baja severidad.
  No puede optar por no recibir críticos (es política de seguridad).
- Las preferencias se guardan en MongoDB, colección notif_preferences.

NO HAGAS:
- No guardes números de teléfono ni emails en Redis (solo IDs, los datos en MongoDB).
- No permitas deshabilitar notificaciones de severidad crítica para admins.
- No hagas que un área pueda modificar preferencias de otras áreas.
```

---

## 📡 MÓDULO OBSERVABILIDAD

---

### PROMPT V17 — DevOps Engineer
**Rol:** 📡 DevOps / SRE Engineer  
**Componente:** Métricas internas y health checks  
**Entregable:** `observability/metrics.py` y `observability/collectors/`

```
Sos un DevOps/SRE Engineer especializado en observabilidad de sistemas
distribuidos y en el principio de "monitorear al monitor".

FILOSOFÍA:
NYXAR es el sistema que detecta problemas en la red de la empresa.
Pero ¿quién detecta problemas en NYXAR mismo?
Este módulo monitorea la salud interna del sistema para que los operadores
sepan cuando algo no está funcionando bien.

ARCHIVO: observability/metrics.py

Definir métricas Prometheus usando prometheus-client:

```python
from prometheus_client import Counter, Gauge, Histogram, Summary

# PIPELINE METRICS
EVENTOS_PROCESADOS = Counter(
    'NYXAR_eventos_total',
    'Total de eventos procesados',
    ['source', 'tipo']
)

EVENTOS_EN_COLA = Gauge(
    'NYXAR_eventos_cola',
    'Eventos actualmente en cola Redis sin procesar',
    ['stream']   # events:raw, events:enriched, events:alerts
)

LATENCIA_ENRIQUECIMIENTO = Histogram(
    'NYXAR_enrichment_latency_seconds',
    'Latencia del proceso de enriquecimiento',
    ['resultado'],  # cache_hit, blocklist_hit, api_call
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# THREAT INTEL METRICS
CACHE_HIT_RATE = Gauge(
    'NYXAR_cache_hit_rate',
    'Porcentaje de hits en caché de enrichment (0-1)'
)

BLOCKLIST_SIZES = Gauge(
    'NYXAR_blocklist_size',
    'Cantidad de IOCs en cada blocklist',
    ['lista']   # spamhaus, urlhaus, misp_ips, etc.
)

APIS_EXTERNAS_CALLS = Counter(
    'NYXAR_api_calls_total',
    'Llamadas a APIs externas de threat intel',
    ['api', 'resultado']   # abuseipdb, virustotal, otx / success, error, rate_limit
)

# SECURITY METRICS
INCIDENTES_ACTIVOS = Gauge(
    'NYXAR_incidentes_activos',
    'Incidentes abiertos por severidad',
    ['severidad']
)

HONEYPOT_HITS = Counter(
    'NYXAR_honeypot_hits_total',
    'Activaciones de honeypots por tipo',
    ['tipo_recurso']
)

RISK_SCORES_DISTRIBUTION = Histogram(
    'NYXAR_risk_scores',
    'Distribución de risk scores de identidades',
    buckets=[10, 20, 40, 60, 80, 100]
)

# SYSTEM HEALTH
MONGODB_OPERATION_LATENCY = Histogram(
    'NYXAR_mongo_latency_seconds',
    'Latencia de operaciones MongoDB',
    ['operacion', 'coleccion'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

REDIS_OPERATION_LATENCY = Histogram(
    'NYXAR_redis_latency_seconds',
    'Latencia de operaciones Redis',
    ['operacion']
)

SERVICIOS_ACTIVOS = Gauge(
    'NYXAR_servicios_activos',
    'Estado de cada servicio del sistema (1=activo, 0=caído)',
    ['servicio']  # collector, enricher, correlator, ai_analyst, notifier
)

AI_TOKENS_USADOS = Counter(
    'NYXAR_ai_tokens_total',
    'Tokens consumidos de la API de Claude',
    ['tipo']  # input, output
)

AI_LLAMADAS = Counter(
    'NYXAR_ai_calls_total',
    'Llamadas a la API de Claude',
    ['tipo', 'resultado']  # autonomo, incidente, ceo / success, error, timeout
)
```

ARCHIVO: observability/collectors/pipeline_collector.py

```python
class PipelineCollector:
    """
    Recolecta métricas del pipeline de procesamiento de eventos.
    Corre cada 30 segundos y actualiza los Gauges de Prometheus.
    """
    
    async def collect(self) -> None:
        """
        1. Consultar Redis para el tamaño de cada stream (eventos en cola)
        2. Consultar MongoDB para contar incidentes por severidad
        3. Consultar MongoDB para distribución de risk_scores actuales
        4. Verificar heartbeat de cada servicio (ver abajo)
        5. Actualizar los Gauges correspondientes
        """
    
    async def check_service_health(self, servicio: str) -> bool:
        """
        Cada servicio publica un heartbeat en Redis cada 30 segundos:
        Key: "heartbeat:{servicio}" con TTL=90 segundos.
        Si la key no existe, el servicio lleva más de 90 segundos sin responder.
        
        Todos los servicios deben agregar en su main.py:
        asyncio.create_task(_heartbeat_loop(redis_bus, servicio_nombre))
        """
```

HEARTBEAT EN CADA SERVICIO:
Agregar esta función a todos los servicios existentes (collector, enricher, etc.):
```python
async def _heartbeat_loop(redis_bus: RedisBus, nombre: str) -> None:
    """Publica un heartbeat en Redis cada 30 segundos."""
    while True:
        await redis_bus.cache_set(f"heartbeat:{nombre}", 
                                   {"ts": datetime.utcnow().isoformat()}, 
                                   ttl=90)
        await asyncio.sleep(30)
```

ENDPOINT DE MÉTRICAS:
```python
# observability/main.py
# Exponer métricas en formato Prometheus en puerto 9090

GET /metrics    → prometheus-client generate_latest()
GET /health     → health check detallado (ver health.py)
```

REGLAS:
- Las métricas de Prometheus se exponen en el puerto 9090 (configurable).
- Actualizar métricas desde el código de cada módulo (instrumentación in-situ),
  no solo desde el collector externo.
- Los histogramas tienen buckets diseñados para el caso de uso
  (no usar los buckets default de Prometheus).

NO HAGAS:
- No expongas métricas que contengan datos de usuarios o IPs.
  Solo estadísticas agregadas.
- No hagas que la recolección de métricas sea más costosa que el sistema mismo.
- No uses Grafana (lo dejamos para una fase futura). Solo el endpoint /metrics.
```

---

### PROMPT V18 — DevOps Engineer
**Rol:** 📡 DevOps Engineer  
**Componente:** Dashboard de observabilidad interno  
**Entregable:** Vista de health en React + `observability/health.py`

```
Sos un DevOps Engineer especializado en diseño de health checks
y dashboards de operaciones internas.

ARCHIVO: observability/health.py

```python
class HealthChecker:
    """
    Verifica y reporta el estado de salud de todos los componentes.
    """
    
    async def full_check(self) -> HealthReport:
        """
        Ejecuta todos los checks en paralelo con asyncio.gather().
        Retorna el reporte completo.
        """
    
    async def check_redis(self) -> ComponentHealth:
        """PING a Redis. Latencia, tamaño de memoria, clientes conectados."""
    
    async def check_mongodb(self) -> ComponentHealth:
        """
        db.adminCommand({ping:1}).
        También: latencia de una query simple, espacio en disco,
        tamaño de la colección events (time series).
        """
    
    async def check_pipeline(self) -> ComponentHealth:
        """
        Verifica que el pipeline esté fluyendo:
        - Timestamp del último evento en events:raw (Redis)
        - Timestamp del último evento en MongoDB
        - Si ningún evento llegó en los últimos 10 minutos: WARNING
        - Si ningún evento llegó en los últimos 30 minutos: CRITICAL
        """
    
    async def check_services(self) -> dict[str, ComponentHealth]:
        """Verifica heartbeats de todos los servicios."""
    
    async def check_apis(self) -> dict[str, ComponentHealth]:
        """
        Verificación liviana de APIs externas (sin consumir cuota):
        - AbuseIPDB: GET /check?ipAddress=8.8.8.8 (IP pública conocida)
        - OTX: GET /api/v1/user/me (solo verifica auth)
        - Claude API: verificar que la API key es válida sin generar tokens
        Solo verificar si la API está configurada (key presente en .env).
        """

class ComponentHealth(BaseModel):
    nombre: str
    estado: Literal["ok", "warning", "critical", "unknown"]
    latencia_ms: Optional[float]
    mensaje: str
    detalles: dict = {}
    checked_at: datetime

class HealthReport(BaseModel):
    estado_general: Literal["ok", "degradado", "critico"]
    componentes: dict[str, ComponentHealth]
    servicios: dict[str, ComponentHealth]
    apis: dict[str, ComponentHealth]
    resumen: str   # una línea describiendo el estado
    generated_at: datetime
```

ENDPOINT DE HEALTH EN LA API PRINCIPAL:
```python
# Agregar a api/main.py

GET /health
  # Respuesta rápida (< 100ms): estado general del sistema
  # {"status": "ok"|"degradado"|"critico", "timestamp": "..."}

GET /health/detail
  # Respuesta completa con todos los componentes
  # Puede tardar hasta 2 segundos (hace todos los checks)
  # Usado por el dashboard de observabilidad
```

VISTA EN EL DASHBOARD: dashboard/src/views/SystemHealth.jsx

Layout: Grid de cards, una por componente del sistema.

Cada card muestra:
- Nombre del componente con ícono representativo
- StatusDot grande (verde/naranja/rojo) con animación
- Latencia en ms (si aplica)
- Mensaje descriptivo del estado
- Timestamp del último check

Cards del sistema:
- 🔴/🟢 Redis — latencia, memoria usada
- 🔴/🟢 MongoDB — latencia, documentos en events (hoy)
- 🔴/🟢 Pipeline — último evento procesado hace N segundos
- 🔴/🟢 Collector — heartbeat
- 🔴/🟢 Enricher — heartbeat + cache hit rate
- 🔴/🟢 Correlator — heartbeat + incidentes detectados hoy
- 🔴/🟢 AI Analyst — heartbeat + tokens usados hoy
- 🔴/🟢 Notifier — heartbeat + notificaciones enviadas hoy
- 🔴/🟢 AbuseIPDB API — disponible/no disponible
- 🔴/🟢 OTX API — disponible/no disponible
- 🔴/🟢 MISP — disponible/no disponible (si configurado)

Panel inferior:
- Gráfico de throughput: eventos procesados por minuto (últimas 2 horas)
  Usando recharts LineChart con datos que llegan por WebSocket cada 30 seg.
- Alerta automática: si cualquier componente pasa a "critical",
  mostrar banner rojo en la parte superior del dashboard completo.

NUEVO EVENTO WEBSOCKET:
El servidor emite "health_update" cada 60 segundos con el HealthReport completo.
El dashboard actualiza todas las cards simultáneamente.

REGLAS:
- La vista de SystemHealth es accesible desde un ícono en la barra de navegación.
- Si el estado general es "critico": el ícono de la barra parpadea en rojo.
- Los checks de APIs externas no consumen cuota (usar endpoints de verificación
  que no generan uso facturable).

NO HAGAS:
- No hagas que /health/detail tarde más de 3 segundos.
  Usar asyncio.wait_for con timeout=2.5 para cada check individual.
- No expongas información sensible en el health check público (/health).
  Solo estado general. Los detalles en /health/detail requieren auth.
- No instales Prometheus, Grafana ni ningún stack de observabilidad externo.
  El sistema se monitorea a sí mismo.
```

---

## 🧪 TESTING DE MÓDULOS V2

---

### PROMPT V19 — QA Engineer
**Rol:** 🧪 QA Engineer  
**Componente:** Tests de integración para módulos V2  
**Entregable:** `tests/v2/` con cobertura de los nuevos módulos

```
Sos un QA Engineer especializado en testing de integraciones complejas
y sistemas distribuidos de seguridad.

Tu tarea es crear los tests para los 7 nuevos módulos de NYXAR V2.

ESTRUCTURA:
tests/v2/
├── conftest_v2.py
├── test_misp_client.py
├── test_misp_ingestor.py
├── test_ad_resolver.py
├── test_auto_response.py
├── test_playbooks.py
├── test_hunting.py
├── test_reporter.py
├── test_notifier.py
└── test_observability.py

TEST_MISP_CLIENT.PY (con mock de la API de MISP):
- test_connect_exitoso: respuesta válida de MISP → True
- test_connect_api_key_invalida: 403 → False con log
- test_get_attributes_filtra_por_tipo: solo retorna ip-dst cuando se pide
- test_search_attribute_encontrado: valor en MISP → retorna atributos
- test_search_attribute_no_encontrado: 404 → retorna lista vacía
- test_rate_limit_reintenta: 429 → backoff y reintento exitoso
- test_ssl_error_manejado: SSL error → retorna None, no crashea

TEST_MISP_INGESTOR.PY:
- test_ingest_ips_carga_blocklist: IPs de MISP → guardadas en Redis blocklist:misp_ips
- test_ingest_no_duplica: mismo IOC dos veces → solo existe una vez en Redis
- test_contexto_guardado: atributo MISP → metadatos guardados en "misp:meta:{valor}"
- test_map_threat_level: level=1 → "malicioso", level=3 → "sospechoso"
- test_sync_incremental: segunda sync con timestamp → solo trae eventos nuevos

TEST_AD_RESOLVER.PY:
- test_resolve_desde_cache: IP en Redis → retorna sin consultar MongoDB
- test_resolve_desde_wazuh: IP no en cache, logon en MongoDB → resuelve correctamente
- test_resolve_ip_desconocida: IP nunca vista → retorna "desconocido" sin error
- test_invalidate_limpia_cache: invalidate(ip) → siguiente resolve va a MongoDB
- test_ip_servidor_resuelve_hostname: servidor sin sesión de usuario → retorna hostname

TEST_AUTO_RESPONSE.PY:
- test_propuesta_creada: incidente critico → proposal creado en MongoDB
- test_auto_approve_disabled: incidente critico, AUTO_RESPONSE_CRITICO=false → requiere aprobación
- test_auto_approve_enabled: incidente critico, AUTO_RESPONSE_CRITICO=true → ejecuta sin aprobar
- test_approve_ejecuta: proposal aprobado → playbook ejecutado
- test_reject_no_ejecuta: proposal rechazado → playbook no ejecutado
- test_proposal_expira: proposal sin aprobar por APPROVAL_TIMEOUT → estado=expirado

TEST_PLAYBOOKS.PY (con mocks de Firewall API y AD):
- test_quarantine_ip_interna: IP válida interna → bloquea en firewall mock, retorna exitoso
- test_quarantine_ip_externa_falla: IP 8.8.8.8 → check_preconditions falla
- test_block_ip_externa: IP externa → regla creada en firewall mock
- test_block_ip_interna_rechazada: IP RFC1918 → error de precondición
- test_disable_user_ad_write_disabled: AD_WRITE_ENABLED=false → retorna error claro
- test_disable_user_admin_rechazado: Domain Admin → check_preconditions falla
- test_quarantine_idempotente: quarantine dos veces la misma IP → sin duplicados
- test_undo_quarantine: undo → regla eliminada del firewall mock

TEST_HUNTING.PY:
- test_hipotesis_generada: contexto válido → Claude mock retorna hipótesis válidas
- test_hipotesis_json_valido: respuesta de Claude bien formada → parsea correctamente
- test_hipotesis_json_invalido: Claude retorna texto roto → no crashea, loggea warning
- test_query_builder_valida_pipeline: pipeline con $out → rechazado por validator
- test_query_builder_sin_match_rechazado: pipeline sin $match → rechazado (full scan)
- test_hunter_timeout: query que tarda más de MAX_QUERY_DURATION_SECONDS → lista vacía
- test_hunt_completo: hipótesis → queries → resultados → conclusión (flujo end-to-end mock)

TEST_NOTIFIER.PY (con mocks de Slack/Email/WhatsApp):
- test_slack_envia_critico: incidente critico → Slack webhook llamado
- test_email_envia_con_html: notificación → email HTML enviado via SMTP mock
- test_whatsapp_trunca_mensaje: mensaje largo → truncado a 200 chars
- test_dedup_previene_repeticion: mismo evento dos veces en 15 min → solo 1 envío
- test_quiet_hours_bloquea_medio: hora 2am, severidad media → no envía
- test_quiet_hours_no_bloquea_critico: hora 2am, severidad critica → sí envía
- test_canal_falla_intenta_siguiente: Slack falla → intenta email
- test_honeypot_siempre_envía: honeypot hit, hora 3am → envía sin importar nada

TEST_OBSERVABILITY.PY:
- test_heartbeat_detecta_servicio_caido: TTL expirado → estado=critical
- test_redis_check_latencia: Redis respondiendo → latencia en ms
- test_pipeline_sin_eventos_warning: sin eventos en 15 min → warning
- test_pipeline_sin_eventos_critico: sin eventos en 35 min → critical
- test_health_report_formato: full_check() → HealthReport válido con todos los campos
- test_metricas_prometheus_expuestas: GET /metrics → respuesta en formato Prometheus
- test_health_endpoint_rapido: GET /health → responde en menos de 200ms

REGLAS ADICIONALES PARA TESTS V2:
- Los mocks de APIs externas (MISP, Slack, etc.) usan httpx.MockTransport.
- Los tests de AD usan ldap3 con MockStrategy para simular el servidor.
- Todos los tests de playbooks verifican que el audit_log fue creado.
- Los tests de notificaciones verifican deduplicación con Redis real (integration marker).
- Cada test limpia exactamente lo que creó (fixtures con yield + cleanup).

NO HAGAS:
- No hagas tests que dependan de APIs externas reales.
  Todo mockeado o con servidores locales de test.
- No testees la lógica interna de Slack/WhatsApp/SMTP. Eso es su responsabilidad.
  Solo verificar que el mensaje fue enviado con el contenido correcto.
- No hagas tests que tarden más de 5 segundos individualmente.
- No uses time.sleep() en tests async. Solo asyncio.sleep() si es estrictamente necesario.
```

---

## 📌 Guía de Integración V2 con el Sistema V1

### Orden de implementación recomendado

```
V1 completo y con tests pasando
        │
        ▼
1. observability/  → monitorear el sistema mientras se agrega lo demás
        │
        ▼
2. ad_connector/   → enriquecer identidades con datos reales de la empresa
        │
        ▼
3. notifier/       → empezar a recibir alertas en canales reales
        │
        ▼
4. misp_connector/ → ampliar la threat intel con IOCs comunitarios
        │
        ▼
5. reporter/       → documentar automáticamente lo que está pasando
        │
        ▼
6. auto_response/  → agregar capacidad de respuesta (con mucho cuidado)
        │
        ▼
7. threat_hunting/ → último, cuando el sistema base está maduro y confiable
```

### Variables de entorno nuevas en V2 (agregar a .env.example)

```bash
# MISP
MISP_URL=
MISP_API_KEY=
MISP_VERIFY_SSL=true
MISP_CONTRIBUTE=false
MISP_TLP=white

# Active Directory
AD_SERVER=
AD_PORT=389
AD_USE_SSL=false
AD_DOMAIN=empresa.local
AD_BASE_DN=DC=empresa,DC=local
AD_USER=
AD_PASSWORD=
AD_SYNC_INTERVAL=300
AD_WRITE_ENABLED=false

# Auto Response
AUTO_RESPONSE_ENABLED=false
AUTO_RESPONSE_CRITICO=false
APPROVAL_TIMEOUT=24
FIREWALL_API_URL=
PROTECTED_IPS=192.168.1.1,192.168.1.2

# Notifications
NOTIFY_ADMINS=
NOTIFY_SECURITY_TEAM=
NOTIFY_REPORT_RECIPIENTS=
NOTIFY_CHANNELS_ENABLED=email
NOTIFY_QUIET_START=23:00
NOTIFY_QUIET_END=07:00
SLACK_WEBHOOK_URL=
SLACK_BOT_TOKEN=
SLACK_DEFAULT_CHANNEL=#NYXAR-alerts
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=true
EMAIL_FROM=
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=

# Reports
REPORT_STORAGE_PATH=./data/reports
REPORT_RETENTION_DAYS=90

# Observability
METRICS_PORT=9090
HEARTBEAT_INTERVAL=30
```

### Señales de que un módulo V2 está listo para producción

```
✅ Tests unitarios pasando con coverage >= 80%
✅ Tests de integración pasando
✅ Heartbeat visible en el dashboard de observabilidad
✅ Al menos 1 notificación de prueba enviada y recibida correctamente
✅ Audit log generando entradas (para auto_response)
✅ Sin errores en logs durante 24 horas en el laboratorio
```

---

*NYXAR — PROMPTS_V2.md — Módulos Avanzados — v1.0 — 2026*
