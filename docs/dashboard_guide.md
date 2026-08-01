# IGNIS Cloud Dashboard — Version 1 Complete Documentation

**System Title:** IGNIS Central Operations & Research Control Center  
**Framework Version:** 2.0.0 (IGNIS v1 Core Platform Complete)  
**Parent Project:** Autonomous Wildfire Early Warning and Pre-Suppression Using Edge-Fog-Cloud (EFC) Architecture in Indian Forest Ecosystems

---

## 1. Executive Summary

The **IGNIS Cloud Dashboard** serves as the central operational hub and research testbed visualization engine for the IGNIS Edge-Fog-Cloud wildfire prevention platform. Designed to meet the dual requirements of **Real-Time Regional Operations (NOC)** and **Scientific Research & Experimentation**, the dashboard provides complete visibility into telemetry ingestion, fog decision states, lateral coordination timelines, benchmark metric evaluations, regression analysis, and reproducibility publishing.

The UI is built with a high-contrast dark theme (`#0f172a` / `#1e293b` palette with `#38bdf8` active highlights), strict professional formatting (zero emojis/decorative icons), responsive layouts, and low-latency SSE/polling updates.

---

## 2. Navigation Map & Route Summary Table

| Page Name | URL Route | HTTP Method | Primary Role & Core Purpose | Target Audience |
| :--- | :--- | :--- | :--- | :--- |
| **Regional Operations NOC** | `/` | `GET` | Real-time zone monitoring, system health checking, lateral event timeline, advisory command overrides over MQTT. | Regional Operators, NOC Engineers |
| **Experiment Control Center** | `/experiments` | `GET` | Interactive simulation execution control, parameter tuning, SSE progress streaming, process state management, live console logs. | Research Scientists, Test Engineers |
| **Historical Report Browser** | `/reports` | `GET` | Automated cataloging and rendering of generated HTML and Markdown research reports (sorted Newest First). | Research Authors, Reviewers |
| **Historical Experiment Repository**| `/repository` | `GET` | Read-only search, multi-field filtering, sorting, pagination, and detailed inspection of all archived experiment runs. | Data Engineers, Auditors |
| **Side-by-Side Comparison** | `/comparison` | `GET` | Side-by-side metric diffs, verdict deltas, confidence interval overlaps, and automated regression detection against baseline rules. | System Architects, QA Lead |
| **Interactive Chart Gallery** | `/charts` | `GET` | Visual gallery of performance distributions, decision latency curves, lateral propagation timelines, and false positive rates. | Data Analysts, Researchers |
| **Real-Time Benchmarks** | `/metrics` | `GET` | Executive KPI dashboard summarizing key validation metrics (latency, propagation speed, continuity, crosstalk). | Executive Sponsors, Architects |
| **Scenario Definition Browser** | `/scenarios` | `GET` | Read-only catalog of YAML scenario specifications (S1–S7) showing assertions, parameters, and raw YAML specs. | Simulation Engineers |
| **Settings & Export Hub** | `/settings` | `GET` | Configuration manager, export capability matrix, formats exporter (MD, HTML, CSV, JSON, ZIP, PDF, DOCX), and reproducibility bundle builder. | Platform Admin, Researchers |

---

## 3. Detailed Page Breakdown

