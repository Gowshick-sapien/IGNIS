# IGNIS Version 1 — Comprehensive Capabilities, Technical Stack & Architectural Specification

**System Title:** Intelligent Geo-distributed Network for Wildfire Intervention and Surveillance (IGNIS)  
**Platform Version:** 1.0.0 (Phases A through G Complete)  
**Parent Concept:** Autonomous Wildfire Early Warning and Pre-Suppression Using Edge-Fog-Cloud (EFC) Architecture in Indian Forest Ecosystems  
**Reference Domain:** Simlipal Tiger Reserve / National Park, Odisha, India

---

## 1. Executive Overview & System Purpose

**IGNIS** is a research-oriented Edge-Fog-Cloud (EFC) decision-architecture validation testbed designed to revolutionize wildfire early warning and pre-suppression. Traditional wildfire monitoring relies heavily on remote satellite thermal sensors or centralized cloud telemetry ingestion, introducing delays of minutes to hours before actionable suppression signals reach ground crews.

IGNIS replaces centralized bottlenecks with a **hierarchical, multi-tier distributed architecture**:
1. **Edge Tier:** Low-power sensor nodes deployed across forest zones providing high-frequency microclimate readings.
2. **Fog Tier:** Solar-powered local fog servers stationed within forest zones (e.g., Simlipal North 4A, Simlipal Core 4B, Simlipal South 4C) executing autonomous real-time risk scoring, deterministic state machine evaluation, and peer-to-peer lateral coordination.
3. **Cloud Tier:** Centralized Regional Operations NOC, time-series telemetry store (InfluxDB), automated regression detector, experiment orchestrator, and web dashboard framework.

```mermaid
graph TB
    subgraph EdgeTier["1. EDGE TIER - Sensors and Microclimates"]
        direction LR
        E1["Edge Node 4B-E1: Temp, Humidity, Wind, Smoke, Flame"]
        E2["Edge Node 4B-E2"]
        E3["Edge Node 4B-E3"]
    end

    subgraph FogTier["2. FOG TIER - Local Intelligence and Autonomous Pre-Suppression"]
        MQTT_FOG["Local MQTT Broker Port 1883"]
        FOG_NODE["Fog Node Server Zone 4B Core"]
        FOG_PEERS["Adjacent Fog Nodes Zone 4A and 4C"]
    end

    subgraph CloudTier["3. CLOUD TIER - Regional Operations NOC and Research Control"]
        CLOUD_BROKER["Cloud MQTT Broker Port 1884"]
        INGESTOR["Cloud Ingestor Worker"]
        INFLUX["InfluxDB v2 Time-Series DB Port 8086"]
        DASHBOARD["IGNIS Cloud Dashboard Port 8000 and 9000"]
    end

    E1 -->|Telemetry Stream| MQTT_FOG
    E2 -->|Telemetry Stream| MQTT_FOG
    E3 -->|Telemetry Stream| MQTT_FOG
    MQTT_FOG -->|Sensor Readings| FOG_NODE

    FOG_NODE -->|Peer Warning under 5 sec| FOG_PEERS
    FOG_PEERS -->|Peer Warning| FOG_NODE

    FOG_NODE -->|Buffered Sync| CLOUD_BROKER
    CLOUD_BROKER -->|MQTT Ingest| INGESTOR
    INGESTOR -->|Batch Writes| INFLUX
    INFLUX -->|Stateless Query| DASHBOARD

    DASHBOARD -->|Advisory Overrides| CLOUD_BROKER
    CLOUD_BROKER -->|Command Routing| FOG_NODE
```

---

## 2. Complete Technical Stack Matrix

