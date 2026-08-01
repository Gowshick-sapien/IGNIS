# Phase G2 — Experiment Management & Control Center: Sub-Phase Implementation Plan

Phase G2 exposes the IGNIS experiment orchestration pipeline (`run_experiment.py`) through versioned REST HTTP endpoints and equips the Cloud Dashboard (port 9000) with an interactive Experiment Control Center, Report Browser, Interactive Chart Gallery, and Scenario Selector.

---

## Overview & Objectives

Following the completion of Phase G1 (Interactive Self-Contained HTML Reporting Engine & Plotly Integration), Phase G2 elevates IGNIS from a CLI-driven simulation tool into a web-driven experimentation platform.

### Key Objectives
1. **Subprocess Lifecycle Manager (`ProcessManager`)**: A singleton, state-machine-backed subprocess service managing the execution lifecycle of `run_experiment.py` (`IDLE`, `STARTING`, `RUNNING`, `PAUSING`, `PAUSED`, `STOPPING`, `COMPLETED`, `FAILED`), log streaming, PID tracking, and Windows-compatible cooperative pause/resume capabilities.
2. **Experiment API Routes (`/api/v1/experiment/*`)**: Versioned HTTP REST endpoints enabling control center front-ends and external scripts to launch experiments, selectively trigger scenarios (`S3`, `S4,S5`, `failed`, `all`), pause/resume/stop runs, load historical results, query execution status, and read log tails.
3. **Pydantic API Schemas (`src/cloud_dashboard/schemas.py`)**: Strongly-typed request/response models and standardized error response payloads for clean FastAPI OpenAPI documentation and type validation.
4. **Dashboard Control Center & Browsers**:
   - **`experiments.html`**: Experiment launch form, scenario selector, dynamic action controls (Run, Pause, Resume, Stop), real-time status summary, and log tail viewer.
   - **`reports.html`**: Historical report browser listing reports (sorted **Newest First** by default) with inline Markdown preview and interactive HTML report links.
   - **`charts.html`**: Interactive Plotly.js chart gallery with scenario dropdown filters.
   - **`scenarios.html`**: Read-only scenario browser displaying YAML scenario configs (S1–S7), assertions, and checkboxes for targeted execution.
   - **`base.html` & `partials/navbar.html`**: Base Jinja2 layout template and included navigation sidebar maintaining professional styling across all pages via template inheritance.
5. **Strict Compliance with Professional Standards**: Text-and-colour badges only; zero emoji, decorative symbols, or consumer styling.

---

## Technical Deliverables & File Manifest

