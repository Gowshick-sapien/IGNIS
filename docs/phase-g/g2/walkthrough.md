# Phase G2 — Experiment Management & Control Center: Sub-Phase Walkthrough

Phase G2 elevates IGNIS from a CLI-driven simulation tool into a web-driven experimentation platform. It exposes the experiment orchestration pipeline (`run_experiment.py`) through versioned HTTP REST endpoints and equips the Cloud Dashboard (port 9000) with an interactive Experiment Control Center, Report Browser, Interactive Chart Gallery, and Scenario Selector.

---

## Accomplished Implementation

### 1. Strongly-Typed Pydantic Schemas (`src/cloud_dashboard/schemas.py`)
- Created Pydantic models for type safety, validation, and OpenAPI documentation:
  - `ExperimentRunRequest` (`trials`, `seed`, `clean`, `scenarios`)
  - `ExperimentStatusResponse` (`experiment_id`, `state`, `pid`, `current_scenario`, `current_trial`, `total_trials`, `start_time`)
  - `ExperimentLogResponse` (`lines`, `tail`, `total_lines`)
  - `ExperimentLoadRequest` (`path`)
  - `ErrorResponse` (`error`, `message`, `details`)
- Standardized non-200 HTTP responses across all endpoints with explicit error codes (`ExperimentAlreadyRunning`, `InvalidStateTransition`, `ExperimentNotFound`, `FileNotFound`, `SubprocessExecutionError`).

### 2. Subprocess Lifecycle Manager (`src/cloud_dashboard/services/process_manager.py`)
- Implemented `ProcessManager` as a thread-safe singleton state machine managing child process execution of `run_experiment.py`.
- States enforced: `IDLE`, `STARTING`, `RUNNING`, `PAUSING`, `PAUSED`, `STOPPING`, `COMPLETED`, `FAILED`.
- Features:
  - ISO8601 experiment ID generation: `exp-YYYYMMDDTHHMMSSZ-{4hex}`.
  - Command argument forwarding (`--trials`, `--seed`, `--clean`, `--scenarios`).
  - Windows-compatible cooperative pause via `.pause_flag` file.
  - Non-blocking log tail reading with `utf-8` decoding (`errors='replace'`).
  - Single active execution isolation (rejecting concurrent runs with `InvalidStateTransition`).

### 3. Versioned REST API Routes (`src/cloud_dashboard/routes/experiments.py`)
- Mounted `/api/v1/experiment/*` API router:
  - `POST /api/v1/experiment/run`: Launches experiment run.
  - `POST /api/v1/experiment/stop`: Terminates child process PID gracefully.
  - `POST /api/v1/experiment/pause`: Issues cooperative pause.
  - `POST /api/v1/experiment/resume`: Clears pause flag and resumes execution.
  - `POST /api/v1/experiment/restart`: Terminates current run, assigns a **new Experiment ID**, and spawns a new run from scratch.
  - `POST /api/v1/experiment/clean`: Cleans working result output directory.
  - `POST /api/v1/experiment/load`: Imports raw simulation metrics into active view context.
  - `GET /api/v1/experiment/status`: Returns current state machine state and execution details.
  - `GET /api/v1/experiment/results`: Returns active `metrics.json` contents.
  - `GET /api/v1/experiment/logs`: Returns trailing log lines.

### 4. Page Routes & Templates (`src/cloud_dashboard/routes/dashboard_routes.py` & `templates/`)
- Converted `routes` into a Python package (`src/cloud_dashboard/routes/`).
- Built Jinja2 template inheritance structure:
  - `base.html`: Base HTML template with professional styling, Plotly.js CDN link, and `{% include "partials/navbar.html" %}`.
  - `partials/navbar.html`: Shared text-only sidebar navigation (`Dashboard`, `Experiments`, `Reports`, `Charts`, `Scenarios`).
  - `experiments.html`: Experiment Control Center form, scenario dropdown (`all`, `failed`, `S1`-`S7`), live status panel, action buttons (Run, Pause, Resume, Stop, Restart), and live log tail viewer.
  - `reports.html`: Historical report browser displaying generated HTML and Markdown reports sorted **Newest First** by timestamp.
  - `charts.html`: Interactive Plotly.js chart gallery.
  - `scenarios.html`: Strictly **Read-Only** scenario browser rendering YAML files (S1–S7) as cards.

### 5. Application Integration (`src/cloud_dashboard/app.py`)
- Registered `ProcessManager` singleton in FastAPI lifespan startup (`app.state.process_manager`).
- Mounted `experiments_router`, `dashboard_router`, and static asset directories (`/results`, `/reports`).

---

## Verification & Automated Test Results

Ran complete Phase G2 Pytest test suite across all 5 test modules:

```bash
python -m pytest tests/test_process_manager.py tests/test_experiment_api.py tests/test_dashboard_routes.py tests/test_scenario_routes.py tests/test_navigation.py -v
```

### Output:
```
============================= test session starts =============================
platform win32 -- Python 3.12.2, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\projects\IGNIS
collected 18 items

tests/test_process_manager.py::test_process_manager_singleton PASSED     [  5%]
tests/test_process_manager.py::test_invalid_transitions PASSED           [ 11%]
tests/test_process_manager.py::test_experiment_start_and_status PASSED   [ 16%]
tests/test_process_manager.py::test_cooperative_pause_resume PASSED      [ 22%]
tests/test_process_manager.py::test_restart_semantics PASSED             [ 27%]
tests/test_process_manager.py::test_log_tail_reading PASSED              [ 33%]
tests/test_experiment_api.py::test_get_status_endpoint PASSED            [ 38%]
tests/test_experiment_api.py::test_run_and_duplicate_conflict PASSED     [ 44%]
tests/test_experiment_api.py::test_invalid_state_transition_contract PASSED [ 50%]
tests/test_experiment_api.py::test_get_logs_endpoint PASSED              [ 55%]
tests/test_dashboard_routes.py::test_experiments_page_route PASSED       [ 61%]
tests/test_dashboard_routes.py::test_reports_page_route PASSED           [ 66%]
tests/test_dashboard_routes.py::test_charts_page_route PASSED            [ 72%]
tests/test_dashboard_routes.py::test_reports_list_api PASSED             [ 77%]
tests/test_scenario_routes.py::test_scenarios_page_route PASSED          [ 83%]
tests/test_scenario_routes.py::test_scenarios_parsed_cards PASSED        [ 88%]
tests/test_navigation.py::test_navbar_presence_on_all_pages PASSED       [ 94%]
tests/test_navigation.py::test_navbar_active_highlighting PASSED         [100%]

======================== 18 passed in 2.09s ========================
```
