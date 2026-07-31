"""IGNIS Experiment Execution & Lifecycle API Routes (Phase G2).

Versioned REST HTTP API endpoints (/api/v1/experiment/*) for experiment control.
"""

import os
import json
import logging
from typing import Any, Dict
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse

from ..schemas import (
    ExperimentRunRequest,
    ExperimentStatusResponse,
    ExperimentLogResponse,
    ExperimentLoadRequest,
    ErrorResponse,
)
from ..services.process_manager import ProcessManager, InvalidStateTransition

logger = logging.getLogger("experiment_routes")

experiments_router = APIRouter(prefix="/api/v1/experiment", tags=["experiment"])


def _error_response(status_code: int, error_code: str, message: str, details: Dict[str, Any] = None) -> JSONResponse:
    payload = ErrorResponse(error=error_code, message=message, details=details).model_dump()
    return JSONResponse(status_code=status_code, content=payload)


def _get_process_manager(request: Request) -> ProcessManager:
    pm: ProcessManager = getattr(request.app.state, "process_manager", None)
    if pm is None:
        # Fallback singleton instantiation
        pm = ProcessManager()
        request.app.state.process_manager = pm
    return pm


@experiments_router.post("/run", response_model=Dict[str, Any])
async def run_experiment(req: ExperimentRunRequest, request: Request):
    """Launch experiment subprocess with specified configuration."""
    pm = _get_process_manager(request)
    try:
        res = pm.start_experiment(
            trials=req.trials,
            seed=req.seed,
            clean=req.clean,
            scenarios=req.scenarios
        )
        return {"status": "success", "data": res}
    except InvalidStateTransition as e:
        status_info = pm.get_status()
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_code="ExperimentAlreadyRunning" if status_info["state"] in ("RUNNING", "STARTING") else "InvalidStateTransition",
            message=str(e),
            details=status_info
        )
    except Exception as e:
        logger.error(f"Error starting experiment: {e}")
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="SubprocessExecutionError",
            message=str(e)
        )


@experiments_router.post("/stop", response_model=Dict[str, Any])
async def stop_experiment(request: Request):
    """Stop running experiment subprocess."""
    pm = _get_process_manager(request)
    try:
        res = pm.stop_experiment()
        return {"status": "success", "data": res}
    except InvalidStateTransition as e:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_code="InvalidStateTransition",
            message=str(e),
            details=pm.get_status()
        )


@experiments_router.post("/pause", response_model=Dict[str, Any])
async def pause_experiment(request: Request):
    """Pause running experiment cooperatively."""
    pm = _get_process_manager(request)
    try:
        res = pm.pause_experiment()
        return {"status": "success", "data": res}
    except InvalidStateTransition as e:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_code="InvalidStateTransition",
            message=str(e),
            details=pm.get_status()
        )


@experiments_router.post("/resume", response_model=Dict[str, Any])
async def resume_experiment(request: Request):
    """Resume paused experiment execution."""
    pm = _get_process_manager(request)
    try:
        res = pm.resume_experiment()
        return {"status": "success", "data": res}
    except InvalidStateTransition as e:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_code="InvalidStateTransition",
            message=str(e),
            details=pm.get_status()
        )


@experiments_router.post("/restart", response_model=Dict[str, Any])
async def restart_experiment(req: ExperimentRunRequest, request: Request):
    """Stop current experiment (if active), clear state, and launch a new experiment run."""
    pm = _get_process_manager(request)
    try:
        res = pm.restart_experiment(
            trials=req.trials,
            seed=req.seed,
            clean=req.clean,
            scenarios=req.scenarios
        )
        return {"status": "success", "data": res}
    except Exception as e:
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="SubprocessExecutionError",
            message=str(e)
        )


@experiments_router.post("/clean", response_model=Dict[str, Any])
async def clean_results(request: Request):
    """Clean transient experiment results directory."""
    pm = _get_process_manager(request)
    try:
        res = pm.clean_results()
        return {"status": "success", "data": res}
    except InvalidStateTransition as e:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_code="InvalidStateTransition",
            message=str(e),
            details=pm.get_status()
        )


@experiments_router.post("/load", response_model=Dict[str, Any])
async def load_results(req: ExperimentLoadRequest, request: Request):
    """Import external or archived simulation metrics into active view context."""
    pm = _get_process_manager(request)
    try:
        res = pm.load_results(req.path)
        return {"status": "success", "data": res}
    except FileNotFoundError as e:
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="FileNotFound",
            message=str(e)
        )
    except InvalidStateTransition as e:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_code="InvalidStateTransition",
            message=str(e),
            details=pm.get_status()
        )


@experiments_router.get("/status", response_model=Dict[str, Any])
async def get_experiment_status(request: Request):
    """Fetch current ProcessManager state machine status."""
    pm = _get_process_manager(request)
    return {"status": "success", "data": pm.get_status()}


@experiments_router.get("/results", response_model=Dict[str, Any])
async def get_experiment_results(request: Request):
    """Fetch current active metrics.json output."""
    pm = _get_process_manager(request)
    metrics_path = os.path.join(pm.results_dir, "metrics.json")
    if not os.path.exists(metrics_path):
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ExperimentNotFound",
            message="No active or loaded metrics.json available."
        )
    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"status": "success", "data": data}
    except Exception as e:
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="FileReadError",
            message=f"Error reading metrics.json: {e}"
        )


@experiments_router.get("/logs", response_model=Dict[str, Any])
async def get_experiment_logs(tail: int = 100, request: Request = None):
    """Fetch trailing lines from active experiment log file."""
    pm = _get_process_manager(request)
    lines, req_tail, total = pm.get_logs(tail=tail)
    log_resp = ExperimentLogResponse(lines=lines, tail=req_tail, total_lines=total)
    return {"status": "success", "data": log_resp.model_dump()}
