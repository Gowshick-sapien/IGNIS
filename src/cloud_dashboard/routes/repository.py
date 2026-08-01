"""IGNIS Repository API & UI Routes (Phase G4).

Provides strictly READ-ONLY endpoints for searching, filtering, sorting, paginating, and viewing archived experiments.
"""

import os
import math
import logging
from typing import Optional

from fastapi import APIRouter, Request, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from ..schemas import RepositoryListResponse, ErrorResponse
from ..services.repository_manager import RepositoryManager

logger = logging.getLogger("repository_routes")
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

repository_router = APIRouter(tags=["Experiment Repository"])


def get_repository_manager(request: Request) -> RepositoryManager:
    """Dependency helper retrieving RepositoryManager singleton instance."""
    rm = getattr(request.app.state, "repository_manager", None)
    if not rm:
        # Fallback if state not attached
        workspace_dir = getattr(request.app.state, "workspace_dir", None)
        rm = RepositoryManager(workspace_dir=workspace_dir)
    return rm


# ============================================================================
# UI View Route
# ============================================================================

@repository_router.get("/repository", response_class=HTMLResponse)
async def get_repository_page(request: Request):
    """Renders the interactive Repository Browser timeline page."""
    return templates.TemplateResponse(
        request=request,
        name="repository.html",
        context={"active_page": "repository", "active_tab": "repository"}
    )


# ============================================================================
# READ-ONLY REST API Endpoints (v1)
# ============================================================================

@repository_router.get(
    "/api/v1/repository",
    response_model=RepositoryListResponse,
    responses={500: {"model": ErrorResponse}}
)
async def list_repository_experiments(
    request: Request,
    verdict: Optional[str] = Query(None, description="Filter by verdict (PASS, FAIL, INVALID)"),
    scenario: Optional[str] = Query(None, description="Filter by scenario ID (e.g., S3)"),
    commit: Optional[str] = Query(None, description="Filter by git commit hash prefix"),
    from_date: Optional[str] = Query(None, description="ISO8601 start date cutoff"),
    to_date: Optional[str] = Query(None, description="ISO8601 end date cutoff"),
    sort: str = Query("timestamp", description="Sort by timestamp, verdict, duration, or trials"),
    order: str = Query("desc", description="Sort direction: asc or desc"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    rm: RepositoryManager = Depends(get_repository_manager)
):
    """READ-ONLY: Search, filter, sort, and paginate historical archived experiment runs."""
    try:
        experiments, total = rm.list_experiments(
            verdict=verdict,
            scenario=scenario,
            commit=commit,
            from_date=from_date,
            to_date=to_date,
            sort=sort,
            order=order,
            page=page,
            page_size=page_size
        )
        total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

        return {
            "status": "success",
            "data": {
                "experiments": experiments,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        }
    except Exception as e:
        logger.error(f"Error querying repository list: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query repository index: {str(e)}")


@repository_router.get(
    "/api/v1/repository/{experiment_id}",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_repository_experiment_detail(
    experiment_id: str,
    rm: RepositoryManager = Depends(get_repository_manager)
):
    """READ-ONLY: Fetch full detailed metadata, scenario metrics, manifest hash, and report paths for an experiment."""
    detail = rm.get_experiment_detail(experiment_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found in repository.")
    return {"status": "success", "data": detail}


@repository_router.get("/api/v1/repository/{experiment_id}/report.html", response_class=HTMLResponse)
async def get_archived_html_report(
    experiment_id: str,
    rm: RepositoryManager = Depends(get_repository_manager)
):
    """READ-ONLY: Serve archived self-contained HTML report if present."""
    detail = rm.get_experiment_detail(experiment_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    
    html_path = os.path.join(detail["directory_path"], "report.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="Archived HTML report not found for this experiment.")

    return FileResponse(html_path, media_type="text/html")


@repository_router.get("/api/v1/repository/{experiment_id}/charts/{chart_name}")
async def get_archived_chart_image(
    experiment_id: str,
    chart_name: str,
    rm: RepositoryManager = Depends(get_repository_manager)
):
    """READ-ONLY: Serve archived Matplotlib chart image."""
    detail = rm.get_experiment_detail(experiment_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    
    chart_path = os.path.join(detail["directory_path"], "charts", chart_name)
    if not os.path.exists(chart_path):
        raise HTTPException(status_code=404, detail=f"Chart '{chart_name}' not found for experiment.")

    return FileResponse(chart_path, media_type="image/png")
