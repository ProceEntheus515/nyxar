import asyncio
import os
import signal

from shared.logger import get_logger
from shared.mongo_client import MongoClient
from shared.redis_bus import RedisBus

# Modulos
from collector.parsers.dns_parser import DnsParser
from collector.parsers.proxy_parser import ProxyParser
from collector.parsers.firewall_parser import FirewallParser
from collector.parsers.wazuh_parser import WazuhParser

logger = get_logger("collector.main")

async def main():
    logger.info("Inicializando CyberPulse Collector...")
    redis_bus = RedisBus()
    await redis_bus.connect()
    mongo_client = MongoClient()
    await mongo_client.connect()
    
    # Rutas por defecto del host, pueden venir de .env
    pihole_path = os.getenv("LOG_DNS_PATH", "/logs/dns/pihole.log")
    proxy_path = os.getenv("LOG_PROXY_PATH", "/logs/proxy/access.log")
    firewall_path = os.getenv("LOG_FIREWALL_PATH", "/logs/firewall/ufw.log")
    
    # Instanciamos parsers
    dns = DnsParser(log_path=pihole_path, redis_bus=redis_bus)
    proxy = ProxyParser(log_path=proxy_path, redis_bus=redis_bus)
    fw = FirewallParser(log_path=firewall_path, redis_bus=redis_bus)
    wazuh = WazuhParser(redis_bus=redis_bus, mongo_client=mongo_client)
    
    # Manejo graceful shutdown
    loop = asyncio.get_event_loop()
    
    def shutdown_signal():
        logger.info("Recibida señal de apagado. Finalizando Collector...")
        for task in asyncio.all_tasks():
            task.cancel()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_signal)
        except NotImplementedError:
            pass # Windows compatibility for local dev
    
    try:
        # Lanzamos todos en paralelo en el event_loop
        await asyncio.gather(
            dns.start(),
            proxy.start(),
            fw.start(),
            wazuh.start(),
            return_exceptions=True
        )
    except asyncio.CancelledError:
        pass
    finally:
        await redis_bus.disconnect()
        await mongo_client.disconnect()
        logger.info("Collector finalizado limpiamente.")

if __name__ == "__main__":
    asyncio.run(main())
