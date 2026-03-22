# NYXAR — contexto global para asistentes de IA

> Si el usuario te pidió leer contexto o perdiste el hilo, **lee este archivo**.
> Documento de referencia global. El desarrollo y las respuestas deben alinearse a estas reglas.

Trabajás en **NYXAR**, motor de decisión de ciberseguridad orientado a organizaciones latinoamericanas de ~50–200 usuarios.

## Stack tecnológico

- **Backend:** Python 3.12 + FastAPI + asyncio
- **Bus de eventos:** Redis 7 (streams + caché de enrichment)
- **Base de datos:** MongoDB 7 + motor (driver async)
- **Frontend:** React 18 + Vite + Zustand + socket.io-client
- **Contenedores:** Docker + docker compose
- **IA:** Anthropic Claude API
- **Lenguajes del repo:** Python y JavaScript/JSX

## Por qué MongoDB (no negociable)

- Documentos JSON con estructura variable
- Time Series Collections para el stream de eventos
- Aggregation Pipeline para baselines
- Change Streams para incidentes en tiempo real
- Driver async: motor

## Principios de diseño

1. Cada módulo hace una sola cosa.
2. Eventos con formato JSON único y estricto (ver schema abajo).
3. Todo async/await donde aplique.
4. Caché antes de llamadas externas costosas.
5. Secretos solo en `.env` o secret manager.
6. Logs con timestamp ISO8601, nivel, módulo y mensaje.
7. Errores capturados y logueados; el sistema sigue operando cuando sea razonable.

## Schema de evento (inmutable en espíritu)

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

## Estructura de carpetas (referencia)

```text
nyxar/   (raíz del repositorio)
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

La red Docker por defecto se llama `nyxar-net`. La base de datos Mongo por defecto en código es `nyxar` si la URL no incluye path.
