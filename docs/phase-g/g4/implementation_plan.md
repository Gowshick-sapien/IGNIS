# Phase G4 — Experiment Repository: Sub-Phase Implementation Plan

Phase G4 equips IGNIS with a persistent, searchable experiment repository. It automatically archives every completed or failed experiment into an immutable directory structure backed by a normalized SQLite index (`experiment_repository/metadata.db`) with built-in schema migration support and an interactive Repository Browser UI.

---

## Overview & Objectives

Following Phase G1 (Interactive Reporting), Phase G2 (Experiment Management FSM), and Phase G3 (Live Progress Streaming), Phase G4 guarantees complete experiment auditability, historical reproducibility, and long-term trend analysis.

### Key Objectives
1. **Automatic Atomic Experiment Archival (`RepositoryManager`)**: A dedicated service (`src/cloud_dashboard/services/repository_manager.py`) acting as the **sole writer** to `experiment_repository/`. Copies active simulation artifacts (`raw_results.json`, `metrics.json`, `experiment_manifest.json`, `progress_events.jsonl`, `logs/experiment.log`, `charts/*.png`, `report.md`, `report.html`) into a staging folder first (`.tmp_{exp_id}`) and atomically renames it to an immutable, timestamped archive folder (`YYYY-MM-DD_HH-MM-SS_{exp_id}`) upon verification.
2. **Normalized SQLite Index (`metadata.db`) & Schema Migrations (`repository_migrations.py`)**: An indexed SQLite database (`experiment_repository/metadata.db`) with `PRAGMA user_version = 1` tracking, schema migration support (`RepositoryMigrations`), transaction boundaries (`BEGIN TRANSACTION` / `COMMIT` / `ROLLBACK`), `manifest_sha256` integrity tracking, `archive_schema_version = "1.0"`, and `archived_at` timestamps.
3. **Pydantic API Schemas (`schemas.py`)**: Strongly-typed request/response models (`RepositoryQueryRequest`, `RepositoryExperimentSummary`, `RepositoryExperimentDetail`, `RepositoryListResponse`).
4. **Read-Only Versioned REST API (`/api/v1/repository/*`)**: Strictly read-only endpoints for listing, searching, filtering (`verdict`, `scenario`, `commit`, `date`), sorting (`timestamp`, `duration`, `verdict`, `trials`), paginating, and fetching full details of historical experiment runs.
5. **Repository Browser UI (`repository.html`)**: A clean, professional Jinja2 template (inheriting `base.html` and `navbar.html`) providing a timeline browser, filter controls, expandable card details, and direct links to archived interactive HTML reports and Matplotlib charts.
6. **Strict Compliance with Professional Standards**: Immutability policy (archived runs are never overwritten), zero emoji, zero gaming visual noise, text-and-colour badges only.

---

## User Review Required

> [!IMPORTANT]
> **Sole Writer, Atomic Copy & Read-Only API**: `RepositoryManager` is the **only service** permitted to write to `experiment_repository/`. Artifacts are copied to a temporary folder (`.tmp_*`) and atomically renamed upon integrity verification. The REST API (`/api/v1/repository/*`) is strictly **READ ONLY**.

> [!NOTE]
> **Database Auto-Initialization & Schema Versioning**: `metadata.db` is automatically created inside `experiment_repository/` at startup if it does not exist. Schema migrations are managed by `RepositoryMigrations` using `PRAGMA user_version`. All database insertions use explicit transaction blocks (`BEGIN TRANSACTION` ... `COMMIT`).

---

## Technical Deliverables & File Manifest