### 3.1. Regional Operations NOC (`/`)
* **URL:** [http://localhost:8000/](http://localhost:8000/)
* **Primary Role:** Real-Time Operational Monitoring & Advisory Command Center.
* **Update Mechanism:** Polling every 2.0s via `/api/snapshot?zone_id=4B` and `/api/lateral-timeline`.
* **Key Components & Features:**
  * **System Component Health Bar:** Status monitors for Cloud Broker (MQTT), InfluxDB Time-Series DB, Fog Node instance, and Cloud Ingestor service.
  * **Zone Status Overview Card:** Real-time Wildfire Hazard Index (WHI score), state classification (`NORMAL`, `ELEVATED`, `CRITICAL`), clamping status, and advisory override badge.
  * **Edge Sensor Telemetry Table:** Live node-by-node telemetry stream displaying Temperature (°C), Humidity (%), Wind Speed (km/h), Smoke (PPM), and Flame Detection status.
  * **Lateral Coordination Event Timeline:** Visual timeline mapping inter-fog peer events, hazard propagation, and peer-to-peer warning message exchanges.
  * **Operator Advisory Control Panel:** Form to issue binding operational commands (`SET_SAFETY_MODE`, `FORCE_CLAMP_WHI`, `RESET_OVERRIDE`, `ADJUST_THRESHOLD`) with custom parameters and TTL. Dispatches payloads to MQTT topic `ignis/v1/advisory/zone/{zone_id}/command` and logs audit records to InfluxDB.
  * **Live Alerts & Audit Log Feed:** Real-time log stream recording system state changes, safety clamps, and operator actions.

---

### 3.2. Experiment Control Center (`/experiments`)
* **URL:** [http://localhost:8000/experiments](http://localhost:8000/experiments)
* **Primary Role:** Interactive Simulation Lifecycle & Process Control.
* **Update Mechanism:** Server-Sent Events (SSE) live connection stream (`/api/v1/experiment/stream`).
* **Key Components & Features:**
  * **Configuration Panel:** Form input for total trials, random seed initialization, clean output directory toggle, and scenario checklist selection (Scenarios S1 through S7).
  * **Process Control Toolbar:** Interactive buttons for `Run`, `Pause`, `Resume`, `Stop`, `Restart`, `Clean`, and `Load` results.
  * **Process State Machine Badge:** Color-coded status badge indicating execution state (`IDLE`, `STARTING`, `RUNNING`, `PAUSED`, `COMPLETED`, `FAILED`).
  * **Live Progress Bar:** Shows percentage completion, active trial index, and current scenario step.
  * **Terminal Console Log Viewer:** Real-time streaming stdout/stderr log output with line buffering, auto-scroll, and log filtering.
  * **Active Results Preview:** Instant metrics summary once simulation execution completes.

---

### 3.3. Historical Report Browser (`/reports`)
* **URL:** [http://localhost:8000/reports](http://localhost:8000/reports)
* **Primary Role:** Report Cataloging & In-Browser Documentation Viewing.
* **Update Mechanism:** Direct filesystem discovery across `results/`, `reports/`, and `experiment_repository/`.
* **Key Components & Features:**
  * **Report Catalog List:** Discovered HTML (`.html`) and Markdown (`.md`) reports automatically sorted Newest First by modification timestamp.
  * **Report Metadata Cards:** File path, relative location, format tag, and formatted UTC timestamp.
  * **Interactive Report Renderer:** Native iframe viewer for HTML reports and markdown renderer for text reports.

---

### 3.4. Historical Experiment Repository (`/repository`)
* **URL:** [http://localhost:8000/repository](http://localhost:8000/repository)
* **Primary Role:** Archived Experiment Search, Audit & Drill-Down Browser.
* **Update Mechanism:** REST API query `/api/v1/repository` against `RepositoryManager` metadata index.
* **Key Components & Features:**
  * **Multi-Parameter Search & Filter Bar:** Filter by verdict (`PASS`, `FAIL`, `INVALID`), scenario ID (`S1`–`S7`), Git Commit Hash prefix, and ISO8601 Date Ranges (`from_date`, `to_date`).
  * **Sorting & Pagination Controls:** Sort by timestamp, verdict, duration, or trial count (asc/desc), with page navigation.
  * **Experiment Archive Grid / Table:** Displays Run ID, Timestamp, Git Commit, Verdict, Duration, and Pass Rate.
  * **Detail Inspector Modal / Drawer:** Clicking any run reveals complete JSON metadata, scenario results, environment parameters (Python/OS info), link to archived `report.html`, and embedded Matplotlib chart images.

---

### 3.5. Side-by-Side Experiment Comparison (`/comparison`)
* **URL:** [http://localhost:8000/comparison](http://localhost:8000/comparison)
* **Primary Role:** Comparative Performance Analysis & Regression Detection.
* **Update Mechanism:** REST API query `/api/v1/experiments/compare?a={expA}&b={expB}` invoking `ComparisonService` and `RegressionDetector`.
* **Key Components & Features:**
  * **Experiment Picker Dropdowns:** Select Baseline Experiment (Experiment A) and Target Experiment (Experiment B).
  * **Executive Summary Banner:** Verdict delta comparison (e.g. `PASS -> PASS` or `PASS -> FAIL`), overall score differential, and environment diffs (commit hash, library versions).
  * **Per-Scenario Metric Diff Table:** Compares indicators side-by-side with absolute difference, percentage change, statistical confidence interval (CI) overlap, and regression flag against thresholds in `config/regression_rules.yaml`.
  * **Visual Metric Diff Charts:** Comparative bar visualizer highlighting metric shifts between runs.

---

### 3.6. Interactive Chart Gallery (`/charts`)
* **URL:** [http://localhost:8000/charts](http://localhost:8000/charts)
* **Primary Role:** High-Resolution Performance & Distribution Charting.
* **Update Mechanism:** Fetches metrics JSON and renders dynamic JavaScript chart components.
* **Key Components & Features:**
  * **Fog Decision Latency Distribution (S3):** Boxplot & line distribution comparing decision speeds against the <150ms requirement.
  * **Lateral Propagation Speed Timeline (S6):** Chart showing peer-to-peer notification latency across fog node clusters (<5s requirement).
  * **False Positive Rate Analysis (S4):** Trial-by-trial noise resistance graph.
  * **Offline Continuity & Queue Flushing (S5):** Enqueued vs flushed message counts during network partitions.
  * **Multi-Zone Cross-Talk & Isolation (S7):** Message routing integrity across simultaneous zone operations.

---

### 3.7. Real-Time Benchmarks (`/metrics`)
* **URL:** [http://localhost:8000/metrics](http://localhost:8000/metrics)
* **Primary Role:** Research Target KPI Dashboard.
* **Update Mechanism:** Endpoint `/api/metrics/latest` parsing `results/metrics.json`.
* **Key Components & Features:**
  * **5 Key KPI Summary Cards:**
    1. *Fog Decision Latency:* Target <150 ms (Avg, Max, Min).
    2. *Lateral Peer Propagation:* Target <5.0 s.
    3. *False Positive Rate:* Target 0.0%.
    4. *Offline Continuity:* Target 100% uninterrupted execution & queue flush.
    5. *Concurrent Zone Integrity:* Target 0 cross-talk messages & 0% loss.
  * **Scenario Assertion Matrix Table:** Pass/Fail evaluation for Scenarios S1 through S7.
  * **Raw Metrics JSON Viewer:** Expandable syntax-highlighted code block.

---

### 3.8. Scenario Definition Browser (`/scenarios`)
* **URL:** [http://localhost:8000/scenarios](http://localhost:8000/scenarios)
* **Primary Role:** Read-Only Reference Catalog for Test Scenarios.
* **Update Mechanism:** Parses YAML scenario files located in `scenarios/*.yaml`.
* **Key Components & Features:**
  * **Scenario Selector Cards:** Quick tab navigation for Scenarios S1 to S7.
  * **Scenario Details Panel:** Name, description, assertion checklist, and evaluation conditions.
  * **Raw YAML View:** Formatted, read-only view of the underlying YAML configuration.

---

### 3.9. Settings & Export Hub (`/settings`)
* **URL:** [http://localhost:8000/settings](http://localhost:8000/settings)
* **Primary Role:** Configuration Management, Format Exporters & Reproducibility Publishing.
* **Update Mechanism:** Interacts with `ExportService`, `BundleService`, and `ResultManager`.
* **Key Components & Features:**
  * **Database & Platform Configuration:** InfluxDB URL, Organization, Bucket name, and status.
  * **Export Capabilities Matrix:** Status indicator for supported export formats (`md`, `html`, `csv`, `json`, `zip`, `pdf`, `docx`) and dependency checks (`weasyprint`, `python-docx`).
  * **One-Click Format Exporter:** Form to download any experiment run in any supported format.
  * **Reproducibility Bundle Builder:** One-click generator creating a complete, self-contained ZIP archive containing code snapshot, seed, dataset, manifest hash, environment specs, and executable run script.

---

## 4. Comprehensive REST API Reference Summary

### 4.1. NOC & Operations Telemetry Endpoints
* `GET /api/zones` — Returns current state across all monitored forest zones.
* `GET /api/snapshot?zone_id={id}` — Stateless snapshot combining database health, zone state, edge readings, system component health, alerts, audit logs, and latency metrics.
* `GET /api/lateral-timeline?minutes={m}` — Returns recent inter-fog lateral coordination events.
* `GET /api/history?zone_id={id}&minutes={m}&season={s}` — Merges live telemetry history with seasonal baseline overlays.
* `POST /api/advisory` — Dispatches operator advisory commands over MQTT to fog nodes and logs audit records.
* `GET /api/metrics/latest` — Fetches current benchmark metrics JSON.

### 4.2. Experiment Execution & Lifecycle Endpoints (`/api/v1/experiment/*`)
* `GET /api/v1/experiment/stream` — SSE endpoint for real-time progress, trial index, state transitions, and console output logs.
* `POST /api/v1/experiment/run` — Launches simulation subprocess with requested parameters (`trials`, `seed`, `clean`, `scenarios`).
* `POST /api/v1/experiment/stop` — Gracefully terminates active simulation.
* `POST /api/v1/experiment/pause` — Cooperatively pauses simulation execution.
* `POST /api/v1/experiment/resume` — Resumes paused simulation.
* `POST /api/v1/experiment/restart` — Stops current run, resets state, and starts new run.
* `POST /api/v1/experiment/clean` — Clears transient result files.
* `POST /api/v1/experiment/load` — Imports external simulation metrics into active state context.
* `GET /api/v1/experiment/status` — Queries `ProcessManager` state machine status.
* `GET /api/v1/experiment/results` — Returns active `metrics.json` content.
* `GET /api/v1/experiment/logs?tail={n}` — Returns trailing lines from active execution log file.

### 4.3. Report Discovery Endpoints (`/api/v1/reports/*`)
* `GET /api/v1/reports/list` — Discovers and lists all generated HTML/MD reports, sorted Newest First.
* `GET /api/v1/reports/{report_id}` — Returns specific report content and metadata.

### 4.4. Repository & Archive Endpoints (`/api/v1/repository/*`)
* `GET /api/v1/repository` — Filter, search, sort, and paginate historical experiment runs.
* `GET /api/v1/repository/{experiment_id}` — Detailed metadata, scenario metrics, manifest hash, and artifact paths.
* `GET /api/v1/repository/{experiment_id}/report.html` — Serves archived self-contained HTML report.
* `GET /api/v1/repository/{experiment_id}/charts/{chart_name}` — Serves archived chart PNG image.

### 4.5. Comparison & Regression Endpoints (`/api/v1/experiments/compare*`)
* `GET /api/v1/experiments/compare?a={id}&b={id}` — Computes side-by-side metric diffs, verdict deltas, and CI overlap.
* `GET /api/v1/experiments/compare/summary?a={id}&b={id}` — Returns executive comparison summary.

### 4.6. Export & Reproducibility Endpoints (`/api/v1/experiment/export/*` & `reproduce`)
* `GET /api/v1/experiment/export/formats` — Queries supported export format capabilities and optional dependency availability.
* `GET /api/v1/experiment/export/{experiment_id}?format={fmt}` — Downloads experiment package in requested format.
* `POST /api/v1/experiment/{experiment_id}/reproduce` — Compiles self-contained reproducibility bundle ZIP.
* `GET /api/v1/experiment/{experiment_id}/download-bundle` — Direct stream download for reproducibility bundle ZIP.

---

## 5. Architectural Design Principles & Standards

1. **Aesthetic Excellence & Theme:** High-density dark interface using `#0f172a` primary background, `#1e293b` container fills, `#38bdf8` accent blue, and `#10b981` success green. Strict zero-emoji, text-only sidebar and badge presentation.
2. **Stateless DB Queries & Offline Graceful Fallback:** Dashboard routes query InfluxDB statelessly. If InfluxDB is offline, the dashboard gracefully switches to offline mode with clear visual indicators without crashing.
3. **Fail-Fast Configuration Validation:** Startup validation verifies `config/regression_rules.yaml` before serving requests.
4. **Complete Advisory Audit Trail:** Every advisory command dispatched via MQTT is assigned a unique `command_id` and sequence number, with status (`SENT`, `FAILED`, `PENDING`) persisted in audit logs.
5. **Reproducibility First:** Built-in manifest hashing, git commit tracking, random seed control, and one-click ZIP bundle generation ensure every experiment can be reproduced independently.

---

## 6. How to Run & Access

### 6.1. Launching the Dashboard Server
From the root workspace directory, run:
```bash
# Start FastAPI Cloud Dashboard Server (using Python virtual environment)
uvicorn src.cloud_dashboard.app:app --host 0.0.0.0 --port 8000 --reload
```

### 6.2. Opening in Browser
Navigate to:
* **Main Operations NOC Dashboard:** [http://localhost:8000/](http://localhost:8000/)
* **Experiment Control Center:** [http://localhost:8000/experiments](http://localhost:8000/experiments)
* **API Interactive Documentation (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
