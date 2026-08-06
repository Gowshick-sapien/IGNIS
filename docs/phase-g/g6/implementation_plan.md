# Phase G6 — Export, Publication & Reproducibility Bundles: Sub-Phase Implementation Plan

Phase G6 completes Phase G by equipping IGNIS with a multi-format export service (`ExportService`), an automated reproducibility bundle generator (`BundleService`), versioned export and publication REST endpoints, and a Settings & Preferences UI (`settings.html`).

---

## Overview & Objectives

Following Phase G1 (Interactive HTML Reporting), Phase G2 (Subprocess Lifecycle FSM), Phase G3 (Live Progress Streaming), Phase G4 (Experiment Repository & SQLite Indexing), and Phase G5 (Analytics, Comparison & Regression Detection), Phase G6 enables one-click publication and complete auditability of IGNIS research artifacts.

### Key Objectives
1. **Unified Export Service (`ExportService`)**: Create `src/cloud_dashboard/services/export_service.py` with a single public interface `export(experiment_id, format)`. Stream artifacts in Markdown (`.md`), interactive HTML (`.html`), tabular CSV (`.csv`), machine-readable JSON (`.json`), complete ZIP archive (`.zip`), and optional PDF/DOCX formats.
2. **Streaming Response Memory Protection**: Use `FileResponse` / `StreamingResponse` with chunked file iterators for ZIP archives and bundles to prevent loading large files into server memory.
3. **HTML-to-PDF Visual Parity**: Convert PDF outputs from HTML using `weasyprint` (`HTML(string=html_content).write_pdf()`) to guarantee visual identity between interactive HTML reports and PDF documents.
4. **Graceful Optional Dependency Handling**: Implement feature degradation for optional PDF (`weasyprint`) and DOCX (`python-docx`) libraries. If absent, the API returns HTTP 501 (`EXPORT_UNAVAILABLE`) with helpful installation commands.
5. **Reproducibility Bundle Builder (`BundleService`)**: Create `src/cloud_dashboard/services/bundle_service.py` to compile self-contained reproduction archives containing raw data, metrics, manifests, progress logs, environment snapshots, scenario definitions, methodology docs, Git state patches (`git_state.json`), and tamper-verifiable `bundle_manifest.json` with SHA256 checksums.
6. **Idempotent Bundle Overwrite Policy**: Re-building a bundle regenerates and overwrites any existing bundle archive, returning the fresh, verified package.
7. **Full `ResultManager` Integration**: Wire `ExportService` and `BundleService` directly into `ResultManager` (`src/cloud_dashboard/services/result_manager.py`) as the public orchestrator API.
8. **Versioned Export REST API (`/api/v1/experiment/export/*`)**: Create `src/cloud_dashboard/routes/export_routes.py` with endpoints for format querying, artifact downloads, and reproducibility package generation.
9. **Settings Page Capability Matrix (`settings.html`)**: Build a clean Jinja2 template (`src/cloud_dashboard/templates/settings.html`) displaying export capability status tables (Format, Status, Reason), default execution settings, and quick export shortcuts.
10. **Navbar Navigation Finalization**: Update `src/cloud_dashboard/templates/partials/navbar.html` to include and highlight the **Settings** link.

---

## Technical Deliverables & File Manifest

