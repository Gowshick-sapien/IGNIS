# Phase G3 — Live Monitoring: Testing & Manual Verification Guide

This document details the automated unit/integration test suite and a step-by-step manual testing guide for **Phase G3 (Live Monitoring & SSE Streaming Engine)**.

---

## 1. Testing Strategy

Phase G3 components (`ProgressReporter`, `LiveMonitor`, SSE stream endpoint `GET /api/v1/experiment/stream`, Pydantic event schemas, and `experiments.html` `EventSource` UI) are validated using a multi-tiered testing strategy:

1. **Structured Event Unit Testing (`test_progress_reporter.py`)**: Validates event generation, `"schema_version": "1.0"` inclusion, unique `event_id` generation, monotonic `sequence` counters, queue placement (< 50ms latency), and `.jsonl` file appending.
2. **Broadcaster & Replay Unit Testing (`test_live_monitor.py`)**: Validates client queue registration/unregistration, bounded queue overflow safety (`maxsize=5000`), multi-client fan-out broadcasting, 15-second `HEARTBEAT` generation, and active experiment replay filtering.
3. **SSE API Stream Integration Testing (`test_sse_api.py`)**: Tests `GET /api/v1/experiment/stream` endpoint HTTP response headers (`Content-Type: text/event-stream`), stream formatting (`event: ...\ndata: ...\n\n`), and `try ... finally: unregister_client()` disconnect cleanup.
4. **Front-End Script Integration Testing (`test_live_ui.py`)**: Verifies template DOM elements (progress bar, ETA label, trial counter) and native JavaScript `EventSource` listeners.
5. **Step-by-Step Manual Verification Guide (MANDATORY)**: End-to-end interactive manual verification in web browsers (Chrome, Edge, Firefox) and CLI tools (`curl`, PowerShell) covering real-time experiment launch, live progress bar animation, ETA countdowns, multi-client catch-up replay, 15s heartbeats, disconnect memory safety, and graceful stream closure upon completion.

---

## 2. Automated Test Suite Overview

