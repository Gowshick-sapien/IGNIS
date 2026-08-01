"""IGNIS Comparison API & UI Routes (Phase G5).

Provides endpoints for side-by-side experiment comparisons, metric diffs, and regression summaries.
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, Request, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..schemas import ComparisonResponse, ErrorResponse
from ..services.result_manager import ResultManager
from ..services.comparison_service import ComparisonService

logger = logging.getLogger("comparison_routes")
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

comparison_router = APIRouter(tags=["Experiment Comparison"])


def get_comparison_service(request: Request) -> ComparisonService:
    """Dependency helper retrieving ComparisonService instance."""
    cs = getattr(request.app.state, "comparison_service", None)
    if not cs:
        rm = getattr(request.app.state, "repository_manager", None)
        cs = ComparisonService(repository_manager=rm)
    return cs


def get_result_manager(request: Request) -> ResultManager:
    """Dependency helper retrieving ResultManager instance."""
    res_mgr = getattr(request.app.state, "result_manager", None)
    if not res_mgr:
        cs = get_comparison_service(request)
        res_mgr = ResultManager(comparison_service=cs)
    return res_mgr


# ============================================================================
# UI View Route
# ============================================================================

@comparison_router.get("/comparison", response_class=HTMLResponse)
async def get_comparison_page(request: Request):
    """Renders the interactive side-by-side Experiment Comparison page."""
    return templates.TemplateResponse(
        request=request,
        name="comparison.html",
        context={"active_page": "comparison", "active_tab": "comparison"}
    )


# ============================================================================
# READ-ONLY REST API Endpoints (v1)
# ============================================================================

@comparison_router.get(
    "/api/v1/experiments/compare",
    response_model=ComparisonResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def compare_experiments(
    a: str = Query(..., description="Experiment A ID (Baseline)"),
    b: str = Query(..., description="Experiment B ID (Target)"),
    cs: ComparisonService = Depends(get_comparison_service)
):
    """READ-ONLY: Calculate side-by-side metric diffs, verdict deltas, and CI overlap between two experiments."""
    try:
        data = cs.compare(exp_a_id=a, exp_b_id=b)
        return {"status": "success", "data": data}
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        logger.error(f"Error computing experiment comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compute experiment comparison: {str(e)}")


@comparison_router.get(
    "/api/v1/experiments/compare/summary",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_comparison_summary(
    a: str = Query(..., description="Experiment A ID (Baseline)"),
    b: str = Query(..., description="Experiment B ID (Target)"),
    cs: ComparisonService = Depends(get_comparison_service)
):
    """READ-ONLY: Get executive summary verdict and indicator diffs for two experiments."""
    try:
        full_comp = cs.compare(exp_a_id=a, exp_b_id=b)
        summary = {
            "experiment_a": a,
            "experiment_b": b,
            "verdict_delta": full_comp["verdict_delta"],
            "environment_diff": full_comp["environment_diff"]
        }
        return {"status": "success", "data": summary}
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        logger.error(f"Error computing comparison summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compute comparison summary: {str(e)}")
