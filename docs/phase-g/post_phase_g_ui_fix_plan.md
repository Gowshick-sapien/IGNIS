# Merge Control Center UI into Cloud NOC Dashboard

Incorporate the best visual and interactive elements from the local Range Forest Control Center (`localhost:8000`) into the main Cloud NOC Dashboard (`localhost:9000`), extending them to all 3 zones (4A, 4B, 4C) without duplicating the batch experiment runner scope.

## User Review Required

> [!IMPORTANT]
> **Scope Clarification**: The Experiments page (`/experiments`) remains untouched — it handles batch subprocess benchmarking. What we are adding to the NOC Dashboard (`/`) is the **interactive real-time simulation panel** (scenario injection + rich WHI visualisation) which is a fundamentally different feature: live MQTT-driven scenario injection vs. batch trial execution.

> [!WARNING]
> **Backend Dependency**: The Simulation Panel injects scenarios via MQTT control messages to edge nodes. This requires the **local MQTT brokers** (ports 1881–1883) and **fog nodes** to be running (i.e., `docker-compose up`). When services are offline, the simulation panel will display a "Services Offline" state gracefully.

## Open Questions

> [!IMPORTANT]
> **Q1: Zone-Specific vs. Global Scenarios** — Currently S1/S2 affect all nodes in a single zone, and S3/S4 affect one localised node. Should the simulation panel on the NOC Dashboard:
> - **(A)** Target only the currently selected zone (from the existing zone dropdown), or
> - **(B)** Allow the operator to pick any zone independently for scenario injection?
>
> *(Plan assumes option A — scenarios target the currently selected zone.)*

> [!IMPORTANT]
> **Q2: Simultaneous Scenarios** — Should operators be able to run different scenarios on different zones concurrently (e.g., S2 on 4A + S3 on 4B), or should it be one active scenario at a time across the whole system?
>
> *(Plan assumes one active scenario per zone, with the ability to run different scenarios on different zones concurrently.)*

---

## Proposed Changes

### Component 1: Backend — Multi-Zone Scenario Service for Cloud Dashboard

The current `ScenarioService` in `src/control_center/scenario_service.py` is hard-wired to a single zone via `ZONE_ID` env var and connects to a single local MQTT broker. For the cloud dashboard, we need a service that can target any of the 3 zones by routing MQTT publishes through the correct broker.

---

#### [NEW] `src/cloud_dashboard/services/simulation_service.py`

A multi-zone scenario orchestrator for the cloud dashboard context.

**Key design decisions:**
- Maintains a **per-zone scenario state** dict (`{"4A": {thread, status, step, total}, "4B": {...}, "4C": {...}}`) so zones can run scenarios independently.
- Routes MQTT control messages to the correct zone broker. In Docker, the cloud dashboard connects to the **central cloud broker** (port 1884). The fog nodes subscribe to the cloud broker for advisory commands, so we publish scenario control commands on the **cloud broker** using the existing topic pattern `ignis/v1/system/zone/{zone_id}/edge/{node_id}/control`. This avoids needing direct connections to each local broker.
- Reuses `ScenarioGenerator` from `src/scenario.py` (same step definitions).
- Exposes `start_scenario(zone_id, scenario_id)`, `stop_scenario(zone_id)`, `get_all_status()` methods.

```python
# Core structure:
class SimulationService:
    def __init__(self, mqtt_host, mqtt_port):
        self.zone_states = {
            "4A": {"thread": None, "scenario": None, "step": 0, "total": 0, "status": "idle"},
            "4B": {"thread": None, "scenario": None, "step": 0, "total": 0, "status": "idle"},
            "4C": {"thread": None, "scenario": None, "step": 0, "total": 0, "status": "idle"},
        }
        self.zone_nodes = {
            "4A": ["4A-E1", "4A-E2", "4A-E3"],
            "4B": ["4B-E1", "4B-E2", "4B-E3"],
            "4C": ["4C-E1", "4C-E2", "4C-E3"],
        }
```

---

#### [MODIFY] `src/cloud_dashboard/app.py`

- Import and instantiate `SimulationService` in the lifespan startup.
- Store in `app.state.simulation_service`.
- Connect to cloud MQTT broker (`CLOUD_MQTT_HOST` / `CLOUD_MQTT_PORT`).
- Graceful disconnect on shutdown.

---

#### [NEW] `src/cloud_dashboard/routes/simulation_routes.py`

