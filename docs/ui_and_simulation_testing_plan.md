# IGNIS — Unified Simulation & Dashboard UI Testing and Verification Plan

**Document Title:** IGNIS Operations Dashboard & Live Multi-Zone Simulation Testing Plan  
**Target Systems:** Cloud Operations NOC Dashboard (`http://localhost:8000/`), Simulation Engine, Multi-Zone Edge-Fog Telemetry  
**Platform Version:** 1.1.0 (Post Phase-G UI Modernization)  

---

## 1. Overview & Verification Scope

This document provides the definitive verification and quality assurance plan for the unified **IGNIS Cloud Operations Dashboard** and its integrated **Multi-Zone Simulation Control Panel**. It combines automated test suites, CLI-based API validation, and rigorous step-by-step manual test protocols.

### Key Verification Goals:
1. **Multi-Zone Visual Fidelity:** Validate that Zones 4A (North), 4B (Core), and 4C (South) are accurately rendered with glowing status rings, WHI gradient progress bars, and reactive sensor confirmation badges.
2. **Live Scenario Injection:** Verify that scenarios (S1, S2, S3, S4, S6) trigger thread-safe MQTT commands across isolated zone brokers without blocking dashboard polling.
3. **Threshold Alert Highlighting:** Confirm that individual edge node sensor values (`temperature_c`, `humidity_pct`, `wind_speed_kmh`, `soil_moisture_pct`, `gas_ppm`, `thermal_anomaly_c`) highlight in red when exceeding emergency thresholds.
4. **Safety Mechanisms & Clamping:** Verify visual display of Single-Sensor Fault clamping (`[WARNING] Clamped to YELLOW`) and Lateral Wind Preemptive Escalation chips (` Lateral Wind from Zone X`).
5. **System Co-existence:** Ensure that manual advisory operator overrides, historical time-series charts, and multi-trial experiment tools continue functioning without regression.

---

## 2. Test Architecture & Environment Prerequisites

```mermaid
graph TD
    subgraph Client["Operator & Tester Tier"]
        Browser["Web Browser (Chrome/Firefox/Edge) @ http://localhost:8000/"]
        CLI["CLI Test Suite / Pytest / cURL"]
    end

    subgraph CloudLayer["Cloud Dashboard Tier (Port 8000)"]
        FastAPI["FastAPI App (app.py)"]
        SimService["SimulationService (Multi-Threaded Runner)"]
        DB["CloudDashboardDB (InfluxDB v2 Connector)"]
    end

    subgraph MessagingTier["Distributed MQTT Network"]
        CloudBroker["Cloud MQTT Broker (:1884)"]
        Zone4ABroker["Zone 4A Broker (:1881)"]
        Zone4BBroker["Zone 4B Broker (:1883)"]
        Zone4CBroker["Zone 4C Broker (:1885)"]
    end

    subgraph EdgeFogTier["Edge-Fog Field Simulation"]
        FogNodes["3 Fog Nodes (4A, 4B, 4C)"]
        EdgeNodes["9 Edge Simulators (4A-E1..E3, 4B-E1..E3, 4C-E1..E3)"]
    end

    Browser -->|HTTP Polling & JSON API| FastAPI
    CLI -->|Pytest & REST Requests| FastAPI
    FastAPI --> SimService
    SimService -->|Control Payloads| MessagingTier
    MessagingTier --> EdgeNodes
    EdgeNodes -->|Telemetry Streams| FogNodes
    FogNodes -->|Zone State & Alert Broadcasts| MessagingTier
    MessagingTier --> CloudBroker
    CloudBroker --> DB
    DB --> FastAPI
```

### Environment Startup Checklist:

1. **Option A: Full Docker Environment (Recommended for End-to-End Field Validation)**
   ```powershell
   # Start all 16 microservices (Mosquitto brokers, InfluxDB, Fog Nodes, Edge Simulators)
   docker compose up -d

   # Verify all containers are healthy
   docker compose ps
   ```

