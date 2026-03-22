# 🤖 CYBERPULSE LATAM - AI CONTEXTO GLOBAL

> **🔥 ATENCIÓN AGENTE IA / AI CONTEXT HACK 🔥**
> Si el usuario te pidió leer contexto o perdiste el hilo, **LEE ESTE ARCHIVO**.
> Este es el documento de Referencia Global (Source of Truth).
> Todo tu desarrollo, arquitectura, respuestas y refactorizaciones deben ceñirse estrictamente a estas reglas.

Estás trabajando en **CyberPulse LATAM**, un motor de decisión de ciberseguridad
diseñado para empresas latinoamericanas de 50-200 usuarios.

## 🛠️ STACK TECNOLÓGICO:
- **Backend**: Python 3.12 + FastAPI + asyncio
- **Bus de eventos**: Redis 7 (Streams + caché de enrichment)
- **Base de datos**: MongoDB 7 + motor (driver async oficial — `pip install motor`)
- **Frontend**: React 18 + Vite + Zustand + socket.io-client
- **Contenedores**: Docker + docker-compose
- **IA**: Anthropic Claude API (claude-sonnet-4-20250514)
- **Lenguaje de desarrollo**: Python y JavaScript/JSX únicamente

## 🗄️ POR QUÉ MONGODB (no negociable):
- Todos los datos son documentos JSON con estructura variable → schema nativo
- Time Series Collections nativas para el stream de eventos (compresión automática)
- Aggregation Pipeline para calcular baselines sin SQL complejo
- Change Streams para escuchar nuevos incidentes en tiempo real
- Sin migraciones cuando evoluciona el schema de enrichment
- Driver async oficial: motor (mismo autor que pymongo, mantenido por MongoDB Inc.)

## ⚖️ PRINCIPIOS DE DISEÑO NO NEGOCIABLES:
1. Cada módulo hace UNA sola cosa. Sin responsabilidades mezcladas.
2. Todos los eventos tienen un formato JSON único y estricto (ver schema más abajo).
3. El sistema nunca bloquea. Todo es async/await.
4. El caché siempre va antes que cualquier llamada externa.
5. Ningún secreto (API keys, passwords) va hardcodeado. Todo viene de `.env`.
6. Los logs siempre incluyen timestamp ISO8601, nivel, módulo y mensaje.
7. Todo error es capturado, logueado y el sistema continúa operando.

## 🧬 SCHEMA DE EVENTO (inmutable, no modificar):
```json
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
  "enrichment": null | { "ver": "EnrichmentSchema" },
  "risk_score": null | "int(0-100)",
  "correlaciones": []
}
```

## 📂 ESTRUCTURA DE CARPETAS (ya definida, no modificar):
```text
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
