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
from .services.comparison_service import ComparisonService
from .services.regression_detector import RegressionDetector
from .services.report_service import ReportService
from .services.export_service import ExportService
from .services.bundle_service import BundleService
from .services.result_manager import ResultManager
from .services.simulation_service import SimulationService
from .routes.experiments import experiments_router
from .routes.dashboard_routes import dashboard_router
from .routes.repository import repository_router
from .routes.comparison import comparison_router
from .routes.export_routes import export_router
from .routes.simulation_routes import simulation_router

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

    # 3. Fail-fast validation of config/regression_rules.yaml (Phase G5)
    regression_detector = RegressionDetector(repository_manager=repo_manager)
    try:
        regression_detector.validate_config()
        logger.info("RegressionDetector config validated successfully.")
    except Exception as rule_err:
        logger.error(f"Fail-fast configuration error in regression_rules.yaml: {rule_err}")
        raise rule_err

    app.state.regression_detector = regression_detector
    comparison_service = ComparisonService(repository_manager=repo_manager)
    app.state.comparison_service = comparison_service
    report_service = ReportService()
    app.state.report_service = report_service
    export_service = ExportService(repository_manager=repo_manager)
    app.state.export_service = export_service
    bundle_service = BundleService(repository_manager=repo_manager)
    app.state.bundle_service = bundle_service

    result_manager = ResultManager(
        report_service=report_service,
        comparison_service=comparison_service,
        regression_detector=regression_detector,
        export_service=export_service,
        bundle_service=bundle_service
    )
    app.state.result_manager = result_manager
    logger.info("Phase G6 Export and Publication services (ResultManager, ExportService, BundleService) registered in app.state.")

    # 4. Instantiate DB connection (graceful optional fallback)
    db = CloudDashboardDB()
    try:
        db.connect()
        logger.info("Cloud Dashboard connected to InfluxDB.")
    except Exception as e:
        logger.warning(f"InfluxDB not reachable during startup: {e}. Dashboard running in offline mode.")

    # 5. Instantiate SimulationService singleton for live multi-zone scenario injection
    simulation_service = SimulationService()
    app.state.simulation_service = simulation_service
    logger.info("SimulationService registered in app.state.")

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

    try:
        simulation_service.stop_all()
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
app.include_router(comparison_router)
app.include_router(export_router)
app.include_router(simulation_router)
app.include_router(router)
