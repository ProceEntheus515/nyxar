"""
Servicio de sincronizacion AD: sync completo al iniciar, luego incremental cada AD_SYNC_INTERVAL.
Si AD no esta configurado o no responde, el proceso espera o sale sin tumbar el stack.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus
from shared.wazuh_logons import ensure_wazuh_logons_indexes

from ad_connector.client import ADClient
from ad_connector.identity_sync import IdentitySync

logger = get_logger("ad_connector.main")

STATE_DOC_ID = "ad_connector"
CONNECT_RETRY_S = 60
OVERLAP = timedelta(minutes=5)


async def _load_incremental_since(db) -> datetime:
    doc = await db.ad_sync_state.find_one({"_id": STATE_DOC_ID})
    if doc and doc.get("ultimo_incremental_utc"):
        ts = doc["ultimo_incremental_utc"]
        if isinstance(ts, datetime):
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts.astimezone(timezone.utc)
    return datetime.now(timezone.utc) - timedelta(days=1)


async def _save_incremental_watermark(db, ts: datetime) -> None:
    await db.ad_sync_state.update_one(
        {"_id": STATE_DOC_ID},
        {
            "$set": {
                "ultimo_incremental_utc": ts,
                "actualizado_en": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )


async def run_loop() -> None:
    interval = int(os.getenv("AD_SYNC_INTERVAL", "300"))
    mongo = MongoClient()
    redis_bus = RedisBus()
    await mongo.connect()
    await redis_bus.connect()

    try:
        await ensure_wazuh_logons_indexes(mongo.db)
    except Exception as e:
        logger.warning("Indices wazuh_logons no garantizados: %s", e)

    client = ADClient(mongo_client=mongo)
    syncer = IdentitySync(mongo_client=mongo, redis_bus=redis_bus)

    if not client.is_configured():
        logger.warning(
            "AD no configurado (AD_SERVER, AD_BASE_DN, AD_USER, AD_PASSWORD). "
            "Saliendo sin error para entornos sin LDAP."
        )
        await redis_bus.disconnect()
        await mongo.disconnect()
        return

    need_full = True

    while True:
        try:
            if not await client.connect():
                logger.error(
                    "No se pudo conectar a AD. Reintento en %s s.",
                    CONNECT_RETRY_S,
                )
                await asyncio.sleep(CONNECT_RETRY_S)
                continue

            if need_full:
                logger.info("Sincronizacion completa AD")
                stats = await syncer.full_sync(client)
                logger.info("full_sync AD: %s", stats)
                await _save_incremental_watermark(
                    mongo.db,
                    datetime.now(timezone.utc),
                )
                await syncer.refresh_host_cache_from_logons(client)
                need_full = False
            else:
                desde = await _load_incremental_since(mongo.db) - OVERLAP
                stats_inc = await syncer.incremental_sync(client, desde)
                logger.info("incremental_sync AD: %s", stats_inc)
                await _save_incremental_watermark(
                    mongo.db,
                    datetime.now(timezone.utc),
                )
                await syncer.refresh_host_cache_from_logons(client)

            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Error en bucle AD: %s", e)
            need_full = True
            await asyncio.sleep(CONNECT_RETRY_S)


async def main() -> None:
    await run_loop()


if __name__ == "__main__":
    asyncio.run(main())
