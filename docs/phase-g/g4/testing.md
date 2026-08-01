# Phase G4 — Experiment Repository: Testing & Verification Plan

This document outlines the testing strategy, manual verification steps, and automated test suite details for Phase G4 (Experiment Repository & SQLite Indexing).

---

## Overview of Phase G4 Capabilities

Phase G4 equips IGNIS with a persistent, searchable experiment repository backed by a normalized SQLite index (`experiment_repository/metadata.db`).

### Verified Core Capabilities:
1. **Automatic Atomic Archival (`RepositoryManager`)**: Sole writer service copying simulation outputs (`raw_results.json`, `metrics.json`, `experiment_manifest.json`, `progress_events.jsonl`, `logs/`, `charts/`, `report.md`, `report.html`) into staging folders first (`.tmp_*`) and atomically renaming to timestamped archive folders (`YYYY-MM-DD_HH-MM-SS_{exp_id}`).
2. **Normalized SQLite Metadata Database**: `experiment_repository/metadata.db` auto-created with SQLite `PRAGMA user_version = 1`, `experiments` and `experiment_scenarios` relational tables, and explicit transaction boundaries (`BEGIN TRANSACTION` / `COMMIT` / `ROLLBACK`).
3. **Reproducibility & Integrity Features**: `manifest_sha256` SHA-256 integrity digest, `archive_schema_version = "1.0"`, and `archived_at` timestamps.
4. **Strictly Read-Only REST API**: Endpoints under `/api/v1/repository/*` for searching, filtering (`verdict`, `scenario`, `commit`, `date`), sorting (`timestamp`, `duration`, `verdict`, `trials`), paginating, and fetching full experiment details.
5. **Interactive Repository Browser UI**: Timeline interface rendered at `http://localhost:9000/repository` inheriting `base.html` & `navbar.html`.

---

## Automated Pytest Suite

The automated test suite consists of 11 tests across 4 dedicated test modules in `tests/`:

```powershell
python -m pytest tests/test_repository_migrations.py tests/test_repository_manager.py tests/test_repository_api.py tests/test_repository_ui.py -v
```

### Module Breakdown:
1. **`tests/test_repository_migrations.py`**:
   - `test_repository_migrations_user_version`: Verifies `PRAGMA user_version = 1` creation and table/index DDL migration.
   - `test_repository_migrations_idempotency`: Verifies migration engine can run repeatedly without error.
2. **`tests/test_repository_manager.py`**:
   - `test_repository_manager_archive_experiment`: Verifies atomic directory staging, file copying, `manifest_sha256` calculation, and SQLite insertion.
   - `test_repository_manager_immutability`: Verifies duplicate archival attempts enforce immutability without overwriting existing data.
   - `test_repository_manager_query_and_filter`: Verifies SQL query filtering by verdict.
3. **`tests/test_repository_api.py`**:
   - `test_api_list_repository`: Verifies `GET /api/v1/repository` lists archived runs.
   - `test_api_filter_repository`: Verifies API filtering by verdict (`PASS`/`FAIL`) and scenario (`S3`).
   - `test_api_get_repository_detail`: Verifies `GET /api/v1/repository/{id}` returns complete experiment metadata.
   - `test_api_get_repository_detail_not_found`: Verifies HTTP 404 on missing experiment IDs.
4. **`tests/test_repository_ui.py`**:
   - `test_repository_ui_page_rendering`: Verifies `GET /repository` returns HTTP 200 with HTML DOM elements.
   - `test_repository_navbar_active_state`: Verifies navbar Repository link active class highlighting.

---

## Manual Verification Walkthrough

Follow these steps to manually verify the Repository Browser and Archival workflow in a web browser:

### Step 1: Start IGNIS Dashboard Server

```powershell
python -m uvicorn src.cloud_dashboard.app:app --port 9000
```

---

### Step 2: Execute an Experiment Run

1. Open `http://localhost:9000/experiments`.
2. Configure parameters:
   - **Trials per Scenario**: `5`
   - **Target Scenarios**: `S3 - Communication Degradation & Buffer`
3. Click **Run Experiment** and wait for execution to complete (`COMPLETED` or `FAILED`).

---

### Step 3: Verify Automatic Archival in Repository Browser

1. Navigate to `http://localhost:9000/repository` (or click **Repository** in the sidebar navbar).
2. **Verification Checklist**:
   - The **Repository** navbar link is highlighted as active.
   - The top header displays `Total Archived: 1` (or count of archived runs).
   - The new experiment run appears at the top of the timeline list with its Experiment ID, execution timestamp, archived timestamp, commit hash, duration, and verdict badge.
   - Click **Details** to expand the scenario summary table (displays Scenario ID, Verdict, Trials, Mean Latency).
   - Click **View Report** to open the archived self-contained HTML report in a new tab (`/api/v1/repository/{id}/report.html`).

---

### Step 4: Test Search & Filtering Toolbar

1. Select **Verdict: PASS** in the filter toolbar and click **Apply Filters**.
2. Select **Scenario: S3** in the filter toolbar and click **Apply Filters**.
3. Type a commit hash prefix into the **Git Commit Hash** field and click **Apply Filters**.
4. Click **Reset** to clear all filters and restore the full historical timeline.

---

### Step 5: Verify SQLite Database Structure & Immutability

1. Inspect `experiment_repository/metadata.db` on disk.
2. Confirm the directory `experiment_repository/YYYY-MM-DD_HH-MM-SS_exp-ID/` contains:
   - `raw_results.json`
   - `metrics.json`
   - `experiment_manifest.json`
   - `report.html` & `report.md`
3. Confirm that running another experiment creates a **new timestamped directory**, preserving the existing archived folder untouched.