| Layer / Subsystem | Technology / Library | Purpose & Responsibility |
| :--- | :--- | :--- |
| **Core Runtime Language** | **Python 3.10+** | Asynchronous execution environment, typing support, dataclasses, and concurrent task management. |
| **Web Framework & API** | **FastAPI (v0.100+)** | High-performance async web app hosting REST HTTP routes (`/api/v1/*`), Jinja2 templating, and SSE streaming. |
| **ASGI Web Server** | **Uvicorn** | Production-grade ASGI server handling asynchronous HTTP connections and Server-Sent Events (SSE). |
| **Messaging & Events** | **MQTT / Eclipse Mosquitto (v2)** | Lightweight pub/sub message routing for Edge-Fog, Fog-Fog (lateral), and Fog-Cloud communications. |
| **MQTT Client Library** | **Paho-MQTT** | Python MQTT client managing connections, subscriptions, message buffering, and QoS delivery. |
| **Time-Series Database** | **InfluxDB v2 (v2.7)** | Persistent high-throughput storage for sensor telemetry, fog decision states, performance metrics, and audit logs. |
| **Database Client** | **InfluxDB-Client Python** | Flux query builder, write API client with automatic retry logic and batch processing. |
| **Containerization** | **Docker & Docker Compose (v2)** | Multi-container microservice orchestration isolating edge nodes, fog nodes, MQTT brokers, ingestor, and dashboard. |
| **Data Validation** | **Pydantic v2** | Strongly-typed schema definition, request payload validation, and OpenAPI doc generation. |
| **Configuration Engine** | **PyYAML & JSON** | Declarative configuration for forest zone topologies, test scenarios (S1–S7), and regression rules. |
| **Statistical Engine** | **NumPy & SciPy** | Descriptive statistics, moving averages, standard deviation, and Student-t 95% confidence interval calculations. |
| **Interactive Visualization** | **Plotly.js (v2.27.0 Vendored)** | Client-side interactive charting for standalone HTML reports and live web dashboards without external CDN calls. |
| **Static Charting Engine** | **Matplotlib** | Headless server-side PNG rendering for archived experiment chart generation. |
| **Document Exporters** | **WeasyPrint & python-docx** | Programmatic export of experiment runs into PDF documents and Word (.docx) publications. |
| **Front-End Styling** | **Vanilla CSS3 & HTML5** | Custom dark glassmorphism theme (`#0f172a` / `#1e293b`), zero-emoji academic design, responsive layouts. |
| **Test Automation** | **Pytest & Unittest** | Comprehensive unit test suite, mock network test cases, state transition tests, and API integration tests. |

---

## 3. End-to-End Core Capabilities (Phases A through G)

