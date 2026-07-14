# Walkthrough — Phase D, Sub-Phase D4: Multi-Zone Dashboard & API

Sub-Phase D4 upgrades the Central NOC Operations Dashboard and APIs to support a dynamic, zone-agnostic multi-zone topology with real-time lateral propagation timeline tracking.

---

## Technical Implementations & Codebase Changes

### 1. Cloud Ingestor
- **[MODIFY] [src/cloud_ingestor/mqtt_service.py](file:///d:/projects/IGNIS/src/cloud_ingestor/mqtt_service.py)**:
  - Implemented topic routing for `lateral` topics.
  - Added `process_lateral_event(...)` which writes incoming lateral broadcasts to the `lateral_events` measurement in InfluxDB, saving the state, WHI, wind speed, and wind direction.

### 2. Dashboard Database API
- **[MODIFY] [src/cloud_dashboard/database.py](file:///d:/projects/IGNIS/src/cloud_dashboard/database.py)**:
  - Implemented `get_all_zone_states()` returning pivoted records for all active forest division zones.
  - Upgraded `get_historical_chart_data(...)` to dynamically compile and discover node IDs from query records rather than using hardcoded E11/E12/E13 loops.
  - Implemented `get_lateral_events(...)` to retrieve logged neighbor notification sequences.

### 3. FastAPI Routing & App Setup
- **[MODIFY] [src/cloud_dashboard/app.py](file:///d:/projects/IGNIS/src/cloud_dashboard/app.py)**:
  - Removed `ZONE_ID` environment variables and `app.state.zone_id` initialization, making the dashboard server zone-agnostic.
- **[MODIFY] [src/cloud_dashboard/routes.py](file:///d:/projects/IGNIS/src/cloud_dashboard/routes.py)**:
  - Created `/api/zones` and `/api/lateral-timeline` endpoints.
  - Updated `/api/snapshot`, `/api/history`, and `/api/advisory` to fetch and command division zones dynamically using a `zone_id` parameter instead of the singleton application state.

### 4. Glassmorphic NOC User Interface
- **[MODIFY] [src/cloud_dashboard/templates/index.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/index.html)**:
  - **Zone Select Dropdown**: Introduced a zone selector in the header to shift the dashboard focus.
  - **Zone Overview Bar**: Added a dynamic top card deck rendering states, WHI index, and warning indicators for all division zones.
  - **Dynamic Chart Datasets**: Re-engineered Chart.js datasets binding in JavaScript to dynamically map keys present under `response.nodes` (e.g. `4B-E1`, `4C-E3`).
  - **Lateral Coordination Timeline**: Added a timeline panel displaying active propagation events logged in InfluxDB.

---

## Verification & Validation Results

### Unit Test Execution
All unit tests in the project run successfully:
```bash
python -m unittest discover tests
```
Output:
```text
Ran 25 tests in 0.044s

OK
```
