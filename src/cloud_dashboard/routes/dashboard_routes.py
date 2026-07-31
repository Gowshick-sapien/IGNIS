"""IGNIS Cloud Dashboard Pages & Data Routes (Phase G2).

Serves dashboard page views (/experiments, /reports, /charts, /scenarios) and reporting APIs.
"""

import os
import glob
import sys
import json
import logging
from typing import Dict, List, Any
import yaml
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger("dashboard_routes")

dashboard_router = APIRouter(tags=["dashboard"])

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def _get_workspace_dir(request: Request) -> str:
    pm = getattr(request.app.state, "process_manager", None)
    if pm:
        return pm.workspace_dir
    return os.getcwd()


@dashboard_router.get("/experiments", response_class=HTMLResponse)
async def experiments_page(request: Request):
    """Experiment Control Center page."""
    return templates.TemplateResponse(
        request=request,
        name="experiments.html",
        context={"active_page": "experiments"}
    )


@dashboard_router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Historical Report Browser page (default sorted Newest First)."""
    workspace_dir = _get_workspace_dir(request)
    reports = _discover_reports(workspace_dir)
    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={"active_page": "reports", "reports": reports}
    )


@dashboard_router.get("/charts", response_class=HTMLResponse)
async def charts_page(request: Request):
    """Interactive Chart Gallery page."""
    return templates.TemplateResponse(
        request=request,
        name="charts.html",
        context={"active_page": "charts"}
    )


@dashboard_router.get("/scenarios", response_class=HTMLResponse)
async def scenarios_page(request: Request):
    """Read-Only Scenario Browser page."""
    workspace_dir = _get_workspace_dir(request)
    scenarios = _parse_scenarios_readonly(workspace_dir)
    return templates.TemplateResponse(
        request=request,
        name="scenarios.html",
        context={"active_page": "scenarios", "scenarios": scenarios}
    )


@dashboard_router.get("/api/v1/reports/list")
async def list_reports_api(request: Request):
    """API returning all discovered reports sorted Newest First."""
    workspace_dir = _get_workspace_dir(request)
    reports = _discover_reports(workspace_dir)
    return {"status": "success", "data": {"reports": reports}}


@dashboard_router.get("/api/v1/reports/{report_id}")
async def get_report_api(report_id: str, request: Request):
    """Fetch content of specific report by ID."""
    workspace_dir = _get_workspace_dir(request)
    reports = _discover_reports(workspace_dir)
    target = next((r for r in reports if r["id"] == report_id), None)
    if not target:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")
    
    file_path = target["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Report file not found on disk.")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "data": {"report": target, "content": content}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading report: {e}")


def _discover_reports(workspace_dir: str) -> List[Dict[str, Any]]:
    """Discovers HTML and Markdown reports across results/, reports/, docs/, and experiment_repository/, sorting them Newest First."""
    reports_list = []
    
    search_dirs = [
        os.path.join(workspace_dir, "results"),
        os.path.join(workspace_dir, "reports"),
        os.path.join(workspace_dir, "experiment_repository"),
    ]
    
    found_paths = set()
    for sdir in search_dirs:
        if os.path.exists(sdir):
            for ext in ("*.html", "*.md"):
                # Top level files
                for filepath in glob.glob(os.path.join(sdir, ext)):
                    found_paths.add(os.path.abspath(filepath))
                # Recursive subfolder files
                for filepath in glob.glob(os.path.join(sdir, "**", ext), recursive=True):
                    found_paths.add(os.path.abspath(filepath))
    
    for path in found_paths:
        fname = os.path.basename(path)
        # Exclude hidden files or pure developer documentation specs
        if fname.startswith(".") or fname.startswith("AGENTS") or fname == "README.md":
            continue
            
        mtime = os.path.getmtime(path)
        mtime_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        mtime_str = mtime_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        rel_path = os.path.relpath(path, workspace_dir).replace("\\", "/")
        report_id = rel_path.replace("/", "_").replace(".", "_")
        
        reports_list.append({
            "id": report_id,
            "filename": fname,
            "relative_path": rel_path,
            "file_path": path,
            "format": "html" if fname.endswith(".html") else "markdown",
            "mtime": mtime,
            "mtime_str": mtime_str
        })
    
    # Sort NEWEST FIRST (descending mtime)
    reports_list.sort(key=lambda r: r["mtime"], reverse=True)
    return reports_list


def _parse_scenarios_readonly(workspace_dir: str) -> List[Dict[str, Any]]:
    """Strictly parses YAML scenario files for display (Read-Only)."""
    scenarios_dir = os.path.join(workspace_dir, "scenarios")
    scenarios_list = []
    
    if not os.path.exists(scenarios_dir):
        return scenarios_list
    
    yaml_files = sorted(glob.glob(os.path.join(scenarios_dir, "*.yaml")))
    for ypath in yaml_files:
        s_id = os.path.splitext(os.path.basename(ypath))[0].upper()
        try:
            with open(ypath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            
            scenarios_list.append({
                "id": s_id,
                "file_name": os.path.basename(ypath),
                "name": data.get("name", s_id),
                "description": data.get("description", "No description provided."),
                "assertions": data.get("assertions", []),
                "raw_yaml": yaml.dump(data, sort_keys=False)
            })
        except Exception as e:
            logger.warning(f"Error parsing scenario {ypath}: {e}")
            scenarios_list.append({
                "id": s_id,
                "file_name": os.path.basename(ypath),
                "name": s_id,
                "description": f"YAML Parse Error: {e}",
                "assertions": [],
                "raw_yaml": ""
            })
            
    return scenarios_list