2. **Option B: Standalone Dashboard Development Server**
   ```powershell
   # From repository root
   python -m uvicorn src.cloud_dashboard.app:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## 3. Automated Test Suite

The automated test suite verifies backend services, API contracts, MQTT payload routing, thread safety, and HTML markup integrity.

### 3.1 Running the Automated Tests

Execute the following commands from the repository root:

```powershell
# Run the dedicated simulation & UI integration test suite
python -m pytest tests/test_simulation_integration.py -v

# Run the complete dashboard & scenario validation suite
python -m pytest tests/test_dashboard_routes.py tests/test_scenario_routes.py tests/test_simulation_integration.py -v
```

### 3.2 Automated Test Coverage Matrix

| Test ID | Test Function | Target File | Verification Scope | Expected Result |
| :--- | :--- | :--- | :--- | :--- |
| **AUT-01** | `test_dashboard_ui_elements_present` | `tests/test_simulation_integration.py` | `GET /` HTML markup | Contains `sim-control-drawer`, scenario buttons `btn-scenario-S1`..`S6`, `edge-nodes-container`, and JS handlers. |
| **AUT-02** | `test_simulation_status_endpoint` | `tests/test_simulation_integration.py` | `GET /api/simulation/status` | Returns valid status JSON with `zone_id`, `is_active`, `running_scenario`, and `progress_pct` for 4A, 4B, 4C. |
| **AUT-03** | `test_simulation_start_invalid_params` | `tests/test_simulation_integration.py` | `POST /api/simulation/start` | Returns HTTP 400 Bad Request when supplied invalid `zone_id` (`99Z`) or unknown `scenario_id`. |
| **AUT-04** | `test_simulation_start_and_stop_lifecycle` | `tests/test_simulation_integration.py` | Start/Stop API lifecycle | Successfully launches S1 scenario thread, reflects `running_scenario="S1"`, stops upon request, and returns to `idle`. |
| **AUT-05** | `test_dashboard_snapshot_edge_readings` | `tests/test_dashboard_routes.py` | `GET /api/snapshot` | Snapshot payload includes `edge_readings` array with telemetry parameters. |

---

## 4. CLI API Verification Runbook

You can test and verify all simulation and snapshot APIs directly from PowerShell or Terminal using `curl.exe` or `Invoke-RestMethod`.

> **Note on Ports**:
> - **Port 9000**: Used when running full Docker Compose (`docker compose up -d` — Cloud Dashboard).
> - **Port 8000**: Used when running standalone Control Center or local `uvicorn src.cloud_dashboard.app:app --port 8000`.

### Step 1: Poll Baseline Simulation Status
```powershell
curl.exe http://localhost:9000/api/simulation/status
```
**Expected Response:**
```json
[
  {"zone_id":"4A","running_scenario":null,"current_step":0,"total_steps":0,"status":"idle","is_active":false,"progress_pct":0,"error":null},
  {"zone_id":"4B","running_scenario":null,"current_step":0,"total_steps":0,"status":"idle","is_active":false,"progress_pct":0,"error":null},
  {"zone_id":"4C","running_scenario":null,"current_step":0,"total_steps":0,"status":"idle","is_active":false,"progress_pct":0,"error":null}
]
```

### Step 2: Trigger Scenario S3 (Sudden Ignition) on Zone 4B
```powershell
curl.exe -X POST http://localhost:9000/api/simulation/start -H "Content-Type: application/json" -d "{\""zone_id\"": \""4B\"", \""scenario_id\"": \""S3\""}"
```
**Expected Response:**
```json
{
  "status": "started",
  "zone_id": "4B",
  "scenario_id": "S3",
  "total_steps": 6
}
```

### Step 3: Check Active Step Progress
```powershell
curl.exe "http://localhost:9000/api/simulation/status?zone_id=4B"
```
**Expected Response:**
```json
{
  "zone_id": "4B",
  "running_scenario": "S3",
  "current_step": 3,
  "total_steps": 6,
  "status": "running",
  "is_active": true,
  "progress_pct": 50,
  "error": null
}
```

### Step 4: Stop Simulation and Reset Zone Nodes
```powershell
curl.exe -X POST http://localhost:9000/api/simulation/stop -H "Content-Type: application/json" -d "{\""zone_id\"": \""4B\""}"
```
**Expected Response:**
```json
{
  "status": "stopped",
  "zone_id": "4B"
}
```

---

## 5. Comprehensive Manual Testing Protocols (Step-by-Step)

Perform these manual test cases in a browser at `http://localhost:9000/` with the full system running (`docker compose up -d`).