| Action | Path | Description |
|---|---|---|
| **[NEW]** | [src/cloud_dashboard/services/export_service.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/export_service.py) | Multi-format exporter with unified `export(exp_id, format)` interface, export origin metadata, and streaming response support |
| **[NEW]** | [src/cloud_dashboard/services/bundle_service.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/bundle_service.py) | Reproducibility bundle builder capturing complete data, environment, scenarios, methodology, Git state, and `bundle_manifest.json` SHA256 checksums |
| **[MODIFY]** | [src/cloud_dashboard/services/result_manager.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/result_manager.py) | Wire `ExportService` and `BundleService` into `ResultManager` orchestrator |
| **[NEW]** | [src/cloud_dashboard/routes/export_routes.py](file:///d:/projects/IGNIS/src/cloud_dashboard/routes/export_routes.py) | REST API endpoints for multi-format export (`/api/v1/experiment/export/*`), bundle creation (`/reproduce`), and `/settings` view |
| **[NEW]** | [src/cloud_dashboard/templates/settings.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/settings.html) | Settings and export preferences page with format capability status table and one-click downloads |
| **[MODIFY]** | [src/cloud_dashboard/schemas.py](file:///d:/projects/IGNIS/src/cloud_dashboard/schemas.py) | Pydantic request/response schemas for export format queries and bundle status |
| **[MODIFY]** | [src/cloud_dashboard/templates/partials/navbar.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/partials/navbar.html) | Add Settings navigation item with active tab highlighting |
| **[MODIFY]** | [src/cloud_dashboard/app.py](file:///d:/projects/IGNIS/src/cloud_dashboard/app.py) | Register `ExportService` and `BundleService` in lifespan, wire to `ResultManager`, and mount export router |
| **[NEW]** | [docs/phase-g/g6/implementation_plan.md](file:///d:/projects/IGNIS/docs/phase-g/g6/implementation_plan.md) | Sub-phase G6 specification document in repository |
| **[NEW]** | [tests/test_export_service.py](file:///d:/projects/IGNIS/tests/test_export_service.py) | Unit tests for Markdown, HTML, CSV, JSON, ZIP generation, export metadata, and missing dependency handling |
| **[NEW]** | [tests/test_bundle_service.py](file:///d:/projects/IGNIS/tests/test_bundle_service.py) | Unit tests for reproducibility bundle directory structure, manifest inclusion, and Git state capture |
| **[NEW]** | [tests/test_bundle_integrity.py](file:///d:/projects/IGNIS/tests/test_bundle_integrity.py) | Integrity tests extracting generated bundles and verifying SHA256 checksums of every required file |
| **[NEW]** | [tests/test_export_api.py](file:///d:/projects/IGNIS/tests/test_export_api.py) | Integration tests for `/api/v1/experiment/export/{id}`, `/export/formats`, and `/reproduce` endpoints |
| **[NEW]** | [tests/test_settings_ui.py](file:///d:/projects/IGNIS/tests/test_settings_ui.py) | Integration tests for `/settings` view rendering and navbar active highlighting |

---

## Detailed Architectural Specifications

### 1. Export Matrix & Unified Interface

```python
class ExportService:
    def export(self, experiment_id: str, format: str) -> str:
        """Unified public interface for format exports."""
        fmt = format.lower()
        if fmt == "md": return self._export_markdown(experiment_id)
        elif fmt == "html": return self._export_html(experiment_id)
        elif fmt == "csv": return self._export_csv(experiment_id)
        elif fmt == "json": return self._export_json(experiment_id)
        elif fmt == "zip": return self._export_zip(experiment_id)
        elif fmt == "pdf": return self._export_pdf(experiment_id)
        elif fmt == "docx": return self._export_docx(experiment_id)
        else: raise ValueError(f"Unsupported format: {format}")
```

| Format | Service Method | Response Type | Origin Metadata Embedded | Required Library | Fallback Behavior when Library Absent |
|---|---|---|---|---|---|
| **Markdown** | `_export_markdown` | `FileResponse` | Header block | Standard Library | Always available |
| **HTML** | `_export_html` | `FileResponse` | Meta tags + Header | Standard Library | Always available (Plotly embedded) |
| **CSV** | `_export_csv` | `FileResponse` | CSV Header rows | `csv` (Standard Lib) | Always available (Summary + Metric rows) |
| **JSON** | `_export_json` | `FileResponse` | `export_metadata` block | `json` (Standard Lib) | Always available (Metrics + Manifest + Regression) |
| **ZIP** | `_export_zip` | `FileResponse` | ZIP comment | `zipfile` (Standard Lib) | Always available (Complete experiment folder zip) |
| **PDF** | `_export_pdf` | `FileResponse` | Footer / Metadata | `weasyprint` (Optional) | HTTP 501 `EXPORT_UNAVAILABLE`: `"PDF export requires weasyprint. Install with: pip install weasyprint"` |
| **DOCX** | `_export_docx` | `FileResponse` | Document Header | `python-docx` (Optional) | HTTP 501 `EXPORT_UNAVAILABLE`: `"DOCX export requires python-docx. Install with: pip install python-docx"` |

---

### 2. Reproducibility Bundle Layout (`BundleService`)

`BundleService.build_bundle(experiment_id)` generates a ZIP archive named `reproducibility_bundle_{exp_id}.zip` with the following internal layout:

```
reproducibility_bundle_exp-20260801T043524Z-b2d8/
 bundle_manifest.json               # Tamper verification manifest with file SHA256 hashes
 README.md                          # Comprehensive instructions, requirements, runtime & SHA256 hashes
 report/
    project_results_report.md      # Summary Markdown report
    report.html                    # Self-contained interactive HTML report (offline Plotly)
 charts/
    *.png                          # All 10 publication-ready Matplotlib PNG charts
 data/
    metrics.json                   # Aggregated statistics and confidence intervals
    raw_results.json               # Full raw trial execution events
    experiment_manifest.json       # Execution manifest and reproducibility hashes
    regression_summary.json        # Automatic regression analysis summary
    progress_events.jsonl          # Time-stamped progress execution log
 environment/
    requirements.txt               # Current Python package requirements
    docker-compose.yml             # System docker compose configuration snapshot
    platform_metadata.json         # OS, Python runtime, Docker daemon, and hostname
    git_state.json                 # Branch name, commit hash, commit message, git status, and diff patch
 scenarios/
    S1_baseline.yaml ... S7.yaml   # Exact YAML scenario definitions executed
 logs/
    experiment.log                 # Standard output & orchestrator execution log
 methodology/
     architecture.md                # System architecture document snapshot
     regression_rules.yaml          # Regression thresholds used during evaluation
```

---

### 3. Bundle Manifest Schema (`bundle_manifest.json`)

```json
{
  "bundle_version": "1.0.0",
  "bundle_time": "2026-08-01T12:00:00Z",
  "experiment_id": "exp-20260801T043524Z-b2d8",
  "bundle_generator_version": "phase-g-6.0",
  "checksums": {
    "data/metrics.json": "a1b2c3...",
    "data/raw_results.json": "d4e5f6...",
    "data/experiment_manifest.json": "7890ab...",
    "report/report.html": "cdef12...",
    "report/project_results_report.md": "345678..."
  }
}
```

---

### 4. REST API Contract

1. **`GET /api/v1/experiment/export/formats`**
   - Returns availability status of all export formats.

2. **`GET /api/v1/experiment/export/{experiment_id}?format={format}`**
   - Returns stream file download (`FileResponse`) with `Content-Disposition: attachment; filename="..."`.

3. **`POST /api/v1/experiment/{experiment_id}/reproduce`**
   - Compiles reproducibility bundle and streams `reproducibility_bundle_{experiment_id}.zip`.

4. **`GET /settings`**
   - Renders Jinja2 template `settings.html` containing format capability status table.