New API router exposing 3 endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/simulation/start` | `{"zone_id": "4B", "scenario_id": "S3"}` — starts scenario on specified zone |
| `POST` | `/api/simulation/stop` | `{"zone_id": "4B"}` — stops running scenario on specified zone and resets to baseline |
| `GET` | `/api/simulation/status` | Returns status of all 3 zones: `[{"zone_id": "4A", "scenario": null, "status": "idle", "step": 0, "total": 0}, ...]` |

---

### Component 2: Frontend — Enhanced NOC Dashboard UI

The existing NOC Dashboard (`index.html`) has a 3-column layout: Left (health + zone card + advisory), Middle (stats + charts), Right (logs + audit). We will add two new visual sections inspired by the Control Center's design.

---

#### [MODIFY] `src/cloud_dashboard/templates/index.html`

##### Change 1: Replace Zone Overview Bar with Rich WHI Cards (lines ~542-545)

**Current**: Simple 3-column grid of basic zone cards showing state text + WHI number.

**New**: Each zone card gets the Control Center's premium styling:
- **Glowing circular status ring** with pulsing animations (GREEN/YELLOW/ORANGE/RED border glow)
- **Large WHI score** with gradient text styling (Outfit font, 36px)
- **Colour-gradient progress bar** (`green → yellow → red`) showing WHI as percentage fill
- **Confirming sensor badges** row (Temp, Humid, Wind, Soil, Gas, Thermal) that light up when thresholds are crossed
- **Clamping warning banner** (dashed yellow border) when false-positive guard is active
- **Lateral warning badge** when preemptive escalation is active
- Click-to-select behaviour (existing) preserved

**Layout**: 3-column grid, each card ~300px min-width, responsive to 1-column on mobile.

##### Change 2: Add Collapsible Simulation Control Panel (new section after zone bar)

A new panel inserted between the zone overview bar and the main dashboard grid. Designed as a **collapsible drawer** (collapsed by default to keep the dashboard clean, with a toggle button):

```

  Simulation Control Panel                    [Zone: 4B ]   ← collapsed header

                                                               ← expanded panel
           
  S1 Normal  S2 Slow    S3 Sudden  S4 Fault        
    Day        Build     Ignition    Sensor        
           
                                                
  S6 Lateral  [ 3/6 Steps]  [RESET BASELINE]   
    Spread                                                
                                                

```

**Key design principles:**
- **Collapsible by default** — NOC operators who don't need simulation see a clean dashboard; researchers can expand it.
- **Zone selector** in the panel header auto-syncs with the main zone dropdown (or can be changed independently).
- **5 scenario buttons** (S1–S4, S6) matching the Control Center, with title + short description.
- **Per-zone status indicator** showing `Running: S3 (Step 3/6)` with a compact progress bar when a scenario is active.
- **RESET BASELINE** stop button (red accent).
- Uses the same glassmorphism card styling (`backdrop-filter: blur`, translucent bg, subtle border) as the existing panels.

##### Change 3: Add Edge Node Sensor Grid (new section after main dashboard grid)

A new bottom section showing real-time edge node sensor readings, inspired by the Control Center's edge card grid:

```
 Edge Node Sensor Arrays 
                                                                        
              
  Edge Node 4B-E1   Edge Node 4B-E2   Edge Node 4B-E3            
  Seq: 142 | OK     Seq: 143 | OK     Seq: 141 | OK              
                    
  Temp  Humid  Temp  Humid  Temp  Humid           
  32.1° 45.2%  55.0° 18.3%  31.8° 46.1%           
                    
                    
  Wind  SoilM  Wind  SoilM  Wind  SoilM           
  12km  22.1%  28km   8.2%  11km  23.0%           
                    
                    
  Gas   Therm  Gas   Therm  Gas   Therm           
  15ppm 0.3°   45ppm 4.2°   14ppm 0.4°            
                    
              

