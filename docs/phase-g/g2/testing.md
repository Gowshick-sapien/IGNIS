# Phase G2 — Experiment Management & Control Center: Testing & Manual Verification Guide

This document details the automated unit/integration test suite and a comprehensive step-by-step manual testing guide for **Phase G2 (Experiment Management & Dashboard Control Center)**.

---

## 1. Testing Strategy

Phase G2 components (`ProcessManager`, Pydantic API schemas, versioned REST endpoints `/api/v1/experiment/*`, Jinja2 layout templates, dashboard routes, and read-only scenario parsing) are validated using a multi-tiered approach:

1. **Unit Test Isolation (`test_process_manager.py`)**: Tests `ProcessManager` state machine transitions, singleton pattern isolation, PID management, Windows-compatible cooperative pause flag creation/removal, and log tail extraction.
2. **API Contract & Schema Testing (`test_experiment_api.py`)**: Validates REST HTTP endpoints under `/api/v1/experiment/*`, Pydantic payload models (`ExperimentRunRequest`, `ExperimentLoadRequest`), standardized `ErrorResponse` JSON contracts, HTTP status codes (200, 400, 404, 409, 500), and restart semantics.
3. **Dashboard Page & Template Inheritance Testing (`test_dashboard_routes.py` & `test_navigation.py`)**: Verifies template inheritance from `base.html`, consistent navbar inclusion across all pages (`/experiments`, `/reports`, `/charts`, `/scenarios`), active menu highlighting, and default **Newest First** report sorting.
4. **Scenario Parsing & Policy Enforcement (`test_scenario_routes.py`)**: Validates that YAML scenario definitions (S1–S7) are parsed cleanly into cards and that a strict **Read-Only** policy is enforced.
5. **Step-by-Step Manual Verification Guide (MANDATORY)**: End-to-end interactive manual verification in web browsers (Chrome, Edge, Firefox) and CLI tools (`curl`, PowerShell) covering real-time experiment launch, live log streaming, cooperative pause/resume on Windows, stop/restart semantics, error handling, report browsing, chart rendering, and scenario inspection.

---

## 2. Automated Test Suite Overview