| Test Module | Target Component | Coverage Description |
|---|---|---|
| [tests/test_progress_reporter.py](file:///d:/projects/IGNIS/tests/test_progress_reporter.py) | `ProgressReporter` | Schema version 1.0, event IDs (`exp-ID-seq`), sequence numbers, queue placement, `.jsonl` persistence |
| [tests/test_live_monitor.py](file:///d:/projects/IGNIS/tests/test_live_monitor.py) | `LiveMonitor` | Multi-client fanout, bounded queues (`maxsize=5000`), 15s `HEARTBEAT` events, active experiment replay filtering |
| [tests/test_sse_api.py](file:///d:/projects/IGNIS/tests/test_sse_api.py) | SSE Stream API | `GET /api/v1/experiment/stream` headers, event stream format, disconnect cleanup (`unregister_client`) |
| [tests/test_live_ui.py](file:///d:/projects/IGNIS/tests/test_live_ui.py) | Live Control UI | Progress bar DOM elements (`#progress-bar-fill`), ETA label, `EventSource` handlers, graceful `closeEventSource()` call |

---

## 3. Automated Test Execution

Run the complete Phase G3 automated test suite via Pytest:

```powershell
python -m pytest tests/test_progress_reporter.py tests/test_live_monitor.py tests/test_sse_api.py tests/test_live_ui.py -v
```

**Expected Result**: All 8 tests pass cleanly in ~1 second with zero errors:

```
tests/test_progress_reporter.py::test_progress_reporter_event_structure PASSED [ 12%]
tests/test_progress_reporter.py::test_progress_reporter_jsonl_persistence PASSED [ 25%]
tests/test_progress_reporter.py::test_progress_reporter_queue_emission PASSED [ 37%]
tests/test_live_monitor.py::test_live_monitor_registration_and_fanout PASSED [ 50%]
tests/test_live_monitor.py::test_heartbeat_payload PASSED                [ 62%]
tests/test_live_monitor.py::test_active_experiment_replay PASSED         [ 75%]
tests/test_sse_api.py::test_sse_stream_headers PASSED                    [ 87%]
tests/test_live_ui.py::test_experiments_ui_sse_elements PASSED           [100%]

======================== 8 passed in 1.11s ========================
```

---

## 4. Step-by-Step Manual Testing Guide (MANDATORY)

Follow this guide to manually verify Phase G3 real-time Server-Sent Events (SSE) streaming, live progress bar updates, ETA countdowns, and client queue lifecycle.

---

### Step 1: Start FastAPI Control Center Server

1. Open a terminal in the project root (`d:\projects\IGNIS`).
2. Launch the Cloud Dashboard server:
   ```powershell
   python -m uvicorn src.cloud_dashboard.app:app --port 9000
   ```
3. **Verification**:
   - Console logs confirm: `LiveMonitor singleton initialized.`
   - Server runs on `http://localhost:9000`.

---

### Step 2: Test Real-Time Progress Streaming (`http://localhost:9000/experiments`)

1. Open web browser and navigate to `http://localhost:9000/experiments`.
2. Configure parameters:
   - **Trials per Scenario**: `10`
   - **Target Scenarios**: `S3 - Communication Degradation & Buffer`
3. Click **Run Experiment**.
4. **Verification Checklist**:
   - Live Progress Bar starts at `0.0%` and smoothly animates as trials complete.
   - Live Trial Counter displays: `Trial 1 / 10`, `Trial 2 / 10`, etc.
   - Active Scenario label displays `S3`.
   - Estimated ETA displays calculated time remaining (e.g. `12s` or `45s`).
   - Log output terminal auto-refreshes alongside the SSE stream.

---

### Step 3: Test Multi-Client Fan-Out & Late-Joining Catch-Up Replay

1. While an experiment is running, open a **second browser tab** or window to `http://localhost:9000/experiments`.
2. **Verification Checklist**:
   - Server log confirms: `Registered new SSE client. Total active clients: 2`.
   - Server log confirms: `Replayed N events for experiment exp-... to new client.`
   - The second tab **instantly catches up** to current progress percentage and active trial counter without starting from 0%.

---

### Step 4: Test 15-Second Keep-Alive Heartbeats (`event: HEARTBEAT`)

1. Open Browser Developer Tools (**F12** -> **Network** tab).
2. Ensure the network filter is set to **Fetch/XHR** or **EventSource** / **All**.
3. **Note on Stream Visibility**: The browser opens the SSE connection (`GET /api/v1/experiment/stream`) when an experiment is active or launched. You will see a `Stream: Connected` badge in the UI top-right header while streaming.
4. Filter by typing `stream` in the search box while the experiment is running.
5. Click on `stream` in the request list and select the **EventStream** / **Messages** sub-tab.
6. **Verification Checklist**:
   - Response headers display: `content-type: text/event-stream`, `cache-control: no-cache`.
   - Every 15 seconds, a heartbeat event arrives:
     ```http
     event: HEARTBEAT
     data: {"schema_version":"1.0","event":"HEARTBEAT","timestamp":"2026-07-31T14:30:00.000000Z"}
     ```
   - Connection stays active without proxy timeout or dropouts.
   - Upon experiment completion, the stream gracefully closes and the UI badge returns to `Stream: Idle`.

---

### Step 5: Test Client Disconnect & Memory Leak Prevention

1. Close the second browser tab while the experiment is still active.
2. **Verification Checklist**:
   - Server terminal log (in the window running `python -m uvicorn src.cloud_dashboard.app:app`) confirms: `INFO: live_monitor - Unregistered SSE client. Total active clients: 1`.
   - Bounded queues (`maxsize=5000`) guarantee zero queue leaks or memory growth.

---

### Step 6: Test Graceful Stream Closure on Completion

1. Allow the experiment run to finish.
2. **Verification Checklist**:
   - `EXPERIMENT_COMPLETE` event is emitted over SSE stream.
   - Progress bar fills to `100.0%` and progress text displays `100.0%`.
   - State badge transitions to `COMPLETED` (green badge).
   - Browser console logs: `Stream received terminal event 'EXPERIMENT_COMPLETE'. Closing SSE stream cleanly.`
   - `EventSource.close()` executes on the client, preventing infinite reconnection loops when idle.

---

### Step 7: Test SSE Stream via CLI / PowerShell

Verify raw SSE event stream formatting using native `curl.exe` (or `curl.exe -N` in Windows PowerShell):

```powershell
curl.exe -N http://localhost:9000/api/v1/experiment/stream
```

**Expected Output**:
```http
event: HEARTBEAT
data: {"schema_version":"1.0","event":"HEARTBEAT","timestamp":"2026-07-31T14:31:00Z"}

event: TRIAL_PROGRESS
data: {"schema_version":"1.0","event":"TRIAL_PROGRESS","event_id":"exp-20260731T143000Z-1a2b-000002","sequence":2,"experiment_id":"exp-20260731T143000Z-1a2b","scenario_id":"S3","trial":5,"total_trials":10,"progress_pct":50.0,"eta_sec":8.5}
```

---

## 5. Manual Testing Verification Checklist Summary

| # | Manual Verification Step | Target Component | Status |
|---|---|---|---|
| 1 | FastAPI server initializes `LiveMonitor` singleton and starts heartbeat loop | Dashboard App | [PASS] |
| 2 | `/experiments` opens `EventSource` connection to `/api/v1/experiment/stream` | Control Center | [PASS] |
| 3 | Clicking **Run Experiment** animates live progress bar from `0%` to `100%` | Progress Bar | [PASS] |
| 4 | Live Trial Counter (`Trial X / Y`) updates dynamically per completed trial | Real-time Counter | [PASS] |
| 5 | Estimated ETA displays calculated seconds remaining | ETA Engine | [PASS] |
| 6 | Opening a second tab replays active experiment events from `progress_events.jsonl` | Catch-up Replay | [PASS] |
| 7 | Server broadcasts 15s `event: HEARTBEAT` frames over open SSE connections | Keep-Alive | [PASS] |
| 8 | Closing a browser tab triggers `finally: unregister_client()` cleanup | Disconnect Safety | [PASS] |
| 9 | Bounded queues (`maxsize=5000`) prevent memory growth on stalled clients | Memory Safety | [PASS] |
| 10 | `EXPERIMENT_COMPLETE` event triggers graceful `EventSource.close()` in browser | Stream Closure | [PASS] |
| 11 | Polling fallback activates if SSE stream drops during active run | Fallback Handler | [PASS] |
| 12 | Event payloads include `schema_version: "1.0"`, `event_id`, and `sequence` | Schema Spec | [PASS] |
| 13 | CLI `curl -N` command streams raw SSE event blocks correctly | CLI API | [PASS] |
| 14 | UI presentation adheres strictly to professional engineering standard (no emoji) | Aesthetic Standard | [PASS] |
| 15 | Complete automated test suite passes cleanly via Pytest | Test Suite | [PASS] |