### 3.1. Phase A — Core Wildfire Decision Engine
* **Multi-Sensor Data Normalization:** Ingests temperature, relative humidity, wind speed, smoke PPM, and flame sensor states, scaling raw values into unified 0.0–1.0 risk coefficients ([src/scoring/whi.py](file:///d:/projects/IGNIS/src/scoring/whi.py)).
* **Wildfire Hazard Index (WHI) Formula:** Computes a continuous composite risk score using weighted multi-factor equations calibrated for Indian forest fuel types.
* **Multi-Sensor Temporal Confirmation:** Evaluates consecutive telemetry ticks before escalating state, effectively filtering out transient sensor spikes or localized noise.
* **Deterministic Zone State Machine:** Transitions through `NORMAL` → `ELEVATED` → `CRITICAL` states with hysteresis safety gates to prevent oscillation.
* **Autonomous Pre-Suppression Action Trigger:** Automatically generates logged action records (water mist activation, drone reconnaissance dispatch, acoustic deterrents) in **under 150 ms** upon entering `CRITICAL` state.

---

### 3.2. Phase B — Distributed Containerized Architecture & MQTT Protocol
* **Containerized Microservices:** Isolated Docker services representing Edge Sensor Nodes, Zone Fog Servers, Local MQTT Brokers, Cloud Brokers, InfluxDB, Ingestor, and Control Center ([docker-compose.yml](file:///d:/projects/IGNIS/docker-compose.yml)).
* **Structured MQTT Topic Hierarchy:**
  ```
  ignis/v1/
  ├── zone/{zone_id}/edge/{node_id}/reading    (Telemetry Stream)
  ├── zone/{zone_id}/edge/{node_id}/control    (Edge Configuration)
  ├── zone/{zone_id}/fog/state                (Zone WHI & Risk State)
  ├── zone/{zone_id}/fog/alert                (Escalation Alerts)
  ├── zone/{zone_id}/fog/action_log            (Autonomous Pre-Suppression Logs)
  └── lateral/zone/{zone_id}/event            (Peer-to-Peer Fog Communications)
  ```
* **Simulated Sensor Drift & GPS Metadata:** Edge simulators ([src/edge_sim.py](file:///d:/projects/IGNIS/src/edge_sim.py)) attach lat/lon coordinates, battery state, and configurable noise profiles.

---

### 3.3. Phase C — Centralized Cloud Layer & InfluxDB Telemetry Store
* **Stateless Cloud Ingestion Pipeline:** Independent worker service ([src/cloud_ingestor/main.py](file:///d:/projects/IGNIS/src/cloud_ingestor/main.py)) asynchronously streams MQTT telemetry into InfluxDB v2 with local memory buffering during DB downtime.
* **Stateless Snapshot API:** Database service ([src/cloud_dashboard/database.py](file:///d:/projects/IGNIS/src/cloud_dashboard/database.py)) queries InfluxDB statelessly to construct instant system health, zone state, edge readings, and performance metrics.
* **Operator Advisory Security Gate:** Regional operators can dispatch binding advisory commands (`SET_SAFETY_MODE`, `FORCE_CLAMP_WHI`, `RESET_OVERRIDE`) over MQTT. Every command is validated with unique UUIDs, sequence numbers, TTL cutoffs, and audit logging.

---

### 3.4. Phase D — Multi-Zone & Peer-to-Peer Lateral Coordination
* **Multi-Zone Topology:** Simultaneous monitoring and execution across 3 forest zones:
  * **Zone 4A:** Simlipal North Range
  * **Zone 4B:** Simlipal Core Protected Area
  * **Zone 4C:** Simlipal South Range
* **Fog-to-Fog (P2P) Lateral Communication:** Fog nodes communicate directly over inter-fog MQTT channels without cloud intervention.
* **Neighbor Risk Propagation:** When Zone 4B detects a `CRITICAL` ignition, it broadcasts a peer warning. Adjacent zones (4A and 4C) immediately adjust safety margins and elevate monitoring frequency within **< 5.0 seconds**.
* **Zone Cross-Talk Isolation:** Strict topic filtering prevents message pollution between non-adjacent or unconfigured zones.

---

### 3.5. Phase E — Fault & Chaos Resilience Engine
* **Chaos Controller:** Integrated impairment injector ([src/chaos_controller/](file:///d:/projects/IGNIS/src/chaos_controller/)) capable of introducing network latency, packet loss, broker crashes, and sensor dropouts.
* **Offline Continuity & Queue Buffering:** Fog nodes use a disk/memory queue publisher ([src/buffered_publisher.py](file:///d:/projects/IGNIS/src/buffered_publisher.py)). During WAN cloud outages, fog decision-making continues uninterrupted locally. Once connection is restored, buffered events flush automatically with **100% data continuity**.
* **Standardized Scenario Library (S1–S7):**
  * `S1` (Baseline Normal Day)
  * `S2` (Slow-Building Environmental Risk)
  * `S3` (Sudden Ignition & Latency Benchmark)
  * `S4` (Sensor Noise & False Positive Resilience)
  * `S5` (Network Partition & Offline Queue Flushing)
  * `S6` (Lateral Peer Propagation Speed)
  * `S7` (Multi-Zone Concurrent Load & Crosstalk Integrity)

---

### 3.6. Phase F — Automated Orchestration & Metric Derivation
* **Experiment Orchestrator:** CLI and API launcher ([src/run_experiment.py](file:///d:/projects/IGNIS/src/run_experiment.py)) running configurable trial counts, random seeds, state cleaning, and scenario selection.
* **Event Stream Metric Derivation:** Derives exact decision latencies and lateral propagation speeds directly from raw event timestamp streams ([src/metrics_collector.py](file:///d:/projects/IGNIS/src/metrics_collector.py)).
* **Statistical Rigor:** Computes sample counts, mean, median, min, max, standard deviation, and Student-t 95% confidence intervals for every scenario metric.

---

### 3.7. Phase G — Unified Web Dashboard & Reproducibility Publishing Engine
* **G1 — Offline Interactive HTML Reporting:** Standalone `report.html` generator powered by vendored Plotly.js, TOC navigation, live full-text search, keyboard shortcuts (`Ctrl+F`, `/`), and dark/light themes.
* **G2 — Process Lifecycle Manager:** Singleton subprocess state machine (`IDLE` → `STARTING` → `RUNNING` → `PAUSED` → `COMPLETED` / `FAILED`) managing experiment execution.
* **G3 — SSE Live Progress Streaming:** Server-Sent Events endpoint (`/api/v1/experiment/stream`) broadcasting live progress percentages, trial numbers, and terminal console logs.
* **G4 — Historical Experiment Repository:** Searchable, filterable (verdict, scenario, commit, date range), sortable, and paginated archive of past runs with detail inspection drawer.
* **G5 — Automated Regression Detector & Side-by-Side Comparison:** Evaluates runs against thresholds in `config/regression_rules.yaml` and calculates side-by-side metric diffs, verdict deltas, and CI overlaps ([src/cloud_dashboard/services/regression_detector.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/regression_detector.py)).
* **G6 — Multi-Format Exporter & Reproducibility Bundle Builder:** One-click format exporter (`md`, `html`, `csv`, `json`, `zip`, `pdf`, `docx`) and reproducibility ZIP bundle generator containing code snapshot, seed, dataset, environment manifest, and run script ([src/cloud_dashboard/services/bundle_service.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/bundle_service.py)).

---

## 4. Key Performance Indicators & Benchmark Validation

| Benchmark Target | Metric Description | Target Threshold | Achieved Performance | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Fog Decision Latency** | Time delta from initial sensor threshold breach to fog action trigger. | **< 150 ms** | **~80 ms – 120 ms** | ✅ PASS |
| **Lateral Peer Propagation** | Time delta for adjacent fog nodes to receive and acknowledge peer warning. | **< 5.0 s** | **~3.2 s – 3.6 s** | ✅ PASS |
| **False Positive Rate** | Rate of invalid `CRITICAL` state transitions under noisy sensor data (S4). | **0.0%** | **0.0%** (10/10 trials) | ✅ PASS |
| **Offline Continuity** | Percentage of enqueued messages successfully flushed after WAN recovery (S5). | **100.0%** | **100.0%** (4/4 flushed) | ✅ PASS |
| **Multi-Zone Crosstalk** | Number of cross-talk messages detected between isolated zones (S7). | **0 messages** | **0 messages** | ✅ PASS |

---

## 5. Unified Dashboard Page Directory

The **IGNIS Central Operations & Research Control Center Dashboard** consolidates all system capabilities into 9 dedicated web views accessible via a unified navigation sidebar:

1. 🌐 **Regional Operations NOC (`/`):** Real-time multi-zone monitoring, InfluxDB status, lateral event timeline, edge sensor readings table, operator advisory MQTT control panel.
2. 🧪 **Experiment Control Center (`/experiments`):** Scenario runner form, trial/seed configuration, process controls, SSE live progress bar, real-time log viewer.
3. 📄 **Historical Report Browser (`/reports`):** Auto-discovered catalog of HTML & Markdown research reports, sorted Newest First with in-browser previews.
4. 🗃️ **Historical Experiment Repository (`/repository`):** Search, filter by verdict/scenario/commit/date, sort, paginate, and view detail inspection drawers.
5. ⚖️ **Side-by-Side Comparison (`/comparison`):** Baseline vs target comparison, executive verdict delta banner, metric diff table with CI overlaps, regression status.
6. 📊 **Interactive Chart Gallery (`/charts`):** Interactive Plotly.js visualization of decision latency distributions, lateral propagation speeds, and continuity curves.
7. 📈 **Real-Time Benchmarks (`/metrics`):** KPI summary cards, scenario assertion pass/fail matrix, and raw JSON data viewer.
8. 📑 **Scenario Definition Browser (`/scenarios`):** Read-only catalog of YAML scenario configs (S1–S7), assertion checklists, and raw YAML viewer.
9. ⚙️ **Settings & Export Hub (`/settings`):** DB configuration, export capabilities matrix, format exporter (MD/HTML/CSV/JSON/ZIP/PDF/DOCX), and reproducibility bundle generator.

For full page-by-page instructions, see [docs/dashboard_guide.md](file:///d:/projects/IGNIS/docs/dashboard_guide.md).

---

## 6. System Execution Commands

### Launching the Dashboard Server
```bash
# Run FastAPI Cloud Dashboard locally
uvicorn src.cloud_dashboard.app:app --host 0.0.0.0 --port 8000 --reload
```

### Launching with Docker Compose
```bash
# Start all 16 microservices (brokers, edge nodes, fog nodes, influxdb, ingestor, dashboard)
docker compose up --build
```

### Running Experiment Suite via CLI
```bash
# Execute 30 trials with clean state initialization
python -m src.run_experiment --trials 30 --clean
```

### Running Test Suite
```bash
# Run full unit and integration test suite
python -m unittest discover tests
```
