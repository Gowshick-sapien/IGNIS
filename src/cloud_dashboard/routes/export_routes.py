"""IGNIS Export & Settings API & UI Routes (Phase G6).

Provides endpoints for format exports, format capabilities queries, reproducibility bundle generation,
and the Settings & Preferences UI.
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, Request, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from ..schemas import ExportFormatCapabilityResponse, ReproducibilityBundleResponse, ErrorResponse
from ..services.result_manager import ResultManager
from ..services.export_service import ExportService
from ..services.bundle_service import BundleService

logger = logging.getLogger("export_routes")
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

export_router = APIRouter(tags=["Export & Publication"])


def get_result_manager(request: Request) -> ResultManager:
    """Dependency helper retrieving ResultManager instance."""
    rm = getattr(request.app.state, "result_manager", None)
    if not rm:
        repo_mgr = getattr(request.app.state, "repository_manager", None)
        rm = ResultManager(
            export_service=ExportService(repository_manager=repo_mgr),
            bundle_service=BundleService(repository_manager=repo_mgr)
        )
    return rm


# ============================================================================
# UI View Route
# ============================================================================

@export_router.get("/settings", response_class=HTMLResponse)
async def get_settings_page(request: Request):
    """Renders the Settings & Export Preferences page."""
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"active_page": "settings", "active_tab": "settings"}
    )


# ============================================================================
# REST API Endpoints (v1)
# ============================================================================

@export_router.get(
    "/api/v1/experiment/export/formats",
    response_model=ExportFormatCapabilityResponse
)
async def get_export_formats(rm: ResultManager = Depends(get_result_manager)):
    """READ-ONLY: Query supported export format capabilities and optional dependency status."""
    caps = rm.get_export_capabilities()
    return {"status": "success", "data": caps}


@export_router.get(
    "/api/v1/experiment/export/{experiment_id}",
    responses={
        404: {"model": ErrorResponse},
        501: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def export_experiment(
    experiment_id: str,
    format: str = Query("zip", description="Target format: md, html, csv, json, zip, pdf, docx"),
    rm: ResultManager = Depends(get_result_manager)
):
    """Stream experiment export file download in the specified format."""
    try:
        file_path = rm.export(experiment_id, format)
        filename = os.path.basename(file_path)
        
        # Determine media type for FileResponse
        media_types = {
            "md": "text/markdown",
            "html": "text/html",
            "csv": "text/csv",
            "json": "application/json",
            "zip": "application/zip",
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }
        fmt_key = format.lower().strip()
        media_type = media_types.get(fmt_key, "application/octet-stream")

        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except NotImplementedError as opt_err:
        # Graceful HTTP 501 EXPORT_UNAVAILABLE response for missing optional dependencies
        raise HTTPException(status_code=501, detail=str(opt_err))
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        logger.error(f"Error exporting experiment {experiment_id} in format {format}: {e}")
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


@export_router.post(
    "/api/v1/experiment/{experiment_id}/reproduce",
    response_model=ReproducibilityBundleResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def create_reproducibility_bundle(
    experiment_id: str,
    rm: ResultManager = Depends(get_result_manager)
):
    """Generate or refresh self-contained reproducibility bundle ZIP for an experiment."""
    try:
        bundle_data = rm.build_reproducibility_bundle(experiment_id)
        return {"status": "success", "data": bundle_data}
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        logger.error(f"Error building reproducibility bundle for {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compile reproducibility bundle: {str(e)}")


@export_router.get("/api/v1/experiment/{experiment_id}/download-bundle")
async def download_reproducibility_bundle(
    experiment_id: str,
    rm: ResultManager = Depends(get_result_manager)
):
    """Direct stream download endpoint for reproducibility bundle ZIP."""
    try:
        bundle_data = rm.build_reproducibility_bundle(experiment_id)
        file_path = bundle_data["bundle_path"]
        filename = os.path.basename(file_path)
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed downloading reproducibility bundle: {str(e)}")
