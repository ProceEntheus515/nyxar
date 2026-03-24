import os
import json
import random
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from collector.normalizer import Normalizer
from shared.logger import get_logger
from shared.redis_bus import RedisBus

logger = get_logger("simulator.generator")

class TrafficGenerator:
    """
    Motor principal de generación de tráfico sintético.
    Genera eventos en tiempo real basados en los perfiles de personas.json.
    """

    def __init__(self, personas: List[Dict[str, Any]], redis_bus: RedisBus):
        self.personas = personas
        self.redis_bus = redis_bus
        self._normalizer = Normalizer(redis_bus)

        self.lab_mode = os.getenv("LAB_MODE", "false").lower() == "true"
        self.time_multiplier = 5 if self.lab_mode else 1
        self.start_time_real = datetime.now(timezone.utc)
        self.start_time_simulated = self.start_time_real
        
        self.active_personas = 0
        self.events_last_minute = 0
        self.unique_domains_seen = set()
        self.total_mb_simulated = 0.0
        
        # Estado interno por persona para trackear "pausas" (meetings, lunch)
        self.persona_states = {p["id"]: {"pause_until": None} for p in personas}

        # Diccionarios de dominios globales aleatorios para ruido
        self.random_domains = ["nytimes.com", "reddit.com", "weather.com", "spotify.com", "whatsapp.com", "wikipedia.org", "netflix.com", "infobae.com", "lanacion.com.ar", "clarin.com"]
        self.new_domains = ["obscure-tracker.net", "click-analytics.ru", "cdn-metrics-99.cn", "unknown-forum.org", "temp-file-share.io"]

    def _simulated_now(self) -> datetime:
        """
        Retorna la hora actual. En LAB_MODE, el tiempo avanza 5x más rápido 
        desde que inició el script, permitiendo ver un día entero en ~4.8 horas.
        """
        now_real = datetime.now(timezone.utc)
        elapsed = now_real - self.start_time_real
        return self.start_time_simulated + (elapsed * self.time_multiplier)

    async def _populate_identity_table(self) -> None:
        """
        Publica en Redis la tabla ip->usuario, ip->hostname y ip->area
        para que el normalizer pueda resolver identidades.
        Usamos la misma key que espera normalizer.py: 'identities:host:{ip}'
        """
        logger.info("Poblando tabla de identidades en Redis (DHCP/AD simulado)...")
        for p in self.personas:
            ip = p["dispositivo"]
            key = f"identities:host:{ip}"
            data = {
                "usuario": p["id"],
                "hostname": p["hostname"],
                "area": p["area"]
            }
            # Cache por 24h
            await self.redis_bus.cache_set(key, data, ttl=86400)
        logger.info(f"Se poblaron {len(self.personas)} identidades exitosamente.")

    def _esta_en_horario(self, persona: dict, now: datetime) -> bool:
        """
        Verifica si la persona está dentro de su horario laboral con ±15 min de spread.
        """
        dias_map = {"lun": 0, "mar": 1, "mie": 2, "jue": 3, "vie": 4, "sab": 5, "dom": 6}
        today_str = list(dias_map.keys())[now.weekday()]
        
        if today_str not in persona["dias_laborales"]:
            return False

        # Parsear HH:MM
        h_ini, m_ini = map(int, persona["horario_inicio"].split(":"))
        h_fin, m_fin = map(int, persona["horario_fin"].split(":"))
        
        # Start and End times today
        start_time = now.replace(hour=h_ini, minute=m_ini, second=0, microsecond=0)
        end_time = now.replace(hour=h_fin, minute=m_fin, second=0, microsecond=0)
        
        # Spread (desfase humano)
        # Determinístico por persona usando el hash de su id para que empiece/termine siempre igual ese día
        offset_minutes = (hash(persona["id"] + str(now.day)) % 30) - 15
        start_time += timedelta(minutes=offset_minutes)
        end_time += timedelta(minutes=offset_minutes)

        if end_time < start_time: # Casos que cruzan la medianoche
            if now >= start_time or now <= end_time:
                return True
        else:
            if start_time <= now <= end_time:
                return True
                
        return False

    async def _emit_dns_event(self, persona: dict, dominio: str, force_blocked: bool = False) -> None:
        """
        Genera log DNS crudo (como dns_parser) y publica en events:raw el Evento normalizado (I01/I16).

        En laboratorio no hay archivo de log físico: el raw se construye aquí y el Normalizer
        produce el mismo contrato que el collector. En producción el collector lee el fichero y normaliza.
        """
        now = self._simulated_now()

        # Ruido humano: ±30 segundos en el timestamp reportado
        offset_seg = int(random.gauss(0, 15))
        ts_event = now + timedelta(seconds=max(min(offset_seg, 30), -30))

        if ts_event > now:
            ts_event = now

        # ISO sin sufijo Z: coincide con _parse_timestamp del Normalizer (%Y-%m-%dT%H:%M:%S)
        ts_iso = ts_event.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        raw_dns_log = {
            "timestamp": ts_iso,
            "client": persona["dispositivo"],
            "domain": dominio,
            "type": "A",
            "status": "BLOCKED" if force_blocked else "NOERROR",
            "blocked": force_blocked,
        }

        evento = await self._normalizer.normalize(raw_dns_log, "dns")
        if evento:
            await self.redis_bus.publish_event(
                self.redis_bus.STREAM_RAW,
                evento.to_redis_dict(),
            )
        
        self.events_last_minute += 1
        self.unique_domains_seen.add(dominio)

    async def _emit_proxy_event(self, persona: dict, dominio: str, force_blocked: bool = False) -> None:
        """
        Genera evento Proxy y publica como si viniera de proxy_parser.
        """
        now = self._simulated_now()
        ts_unix = now.timestamp()
        
        # Volumen simulado
        # IT y Marketing generan requests más pesados (ej. pull images, videos)
        base_bytes = random.gauss(15000, 5000)
        if persona["area"] in ["it", "marketing"]:
            base_bytes *= 3 
            
        bytes_sent = max(500, int(base_bytes))
        
        # Acumular telemetría (convertir a MB)
        self.total_mb_simulated += bytes_sent / (1024 * 1024)

        event = {
            "timestamp": f"{ts_unix:.3f}",
            "client_ip": persona["dispositivo"],
            "method": random.choices(["GET", "POST", "CONNECT"], weights=[0.7, 0.2, 0.1])[0],
            "url": f"https://{dominio}/" if not force_blocked else f"http://{dominio}/",
            "status_code": "403" if force_blocked else random.choices(["200", "301", "404"], weights=[0.85, 0.1, 0.05])[0],
            "bytes": str(bytes_sent),
            "destination_ip": "8.8.8.8" # Simulado genérico
        }

        evento = await self._normalizer.normalize(event, "proxy")
        if evento:
            await self.redis_bus.publish_event(
                self.redis_bus.STREAM_RAW, evento.to_redis_dict()
            )
        self.events_last_minute += 1

    async def _generate_for_persona(self, persona: dict) -> None:
        """Loop infinito de generación para una persona específica."""
        while True:
            now = self._simulated_now()
            state = self.persona_states[persona["id"]]

            # Chequear pausas (reuniones, almuerzo)
            if state["pause_until"] and state["pause_until"] > now:
                # Está en pausa, chequeamos luego
                speed = self.time_multiplier
                await asyncio.sleep(60 / speed)
                continue
            else:
                state["pause_until"] = None # Terminó pausa

            # Chance de iniciar pausa (1% por ciclo de evaluación)
            if random.random() < 0.01:
                pause_mins = random.uniform(20, 60)
                state["pause_until"] = now + timedelta(minutes=pause_mins)
                continue

            en_horario = self._esta_en_horario(persona, now)
            
            # Fuera de horario
            if not en_horario:
                if random.random() < 0.005: # 0.5% chance
                    # Evento esporádico nocturno (sincronizador de fondo)
                    dom = random.choice(persona["dominios_habituales"])
                    await self._emit_dns_event(persona, dom)
                    await self._emit_proxy_event(persona, dom)
                
                speed = self.time_multiplier
                await asyncio.sleep(60 / speed)
                continue

            # --- DENTRO DE HORARIO --- 
            
            # Determinar volumen. Picos en 10-12 y 15-17
            h = now.hour
            is_peak = (10 <= h <= 12) or (15 <= h <= 17)
            events_per_min = random.uniform(4, 8) if is_peak else random.uniform(2, 5)

            # Comportamiento errático para IT
            if persona["area"] == "it" and random.random() < 0.2:
                events_per_min *= random.uniform(0.1, 3.0)

            # Para un intervalo real de simulación, calculamos el sleep base
            # Ej: 5 eventos por minuto -> 1 evento cada 12 segundos simulados
            # Si LAB_MODE = 5x -> 1 evento real cada 2.4 segundos
            
            # Elegir dominio
            roll = random.random()
            force_blocked = False
            
            if roll < 0.01: # 1% dominio nuevo/raro
                dom = random.choice(self.new_domains)
                force_blocked = True if random.random() < 0.5 else False # Algunos bloqueados por fw
            elif roll < 0.06: # 5% dominio aleatorio ruido normal
                dom = random.choice(self.random_domains)
            else: # Habitual
                doms = persona["dominios_habituales"]
                if len(doms) >= 3:
                    if random.random() < 0.7:
                        dom = random.choice(doms[:3])
                    else:
                        dom = random.choice(doms[3:])
                else:
                    dom = random.choice(doms)

            # Emitir
            await self._emit_dns_event(persona, dom, force_blocked=force_blocked)
            if random.random() < 0.5: # 50% genera proxy
                await self._emit_proxy_event(persona, dom, force_blocked=force_blocked)
                
            # Calcular delay al próximo evento
            segundos_simulados_gap = 60.0 / max(events_per_min, 0.1)
            # Aplicar varianza gaussiana al gap
            gap = random.gauss(segundos_simulados_gap, segundos_simulados_gap * 0.3)
            gap_real = max(gap / self.time_multiplier, 0.1) # Min 100ms
            
            await asyncio.sleep(gap_real)

    async def _stats_reporter(self):
        """Reporta métricas cada 60s reales."""
        while True:
            await asyncio.sleep(60)
            now = self._simulated_now()
            
            activas = sum(1 for p in self.personas if self._esta_en_horario(p, now) and (not self.persona_states[p["id"]]["pause_until"] or self.persona_states[p["id"]]["pause_until"] < now))
            
            logger.info("--- REPORTE SIMULADOR ---", extra={
                "lab_mode": self.lab_mode,
                "simulated_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "activos_ahora": activas,
                "eventos_ultimo_min_real": self.events_last_minute,
                "dominios_unicos": len(self.unique_domains_seen),
                "trafico_mb_acumulado": round(self.total_mb_simulated, 2)
            })
            
            self.events_last_minute = 0
            self.active_personas = activas

    async def run(self) -> None:
        logger.info(f"Iniciando Motor de Simulación (LAB_MODE={self.lab_mode})")
        
        await self._populate_identity_table()
        
        tasks = []
        for persona in self.personas:
            logger.debug(f"Scheduleando worker para {persona['id']}")
            tasks.append(asyncio.create_task(self._generate_for_persona(persona)))
            
        tasks.append(asyncio.create_task(self._stats_reporter()))
        
        # Correr hasta que el orquestador principal cancele
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Motor de simulación detenido limpiamente.")
            for t in tasks:
                t.cancel()
