import os
import asyncio
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from shared.logger import get_logger

logger = get_logger("mongo_client")

class MongoClient:
    """
    Singleton de conexión a MongoDB.
    Todos los servicios importan esto para acceder a las colecciones.
    
    Uso:
        client = MongoClient()
        await client.connect()
        evento = await client.db.events.find_one({"_id": event_id})
    """
    
    COLLECTIONS = {
        "events":        "events",        # Time Series
        "identities":    "identities",
        "incidents":     "incidents",
        "ai_memos":      "ai_memos",
        "honeypot_hits": "honeypot_hits",
    }
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoClient, cls).__new__(cls)
            cls._instance._client = None
            cls._instance.db = None
            cls._instance.mongo_url = (
                os.getenv("MONGO_URL")
                or os.getenv("MONGODB_URL")
                or "mongodb://localhost:27017/cyberpulse"
            )
        return cls._instance

    async def connect(self) -> None:
        if not self._client:
            logger.info("Iniciando conexión a MongoDB")
            attempts = 3
            for attempt in range(attempts):
                try:
                    self._client = AsyncIOMotorClient(self.mongo_url, maxPoolSize=20)
                    
                    # Extraer base de datos de la URL, defecto a 'cyberpulse' si no se provee
                    db_name = self.mongo_url.split("/")[-1].split("?")[0]
                    if not db_name:
                        db_name = "cyberpulse"
                        
                    self.db = self._client[db_name]
                    
                    if await self.ping():
                        logger.info("Conectado exitosamente a MongoDB")
                        break
                except Exception as e:
                    logger.error(f"Fallo al conectar a MongoDB (Intento {attempt+1}/{attempts}): {e}")
                    if attempt == attempts - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)

    async def disconnect(self) -> None:
        if self._client:
            logger.info("Cerrando conexión a MongoDB")
            self._client.close()
            self._client = None
            self.db = None

    async def ping(self) -> bool:
        try:
            if not self._client:
                return False
            await self._client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Error haciendo ping a MongoDB: {e}")
            return False
