import os
import uuid
import time
import json
import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import paho.mqtt.client as mqtt

logger = logging.getLogger("cloud_dashboard_routes")
router = APIRouter()

class AdvisoryCommandRequest(BaseModel):
    command: str
    parameters: dict
    issued_by: str = "regional_operator"
    ttl: int = 300
    zone_id: str = "4B"

@router.get("/", response_class=HTMLResponse)
async def read_index():
    template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Cloud dashboard index template not found.")

@router.get("/api/zones")
async def get_zones(request: Request):
    db = request.app.state.db
    return db.get_all_zone_states()

@router.get("/api/lateral-timeline")
async def get_lateral_timeline(request: Request, minutes: int = 10):
    db = request.app.state.db
    return db.get_lateral_events(minutes)

@router.get("/api/snapshot")
async def get_snapshot(request: Request, zone_id: str = "4B"):
    """Statelessly aggregates snapshot details by querying InfluxDB."""
    db = request.app.state.db
    
    # Check InfluxDB health
    influx_health = db.ping_influx()
    if not influx_health:
        return {
            "database_health": "OFFLINE",
            "zone_state": {"zone_id": zone_id, "state": "UNKNOWN", "whi": 0.0, "is_state_clamped": False, "override_active": False, "timestamp": ""},
            "edge_readings": [],
            "system_health": {
                "Cloud_Broker": "UNKNOWN",
                "InfluxDB": "OFFLINE",
                "Fog_Node": "OFFLINE",
                "Cloud_Ingestor": "OFFLINE"
            },
            "alerts": [],
            "action_logs": [],
            "audit_logs": [],
            "performance_metrics": {
                "fog_to_cloud_latency": 0.0,
                "cloud_ingestion_latency": 0.0,
                "influx_write_latency": 0.0,
                "cloud_end_to_end_latency": 0.0,
                "telemetry_rate_pps": 0.0,
                "messages_archived": 0
            }
        }

    # Query metrics statelessly
    zone_state = db.get_latest_zone_state(zone_id)
    edge_readings = db.get_latest_edge_telemetry(zone_id)
    system_health = db.get_system_health(zone_id)
    logs = db.get_recent_alerts_and_logs(zone_id, limit=15)
    performance = db.get_latest_performance_metrics(zone_id)
    
    # Query Cloud Broker health (try a quick socket ping or return active)
    system_health["Cloud_Broker"] = "ONLINE" # Assume online, if we publish successfully
    
    return {
        "database_health": "ONLINE",
        "zone_state": zone_state,
        "edge_readings": edge_readings,
        "system_health": system_health,
        "alerts": logs["alerts"],
        "action_logs": logs["action_logs"],
        "audit_logs": logs["audit_logs"],
        "performance_metrics": performance
    }

@router.get("/api/history")
async def get_history(request: Request, zone_id: str = "4B", minutes: int = 15, season: str = "summer"):
    """Queries time-series averages and merges them with local historical baseline overlays."""
    db = request.app.state.db
    
    # 1. Fetch Influx historical data
    ts_data = db.get_historical_chart_data(zone_id, minutes)
    
    # 2. Fetch baseline data
    baseline = db.get_seasonal_baseline(season)
    
    return {
        "historical_telemetry": ts_data,
        "baseline_profile": baseline
    }

@router.post("/api/advisory")
async def post_advisory(request: Request, body: AdvisoryCommandRequest):
    """Routes advisory commands from NOC dashboard to Fog Node using a one-off publish client."""
    zone_id = body.zone_id
    
    # Generate monotonic sequence number in-memory
    request.app.state.command_sequence += 1
    seq = request.app.state.command_sequence
    cmd_id = str(uuid.uuid4())
    
    # Formulate secure robust payload
    payload = {
        "command_id": cmd_id,
        "sequence_number": seq,
        "zone_id": zone_id,
        "issued_by": body.issued_by,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ttl": body.ttl,
        "command": body.command,
        "parameters": body.parameters
    }
    
    # Perform transient publication
    mqtt_host = os.environ.get("CLOUD_MQTT_HOST", "localhost")
    mqtt_port = int(os.environ.get("CLOUD_MQTT_PORT", 1884))
    
    try:
        client = mqtt.Client(client_id=f"cloud_dashboard_publisher_{uuid.uuid4().hex[:6]}")
        client.connect(mqtt_host, mqtt_port, 10)
        
        # Publish
        advisory_topic = f"ignis/v1/advisory/zone/{zone_id}/command"
        client.publish(advisory_topic, json.dumps(payload))
        client.disconnect()
        
        # Write initial PENDING state in Audit logs
        db = request.app.state.db
        if db.ping_influx():
            # InfluxDB is accessible. Connect/write record
            # We can write from route directly since we have the db reference
            write_api = db.client.write_api()
            # pyrefly: ignore [missing-import]
            from influxdb_client import Point
            p = Point("audit_logs") \
                .tag("zone_id", zone_id) \
                .tag("command_id", cmd_id) \
                .field("command", body.command) \
                .field("issued_by", body.issued_by) \
                .field("status", "PENDING") \
                .field("error_reason", "") \
                .field("details", f"Dispatched command {body.command}. Awaiting response.")
            write_api.write(bucket=db.bucket, org=db.org, record=p)
            
        logger.info(f"Published advisory override {body.command} to {advisory_topic}")
        return {"status": "SENT", "command_id": cmd_id}
    except Exception as e:
        logger.error(f"Failed to publish advisory command: {e}")
        
        # Write failure audit record to database
        try:
            db = request.app.state.db
            if db.ping_influx():
                write_api = db.client.write_api()
                # pyrefly: ignore [missing-import]
                from influxdb_client import Point
                p = Point("audit_logs") \
                    .tag("zone_id", zone_id) \
                    .tag("command_id", cmd_id) \
                    .field("command", body.command) \
                    .field("issued_by", body.issued_by) \
                    .field("status", "FAILED") \
                    .field("error_reason", str(e)) \
                    .field("details", "Failed during MQTT routing dispatch.")
                write_api.write(bucket=db.bucket, org=db.org, record=p)
        except Exception:
            pass
            
        raise HTTPException(status_code=503, detail=f"Advisory command routing failed: {e}")
