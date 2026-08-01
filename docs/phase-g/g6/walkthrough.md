# Phase G6 — Export, Publication & Reproducibility Bundles: Execution Walkthrough

Phase G6 completes Phase G by introducing multi-format export capabilities (`ExportService`), self-contained research reproducibility bundles (`BundleService`), versioned REST endpoints (`/api/v1/experiment/export/*`), and a Settings & Export Preferences UI (`settings.html`).

---

## 1. Accomplishments & Deliverables

### A. Multi-Format Export Service (`ExportService`)
- **[NEW] [src/cloud_dashboard/services/export_service.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/export_service.py)**:
  - Unified public interface `export(experiment_id, format)`.
  - Supports Markdown (`.md`), interactive HTML (`.html`), tabular CSV (`.csv`), machine-readable JSON (`.json`), ZIP archive (`.zip`), and optional PDF/DOCX formats.
  - Standardized origin metadata block (`System`, `Project Phase`, `Experiment ID`, `Export Time`, `Generator Version`) embedded into every export.
  - HTML-to-PDF rendering via `weasyprint` (`HTML(string=html_content).write_pdf()`) ensuring visual identity with interactive HTML reports.
  - Graceful HTTP 501 `EXPORT_UNAVAILABLE` fallback when optional libraries (`weasyprint` / `python-docx`) are absent.

### B. Reproducibility Bundle Builder (`BundleService`)
- **[NEW] [src/cloud_dashboard/services/bundle_service.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/bundle_service.py)**:
  - Compiles self-contained research reproduction ZIP archives (`reproducibility_bundle_{exp_id}.zip`).
  - Includes `bundle_manifest.json` containing SHA256 checksums of all included bundle files for tamper verification.
  - Includes detailed `README.md` documenting system requirements, Docker container images, scenario replay instructions, expected runtimes, and core artifact SHA256 checksums.
  - Includes full directory structure: `report/`, `charts/`, `data/`, `environment/` (`requirements.txt`, `docker-compose.yml`, `platform_metadata.json`, `git_state.json`), `scenarios/`, `logs/`, and `methodology/`.
  - Captures exact Git commit, branch name, status, and uncommitted patch diff (`git_state.json`).
  - Idempotent overwrite/regeneration policy.

### C. Public Orchestrator Integration (`ResultManager`)
- **[MODIFY] [src/cloud_dashboard/services/result_manager.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/result_manager.py)**:
  - Wired `export()`, `get_export_capabilities()`, and `build_reproducibility_bundle()` into `ResultManager`.

### D. REST API Endpoints & FastAPI App Registration
- **[NEW] [src/cloud_dashboard/routes/export_routes.py](file:///d:/projects/IGNIS/src/cloud_dashboard/routes/export_routes.py)**:
  - `GET /settings`: Renders Jinja2 template `settings.html`.
  - `GET /api/v1/experiment/export/formats`: Format capability matrix table endpoint.
  - `GET /api/v1/experiment/export/{experiment_id}`: Stream file download with `FileResponse` / `StreamingResponse`.
  - `POST /api/v1/experiment/{experiment_id}/reproduce`: Bundle creation and metadata response.
  - `GET /api/v1/experiment/{experiment_id}/download-bundle`: Direct stream download of bundle ZIP.
- **[MODIFY] [src/cloud_dashboard/app.py](file:///d:/projects/IGNIS/src/cloud_dashboard/app.py)**:
  - Lifespan registration of `ExportService` and `BundleService` in `app.state` and `ResultManager`.
  - Mounted `export_router`.

### E. User Interface & Navigation
- **[NEW] [src/cloud_dashboard/templates/settings.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/settings.html)**:
  - Format capability status table (Format, Status badges, Reason/Installation instructions).
  - Quick Artifact Export & Publication toolbar with dropdown selectors and download buttons.
  - Default execution preferences card.
- **[MODIFY] [src/cloud_dashboard/templates/partials/navbar.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/partials/navbar.html)**:
  - Added Settings item in sidebar menu with active highlight logic (`active_page == 'settings'`).

---

## 2. Test Verification & Results

Ran full pytest suite across all 88 test cases:

```powershell
python -m pytest tests/ -v
```

### Key Test Suites Run:
1. `tests/test_export_service.py` — Verifies `export()` unified interface across Markdown, HTML, CSV, JSON, and ZIP formats, origin metadata embedding, and missing format error handling.
2. `tests/test_bundle_service.py` — Verifies `build_bundle()` ZIP generation, manifest inclusion, and file metadata.
3. `tests/test_bundle_integrity.py` — Extracts generated bundle ZIP archive and verifies SHA256 checksums of every extracted file against `bundle_manifest.json`.
4. `tests/test_export_api.py` — Integration tests for `/api/v1/experiment/export/formats`, `/export/{id}`, and `/reproduce`.
5. `tests/test_settings_ui.py` — Integration tests for `/settings` view rendering and navbar active highlighting.

**Verification Result**: **88 passed, 0 failures** in 8.52 seconds.

---

## 3. Screenshots & Visual Verification

- **Settings & Export Preferences UI**: Accessible at `http://localhost:9000/settings`.
- **Format Capabilities Matrix**: Renders live format status badges and dependency check results.
- **Quick Export Toolbar**: One-click download of exported artifacts and research reproducibility bundles.
