# Phase G3 — Live Monitoring: Sub-Phase Implementation Plan

Phase G3 equips IGNIS with Server-Sent Events (SSE) streaming and real-time execution progress monitoring. It replaces polling-only status checks with an asynchronous event broadcast engine that streams live trial progress, real-time ETA estimates, scenario metric completions, and log events directly to the dashboard interface.

---

## Overview & Objectives

Following the completion of Phase G1 (Interactive Reporting Platform) and Phase G2 (Experiment Management & Control Center FSM), Phase G3 delivers real-time visibility into active simulation runs without client-side polling latency or filesystem reading overhead.

### Key Objectives
1. **Structured Progress Reporter (`ProgressReporter`)**: A typed service (`src/cloud_dashboard/services/progress_reporter.py`) emitting structured progress events to an in-memory `asyncio.Queue` for low-latency distribution, while simultaneously appending events to `results/progress_events.jsonl` for replay, debugging, and archival.
2. **Server-Sent Events (SSE) Broadcaster (`LiveMonitor`)**: An async broadcasting engine (`src/cloud_dashboard/services/live_monitor.py`) exposing `GET /api/v1/experiment/stream` (`text/event-stream`), supporting multi-client fan-out, automatic connection keep-alives (`HEARTBEAT` events every 15s), and clean client disconnect handling.
3. **Orchestrator Pipeline Integration**: Update `run_experiment.py` and `ProcessManager` to emit structured progress events at every pipeline stage (start, scenario start, trial completion, scenario completion, pipeline completion, failure).
4. **Pydantic Event Schemas (`src/cloud_dashboard/schemas.py`)**: Strongly-typed progress event structures for validation and OpenAPI spec generation.
5. **Real-time Control Center UI (`experiments.html`)**: Native browser `EventSource` integration updating progress bar (`0%`–`100%`), live trial counter (`Trial 7 / 30`), live scenario badge, elapsed time, and ETA ("ETA: 42s remaining") with automatic fallback to polling if SSE is interrupted.
6. **Strict Compliance with Professional Standards**: Clean text-and-colour presentation; zero emoji, decorative symbols, or consumer visual noise.

---

## User Review Required

> [!IMPORTANT]
> **SSE Broadcasting & Bounded Queue Fan-Out**: `LiveMonitor` maintains a registry of active client queues (`asyncio.Queue(maxsize=5000)`). When `ProgressReporter` emits an event, `LiveMonitor` fans out the payload to all connected SSE clients asynchronously.

> [!NOTE]
> **Active Experiment Replay Window & Graceful Disconnect**: If a browser opens mid-experiment, `LiveMonitor` filters `results/progress_events.jsonl` for events matching the **currently active `experiment_id`** and replays them to instantly catch up the new client. When an experiment reaches `EXPERIMENT_COMPLETE` or `EXPERIMENT_FAILED`, the server gracefully closes the `EventSource` stream and the client transitions to an idle state.

---

## Open Questions

None. The SSE streaming architecture, event schemas, ETA calculation formula, and template changes are fully specified.

---

## Technical Deliverables & File Manifest