| Action | Path | Description |
|---|---|---|
| **[NEW]** | [src/cloud_dashboard/schemas.py](file:///d:/projects/IGNIS/src/cloud_dashboard/schemas.py) | Pydantic API request/response models and standardized error schemas |
| **[NEW]** | [src/cloud_dashboard/services/process_manager.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/process_manager.py) | Singleton subprocess lifecycle state machine for `run_experiment.py` |
| **[NEW]** | [src/cloud_dashboard/routes/experiments.py](file:///d:/projects/IGNIS/src/cloud_dashboard/routes/experiments.py) | REST API routes (`/api/v1/experiment/*`) for lifecycle execution & status |
| **[NEW]** | [src/cloud_dashboard/routes/dashboard_routes.py](file:///d:/projects/IGNIS/src/cloud_dashboard/routes/dashboard_routes.py) | Page routes (`/experiments`, `/reports`, `/charts`, `/scenarios`) & report APIs |
| **[NEW]** | [src/cloud_dashboard/templates/base.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/base.html) | Root Jinja2 layout template with head metadata, CSS/JS links, and navbar include |
| **[NEW]** | [src/cloud_dashboard/templates/partials/navbar.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/partials/navbar.html) | Shared navigation sidebar component (included in `base.html`) |
| **[NEW]** | [src/cloud_dashboard/templates/experiments.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/experiments.html) | Experiment Control Center page template |
| **[NEW]** | [src/cloud_dashboard/templates/reports.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/reports.html) | Report browser page template (default sorted Newest First) |
| **[NEW]** | [src/cloud_dashboard/templates/charts.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/charts.html) | Interactive Plotly.js chart gallery page template |
| **[NEW]** | [src/cloud_dashboard/templates/scenarios.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/scenarios.html) | Read-only scenario browser page template |
| **[MODIFY]** | [src/cloud_dashboard/app.py](file:///d:/projects/IGNIS/src/cloud_dashboard/app.py) | Lifespan singleton `ProcessManager` instantiation & router mounts |
| **[NEW]** | [docs/phase-g/g2/implementation_plan.md](file:///d:/projects/IGNIS/docs/phase-g/g2/implementation_plan.md) | Phase G2 sub-phase specification document in repository |
| **[NEW]** | [tests/test_process_manager.py](file:///d:/projects/IGNIS/tests/test_process_manager.py) | State machine transition, PID isolation, and pause flag unit tests |
| **[NEW]** | [tests/test_experiment_api.py](file:///d:/projects/IGNIS/tests/test_experiment_api.py) | API endpoint, schema validation, and error contract integration tests |
| **[NEW]** | [tests/test_dashboard_routes.py](file:///d:/projects/IGNIS/tests/test_dashboard_routes.py) | Page route rendering and report API integration tests |
| **[NEW]** | [tests/test_scenario_routes.py](file:///d:/projects/IGNIS/tests/test_scenario_routes.py) | Read-only YAML parsing & scenario browser route tests |
| **[NEW]** | [tests/test_navigation.py](file:///d:/projects/IGNIS/tests/test_navigation.py) | Template inheritance and navbar consistency tests |

---

## Detailed Architectural Specifications

### 1. API Schemas & Error Response Contract (`schemas.py`)

All endpoint request payloads and response structures use explicit Pydantic models.

```python
class ExperimentRunRequest(BaseModel):
    trials: int = Field(default=30, ge=1, le=1000)
    seed: int = Field(default=4321)
    clean: bool = Field(default=True)
    scenarios: str = Field(default="all", description="'all', 'failed', 'S3', or 'S4,S5,S6'")

class ExperimentStatusResponse(BaseModel):
    experiment_id: Optional[str]
    state: str
    pid: Optional[int]
    current_scenario: Optional[str]
    current_trial: Optional[int]
    total_trials: Optional[int]
    start_time: Optional[str]

class ExperimentLogResponse(BaseModel):
    lines: List[str]
    tail: int
    total_lines: int

class ExperimentLoadRequest(BaseModel):
    path: str = Field(..., description="Path to raw_results.json or archived experiment folder")

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None
```

#### Standardized Error Contract
All HTTP 4xx/5xx responses return a consistent JSON body:
```json
{
    "error": "ExperimentAlreadyRunning",
    "message": "Experiment exp-20260731T110000Z-1a2b is currently RUNNING.",
    "details": {"active_experiment_id": "exp-20260731T110000Z-1a2b", "pid": 14208}
}
```

Defined Error Codes:
- `ExperimentAlreadyRunning` (HTTP 409 Conflict)
- `InvalidStateTransition` (HTTP 409 Conflict)
- `ExperimentNotFound` (HTTP 404 Not Found)
- `InvalidRequestPayload` (HTTP 400 Bad Request)
- `FileNotFound` (HTTP 404 Not Found)
- `SubprocessExecutionError` (HTTP 500 Internal Server Error)

---

### 2. State Transition Matrix & Subprocess Lifecycle (`ProcessManager`)

`ProcessManager` enforces a finite state machine. Transitions not explicitly marked **Yes** raise `InvalidStateTransition` (mapped to HTTP 409 Conflict with `error: "InvalidStateTransition"`).

| Current State | Action | Next State | Allowed | HTTP / Result |
|---|---|---|---|---|
| `IDLE` | `start` | `STARTING` | **Yes** | 200 OK |
| `IDLE` | `stop` / `pause` / `resume` | — | **No** | 409 Conflict (`InvalidStateTransition`) |
| `STARTING` | process launched | `RUNNING` | **Yes** | Automatic internal transition |
| `RUNNING` | `start` | — | **No** | 409 Conflict (`ExperimentAlreadyRunning`) |
| `RUNNING` | `pause` | `PAUSING` | **Yes** | 200 OK (`.pause_flag` written) |
| `PAUSING` | event check | `PAUSED` | **Yes** | Automatic upon process pause confirmation |
| `PAUSED` | `resume` | `RUNNING` | **Yes** | 200 OK (`.pause_flag` removed) |
| `PAUSED` | `pause` / `start` | — | **No** | 409 Conflict (`InvalidStateTransition`) |
| `PAUSED` | `stop` | `STOPPING` | **Yes** | 200 OK |
| `RUNNING` | `stop` | `STOPPING` | **Yes** | 200 OK (`SIGTERM` / process terminate) |
| `STOPPING` | exit 0 | `COMPLETED` | **Yes** | Automatic internal transition |
| `STOPPING` | exit != 0 | `FAILED` | **Yes** | Automatic internal transition |
| `RUNNING` | exit 0 | `COMPLETED` | **Yes** | Automatic internal transition |
| `RUNNING` | exit != 0 | `FAILED` | **Yes** | Automatic internal transition |
| `COMPLETED` | `start` | `STARTING` | **Yes** | 200 OK (auto-resets state) |
| `FAILED` | `start` | `STARTING` | **Yes** | 200 OK (auto-resets state) |

#### Process Singleton & Subprocess Isolation
- `ProcessManager` is instantiated **once** during FastAPI application startup (`app.state.process_manager`).
- Guarantees **exactly one** child subprocess (`run_experiment.py`), **one PID**, and **one active experiment ID** (`exp-YYYYMMDDTHHMMSSZ-{4hex}`).

#### Restart Semantics
`restart` (`POST /api/v1/experiment/restart`) performs:
1. Issue `stop()` if current state is `RUNNING`, `PAUSING`, or `PAUSED`.
2. Wait for process exit and clean transient execution handles.
3. Generate a **brand new unique Experiment ID**.
4. Launch a **new child process** from scratch. It is **not** a process resume or retry of an existing PID.

#### Load Semantics
`load` (`POST /api/v1/experiment/load`):
- Accepts a file or directory path (e.g. `results/raw_results.json` or `experiment_repository/exp-.../raw_results.json`).
- Parses and copies target results into `results/metrics.json` and `results/raw_results.json`.
- Serves purely to **import historical simulation data into active view context** for rendering in dashboard reports and charts. Does **not** trigger process execution.

#### Log Streaming Specification
`get_logs(tail=N)` (`GET /api/v1/experiment/logs`):
- Opens `results/logs/experiment.log` with explicit `UTF-8` encoding and `errors='replace'`.
- Reads the last `N` lines non-blockingly.
- Handles partial line boundaries at file write offsets to prevent truncation crashes on Windows.

---

### 3. Dashboard UI & Template Architecture

#### Jinja2 Layout & Template Inheritance
- `src/cloud_dashboard/templates/base.html`: Root template defining standard `<head>`, CSS stylesheets, Plotly.js CDN link, layout wrapper, header banner, and `{% include "partials/navbar.html" %}`.
- All dashboard pages (`index.html`, `experiments.html`, `reports.html`, `charts.html`, `scenarios.html`) inherit from `base.html` via `{% extends "base.html" %}` and fill `{% block content %}`.

#### Page Specifications
1. **`experiments.html`**:
   - Form inputs: Trial count, seed, clean directory flag, scenario selector (`all`, `failed`, or individual scenario checkboxes).
   - Execution control buttons: **Run Experiment**, **Pause**, **Resume**, **Stop**, **Restart**. Buttons dynamically enable/disable based on current state.
   - Status panel: Live state badge (`IDLE`, `RUNNING`, `PAUSED`, `COMPLETED`, `FAILED`), active scenario, active trial, start time, PID, and log tail viewer.
2. **`reports.html`**:
   - Table of generated experiment reports sorted **Newest First** by timestamp.
   - Includes columns: Experiment ID, Date/Time, Scenarios, Verdict, Actions (View Markdown, Open Interactive HTML Report).
3. **`charts.html`**:
   - Interactive gallery rendering all 10 Plotly.js chart types with a scenario filter select dropdown.
4. **`scenarios.html`**:
   - **Read-Only** scenario browser displaying parsed YAML configs for scenarios S1 through S7 (parameters, assertions, fault injection settings).
   - *Policy*: The web dashboard never modifies YAML scenario files on disk; it only parses and displays them.

---

## Acceptance Criteria Checklist

| # | Acceptance Criterion | Status |
|---|---|---|
| 1 | `ProcessManager` is initialized as a single singleton instance on FastAPI application startup |  PENDING |
| 2 | `POST /api/v1/experiment/run` successfully launches `run_experiment.py` as a child process |  PENDING |
| 3 | State transitions correctly follow `IDLE` → `STARTING` → `RUNNING` → `COMPLETED` / `FAILED` |  PENDING |
| 4 | Attempting to launch an experiment while state is `RUNNING` returns HTTP `409 Conflict` with `ExperimentAlreadyRunning` error payload |  PENDING |
| 5 | Invalid state transitions return HTTP `409 Conflict` with `InvalidStateTransition` error payload |  PENDING |
| 6 | Cooperative pause writes `.pause_flag` file and transitions state to `PAUSING` → `PAUSED` |  PENDING |
| 7 | Resume removes `.pause_flag` file and restores state to `RUNNING` |  PENDING |
| 8 | Stop terminates child process PID and transitions state to `STOPPING` → `COMPLETED` / `FAILED` |  PENDING |
| 9 | Restart terminates existing run (if active), generates a **new Experiment ID**, and spawns a new process |  PENDING |
| 10 | Selective scenario payload (`scenarios: "S3"` or `"S4,S5"`) executes only specified scenarios |  PENDING |
| 11 | `POST /api/v1/experiment/load` imports raw result files into active results without spawning processes |  PENDING |
| 12 | `GET /api/v1/experiment/logs` reads tail lines safely using UTF-8 decoding without line-buffering truncation |  PENDING |
| 13 | All 4xx/5xx API responses conform strictly to the `ErrorResponse` Pydantic schema |  PENDING |
| 14 | Web interface pages (`/experiments`, `/reports`, `/charts`, `/scenarios`) extend `base.html` Jinja2 template |  PENDING |
| 15 | `navbar.html` is rendered consistently across all pages via Jinja2 template inheritance |  PENDING |
| 16 | Reports browser (`/reports`) displays generated experiment reports sorted **Newest First** |  PENDING |
| 17 | Scenario browser (`/scenarios`) renders YAML files as **Read-Only** cards without file mutation |  PENDING |
| 18 | Dashboard UI complies strictly with professional engineering standard (zero emoji, zero gaming icons) |  PENDING |
| 19 | Existing CLI experiment execution (`python src/run_experiment.py`) remains fully operational and backward compatible |  PENDING |
| 20 | Complete automated test suite passes cleanly via Pytest |  PENDING |

---

## Comprehensive Test Plan

The G2 test suite is organized into dedicated, focused test modules under `tests/`:

1. **`tests/test_process_manager.py`**:
   - Unit tests for state machine state transitions and state validation.
   - Unit tests for subprocess launch, PID capture, log file creation, and termination.
   - Unit tests for cooperative pause flag creation and removal.
   - Singleton isolation tests ensuring concurrent instantiation is prevented.

2. **`tests/test_experiment_api.py`**:
   - FastAPI `TestClient` integration tests for all endpoints under `/api/v1/experiment/*`.
   - Payload validation tests using `ExperimentRunRequest`, `ExperimentLoadRequest`.
   - Error response contract tests verifying HTTP status codes (400, 404, 409, 500) and `ErrorResponse` schema structure.
   - Restart semantics validation (verifying new experiment ID assignment).

3. **`tests/test_dashboard_routes.py`**:
   - Integration tests for page routes (`/experiments`, `/reports`, `/charts`).
   - Report listing integration tests verifying **Newest First** sorting order.
   - JSON report content API endpoint tests (`/api/v1/reports/list`, `/api/v1/reports/{id}`).

4. **`tests/test_scenario_routes.py`**:
   - Tests for `/scenarios` page rendering.
   - Verification that scenario YAML files are parsed, structured into cards, and strictly read-only.

5. **`tests/test_navigation.py`**:
   - DOM/HTML structure tests verifying Jinja2 template inheritance from `base.html`.
   - Verification that `navbar.html` is included on every dashboard view with correct active page highlighting.

---

## Verification Commands

```bash
# Run full Phase G2 test suite
pytest tests/test_process_manager.py tests/test_experiment_api.py tests/test_dashboard_routes.py tests/test_scenario_routes.py tests/test_navigation.py -v

# Launch dashboard locally to manually verify UI
python -m uvicorn src.cloud_dashboard.app:app --port 9000
```
