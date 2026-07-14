# Testing Guidelines — Phase D, Sub-Phase D4: Multi-Zone Dashboard & API

This document describes the testing requirements and validation procedures for **Phase D, Sub-Phase D4 (Multi-Zone Dashboard & API)** of the IGNIS system.

---

## Testing Prerequisites
- **Docker Stack**: Ensure the Docker daemon is active.
- **InfluxDB Schema**: Databases must have active measurements for `zone_state`, `telemetry`, and `lateral_events`.

---

## Integration Verification Procedures

### 1. Launch Multi-Zone Infrastructure
Start the Docker Compose containers:
```bash
docker compose up --build -d
```

### 2. Verify API Endpoints
Execute HTTP calls using curl or a browser to ensure new routes resolve successfully:

- **All Zone States**:
  ```bash
  curl http://localhost:9000/api/zones
  ```
  Expected output: List of states for Zones 4A, 4B, and 4C.

- **Lateral Event Timeline**:
  ```bash
  curl http://localhost:9000/api/lateral-timeline?minutes=10
  ```
Expected output:

Returns HTTP 200 OK.
Returns a valid JSON array of lateral coordination events generated within the requested time window.
If no lateral events have occurred during the specified period, an empty array ([]) is expected.

- **Dynamic Zone Snapshot**:
  ```bash
  curl http://localhost:9000/api/snapshot?zone_id=4A
  ```
  Expected output: Snapshot metrics specific to Zone 4A and its prefixed nodes (`4A-E1`, `4A-E2`, `4A-E3`).

### 3. Verify UI Updates
- Open `http://localhost:9000` in a browser.
- **Top Zone Cards**: Check if cards for Zone 4A, 4B, and 4C are rendered at the top, showing their current severity level.
- **Zone Selector**: Select Zone 4A, 4B, or 4C from the dropdown in the header and verify that the detail status panels and the trend charts reload dynamically with the matching zone data.
- **Dynamic Node Plots**: Verify that the Chart.js legends match the zone-prefixed nodes (e.g. `Node 4B-E1`, `Node 4B-E2`, `Node 4B-E3` when Zone 4B is selected).