| Test Module | Target Component | Coverage Description |
|---|---|---|
| [tests/test_process_manager.py](file:///d:/projects/IGNIS/tests/test_process_manager.py) | `ProcessManager` | Singleton isolation, state machine transitions (`IDLE`, `STARTING`, `RUNNING`, `PAUSED`, `STOPPING`, `COMPLETED`, `FAILED`), invalid transition rejection, pause flag handling, log reading |
| [tests/test_experiment_api.py](file:///d:/projects/IGNIS/tests/test_experiment_api.py) | REST API (`/api/v1/experiment/*`) | Endpoint execution, Pydantic schemas, HTTP 409 conflict handling, standardized `ErrorResponse` payloads, restart semantics |
| [tests/test_dashboard_routes.py](file:///d:/projects/IGNIS/tests/test_dashboard_routes.py) | Dashboard View Routes | Page rendering (`/experiments`, `/reports`, `/charts`), newest-first report discovery API (`/api/v1/reports/list`) |
| [tests/test_scenario_routes.py](file:///d:/projects/IGNIS/tests/test_scenario_routes.py) | Scenario Browser | YAML parsing for scenarios S1–S7, assertion extraction, read-only policy enforcement |
| [tests/test_navigation.py](file:///d:/projects/IGNIS/tests/test_navigation.py) | Template Architecture | Jinja2 `base.html` inheritance, shared `navbar.html` inclusion, active route highlighting |

---

## 3. Automated Test Execution

Run the complete Phase G2 automated test suite via Pytest:

```powershell
python -m pytest tests/test_process_manager.py tests/test_experiment_api.py tests/test_dashboard_routes.py tests/test_scenario_routes.py tests/test_navigation.py -v
```

**Expected Result**: All 18 tests pass cleanly in under 3 seconds with zero errors.

---

## 4. Step-by-Step Manual Testing Guide (MANDATORY)

Follow this guide to manually verify Phase G2 web interfaces, REST APIs, state machine execution, and subprocess isolation.

---

### Step 1: Start FastAPI Control Center Server

1. Open a terminal in the project root (`d:\projects\IGNIS`).
2. Launch the Cloud Dashboard server:
   ```powershell
   python -m uvicorn src.cloud_dashboard.app:app --port 9000
   ```
3. **Verification**:
   - Console logs confirm: `ProcessManager singleton registered in app.state.`
   - Console logs confirm: `IGNIS Cloud Dashboard initialized successfully.`
   - Server runs on `http://localhost:9000`.

---

### Step 2: Test Experiment Control Center (`http://localhost:9000/experiments`)

1. Open web browser and navigate to `http://localhost:9000/experiments`.
2. **Verification Checklist**:
   - Header title displays: **Experiment Control Center**.
   - Current state badge in top right displays `IDLE` (gray badge).
   - Execution Parameters form displays:
     - **Trials per Scenario**: `30` (default)
     - **Base Random Seed**: `4321` (default)
     - **Target Scenarios**: `All Scenarios (S1 - S7)`
     - **Clean output directory before run**: Checked
   - Action Buttons state:
     - **Run Experiment**: Enabled (blue)
     - **Pause**: Disabled
     - **Resume**: Disabled
     - **Stop**: Disabled
     - **Restart**: Enabled
   - Subprocess Output Log box displays log status.

---

### Step 3: Test Interactive Experiment Execution & Live Log Streaming

1. In the form, set **Trials per Scenario** to `5` and select **Target Scenarios** as `S3 - Communication Degradation & Buffer`.
2. Click **Run Experiment**.
3. **Verification Checklist**:
   - Action message displays: `Experiment started successfully.` (green text).
   - Current state badge updates to `RUNNING` (blue badge).
   - Execution State Details panel displays:
     - **Experiment ID**: `exp-YYYYMMDDTHHMMSSZ-{4hex}`
     - **Subprocess PID**: Integer process ID (e.g. `14208`)
     - **Started At**: ISO8601 timestamp
   - Action Buttons update dynamically:
     - **Run Experiment**: Disabled
     - **Pause**: Enabled
     - **Stop**: Enabled
     - **Resume**: Disabled
   - Subprocess Output Log box auto-refreshes every 2 seconds, displaying live stdout execution lines.
   - Verify that [results/logs/experiment.log](file:///d:/projects/IGNIS/results/logs/experiment.log) is created on disk.

---

### Step 4: Test Windows Cooperative Pause & Resume Execution

1. While the experiment is running (or during a multi-trial run), click **Pause**.
2. **Verification Checklist**:
   - Action message displays: `Pause signal sent.`
   - State badge updates to `PAUSED` (orange badge).
   - Action Buttons update:
     - **Resume**: Enabled
     - **Pause**: Disabled
     - **Run Experiment**: Disabled
     - **Stop**: Enabled
   - Check the project root directory (`d:\projects\IGNIS`): verify that `.pause_flag` file is created.
3. Click **Resume**.
4. **Verification Checklist**:
   - Action message displays: `Experiment resumed.`
   - State badge restores to `RUNNING` (blue badge).
   - Check project root directory: verify `.pause_flag` file is deleted.

---

### Step 5: Test Experiment Stop & Restart Semantics

1. While state is `RUNNING` or `PAUSED`, click **Stop**.
2. **Verification Checklist**:
   - Action message displays: `Experiment stopped.`
   - State badge updates to `COMPLETED` or `FAILED`.
   - Child subprocess PID is terminated.
   - **Run Experiment** button becomes enabled again.
3. Click **Restart**.
4. **Verification Checklist**:
   - Action message displays: `Experiment restarted with new ID.`
   - Verify a **brand new unique Experiment ID** is generated (different from previous run).
   - State badge transitions back to `RUNNING`.

---

### Step 6: Test Concurrent Run Conflict & Standardized Error Contracts

1. Keep an experiment running on the web dashboard.
2. Open a second terminal or PowerShell prompt and attempt to trigger a second run via REST API:
   ```powershell
   Invoke-RestMethod -Uri "http://localhost:9000/api/v1/experiment/run" -Method POST -ContentType "application/json" -Body '{"trials": 5, "seed": 100, "clean": false, "scenarios": "S1"}'
   ```
3. **Verification Checklist**:
   - Response returns HTTP Status `409 Conflict`.
   - JSON error payload conforms strictly to `ErrorResponse` schema:
     ```json
     {
       "error": "ExperimentAlreadyRunning",
       "message": "Cannot start experiment: Current state is RUNNING",
       "details": {
         "experiment_id": "exp-20260731T...",
         "state": "RUNNING",
         "pid": 14208
       }
     }
     ```

---

### Step 7: Test Historical Report Browser (`http://localhost:9000/reports`)

1. Open web browser and navigate to `http://localhost:9000/reports`.
2. **Verification Checklist**:
   - Header title displays: **Historical Report Browser**.
   - Navigation sidebar correctly highlights **Reports** as active item.
   - Reports table lists all discovered report files in `results/`, `reports/`, and `experiment_repository/`.
   - **Default Sort Order**: Reports are listed **Newest First** by last modified timestamp.
   - For HTML reports (`report.html`): Clicking **Open Interactive Report** opens the self-contained HTML report in a new tab.
   - For Markdown reports (`report.md`): Clicking **Preview Markdown** opens an inline preview panel showing full markdown file text.

---

### Step 8: Test Interactive Chart Gallery (`http://localhost:9000/charts`)

1. Open web browser and navigate to `http://localhost:9000/charts`.
2. **Verification Checklist**:
   - Header title displays: **Interactive Chart Gallery**.
   - Navigation sidebar correctly highlights **Charts** as active item.
   - Top right contains scenario filter select dropdown (`Filter: All Scenarios`, `Scenario S1`–`S7`).
   - Grid renders interactive Plotly.js charts:
     - Decision Latency Box Plot (`#chart-latency-box`)
     - Lateral Propagation CI Plot (`#chart-propagation-ci`)
     - False-Positive Rate Trend (`#chart-fp-trend`)
     - Offline Continuity Bar Chart (`#chart-offline-bar`)
   - Hovering over charts shows Plotly tooltips, zoom controls, and image export buttons.

---

### Step 9: Test Read-Only Scenario Browser (`http://localhost:9000/scenarios`)

1. Open web browser and navigate to `http://localhost:9000/scenarios`.
2. **Verification Checklist**:
   - Header title displays: **Scenario Browser (Read-Only)**.
   - Top right displays badge: `READ-ONLY POLICY ENFORCED`.
   - Navigation sidebar correctly highlights **Scenarios** as active item.
   - Scenario cards render parsed YAML configurations for scenarios S1 through S7.
   - Each card displays:
     - Scenario ID (e.g. `S1`, `S3`, `S4`) and YAML file name
     - Title and description
     - Target assertion rules list
     - Collapsible `<details>` section: `View Raw YAML Configuration`
   - **Policy Check**: Verify no editing, form submission, or file mutation options exist on this page.

---

### Step 10: Test REST API Endpoints via CLI / PowerShell

Run the following commands in PowerShell to verify versioned HTTP API endpoints:

#### 1. Query Experiment Status
```powershell
Invoke-RestMethod -Uri "http://localhost:9000/api/v1/experiment/status" -Method GET
```
**Expected Output**: `{"status": "success", "data": {"experiment_id": "...", "state": "IDLE", ...}}`

#### 2. Query Trailing Logs
```powershell
Invoke-RestMethod -Uri "http://localhost:9000/api/v1/experiment/logs?tail=10" -Method GET
```
**Expected Output**: `{"status": "success", "data": {"lines": [...], "tail": 10, "total_lines": ...}}`

#### 3. Query Discovered Reports API
```powershell
Invoke-RestMethod -Uri "http://localhost:9000/api/v1/reports/list" -Method GET
```
**Expected Output**: `{"status": "success", "data": {"reports": [...]}}`

---

## 5. Manual Testing Verification Checklist Summary

| # | Manual Verification Step | Target Component | Status |
|---|---|---|---|
| 1 | FastAPI server launches cleanly with `ProcessManager` lifespan registration | Dashboard App | ✅ PASS |
| 2 | `/experiments` renders control form, state badge (`IDLE`), and action buttons | Control Center | ✅ PASS |
| 3 | Clicking **Run Experiment** launches subprocess and streams live logs | Subprocess Manager | ✅ PASS |
| 4 | State badge transitions dynamically (`IDLE` → `STARTING` → `RUNNING`) | FSM Engine | ✅ PASS |
| 5 | Clicking **Pause** creates `.pause_flag` file and transitions state to `PAUSED` | Cooperative Pause | ✅ PASS |
| 6 | Clicking **Resume** removes `.pause_flag` file and restores state to `RUNNING` | Cooperative Resume | ✅ PASS |
| 7 | Clicking **Stop** terminates child process PID and sets state to `COMPLETED`/`FAILED` | Process Termination | ✅ PASS |
| 8 | Clicking **Restart** terminates active run and generates a **new Experiment ID** | Restart Semantics | ✅ PASS |
| 9 | Concurrent execution request returns HTTP 409 `ExperimentAlreadyRunning` error JSON | Error Contract | ✅ PASS |
| 10 | `/reports` page lists discovered reports sorted **Newest First** | Report Browser | ✅ PASS |
| 11 | Clicking **Open Interactive Report** loads HTML report in new tab | Report Browser | ✅ PASS |
| 12 | Clicking **Preview Markdown** opens inline text preview panel | Report Browser | ✅ PASS |
| 13 | `/charts` page renders Plotly.js charts with scenario filter select | Chart Gallery | ✅ PASS |
| 14 | `/scenarios` page renders YAML scenario cards (S1–S7) with read-only badge | Scenario Browser | ✅ PASS |
| 15 | `navbar.html` is rendered consistently across all pages via `base.html` inheritance | Navigation | ✅ PASS |
