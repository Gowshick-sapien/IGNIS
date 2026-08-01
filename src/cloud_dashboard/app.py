import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from .database import CloudDashboardDB
from .routes import router
from .services.process_manager import ProcessManager
from .services.repository_manager import RepositoryManager
from .routes.experiments import experiments_router
from .routes.dashboard_routes import dashboard_router
from .routes.repository import repository_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cloud_dashboard_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Instantiate ProcessManager singleton
    process_manager = ProcessManager()
    app.state.process_manager = process_manager
    logger.info("ProcessManager singleton registered in app.state.")

    # 2. Instantiate RepositoryManager singleton
    repo_manager = RepositoryManager()
    app.state.repository_manager = repo_manager
    logger.info("RepositoryManager singleton registered in app.state.")

    # 3. Instantiate DB connection (graceful optional fallback)
    db = CloudDashboardDB()
    try:
        db.connect()
        logger.info("Cloud Dashboard connected to InfluxDB.")
    except Exception as e:
        logger.warning(f"InfluxDB not reachable during startup: {e}. Dashboard running in offline mode.")

    app.state.db = db
    app.state.command_sequence = 100

    logger.info("IGNIS Cloud Dashboard initialized successfully.")
    yield

    # Clean shutdown
    if process_manager.state in ("RUNNING", "PAUSED", "PAUSING", "STARTING"):
        try:
            process_manager.stop_experiment()
        except Exception:
            pass

    db.close()
    logger.info("IGNIS Cloud Dashboard shut down clean.")


app = FastAPI(
    title="IGNIS Central Operations & Experimentation Dashboard",
    description="Regional Operations NOC & Research Control Center",
    version="2.0.0",
    lifespan=lifespan
)

# Mount static files if directory exists
os.makedirs("results", exist_ok=True)
os.makedirs("reports", exist_ok=True)
os.makedirs("experiment_repository", exist_ok=True)
os.makedirs("docs/phase-e/charts", exist_ok=True)

app.mount("/results", StaticFiles(directory="results"), name="results")
app.mount("/reports", StaticFiles(directory="reports"), name="reports")
app.mount("/experiment_repository", StaticFiles(directory="experiment_repository"), name="experiment_repository")

# Include Routers
app.include_router(experiments_router)
app.include_router(dashboard_router)
app.include_router(repository_router)
app.include_router(router)
