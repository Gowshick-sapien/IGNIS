import logging
from typing import Optional, List
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("simulation_routes")

simulation_router = APIRouter(tags=["simulation"])


class StartSimulationRequest(BaseModel):
    zone_id: str = Field(..., description="Target Zone ID, e.g. '4A', '4B', '4C'")
    scenario_id: str = Field(..., description="Scenario identifier: 'S1', 'S2', 'S3', 'S4', 'S6'")


class StopSimulationRequest(BaseModel):
    zone_id: Optional[str] = Field(None, description="Target Zone ID to stop. If omitted, all running simulations are stopped.")


@simulation_router.post("/api/simulation/start")
async def start_simulation(request: Request, body: StartSimulationRequest):
    """
    Triggers a real-time scenario simulation on edge nodes for the specified zone.
    Supported scenarios:
      - S1: Normal Day (gentle natural drift, stays GREEN)
      - S2: Slow-Building Risk (gradual drying trend, reaches YELLOW)
      - S3: Sudden Ignition (fire outbreak on middle node, escalates to ORANGE/RED)
      - S4: Single Sensor Fault (gas sensor anomaly, clamped to YELLOW by guard)
      - S6: Lateral Spread (fire in zone with wind blowing south toward neighbor)
    """
    sim_service = getattr(request.app.state, "simulation_service", None)
    if not sim_service:
        raise HTTPException(status_code=503, detail="SimulationService is not initialized on cloud dashboard.")

    zone_id = body.zone_id.upper()
    scenario_id = body.scenario_id.upper()

    res = sim_service.start_scenario(zone_id=zone_id, scenario_id=scenario_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message", "Failed to start simulation."))

    logger.info(f"Started simulation {scenario_id} on Zone {zone_id} via API")
    return res


@simulation_router.post("/api/simulation/stop")
async def stop_simulation(request: Request, body: StopSimulationRequest):
    """
    Stops running scenario simulations and resets edge nodes in the target zone (or all zones) back to baseline.
    """
    sim_service = getattr(request.app.state, "simulation_service", None)
    if not sim_service:
        raise HTTPException(status_code=503, detail="SimulationService is not initialized on cloud dashboard.")

    if body.zone_id:
        res = sim_service.stop_scenario(body.zone_id.upper())
    else:
        sim_service.stop_all()
        res = {"status": "stopped", "message": "All simulation scenarios stopped and reset to baseline."}

    return res


@simulation_router.get("/api/simulation/status")
async def get_simulation_status(request: Request, zone_id: Optional[str] = None):
    """
    Returns current simulation execution status and step progress for all zones or a specific zone.
    """
    sim_service = getattr(request.app.state, "simulation_service", None)
    if not sim_service:
        if zone_id:
            return {"zone_id": zone_id.upper(), "status": "idle", "running_scenario": None, "current_step": 0, "total_steps": 0, "is_active": False}
        return [
            {"zone_id": "4A", "status": "idle", "running_scenario": None, "current_step": 0, "total_steps": 0, "is_active": False},
            {"zone_id": "4B", "status": "idle", "running_scenario": None, "current_step": 0, "total_steps": 0, "is_active": False},
            {"zone_id": "4C", "status": "idle", "running_scenario": None, "current_step": 0, "total_steps": 0, "is_active": False},
        ]

    if zone_id:
        return sim_service.get_status(zone_id.upper())
    return sim_service.get_all_status()
