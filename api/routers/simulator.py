import os
import json
import uuid
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.utils import success_response, error_response
from shared.redis_bus import RedisBus
from shared.logger import get_logger

# Lazy load para no trabar si hay error de modulo en app prod
try:
    from simulator.attack_scenarios import run_scenario, SCENARIOS
except ImportError:
    run_scenario = None
    SCENARIOS = {}

logger = get_logger("api.simulator")
router = APIRouter(prefix="/simulator", tags=["simulator"])
redis_bus = RedisBus()

class ScenarioRequest(BaseModel):
    scenario: str
    target: str
    intensity: str

@router.post("/scenario")
async def start_scenario(req: ScenarioRequest):
    if not run_scenario or req.scenario not in SCENARIOS:
        raise HTTPException(400, "Scenario engine no cargado o no existe")
        
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "simulator", "personas.json")
        with open(path, "r", encoding="utf-8") as f:
            personas = json.load(f)
            
        target_persona = next((p for p in personas if p["id"] == req.target), None)
        if not target_persona:
            raise HTTPException(404, "Target persona ID falso")
            
        # Background task
        asyncio.create_task(run_scenario(
            name=req.scenario,
            target_persona=target_persona,
            intensity=req.intensity,
            redis_bus=redis_bus
        ))
        
        return success_response({"status": "started", "scenario_id": f"sim_{req.scenario}_{uuid.uuid4().hex[:6]}"})
        
    except Exception as e:
        logger.error(f"Error parseando escenarios locales en API: {e}")
        raise HTTPException(500, "Internal API error")

@router.get("/status")
async def simulator_status():
    r = redis_bus.client
    if not r:
         return success_response({"status": "offline"})
         
    # El simulador reportaba identidades via "identities:host:X" keys
    cursor = b"0"
    count = 0
    try:
        while cursor:
            cursor, keys = await r.scan(cursor=cursor, match="identities:host:*", count=1000)
            count += len(keys)
            if cursor == b"0": break
    except Exception:
        pass
        
    data = {
         "status": "running",
         "lab_mode": os.getenv("LAB_MODE", "false").lower() == "true",
         "active_personas": count
    }
    return success_response(data)