---

### Test Protocol M-01: Baseline Layout & Default Multi-Zone Rendering

* **Objective:** Verify that all initial UI elements, cards, and styling render properly in baseline state.
* **Pre-conditions:** Cloud Dashboard running (`http://localhost:9000/`); no active simulation running.
* **Steps:**
  1. Open `http://localhost:9000/` in Chrome or Edge.
  2. Examine the top navigation bar, status indicators, and drawer header.
  3. Inspect the **Multi-Zone WHI Overview** section at the top.
  4. Inspect the **Live Scenario Simulation Control** drawer.
  5. Inspect the **Edge Node Sensor Arrays** section below the historical charts.
* **Verification Checklist:**
  - [ ] **Top Drawer:** Displays `STATUS: IDLE` badge (green tint) and ` Live Scenario Simulation Control`.
  - [ ] **Three Zone Cards:** Displays **ZONE 4A (Simlipal North)**, **ZONE 4B (Simlipal Core)**, and **ZONE 4C (Simlipal South)** side-by-side.
  - [ ] **Zone State Rings:** All 3 zones show `GREEN` with green outer glow ring.
  - [ ] **WHI Scores:** Display low baseline scores (typically `0.000` to `0.250`).
  - [ ] **Progress Bars:** Progress bar fill corresponds to WHI percentage with green hue.
  - [ ] **Sensor Badges:** All 6 badges (`Temp`, `Humid`, `Wind`, `Soil`, `Gas`, `Thermal`) display in muted/inactive grey.
  - [ ] **Active Selection:** Zone 4A or 4B is highlighted with a blue border (`selected` state).
  - [ ] **Edge Nodes Array:** Shows cards for `Node 4B-E1`, `4B-E2`, `4B-E3` with parameter values in normal neutral styling.

---

### Test Protocol M-02: Interactive Zone Switching & Component Synchrony

* **Objective:** Verify that selecting different zones updates all dashboard panels synchronously.
* **Steps:**
  1. Click directly on the **ZONE 4C** rich card.
  2. Observe the header dropdown selector (`#zone-select`) and the simulation drawer target selector (`#sim-zone-selector`).
  3. Observe the detailed Zone State card in the middle section and the Edge Node Sensor Arrays at the bottom.
  4. Now change the header dropdown to **Zone 4A**.
* **Verification Checklist:**
  - [ ] Clicking Zone 4C immediately moves the blue active card outline to Zone 4C.
  - [ ] Header dropdown updates to `Zone 4C`.
  - [ ] Simulation drawer target label updates to `Zone 4C (South)`.
  - [ ] Zone Detail title updates to `ZONE 4C (Simlipal South Zone)`.
  - [ ] Edge Node Sensor Array switches from displaying `4C-E1`, `4C-E2`, `4C-E3`.
  - [ ] Changing the header dropdown to `Zone 4A` synchronizes all corresponding cards and drawer selectors back to Zone 4A.

---

### Test Protocol M-03: Scenario S1 (Normal Day Baseline Drift)

