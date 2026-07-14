import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load configurations
load_dotenv()

from .database import CloudDashboardDB
from .routes import router

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cloud_dashboard_app")

# Lifespan manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Instantiate read-only DB connection
    db = CloudDashboardDB()
    
    # Try connecting with exponential backoff on startup
    connected = False
    retry_delay = 2
    
    while not connected:
        try:
            db.connect()
            connected = True
            logger.info("Cloud Dashboard successfully connected to InfluxDB.")
        except Exception as e:
            logger.warning(f"Dashboard failed to connect to InfluxDB: {e}. Retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 10)
            
    # 2. Store references in app state
    app.state.db = db
    app.state.command_sequence = 100 # Sequence numbers start at 100
    
    logger.info("Central Cloud Dashboard initialized.")
    yield
    
    # Clean shutdown
    db.close()
    logger.info("Central Cloud Dashboard shut down clean.")

import time

# Create FastAPI app
app = FastAPI(
    title="IGNIS Central Operations NOC Dashboard",
    description="Regional Central Monitoring and Override Console",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)