| Action | Path | Description |
|---|---|---|
| **[NEW]** | [src/cloud_dashboard/services/repository_migrations.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/repository_migrations.py) | Schema migration manager checking `PRAGMA user_version` and applying DDL updates |
| **[NEW]** | [src/cloud_dashboard/services/repository_manager.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/repository_manager.py) | Sole writer service for atomic archiving to `experiment_repository/` and indexing metadata in SQLite |
| **[MODIFY]** | [src/cloud_dashboard/schemas.py](file:///d:/projects/IGNIS/src/cloud_dashboard/schemas.py) | Pydantic repository request/response models (`RepositoryQueryRequest`, `RepositoryExperimentDetail`, etc.) |
| **[NEW]** | [src/cloud_dashboard/routes/repository.py](file:///d:/projects/IGNIS/src/cloud_dashboard/routes/repository.py) | Strictly READ-ONLY Versioned REST API (`/api/v1/repository/*`) and view route (`/repository`) |
| **[NEW]** | [src/cloud_dashboard/templates/repository.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/repository.html) | Repository Browser UI with filter controls, search toolbar, and expandable experiment cards |
| **[MODIFY]** | [src/cloud_dashboard/app.py](file:///d:/projects/IGNIS/src/cloud_dashboard/app.py) | Register `RepositoryManager` in lifespan and mount `/repository` router |
| **[MODIFY]** | [src/cloud_dashboard/services/process_manager.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/process_manager.py) | Automatically trigger `RepositoryManager.archive_experiment()` upon state transition to `COMPLETED` or `FAILED` |
| **[NEW]** | [docs/phase-g/g4/implementation_plan.md](file:///d:/projects/IGNIS/docs/phase-g/g4/implementation_plan.md) | Sub-phase G4 specification document in repository |
| **[NEW]** | [tests/test_repository_migrations.py](file:///d:/projects/IGNIS/tests/test_repository_migrations.py) | Unit tests for SQLite `PRAGMA user_version` checks and schema migration logic |
| **[NEW]** | [tests/test_repository_manager.py](file:///d:/projects/IGNIS/tests/test_repository_manager.py) | Unit tests for atomic directory copying, SQLite relational transaction insertion, `manifest_sha256` hashing, and immutability policy |
| **[NEW]** | [tests/test_repository_api.py](file:///d:/projects/IGNIS/tests/test_repository_api.py) | Integration tests for read-only `/api/v1/repository` search, filtering, sorting, pagination, and detail endpoints |
| **[NEW]** | [tests/test_repository_ui.py](file:///d:/projects/IGNIS/tests/test_repository_ui.py) | Integration tests for `/repository` view rendering, navbar active highlight, and filter controls |

---

## Detailed Architectural Specifications

### 1. SQLite Relational Schema (`experiment_repository/metadata.db`)

```sql
-- Schema version tracking
PRAGMA user_version = 1;

CREATE TABLE IF NOT EXISTS experiments (
    experiment_id           TEXT PRIMARY KEY,
    directory               TEXT NOT NULL,
    timestamp               TEXT NOT NULL,
    archived_at             TEXT NOT NULL,
    seed                    INTEGER,
    git_commit              TEXT,
    trial_count             INTEGER,
    overall_verdict         TEXT NOT NULL,    -- PASS, FAIL, INVALID, INCOMPLETE
    execution_duration_sec  REAL,
    platform_os             TEXT,
    platform_python         TEXT,
    platform_docker         TEXT,
    hostname                TEXT,
    regression_rules_hash   TEXT,
    manifest_sha256         TEXT NOT NULL,
    archive_schema_version  TEXT NOT NULL DEFAULT '1.0'
);

CREATE TABLE IF NOT EXISTS experiment_scenarios (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id           TEXT NOT NULL REFERENCES experiments(experiment_id) ON DELETE CASCADE,
    scenario_id             TEXT NOT NULL,    -- e.g., "S3"
    verdict                 TEXT NOT NULL,    -- PASS, FAIL, INVALID, INCOMPLETE
    duration_sec            REAL,
    trial_count             INTEGER,
    latency_mean            REAL,
    latency_ci_low          REAL,
    latency_ci_high         REAL
);

CREATE INDEX IF NOT EXISTS idx_exp_timestamp ON experiments(timestamp);
CREATE INDEX IF NOT EXISTS idx_exp_verdict ON experiments(overall_verdict);
CREATE INDEX IF NOT EXISTS idx_exp_commit ON experiments(git_commit);
CREATE INDEX IF NOT EXISTS idx_scenario_exp ON experiment_scenarios(experiment_id);
CREATE INDEX IF NOT EXISTS idx_scenario_verdict ON experiment_scenarios(verdict);
```

---

### 2. Atomic Archival Workflow (`RepositoryManager`)

To prevent partial or corrupted archives if a process crashes mid-copy:
1. **Stage**: Copy all active outputs from `results/` into temporary staging directory `experiment_repository/.tmp_{experiment_id}/`.
2. **Verify & Hash**: Verify presence of essential files (`metrics.json`, `experiment_manifest.json`) and calculate `manifest_sha256` SHA-256 digest of `experiment_manifest.json`.
3. **Atomically Rename**: Rename `.tmp_{experiment_id}` to `experiment_repository/{YYYY-MM-DD_HH-MM-SS}_{experiment_id}/`.
4. **Transaction Insert**: Execute SQLite `BEGIN TRANSACTION`, insert record into `experiments` table and all scenario rows into `experiment_scenarios` table, and `COMMIT` (or `ROLLBACK` on exception).

---

### 3. Archive Directory Structure

Each completed experiment is archived into `experiment_repository/{YYYY-MM-DD_HH-MM-SS}_{experiment_id}/`:

```
experiment_repository/
    metadata.db                                    # SQLite index
    2026-07-31_14-00-00_exp-20260731T140000Z-9f12/
        raw_results.json
        metrics.json
        experiment_manifest.json
        progress_events.jsonl
        logs/
            experiment.log
        charts/
            decision_latency_boxplot.png
            ...
        report.md
        report.html
```

---

### 4. Read-Only API Query & Search Specifications (`repository.py`)

All endpoints in `routes/repository.py` are strictly **READ ONLY**.

#### `GET /api/v1/repository`
- Query Parameters:
  - `verdict` (optional): Filter by `PASS`, `FAIL`, `INVALID`
  - `scenario` (optional): Filter by scenario ID (e.g. `S3`)
  - `commit` (optional): Filter by git commit hash prefix
  - `from_date` (optional): ISO8601 start date
  - `to_date` (optional): ISO8601 end date
  - `sort` (optional, default `timestamp`): `timestamp`, `verdict`, `duration`, `trials`
  - `order` (optional, default `desc`): `asc` or `desc`
  - `page` (optional, default `1`): Page number (1-indexed)
  - `page_size` (optional, default `20`, max `100`): Items per page

- Response Format:
  ```json
  {
    "status": "success",
    "data": {
      "experiments": [
        {
          "experiment_id": "exp-20260731T140000Z-9f12",
          "directory": "2026-07-31_14-00-00_exp-20260731T140000Z-9f12",
          "timestamp": "2026-07-31T14:00:00Z",
          "archived_at": "2026-07-31T14:00:02Z",
          "seed": 4321,
          "git_commit": "a1b2c3d",
          "trial_count": 30,
          "overall_verdict": "PASS",
          "execution_duration_sec": 42.5,
          "manifest_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          "archive_schema_version": "1.0",
          "scenarios_summary": [
            {"scenario_id": "S1", "verdict": "PASS", "trial_count": 30, "latency_mean": 12.4},
            {"scenario_id": "S3", "verdict": "PASS", "trial_count": 30, "latency_mean": 45.2}
          ]
        }
      ],
      "total": 42,
      "page": 1,
      "page_size": 20,
      "total_pages": 3
    }
  }
  ```

#### `GET /api/v1/repository/{experiment_id}`
- Returns complete experiment metadata, full scenario metrics table, file manifest list, `manifest_sha256` verification hash, and static paths to view archived `report.html`, `report.md`, and `charts/`.

---

## Acceptance Criteria Checklist

| # | Acceptance Criterion | Status |
|---|---|---|
| 1 | `RepositoryManager` is created as sole writer for `experiment_repository/` |  PENDING |
| 2 | `experiment_repository/metadata.db` is auto-created with SQLite `PRAGMA user_version = 1` |  PENDING |
| 3 | `RepositoryMigrations` executes DDL schema migrations sequentially |  PENDING |
| 4 | Archival uses temporary staging directory (`.tmp_*`) and atomic rename to prevent partial copies |  PENDING |
| 5 | `RepositoryManager` executes explicit SQLite `BEGIN TRANSACTION` / `COMMIT` / `ROLLBACK` blocks |  PENDING |
| 6 | Database records include `archive_schema_version = "1.0"`, `archived_at` timestamp, and `manifest_sha256` integrity hash |  PENDING |
| 7 | Finishing an experiment automatically copies `results/` artifacts to `experiment_repository/{timestamp}_{exp_id}/` |  PENDING |
| 8 | Archived experiments strictly enforce immutability (never modified or overwritten) |  PENDING |
| 9 | REST API endpoints (`/api/v1/repository/*`) are strictly READ ONLY |  PENDING |
| 10 | `GET /api/v1/repository` lists archived runs sorted Newest First by default |  PENDING |
| 11 | `GET /api/v1/repository` supports filtering by `verdict`, `scenario`, `commit`, `from_date`, `to_date` |  PENDING |
| 12 | `GET /api/v1/repository` supports sorting by `timestamp`, `verdict`, `duration`, `trials` (asc/desc) and pagination |  PENDING |
| 13 | `GET /api/v1/repository/{experiment_id}` returns full details, metrics, manifest hash, and report links |  PENDING |
| 14 | `/repository` route renders Jinja2 `repository.html` template inheriting `base.html` & `navbar.html` |  PENDING |
| 15 | UI adheres strictly to professional standards (zero emoji, text-and-colour badges only) |  PENDING |
| 16 | Complete automated test suite passes cleanly via Pytest |  PENDING |

---

## Comprehensive Test Plan

The G4 test suite is organized into 4 dedicated test modules under `tests/`:

1. **`tests/test_repository_migrations.py`**:
   - Tests SQLite `PRAGMA user_version` creation and checking.
   - Tests `RepositoryMigrations.migrate()` execution on new and existing databases.

2. **`tests/test_repository_manager.py`**:
   - Unit tests for atomic staging folder creation (`.tmp_*`), verification, and atomic rename.
   - Tests `manifest_sha256` SHA-256 calculation and insertion into SQLite.
   - Tests SQLite transaction boundaries (`BEGIN TRANSACTION` / `COMMIT` / `ROLLBACK`).
   - Test immutability policy (attempting duplicate archival produces separate timestamped entries).

3. **`tests/test_repository_api.py`**:
   - Integration tests verifying `/api/v1/repository` endpoints are strictly read-only.
   - Tests filtering by verdict, scenario, commit, and date ranges.
   - Tests sorting (`timestamp`, `duration`, `verdict`) and pagination.
   - Tests `GET /api/v1/repository/{experiment_id}` detail retrieval.

4. **`tests/test_repository_ui.py`**:
   - Integration tests verifying `/repository` returns HTTP 200 with `repository.html`.
   - Tests navbar active highlighting and filter UI controls.

---

## Verification Commands

```bash
# Run full Phase G4 test suite
python -m pytest tests/test_repository_migrations.py tests/test_repository_manager.py tests/test_repository_api.py tests/test_repository_ui.py -v

# Launch dashboard locally to test repository UI browser
python -m uvicorn src.cloud_dashboard.app:app --port 9000
```