* **Objective:** Verify execution of a normal diurnal cycle without false alarms.
* **Steps:**
  1. In the Simulation Drawer, set target zone to **Zone 4B**.
  2. Click the **S1: Normal Day** button.
  3. Observe the Simulation Drawer badge, progress bar, Zone 4B card, and Edge Node grid over 20–30 seconds.
* **Verification Checklist:**
  - [ ] Drawer status badge updates to `RUNNING: S1` (amber tint).
  - [ ] Scenario button `S1: Normal Day` shows active blue border highlight.
  - [ ] Step progress text advances (`Step 1/4`, `Step 2/4`, `Step 3/4`, `Step 4/4`).
  - [ ] Step progress bar smoothly animates from 0% to 100%.
  - [ ] Zone 4B state **remains GREEN** throughout the simulation.
  - [ ] WHI score stays below `0.350`.
  - [ ] Edge node temperature stays below 35°C; no red alert highlights appear on parameter boxes.
  - [ ] Upon completion, drawer status returns to `STATUS: IDLE`.

---

### Test Protocol M-04: Scenario S2 (Slow-Building Risk / Heatwave)

* **Objective:** Verify progressive escalation to `YELLOW` advisory condition under gradual drying trend.
* **Steps:**
  1. Ensure target zone is **Zone 4B**.
  2. Click the **S2: Slow Risk** button.
  3. Monitor the Zone 4B card and Edge Node readings across Steps 1 to 5.
* **Verification Checklist:**
  - [ ] Drawer indicates `RUNNING: S2`.
  - [ ] Over successive steps, Edge Node temperatures rise (32°C → 36°C → 41°C) and humidity drops (40% → 22%).
  - [ ] When temperature crosses 40°C or humidity drops below 25%, the corresponding parameter boxes on Edge cards **highlight in red**.
  - [ ] On the Zone 4B card, the `Temp` and `Humid` confirmation badges **light up** in active blue.
  - [ ] WHI score increases from ~0.25 to >0.55.
  - [ ] Zone 4B state ring transitions from `GREEN` → `YELLOW` with amber glow.
  - [ ] Zones 4A and 4C remain `GREEN`.

---

### Test Protocol M-05: Scenario S3 (Sudden Ignition Outbreak)

* **Objective:** Verify high-severity fire escalation (`ORANGE`/`RED`), localized node detection, and rapid action triggers.
* **Steps:**
  1. Select target zone **Zone 4B**.
  2. Click the **S3: Sudden Fire** button.
  3. Observe Edge Node `4B-E2` (center node) vs neighbor nodes `4B-E1` and `4B-E3`.
  4. Observe the Incident Timeline and Actions Feed.
* **Verification Checklist:**
  - [ ] Edge Node `4B-E2` displays spike in Temperature (>55°C), Gas (>45 ppm), and Thermal Anomaly (>4.0°C).
  - [ ] On Node `4B-E2`'s card, `Temp`, `Gas`, and `Thermal` parameter boxes turn **bright red**.
  - [ ] Neighbor nodes `4B-E1` and `4B-E3` remain in normal baseline ranges.
  - [ ] Zone 4B card escalates: `GREEN` → `YELLOW` → `ORANGE` → `RED`.
  - [ ] WHI score exceeds `0.800` with red progress bar fill.
  - [ ] `Temp`, `Gas`, `Thermal` sensor confirmation badges light up.
  - [ ] Actions Feed displays automated triggers (e.g., `TRIGGER_RETARDANT_SPRAY`, `DISPATCH_DRONE_RECON`).

---

### Test Protocol M-06: Scenario S4 (Single Sensor Fault & Clamping Guard)

* **Objective:** Verify that a faulty single sensor spike (gas sensor anomaly) is prevented from causing a false RED alert by the Single Fault Guard.
* **Steps:**
  1. Select target zone **Zone 4B**.
  2. Click the **S4: Sensor Fault** button.
  3. Observe the behavior at Step 3 where gas spikes to 100 ppm while temperature and thermal sensors remain normal.