| Action | Path | Description |
|---|---|---|
| **[NEW]** | [src/cloud_dashboard/services/progress_reporter.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/progress_reporter.py) | Structured progress reporter emitting JSON events with `event_id`, `sequence`, `schema_version` to `asyncio.Queue` and `.jsonl` file |
| **[NEW]** | [src/cloud_dashboard/services/live_monitor.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/live_monitor.py) | Async SSE progress broadcaster supporting bounded queues (`maxsize=5000`), multi-client fan-out, 15s `HEARTBEAT` events, active experiment replay filtering, and `finally: unregister_client()` cleanup |
| **[MODIFY]** | [src/cloud_dashboard/schemas.py](file:///d:/projects/IGNIS/src/cloud_dashboard/schemas.py) | Pydantic event schemas (`ProgressEvent`, `TrialProgressData`, `ScenarioCompleteData`, etc.) |
| **[MODIFY]** | [src/cloud_dashboard/routes/experiments.py](file:///d:/projects/IGNIS/src/cloud_dashboard/routes/experiments.py) | Added `GET /api/v1/experiment/stream` SSE streaming endpoint with `try/finally` client queue unregistration |
| **[MODIFY]** | [src/run_experiment.py](file:///d:/projects/IGNIS/src/run_experiment.py) | Emits structured progress events across all 9 execution pipeline stages |
| **[MODIFY]** | [src/cloud_dashboard/templates/experiments.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/experiments.html) | Native browser `EventSource` integration, live progress bar, ETA, live trial stats, and graceful stream closure on completion |
| **[NEW]** | [docs/phase-g/g3/implementation_plan.md](file:///d:/projects/IGNIS/docs/phase-g/g3/implementation_plan.md) | Sub-phase G3 specification document in repository |
| **[NEW]** | [tests/test_progress_reporter.py](file:///d:/projects/IGNIS/tests/test_progress_reporter.py) | Unit tests for `ProgressReporter` queue emission, `event_id`/`sequence` generation, and `.jsonl` logging |
| **[NEW]** | [tests/test_live_monitor.py](file:///d:/projects/IGNIS/tests/test_live_monitor.py) | Unit tests for `LiveMonitor` SSE fanout, multi-client subscription, bounded queues, active replay filtering, and `HEARTBEAT` events |
| **[NEW]** | [tests/test_sse_api.py](file:///d:/projects/IGNIS/tests/test_sse_api.py) | Integration tests for `GET /api/v1/experiment/stream` SSE endpoint and disconnect cleanup |
| **[NEW]** | [tests/test_live_ui.py](file:///d:/projects/IGNIS/tests/test_live_ui.py) | Integration tests for `EventSource` UI script, graceful stream closure, and progress bar DOM updates |

---

## Detailed Architectural Specifications

### 1. Progress Event Specifications (`schemas.py` & `progress_reporter.py`)

Progress events use a standardized JSON payload structure featuring `schema_version`, unique `event_id`, and monotonic `sequence` counter:

```json
{
  "schema_version": "1.0",
  "event": "TRIAL_PROGRESS",
  "event_id": "exp-20260731T140000Z-9f12-000184",
  "sequence": 184,
  "experiment_id": "exp-20260731T140000Z-9f12",
  "scenario_id": "S3",
  "trial": 7,
  "total_trials": 30,
  "scenario_index": 3,
  "total_scenarios": 7,
  "elapsed_sec": 42.5,
  "eta_sec": 128.0,
  "progress_pct": 34.2,
  "timestamp": "2026-07-31T14:00:42.500000Z"
}
```

#### Event Classification Table

| Event Type | Trigger | Key Payload Data |
|---|---|---|
| `EXPERIMENT_STARTED` | Orchestrator pipeline init | `schema_version`, `event_id`, `sequence`, `experiment_id`, `config`, `total_scenarios`, `total_trials`, `start_time` |
| `SCENARIO_STARTED` | Scenario execution start | `schema_version`, `event_id`, `sequence`, `scenario_id`, `scenario_index`, `total_scenarios` |
| `TRIAL_PROGRESS` | Each trial completion | `schema_version`, `event_id`, `sequence`, `scenario_id`, `trial`, `total_trials`, `elapsed_sec`, `eta_sec`, `progress_pct` |
| `SCENARIO_COMPLETE` | Scenario execution end | `schema_version`, `event_id`, `sequence`, `scenario_id`, `status` (`PASS`/`FAIL`/`INVALID`), `duration_sec`, `metrics` |
| `EXPERIMENT_COMPLETE` | Orchestrator complete | `schema_version`, `event_id`, `sequence`, `overall_verdict`, `duration_sec`, `summary_stats` |
| `EXPERIMENT_FAILED` | Pipeline failure | `schema_version`, `event_id`, `sequence`, `error_code`, `error_message`, `failed_at_scenario` |

---

### 2. SSE Broadcaster & Stream Endpoint (`live_monitor.py` & `experiments.py`)

#### `GET /api/v1/experiment/stream`
- Response Header: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`.
- Client Queue & Cleanup: On connect, `LiveMonitor` registers a bounded `asyncio.Queue(maxsize=5000)`. Streaming handler uses `try ... finally: live_monitor.unregister_client(queue)` to ensure zero queue leaks on disconnect.
- Active Experiment Replay Window: When a client connects mid-experiment, `LiveMonitor` reads `results/progress_events.jsonl`, filters for events where `experiment_id == active_experiment_id`, and replays them to catch up the client instantly.
- Heartbeats: Emits `event: HEARTBEAT` (`data: {"schema_version": "1.0", "timestamp": "..."}`) every 15 seconds to keep browser connections alive without confusion with WebSocket ping frames.
- Format:
  ```http
  event: TRIAL_PROGRESS
  data: {"schema_version":"1.0","event":"TRIAL_PROGRESS","event_id":"exp-...-000184","sequence":184,"experiment_id":"exp-...","scenario_id":"S3","trial":7,"total_trials":30,"progress_pct":34.2,"eta_sec":128.0}

  event: HEARTBEAT
  data: {"schema_version":"1.0","timestamp":"2026-07-31T14:01:00Z"}
  ```

#### ETA Calculation Formula
$$\text{Progress \%} = \frac{(\text{scenario\_index} - 1) \times \text{total\_trials} + \text{trial}}{\text{total\_scenarios} \times \text{total\_trials}} \times 100$$

$$\text{ETA (seconds)} = \left( \frac{\text{Elapsed Time}}{\text{Progress \%}} \times (100 - \text{Progress \%}) \right)$$

Moving average smoothing (alpha = 0.2) is applied to prevent jumpy ETA displays.

---

### 3. Front-End EventSource Integration (`experiments.html`)

- `experiments.html` initializes a native JavaScript `EventSource('/api/v1/experiment/stream')`.
- Event Handlers:
  - `addEventListener('EXPERIMENT_STARTED', ...)` -> Resets progress bar to 0%, sets status badge to `RUNNING`.
  - `addEventListener('SCENARIO_STARTED', ...)` -> Updates active scenario label (e.g. `Running S3 - Communication Degradation`).
  - `addEventListener('TRIAL_PROGRESS', ...)` -> Updates progress bar width (`34.2%`), trial badge (`Trial 7 / 30`), elapsed timer, and ETA label (`ETA: 1m 48s`).
  - `addEventListener('SCENARIO_COMPLETE', ...)` -> Updates scenario verdict list.
  - `addEventListener('EXPERIMENT_COMPLETE', ...)` -> Sets progress bar to 100%, updates badge to `COMPLETED`, **gracefully closes `EventSource` connection**, and disables polling.
  - `addEventListener('EXPERIMENT_FAILED', ...)` -> Updates badge to `FAILED`, **gracefully closes `EventSource` connection**, and disables polling.
- Disconnect / Error Handling: If `EventSource` connection drops while experiment is active, UI falls back to 2-second HTTP polling (`/api/v1/experiment/status`) and attempts reconnection.

---

## Acceptance Criteria Checklist

| # | Acceptance Criterion | Status |
|---|---|---|
| 1 | `ProgressReporter` emits structured JSON events containing `schema_version`, `event_id`, and `sequence` to `asyncio.Queue` with < 50ms latency |  PENDING |
| 2 | Progress events are simultaneously persisted to `results/progress_events.jsonl` |  PENDING |
| 3 | `GET /api/v1/experiment/stream` returns HTTP `200` with `Content-Type: text/event-stream` |  PENDING |
| 4 | `LiveMonitor` uses bounded client queues (`maxsize=5000`) and handles multi-client fan-out without memory leaks |  PENDING |
| 5 | `LiveMonitor` sends explicit `event: HEARTBEAT` messages every 15 seconds to keep browser connections alive |  PENDING |
| 6 | Late-joining clients receive catch-up replay from `progress_events.jsonl` filtered strictly by active `experiment_id` |  PENDING |
| 7 | `run_experiment.py` emits `EXPERIMENT_STARTED`, `SCENARIO_STARTED`, `TRIAL_PROGRESS`, `SCENARIO_COMPLETE`, `EXPERIMENT_COMPLETE` |  PENDING |
| 8 | Progress percentage calculation correctly accounts for scenario index and trial index |  PENDING |
| 9 | ETA calculation uses exponential moving average smoothing for steady display |  PENDING |
| 10 | `experiments.html` renders dynamic live progress bar (`0%` to `100%`) using `EventSource` |  PENDING |
| 11 | `experiments.html` displays live trial counter (`Trial X / Y`) and estimated ETA |  PENDING |
| 12 | Browser UI gracefully falls back to HTTP status polling if SSE connection drops while experiment is active |  PENDING |
| 13 | Streaming handler uses `try ... finally: live_monitor.unregister_client()` to guarantee zero queue leakage on client disconnect |  PENDING |
| 14 | All progress event structures conform strictly to Pydantic models in `schemas.py` |  PENDING |
| 15 | UI maintains professional engineering appearance (zero emoji, text-and-colour badges only) |  PENDING |
| 16 | After `EXPERIMENT_COMPLETE` or `EXPERIMENT_FAILED`, the `EventSource` connection is gracefully closed by the server/client and transitions to a polling-disabled idle state |  PENDING |

---

## Comprehensive Test Plan

The G3 test suite is organized into 4 dedicated test modules under `tests/`:

1. **`tests/test_progress_reporter.py`**:
   - Unit tests for event queue placement.
   - Unit tests for `schema_version`, `event_id`, and `sequence` generation.
   - Unit tests for `results/progress_events.jsonl` file appending and JSON formatting.
   - Test progress percentage and ETA math calculations.

2. **`tests/test_live_monitor.py`**:
   - Unit tests for `LiveMonitor` client subscription registration and unregistration.
   - Bounded queue overflow safety test (`maxsize=5000`).
   - Fan-out broadcasting test ensuring all active client queues receive emitted events.
   - Heartbeat generator test verifying 15s `event: HEARTBEAT` messages.
   - Active experiment replay window test verifying catch-up events filtered by `experiment_id`.

3. **`tests/test_sse_api.py`**:
   - Integration tests for `GET /api/v1/experiment/stream` SSE endpoint.
   - Verifies HTTP response headers (`text/event-stream`, `no-cache`).
   - Validates event streaming format (`event: ...\ndata: ...\n\n`).
   - Tests disconnect cleanup (`unregister_client`).

4. **`tests/test_live_ui.py`**:
   - Integration tests verifying `experiments.html` contains `EventSource` initialization script.
   - Verifies graceful `EventSource.close()` call upon receiving `EXPERIMENT_COMPLETE`.
   - DOM element presence check for progress bar, trial counter, and ETA label.

---

## Verification Commands

```bash
# Run full Phase G3 test suite
python -m pytest tests/test_progress_reporter.py tests/test_live_monitor.py tests/test_sse_api.py tests/test_live_ui.py -v

# Launch dashboard locally to test live SSE streaming UI
python -m uvicorn src.cloud_dashboard.app:app --port 9000
```
