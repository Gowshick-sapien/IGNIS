# Phase G6 — Export, Publication & Reproducibility Bundles: Testing & Verification Plan

This document outlines the automated test suite details and manual verification steps for Phase G6.

---

## Overview of Phase G6 Capabilities

Phase G6 equips IGNIS with comprehensive publication and auditability tooling:
1. **Multi-Format Export Service (`ExportService`)**: Single unified public interface `export(experiment_id, format)` supporting Markdown (`.md`), interactive HTML (`.html`), tabular CSV (`.csv`), machine-readable JSON (`.json`), complete ZIP archive (`.zip`), and optional PDF/DOCX formats.
2. **Standardized Origin Metadata**: Embeds metadata headers (`System`, `Phase G6`, `Experiment ID`, `Export Time`, `Generator Version`) into every exported file.
3. **HTML-to-PDF Visual Parity**: Converts PDF outputs from HTML using `weasyprint` (`HTML(string=html).write_pdf()`) to guarantee visual identity between interactive HTML reports and PDF documents.
4. **Graceful Dependency Handling**: Implements feature degradation for optional PDF (`weasyprint`) and DOCX (`python-docx`) libraries. If absent, the API returns HTTP 501 (`EXPORT_UNAVAILABLE`) with helpful `pip install` commands.
5. **Reproducibility Bundle Builder (`BundleService`)**: Compiles self-contained research reproduction ZIP archives (`reproducibility_bundle_{exp_id}.zip`) containing `bundle_manifest.json` (SHA256 checksums), detailed `README.md` (requirements, Docker versions, scenario replay instructions, expected runtimes), `report/`, `charts/`, `data/`, `environment/` (`requirements.txt`, `docker-compose.yml`, `platform_metadata.json`, `git_state.json`), `scenarios/`, `logs/`, and `methodology/`.
6. **Idempotent Bundle Overwrite Policy**: Re-building a bundle regenerates and overwrites existing bundle archives idempotently.
7. **Export REST API (`/api/v1/experiment/export/*`)**: Versioned endpoints for querying format capability status, streaming format downloads (`FileResponse`), and compiling reproducibility packages.
8. **Settings & Preferences UI (`settings.html`)**: Responsive Jinja2 view displaying format capability status matrix tables, dependency installation instructions, default execution preferences, and quick export shortcuts.

---

## Automated Pytest Suite

The Phase G6 test suite consists of 11 dedicated tests across 5 test modules in `tests/`:

```powershell
python -m pytest tests/test_export_service.py tests/test_bundle_service.py tests/test_bundle_integrity.py tests/test_export_api.py tests/test_settings_ui.py -v
```

### Module Breakdown:
1. **`tests/test_export_service.py`**:
   - `test_export_service_format_capabilities`: Verifies capability matrix dict (`available`, `optional_status`).
   - `test_export_service_formats`: Verifies file generation and origin metadata embedding across Markdown, HTML, CSV, JSON, and ZIP formats.
   - `test_export_service_invalid_format`: Verifies `ValueError` raising on unsupported format strings.
2. **`tests/test_bundle_service.py`**:
   - `test_bundle_service_build_bundle`: Verifies reproducibility bundle creation, output ZIP path, file size, and `bundle_manifest.json` inclusion.
   - `test_bundle_service_invalid_experiment`: Verifies `ValueError` raising on non-existent experiment IDs.
3. **`tests/test_bundle_integrity.py`**:
   - `test_bundle_extraction_integrity`: Extracts generated bundle ZIP file to temporary folder and verifies required directory structure (`report/`, `charts/`, `data/`, `environment/`, `scenarios/`, `logs/`, `methodology/`), presence of `git_state.json` and `README.md`, and matching calculated SHA256 checksums against `bundle_manifest.json`.
4. **`tests/test_export_api.py`**:
   - `test_export_formats_endpoint`: Verifies `GET /api/v1/experiment/export/formats` returns HTTP 200 with format capabilities.
   - `test_export_file_endpoint`: Verifies `GET /api/v1/experiment/export/{id}?format=csv` returns HTTP 200 with file attachment headers.
   - `test_export_not_found_endpoint`: Verifies HTTP 404 on missing experiment IDs.
   - `test_reproduce_bundle_endpoint`: Verifies `POST /api/v1/experiment/{id}/reproduce` compiles bundle and returns bundle metadata.
5. **`tests/test_settings_ui.py`**:
   - `test_settings_page_rendering`: Verifies `GET /settings` returns HTTP 200 with DOM tables and forms.
   - `test_settings_navbar_active_state`: Verifies navbar Settings link active class highlighting.

---

## Manual Verification Walkthrough

### Step 1: Start IGNIS Dashboard Server

```powershell
python -m uvicorn src.cloud_dashboard.app:app --port 9000
```

---

### Step 2: Open Settings & Export Preferences Page

1. Open `http://localhost:9000/settings` in your browser (or click **Settings** in sidebar navbar).
2. Confirm:
   - The **Settings** sidebar link is highlighted as active (`class="nav-link active"`).
   - The **Export Format Capabilities & Dependency Matrix** table renders all supported formats.
   - Core formats (`Markdown`, `HTML`, `CSV`, `JSON`, `ZIP`) render green **AVAILABLE** status badges.
   - Optional formats (`PDF`, `Word Document`) render status badges (`AVAILABLE` if `weasyprint` / `python-docx` installed, or `UNAVAILABLE` with clear installation instructions).

---

### Step 3: Test Single-File Export Downloads

1. Under **Quick Artifact Export & Publication Toolbar**, select an archived experiment run (e.g., `exp-20260801T043524Z-b2d8`).
2. Select format **Tabular CSV (.csv)** and click **Download Artifact**.
3. Confirm the browser triggers a file download named `metrics_exp-20260801T043524Z-b2d8.csv`.
4. Open the CSV file and verify:
   - Header comments include `# IGNIS EXPORT METADATA` (`System`, `Phase`, `Experiment ID`, `Exported At`).
   - Includes `SCENARIO SUMMARY TABLE` and `DETAILED METRIC ROWS`.
5. Repeat for **Markdown (.md)**, **Interactive HTML (.html)**, **JSON (.json)**, and **ZIP Archive (.zip)**.

---

### Step 4: Test Reproducibility Bundle Generation & Extraction

1. On the Settings page, select an archived experiment run.
2. Click **Generate Reproducibility Bundle ZIP**.
3. Confirm the browser downloads `reproducibility_bundle_exp-20260801T043524Z-b2d8.zip`.
4. Extract the downloaded ZIP archive and inspect the internal folder structure:
   - `bundle_manifest.json`: Confirm SHA256 checksums are present for all included files.
   - `README.md`: Confirm Python version, Docker version, container images, scenario replay commands, expected runtime, and checksum table are present.
   - `environment/git_state.json`: Confirm Git commit, branch, status, and diff patch are captured.
   - `report/`: Confirm `project_results_report.md` and `report.html` are included.
   - `charts/`: Confirm Matplotlib static PNG charts are included.
   - `data/`: Confirm `metrics.json`, `raw_results.json`, `experiment_manifest.json`, and `regression_summary.json` are included.
   - `scenarios/`: Confirm YAML scenario definitions (`S1` ... `S7`) are included.

---

### Step 5: Test Optional Format Degradation (PDF / DOCX)

1. Select format **PDF Document (.pdf)** on an environment missing `weasyprint`.
2. Click **Download Artifact**.
3. Confirm the backend returns HTTP 501 (`EXPORT_UNAVAILABLE`) with detail: `"PDF export requires weasyprint package. Install with: pip install weasyprint"`.