* **Verification Checklist:**
  - [ ] Edge Node `4B-E2` shows `Gas: 100.0 ppm` (highlighted in red), but `Temp` remains normal (~28°C).
  - [ ] Only the `Gas` confirmation badge lights up on the Zone 4B card (single sensor condition).
  - [ ] The Single Fault Guard engages: Zone 4B state is **clamped to YELLOW** (does NOT escalate to RED).
  - [ ] A yellow warning chip appears on the Zone 4B card: `[WARNING] Clamped to YELLOW (Single Fault Guard)`.
  - [ ] No unwarranted fire suppression actions are dispatched in the Actions Feed.

---

### Test Protocol M-07: Scenario S6 (Lateral Spread & Peer Zone Warning)

* **Objective:** Verify inter-zone wildfire propagation and preemptive warning banner activation on adjacent zones.
* **Steps:**
  1. Set target zone to **Zone 4A (North)**.
  2. Click the **S6: Lateral Spread** button.
  3. Switch viewing focus between Zone 4A and Zone 4B.
* **Verification Checklist:**
  - [ ] Zone 4A escalates to `ORANGE`/`RED` under high wind conditions blowing south.
  - [ ] Zone 4B (adjacent south neighbor) detects the lateral broadcast.
  - [ ] On the Zone 4B card, a warning chip displays: ` Lateral Wind from Zone 4A`.
  - [ ] In the Zone Detail section for Zone 4B, the lateral warning banner displays: `Pre-emptive Escalation: Warning from Zone 4A`.
  - [ ] The **Inter-Zone Lateral Propagation Log** table records the lateral broadcast event with wind velocity and heading.

---

### Test Protocol M-08: Emergency Stop & Baseline Reset Action

* **Objective:** Verify that an operator can immediately abort a running scenario and restore edge nodes to baseline.
* **Steps:**
  1. Start Scenario **S3** on Zone 4B.
  2. While the progress bar is at Step 2 or 3, click the ** Stop / Reset to Baseline** button.
  3. Observe system recovery.
* **Verification Checklist:**
  - [ ] Toast notification appears: `Simulation stopped on Zone 4B. Nodes reset to baseline.`
  - [ ] Drawer status badge returns immediately to `STATUS: IDLE`.
  - [ ] Progress bar disappears and resets to 0%.
  - [ ] Scenario button highlight is removed.
  - [ ] Edge node parameters return to baseline values on the next polling cycle.
  - [ ] Zone 4B WHI decays back toward normal `GREEN` baseline.

---

### Test Protocol M-09: Operator Advisory Override Co-existence

* **Objective:** Verify that manual operator advisory overrides (`SET_SAFETY_MODE`, `FORCE_CLAMP_WHI`) operate correctly alongside the new visualization components.
* **Steps:**
  1. In the **Advisory Overrides & Policy Controls** section on the right, select `FORCE_CLAMP_WHI` or select State `ORANGE` under Quick Status Override.
  2. Click **Apply Force State Override**.
  3. Verify card update, then click **Release Override Gate**.
* **Verification Checklist:**
  - [ ] Toast notification confirms command dispatch with UUID.
  - [ ] Zone Detail card displays the amber badge: `OVERRIDE LOCK ACTIVE`.
  - [ ] Zone card reflects the forced state.
  - [ ] Audit Trail table at the bottom logs the command with `STATUS: SUCCESS`.
  - [ ] Clicking **Release Override Gate** removes the lock badge and returns control to autonomous fog evaluation.

---

### Test Protocol M-10: Responsive Layout & Drawer Collapse

* **Objective:** Verify UI responsiveness and collapsible drawer behavior.
* **Steps:**
  1. Click the header bar of the **Live Scenario Simulation Control** drawer.
  2. Verify the drawer collapses smoothly and the toggle chevron rotates.
  3. Resize the browser window to tablet width (~768px) and mobile width (~480px).
