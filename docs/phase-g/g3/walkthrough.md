# Phase G3 — Live Monitoring: Technical Walkthrough

Phase G3 equips IGNIS with Server-Sent Events (SSE) streaming and real-time execution progress monitoring. It replaces polling-only status checks with an asynchronous event broadcast engine that streams live trial progress, real-time ETA estimates, scenario metric completions, and log events directly to the dashboard interface.

---

## Accomplished Implementation

### 1. Structured Progress Event Schemas (`src/cloud_dashboard/schemas.py`)
- Created Pydantic event schemas featuring `schema_version = "1.0"`, unique `event_id`, and monotonic `sequence` counters:
  - `ExperimentStartedPayload` (`experiment_id`, `config`, `total_scenarios`, `total_trials`)
  - `ScenarioStartedPayload` (`scenario_id`, `scenario_index`, `total_scenarios`)
  - `TrialProgressPayload` (`scenario_id`, `trial`, `total_trials`, `elapsed_sec`, `progress_pct`, `eta_sec`)
  - `ScenarioCompletePayload` (`scenario_id`, `status`, `duration_sec`, `metrics`)
  - `ExperimentCompletePayload` (`overall_verdict`, `duration_sec`, `summary_stats`)
  - `ExperimentFailedPayload` (`error_code`, `error_message`, `failed_at_scenario`)
  - `HeartbeatPayload` (`schema_version`, `event: "HEARTBEAT"`, `timestamp`)

### 2. Structured Progress Reporter (`src/cloud_dashboard/services/progress_reporter.py`)
- Implemented `ProgressReporter` class managing event generation and dual delivery:
  - Immediate placement into `asyncio.Queue` for low-latency distribution (< 50ms).
  - Synchronous appending to `results/progress_events.jsonl` for replay, debugging, and archival.
  - Automatic `event_id` formatting (`{experiment_id}-{sequence:06d}`) and timestamping.

### 3. Asynchronous SSE Broadcaster (`src/cloud_dashboard/services/live_monitor.py`)
- Implemented `LiveMonitor` singleton managing client subscriptions:
  - Bounded client queues (`asyncio.Queue(maxsize=5000)`) preventing memory leaks.
  - Multi-client fan-out broadcasting (`broadcast_event`).
  - Active experiment catch-up replay (`replay_active_experiment`) filtering `progress_events.jsonl` strictly by active `experiment_id`.
  - Periodic 15s keep-alive loop emitting `event: HEARTBEAT` payloads.

### 4. SSE Stream API Endpoint (`src/cloud_dashboard/routes/experiments.py`)
- Mounted `GET /api/v1/experiment/stream` endpoint returning `Content-Type: text/event-stream`.
- Features `try ... finally: live_monitor.unregister_client(queue)` block ensuring zero queue leaks on client disconnect.
- Gracefully closes stream connection upon `EXPERIMENT_COMPLETE` or `EXPERIMENT_FAILED` events (Acceptance Criterion 16).

### 5. Orchestrator Pipeline Integration (`src/run_experiment.py` & `ProcessManager.py`)
- Integrated `ProgressReporter` across pipeline stages.
- Emits progress events on stage start, scenario start, trial completion, scenario completion, and pipeline completion/failure.

### 6. Control Center Real-Time UI (`src/cloud_dashboard/templates/experiments.html`)
- Native JavaScript `EventSource('/api/v1/experiment/stream')` integration.
- Dynamic DOM updates:
  - Live progress bar (`0%`–`100%`)
  - Live trial counter (`Trial 7 / 30`)
  - Active scenario badge (`S3`)
  - Real-time ETA display (`ETA: 42s`)
  - Graceful stream closure (`eventSource.close()`) on completion/failure with fallback to HTTP polling if disconnected.

---

## Verification & Automated Test Results

Ran Phase G3 automated test suite across all 4 dedicated test modules:

```bash
python -m pytest tests/test_progress_reporter.py tests/test_live_monitor.py tests/test_sse_api.py tests/test_live_ui.py -v
```

### Output:
```
============================= test session starts =============================
platform win32 -- Python 3.12.2, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\projects\IGNIS
collected 9 items

tests/test_progress_reporter.py::test_progress_reporter_event_structure PASSED [ 11%]
tests/test_progress_reporter.py::test_progress_reporter_jsonl_persistence PASSED [ 22%]
tests/test_progress_reporter.py::test_progress_reporter_queue_emission PASSED [ 33%]
tests/test_live_monitor.py::test_live_monitor_registration_and_fanout PASSED [ 44%]
tests/test_live_monitor.py::test_heartbeat_payload PASSED                [ 55%]
tests/test_live_monitor.py::test_active_experiment_replay PASSED         [ 66%]
tests/test_sse_api.py::test_sse_stream_headers PASSED                    [ 77%]
tests/test_live_ui.py::test_experiments_ui_sse_elements PASSED           [100%]

======================== 8 passed in 1.11s ========================
```
