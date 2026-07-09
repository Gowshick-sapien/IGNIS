import json
import asyncio
import logging
import queue
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger("control_center_routes")
router = APIRouter()

class ScenarioRequest(BaseModel):
    scenario_id: str

@router.get("/", response_class=HTMLResponse)
async def read_index():
    # Read and serve the index.html template file directly
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Index template not found.")

@router.get("/api/snapshot")
async def get_snapshot(request: Request):
    """Returns the current state snapshot of all cached zones and edge nodes."""
    return request.app.state.listener.get_snapshot()

@router.get("/api/scenario/status")
async def get_scenario_status(request: Request):
    """Returns status of the scenario service."""
    return request.app.state.scenario_service.get_status()

@router.post("/api/scenario/start")
async def start_scenario(request: Request, body: ScenarioRequest):
    """Triggers the specified scenario S1-S4."""
    success = request.app.state.scenario_service.start_scenario(body.scenario_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to start scenario: {body.scenario_id}")
    return {"status": "started", "scenario_id": body.scenario_id}

@router.post("/api/scenario/stop")
async def stop_scenario(request: Request):
    """Stops any running scenario and resets edge nodes."""
    request.app.state.scenario_service.stop_scenario()
    return {"status": "stopped"}

@router.get("/api/stream")
async def stream_updates(request: Request):
    """Server-Sent Events endpoint pushing real-time MQTT message frames to the dashboard."""
    client_queue = queue.Queue(maxsize=100)
    
    # Register this client queue with the MQTT background listener
    request.app.state.listener.register_sse_queue(client_queue)
    
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    logger.info("SSE client disconnected.")
                    break
                
                try:
                    # Non-blocking fetch
                    msg = client_queue.get_nowait()
                    yield f"data: {json.dumps(msg)}\n\n"
                except queue.Empty:
                    # Small sleep to yield control to event loop
                    await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            logger.info("SSE streaming task cancelled.")
        finally:
            # Clean up client registration
            request.app.state.listener.unregister_sse_queue(client_queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

import os
