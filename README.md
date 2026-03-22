# NYXAR

![Status](https://img.shields.io/badge/status-en%20construcci%C3%B3n-orange)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![React](https://img.shields.io/badge/React-18-61dafb)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

```
╔═══════════════════════════════════════════════════════════╗
║                        N Y X A R                          ║
╚═══════════════════════════════════════════════════════════╝
```

**Motor de decisión de ciberseguridad para Latinoamérica**

*Opera desde la oscuridad. Ve todo.*

---

## ¿Qué es NYXAR?

Muchas pymes en la región tienen registros dispersos (DNS, proxy, endpoints) y poco tiempo para correlacionar señales. NYXAR ingiere eventos de red y actividad, los enriquece con listas e IOCs, calcula riesgo por identidad y genera **incidentes** cuando los patrones lo ameritan. El objetivo no es reemplazar a un analista, sino **ordenar el ruido** y ofrecer contexto accionable en un stack que puedas levantar en tu propia infraestructura.

El proyecto incluye un **laboratorio con Docker** (simulador de ataques, dashboard en tiempo real, API REST y sockets) para aprender el flujo sin exponer datos reales. Opcionalmente puedes conectar fuentes reales (Wazuh, AD, MISP) y extender el **motor de respuesta asistida (SOAR)** para proponer acciones que un operador aprueba antes de ejecutarlas.

## Diferencias con otras soluciones

| Aspecto | Splunk / SIEM enterprise | Darktrace (NDR comercial) | SIEM genérico self-hosted | **NYXAR** |
|--------|---------------------------|----------------------------|----------------------------|----------------------|
| Coste de entrada | Alto (licencias, volumen) | Muy alto | Medio-alto (operación) | Bajo: open source + Docker |
| Enfoque | Plataforma amplia | Aprendizaje de red | Depende del stack | Correlación + riesgo + laboratorio LATAM |
| Datos | Todo lo que indexas | Tráfico de red | Lo que conectes | Eventos DNS/proxy/Wazuh + feeds abiertos |
| Despliegue | Cluster dedicado | Appliance / cloud | Variado | `docker-compose`, servicios modulares |
| Transparencia | Caja negra parcial | Caja negra | Depende del vendor | Código visible, reglas y patrones en repo |

NYXAR **no** compite en escala con un SIEM maduro de multinacional; compite en **claridad**, **reproducibilidad** y en un camino claro desde laboratorio a piloto controlado.

## Arquitectura en 30 segundos

```
                    ┌─────────────┐
   Pi-hole / logs   │  COLLECTOR  │──┐
   (DNS, etc.)      └─────────────┘  │
                                      ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────────┐    ┌──────────┐
│  Redis   │◄──►│ ENRICHER │◄──►│ MongoDB  │◄──►│ CORRELATOR  │───►│   API    │
│ streams  │    │+ feeds   │    │ eventos  │    │ incidentes  │    │+ SocketIO│
└──────────┘    └──────────┘    └──────────┘    └─────────────┘    └────┬─────┘
       ▲                                       │                       │
       │                                       ▼                       ▼
       │                               ┌─────────────┐         ┌────────────┐
       └───────────────────────────────│ AI analyst  │         │ DASHBOARD  │
                                       │ (opcional)  │         │  (React)   │
                                       └─────────────┘         └────────────┘
```

**Flujo:** el colector publica eventos crudos en Redis; el enricher normaliza, enriquece (listas, APIs opcionales) y persiste en MongoDB; el correlator consume la cola enriquecida, aplica patrones y abre incidentes; la API y el dashboard muestran estado en vivo. El perfil **lab** añade un simulador que inyecta escenarios sin tráfico real.

## Quick start — laboratorio

Los comandos siguientes funcionan en **macOS**, **Linux** y **Windows** con **Docker Desktop** o **WSL2** (recomendado en Windows).

```bash
git clone https://github.com/TU_ORG/nyxar.git
cd nyxar
cp .env.example .env
# Editar .env: al menos LAB_MODE=true y, si quieres IA, ANTHROPIC_API_KEY (ver sección API keys)
docker compose --profile lab up --build
```

- **Dashboard:** http://localhost:3000  
- **API (docs OpenAPI):** http://localhost:8000/docs  

**Inyectar un ataque de prueba** (requiere `LAB_MODE=true` y perfil `lab` activo):

```bash
curl -X POST http://localhost:8000/api/v1/simulator/scenario \
  -H "Content-Type: application/json" \
  -d "{\"scenario\": \"phishing\", \"target\": \"ventas.silva\", \"intensity\": \"media\"}"
```

Escenarios disponibles: `phishing`, `ransomware`, `dns_tunneling`, `lateral_movement`, `exfiltration`. Los valores de `target` deben coincidir con un `id` de `simulator/personas.json`.

> **Nota:** En `docker-compose` el servicio de base de datos se llama `mongodb`. Si las URLs no resuelven, usa `mongodb://mongodb:27017/nyxar` (o el nombre de base que definas) dentro de la red Docker.

## Obtener API keys gratuitas

El enriquecimiento **mejora** con claves, pero **no es obligatorio**: el sistema sigue usando blocklists locales (Spamhaus, abuse.ch, etc.).

| Servicio | Registro | Tiempo aprox. |
|----------|----------|----------------|
| [AbuseIPDB](https://www.abuseipdb.com/pricing) | Cuenta gratuita con límite diario | ~2 min |
| [AlienVault OTX](https://otx.alienvault.com/) | Registro + API key en perfil | ~3 min |
| [VirusTotal](https://www.virustotal.com/gui/join-us) | Cuenta + clave API | ~3 min |

Guarda las claves en `.env` como `ABUSEIPDB_KEY`, `OTX_KEY`, `VIRUSTOTAL_KEY`.

## Configuración

Variables definidas en `.env.example` (todas pueden ajustarse según tu entorno):

| Variable | Descripción | Requerida | Ejemplo |
|----------|-------------|-----------|---------|
| `REDIS_URL` | URL del broker Redis (DB lógica opcional en path) | Sí (Docker) | `redis://redis:6379/0` |
| `MONGODB_URL` | URI de MongoDB | Sí (Docker) | `mongodb://mongodb:27017/nyxar` |
| `ANTHROPIC_API_KEY` | Claude para el analista IA | No | `sk-ant-...` |
| `ABUSEIPDB_KEY` | Reputación de IP | No | `your_key` |
| `VIRUSTOTAL_KEY` | URLs y hashes | No | `your_key` |
| `OTX_KEY` | AlienVault OTX | No | `your_key` |
| `LAB_MODE` | Activa simulador en la API | No | `true` |
| `LOG_LEVEL` | Nivel de log | No | `INFO` |
| `MISP_URL` | Instancia MISP | No | `https://misp.ejemplo.com` |
| `MISP_API_KEY` | API MISP | No | (secreto) |
| `MISP_VERIFY_SSL` | Verificar TLS | No | `true` |
| `MISP_CONTRIBUTE` | Contribución IOC a MISP | No | `false` |
| `MISP_ORG_NAME` | Nombre org. en eventos | No | `NYXAR` |
| `MISP_TLP` | Etiqueta TLP | No | `tlp:white` |
| `MISP_DISTRIBUTION` | Nivel de distribución MISP | No | `1` |
| `MISP_ALLOW_DISTRIBUTION_ALL` | Permitir distribución amplia | No | `false` |
| `MISP_CONTRIBUTOR_POLL_S` | Polling si no hay Change Stream | No | `60` |
| `AD_SERVER` | Host LDAP/AD | No | `dc01.empresa.local` |
| `AD_PORT` | Puerto LDAP | No | `389` |
| `AD_USE_SSL` | LDAPS | No | `false` |
| `AD_DOMAIN` | Dominio NetBIOS/DNS | No | `empresa.local` |
| `AD_BASE_DN` | Base DN | No | `DC=empresa,DC=local` |
| `AD_USER` / `AD_PASSWORD` | Bind de sincronización | No | (secreto) |
| `AD_SYNC_INTERVAL` | Segundos entre syncs | No | `300` |
| `AD_PRIVILEGED_GROUP_PATTERNS` | CSV para marcar privilegio | No | `admin` |
| `WAZUH_LOGON_RULE_IDS` | IDs de regla logon (CSV) | No | (vacío = fallback) |
| `WAZUH_LOGOFF_RULE_IDS` | IDs de regla logoff (CSV) | No | (vacío = heurística 4634) |
| `WAZUH_LOGONS_TTL_SECONDS` | TTL colección `wazuh_logons` | No | `604800` |
| `AUTO_RESPONSE_ENABLED` | Motor SOAR (proceso aparte o futuro servicio) | No | `false` |
| `AUTO_RESPONSE_POLL_S` | Polling de incidentes (fallback) | No | `45` |
| `AUTO_RESPONSE_CRITICO` | Auto-aprobación en críticos | No | `false` |
| `AUTO_RESPONSE_USE_REDIS` | Notify vía Redis | No | `true` |
| `AUTO_RESPONSE_LOOKBACK_DAYS` | Ventana de incidentes recientes | No | `7` |
| `FIREWALL_API_URL` | POST para bloqueo IP (opcional) | No | (vacío = stub) |
| `AD_WRITE_ENABLED` | Permitir escritura AD en playbooks | No | `false` |

**Producción:** suele añadirse `FRONTEND_CORS_URL` (origen del dashboard) en el entorno de la API; no está en `.env.example` pero la aplicación la lee si está definida.

## Deployment en producción

**Mínimo recomendado (piloto pequeño):** 4 vCPU, 8 GB RAM, 40 GB SSD, Linux x86_64 con Docker Engine. Aumenta RAM si retienes muchos eventos en MongoDB o subes réplicas.

**Diferencias respecto al laboratorio:**

- `LAB_MODE=false` y **sin** perfil `lab` (no levantes el contenedor simulador en entornos reales).
- URLs de `REDIS_URL` y `MONGODB_URL` apuntando a servicios gestionados o clústeres propios; backups de Mongo y políticas de retención definidas.
- Claves y secretos solo en variables de entorno o secret manager, nunca en imagen.
- TLS terminación delante de la API y CORS acotado a tu dominio.

**Arranque típico:**

```bash
docker compose up -d --build
```

Ajusta perfiles, réplicas y volúmenes según tu `docker-compose` de producción (este repo asume un compose de referencia para desarrollo).

## Fuentes de threat intelligence

| Fuente | Tipo | Uso en NYXAR | Frecuencia típica |
|--------|------|-------------------|-------------------|
| Spamhaus DROP | CIDR maliciosos | Redis `blocklist:spamhaus_drop` | ~1 h (scheduler enricher) |
| Spamhaus EDROP | CIDR extendido | `blocklist:spamhaus_edrop` | ~1 h |
| Feodo Tracker (abuse.ch) | IPs | `blocklist:feodo` | ~1 h |
| URLhaus (abuse.ch) | Dominios | `blocklist:urlhaus` | ~1 h |
| ThreatFox (abuse.ch) | IOCs JSON | `blocklist:threatfox` | ~1 h |
| MISP (si configurado) | IOCs por tipo | Sets `blocklist:misp_*` + metadatos | Según conector / eventos |
| AbuseIPDB | API | Enriquecimiento de IP (si hay clave) | Por evento / política interna |
| VirusTotal | API | URL y hash (si hay clave) | Por evento |
| AlienVault OTX | API | Contexto IOC (si hay clave) | Por evento |

Las listas locales permiten **detección útil sin claves**; las APIs reducen falsos negativos en IOCs puntuales.

## Contribuir

1. **Issues:** abre un issue describiendo el comportamiento esperado, versión de Docker/OS y pasos mínimos para reproducir.
2. **Pull requests:** ramas cortas, un cambio lógico por PR cuando sea posible; incluye tests si tocas lógica crítica (`pytest` en la raíz).
3. **Estilo:** Python con formateo consistente (**Black**), lint **Ruff**; frontend **ESLint** (config del dashboard). Antes de subir, ejecuta tests y linters en los paquetes que modifiques.

## Licencia

Este proyecto se ofrece bajo la **licencia MIT**. Puedes usarlo, modificarlo y distribuirlo con pocas restricciones legales, siempre **incluyendo el aviso de copyright y la licencia** en copias sustanciales.

**Uso responsable:** NYXAR está pensado para **defensa** en redes que administres o con autorización explícita. No uses estas herramientas para atacar sistemas ajenos ni para violar leyes locales. El software se entrega “tal cual”, sin garantía de adecuación a un fin particular; la seguridad operativa final es responsabilidad de quien despliega el sistema.
