import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .mqtt_listener import MQTTListener
from .scenario_service import ScenarioService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("control_center_app")

# Fetch configuration from environment
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
ZONE_ID = os.environ.get("ZONE_ID", "4B")

# Lifespan manager for startup/shutdown actions
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Instantiate services
    listener = MQTTListener(mqtt_host=MQTT_HOST, mqtt_port=MQTT_PORT)
    scenario_orchestrator = ScenarioService(mqtt_host=MQTT_HOST, mqtt_port=MQTT_PORT, zone_id=ZONE_ID)
    
    # 2. Connect and start services
    listener.start()
    scenario_orchestrator.connect()
    
    # 3. Store references in app state for use in routes
    app.state.listener = listener
    app.state.scenario_service = scenario_orchestrator
    
    logger.info("Control Center Services initialized.")
    yield
    
    # 4. Clean shutdown
    scenario_orchestrator.stop_scenario()
    scenario_orchestrator.disconnect()
    listener.stop()
    logger.info("Control Center Services shut down clean.")

# Create FastAPI app
app = FastAPI(
    title="IGNIS Range Forest Control Center",
    description="Real-time localized wildfire warning feed",
    version="1.0.0",
    lifespan=lifespan
)

# Import routes to register them (routes.py will import app from here, or we import and include routes router)
from .routes import router
app.include_router(router)