```

**Key features:**
- Shows edge nodes for the **currently selected zone** (switches when zone changes).
- Each sensor parameter box has **threshold-crossing highlighting** (red glow border when value crosses confirmation threshold — same logic as Control Center).
- Data sourced from the existing `/api/snapshot` → `edge_readings` array (already returned by the backend).
- 3-column responsive grid using `repeat(auto-fit, minmax(320px, 1fr))`.

##### Change 4: New CSS for the merged components

New CSS classes added to the `<style>` block:

| CSS Class | Purpose |
|-----------|---------|
| `.zone-overview-card` | Rich WHI card with status ring and gradient progress bar |
| `.whi-ring` | Circular glowing status indicator (140px diameter) |
| `.whi-ring.state-*` | Per-state glow colours + pulse animations |
| `.whi-progress-bar` | Gradient fill bar (green → yellow → red) |
| `.confirm-badge` / `.confirm-badge.active` | Sensor threshold confirmation pills |
| `.clamping-banner` | False-positive guard dashed warning banner |
| `.sim-panel` | Collapsible simulation drawer container |
| `.sim-panel.collapsed` | Collapsed state (height: 0, overflow hidden) |
| `.sim-toggle` | Toggle button for expand/collapse |
| `.sim-btn` | Scenario trigger button with hover lift |
| `.sim-btn.active` | Orange glow for actively running scenario |
| `.sim-stop` | Red-accent reset/stop button |
| `.edge-grid` | Responsive edge node card grid |
| `.edge-card` | Individual edge node card |
| `.param-box` / `.param-box.alerted` | Sensor parameter display with threshold highlighting |

##### Change 5: New JavaScript functions

| Function | Purpose |
|----------|---------|
| `toggleSimPanel()` | Expand/collapse the simulation drawer |
| `triggerSimulation(scenarioId)` | `POST /api/simulation/start` with selected zone + scenario |
| `stopSimulation()` | `POST /api/simulation/stop` for selected zone |
| `pollSimulationStatus()` | `GET /api/simulation/status` — update button states, progress bar (every 2s) |
| `renderRichZoneCards(zones)` | Replaces `pollZones()` rendering with enhanced WHI cards + rings |
| `renderEdgeNodes(edgeReadings)` | Renders edge sensor cards with threshold highlighting |
| Updated `pollSnapshot()` | Extended to also call `renderEdgeNodes()` with `data.edge_readings` |
| Updated `pollZones()` | Extended to use `renderRichZoneCards()` instead of basic zone cards |

---

### Component 3: Backend — Edge Telemetry in Snapshot API

#### [MODIFY] `src/cloud_dashboard/database.py`

The existing `get_latest_edge_telemetry(zone_id)` method already queries InfluxDB for the latest edge readings per zone. No changes needed — it already returns the data. We just need to ensure the snapshot response includes it (which it already does at line 81: `"edge_readings": edge_readings`).

**No database changes required** — the existing backend already returns all the data needed.

---

### Summary of All File Changes

| Action | File | Description |
|--------|------|-------------|
| **[NEW]** | `src/cloud_dashboard/services/simulation_service.py` | Multi-zone scenario orchestrator service |
| **[NEW]** | `src/cloud_dashboard/routes/simulation_routes.py` | REST API endpoints for simulation control |
| **[MODIFY]** | `src/cloud_dashboard/app.py` | Register SimulationService + include simulation router |
| **[MODIFY]** | `src/cloud_dashboard/templates/index.html` | Enhanced zone cards, simulation panel, edge node grid, new CSS + JS |

---

## Verification Plan

### Automated Tests

```bash
# Verify the new API endpoints respond correctly
curl http://localhost:9000/api/simulation/status
# Expected: [{"zone_id":"4A","status":"idle",...}, {"zone_id":"4B",...}, {"zone_id":"4C",...}]

# Start a scenario
curl -X POST http://localhost:9000/api/simulation/start \
  -H "Content-Type: application/json" \
  -d '{"zone_id":"4B","scenario_id":"S3"}'
# Expected: {"status":"started","zone_id":"4B","scenario_id":"S3"}

# Check status during execution
curl http://localhost:9000/api/simulation/status
# Expected: zone 4B shows status:"running", step: N, total: 6

# Stop scenario
curl -X POST http://localhost:9000/api/simulation/stop \
  -H "Content-Type: application/json" \
  -d '{"zone_id":"4B"}'
```

### Manual Verification

1. **Rich Zone Cards**: Open `http://localhost:9000/`. Verify all 3 zone cards display glowing status rings, large WHI scores, gradient progress bars, and sensor confirmation badges.
2. **Zone Card Reactivity**: Run S3 on zone 4B. Verify the 4B zone card transitions GREEN → YELLOW → ORANGE → RED with animated glow and pulsing border. Verify 4A and 4C remain GREEN.
3. **Simulation Panel**: Expand the simulation panel. Click S3. Verify progress indicator shows `Running: S3 (Step 2/6)` with progress bar filling. Click RESET BASELINE. Verify status returns to idle.
4. **Edge Node Grid**: Verify edge node cards appear for the selected zone. Trigger S3 on 4B. Verify the impacted node's Temperature and Gas parameter boxes turn red (threshold exceeded). Switch to zone 4A — verify the cards update to show 4A's edge nodes.
5. **Existing Features Unbroken**: Verify all 9 existing pages still work. Verify the advisory console, historical charts, lateral timeline, and audit trail all function as before.