* **Verification Checklist:**
  - [ ] Clicking the drawer header hides the scenario buttons and controls, leaving a clean uncluttered view.
  - [ ] The chevron arrow rotates -90° when collapsed and 0° when expanded.
  - [ ] On tablet/mobile viewports, the 3 Zone cards stack vertically without text overflow.
  - [ ] Edge node cards wrap into a clean 1-column or 2-column grid.

---

## 6. Verification Checklist & Sign-Off Matrix

| Test ID | Protocol Name | Automation Available | Manual Pass Criteria | Result |
| :--- | :--- | :---: | :--- | :---: |
| **TC-01** | Baseline Multi-Zone Rendering | Yes (AUT-01) | 3 cards visible, all GREEN, badges inactive, WHI < 0.35 | **[PASS]** |
| **TC-02** | Interactive Zone Synchronization | Yes (AUT-01) | Card click updates dropdown, drawer, detail, and edge grid | **[PASS]** |
| **TC-03** | S1 Normal Day Simulation | Yes (AUT-04) | 4-step progress, stays GREEN, parameters normal | **[PASS]** |
| **TC-04** | S2 Slow-Building Risk | Yes (AUT-04) | Escalates to YELLOW, Temp/Humid badges light up, boxes red | **[PASS]** |
| **TC-05** | S3 Sudden Outbreak Ignition | Yes (AUT-04) | Center node red boxes, zone escalates to RED, actions trigger | **[PASS]** |
| **TC-06** | S4 Single Sensor Fault Guard | Yes (AUT-03) | Gas 100ppm, single badge active, clamped to YELLOW chip | **[PASS]** |
| **TC-07** | S6 Lateral Spread Propagation | Yes (AUT-02) | Zone 4A fire + Zone 4B displays lateral wind warning chip | **[PASS]** |
| **TC-08** | Emergency Stop & Reset | Yes (AUT-04) | Instant stop, nodes return to baseline, progress clears | **[PASS]** |
| **TC-09** | Advisory Override Co-existence | Yes (AUT-05) | Override badge displays, audit log recorded, release works | **[PASS]** |
| **TC-10** | Drawer Collapse & Responsiveness | Yes (AUT-01) | Header click toggles drawer, responsive grid scaling | **[PASS]** |

---

## 7. Diagnostic & Troubleshooting Reference

### 1. Checking Live MQTT Topics

**Option A: Subscribe to Continuous Telemetry Stream (Fires every 3s)**
To see live sensor readings streaming continuously:
```powershell
docker exec -it ignis-mqtt-broker-4b mosquitto_sub -t "ignis/v1/telemetry/#" -v
```

**Option B: Subscribe to Control Commands (Fires when clicking Scenario Buttons)**
Control topics only print when a scenario button is clicked or triggered via API:
```powershell
docker exec -it ignis-mqtt-broker-4b mosquitto_sub -t "ignis/v1/system/zone/+/edge/+/control" -v
```

### 2. Checking InfluxDB Live Telemetry Ingestion
```powershell
curl.exe -X POST "http://localhost:8086/api/v2/query?org=ignis-org" -H "Authorization: Token ignis-super-secret-token" -H "Content-Type: application/vnd.flux" -d 'from(bucket:\"ignis-telemetry\") |> range(start: -2m) |> limit(n:5)'
```

### 3. FastAPI Service Logs
When running with Uvicorn, observe log outputs for simulation thread status:
```
[INFO] simulation_routes: Started simulation S3 on Zone 4B via API
[INFO] simulation_service: [Zone 4B] Publishing Step 1/6 for S3 on 4B-E2
[INFO] simulation_service: [Zone 4B] Publishing Step 2/6 for S3 on 4B-E2
[INFO] simulation_service: Simulation stopped and Zone 4B reset to baseline.
```
