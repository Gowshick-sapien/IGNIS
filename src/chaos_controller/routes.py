import time
import threading
from typing import Optional, Dict
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from src.chaos_controller.docker_adapter import DockerAdapter

router = APIRouter(prefix="/api/chaos")
adapter = DockerAdapter()

# In-memory status tracker for the status endpoint
chaos_status = {
    "disconnected_zones": {},  # zone_id -> {disconnected_at: str, duration_sec: int}
    "killed_containers": {}    # container_name -> {killed_at: str, duration_sec: int}
}
status_lock = threading.Lock()

class DisconnectCloudRequest(BaseModel):
    zone_id: str
    duration_sec: Optional[int] = 0

class RestoreCloudRequest(BaseModel):
    zone_id: str

class KillContainerRequest(BaseModel):
    container_name: str
    duration_sec: Optional[int] = 0

class RestartContainerRequest(BaseModel):
    container_name: str

def delayed_reconnect(zone_id: str, container_name: str, duration_sec: int):
    time.sleep(duration_sec)
    adapter.reconnect(container_name, "cloud-net")
    with status_lock:
        if zone_id in chaos_status["disconnected_zones"]:
            del chaos_status["disconnected_zones"][zone_id]

def delayed_restart(container_name: str, duration_sec: int):
    time.sleep(duration_sec)
    adapter.restart(container_name)
    with status_lock:
        if container_name in chaos_status["killed_containers"]:
            del chaos_status["killed_containers"][container_name]

@router.post("/disconnect_cloud")
def disconnect_cloud(req: DisconnectCloudRequest, background_tasks: BackgroundTasks):
    zone_id = req.zone_id.upper()
    container_name = f"ignis-fog-node-{zone_id.lower()}"
    
    res = adapter.disconnect(container_name, "cloud-net")
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["details"])
        
    with status_lock:
        chaos_status["disconnected_zones"][zone_id] = {
            "disconnected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_sec": req.duration_sec
        }
        
    if req.duration_sec > 0:
        background_tasks.add_task(delayed_reconnect, zone_id, container_name, req.duration_sec)
        
    return res

@router.post("/restore_cloud")
def restore_cloud(req: RestoreCloudRequest):
    zone_id = req.zone_id.upper()
    container_name = f"ignis-fog-node-{zone_id.lower()}"
    
    res = adapter.reconnect(container_name, "cloud-net")
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["details"])
        
    with status_lock:
        if zone_id in chaos_status["disconnected_zones"]:
            del chaos_status["disconnected_zones"][zone_id]
            
    return res

@router.post("/kill_container")
def kill_container(req: KillContainerRequest, background_tasks: BackgroundTasks):
    container_name = req.container_name
    
    res = adapter.kill(container_name)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["details"])
        
    with status_lock:
        chaos_status["killed_containers"][container_name] = {
            "killed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_sec": req.duration_sec
        }
        
    if req.duration_sec > 0:
        background_tasks.add_task(delayed_restart, container_name, req.duration_sec)
        
    return res

@router.post("/restart_container")
def restart_container(req: RestartContainerRequest):
    container_name = req.container_name
    
    res = adapter.restart(container_name)
    if not res["success"]:
        raise HTTPException(status_code=400, detail=res["details"])
        
    with status_lock:
        if container_name in chaos_status["killed_containers"]:
            del chaos_status["killed_containers"][container_name]
            
    return res

@router.get("/status")
def get_status():
    with status_lock:
        return dict(chaos_status)
