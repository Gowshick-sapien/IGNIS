# Consolidated Testing Guidelines — Phase D: Multi-Zone Coordination

This document details the verification procedures and manual testing strategies for validating **Phase D: Multi-Zone Coordination**.

---

## 1. Automated Unit Tests

Execute the comprehensive test suite locally to verify configuration merging, circular wind bearing averaging, modulo wind alignment cones, and pre-emptive zone state transitions:

```bash
python -m unittest discover tests
```

Expected output:
```text
Ran 26 tests in 0.028s

OK
```

---

## 2. Integrated Cluster Validation

### Step A: Spin Up Multi-Zone Containers
Start the coordinated cluster of 3 zones and central cloud services:
```bash
docker compose up --build -d
```

### Step B: Validate REST API Routes
Verify that the stateless endpoints return valid data matching active zones:

1. **Active Zones Snapshot**:
   ```bash
   curl http://localhost:9000/api/zones
   ```
   *Expected*: JSON array containing status, max WHI, and warning logs for all active zones.

2. **Downwind Propagation Timeline**:
   ```bash
   curl http://localhost:9000/api/lateral-timeline?minutes=15
   ```
   *Expected*: JSON array mapping generated lateral warnings and wind vectors.

3. **Dynamic Snapshot**:
   ```bash
   curl http://localhost:9000/api/snapshot?zone_id=4A
   ```
   *Expected*: Snapshot metadata representing Zone 4A's status and telemetry.

4. **Dynamic Override Command**:
   ```bash
   curl -X POST http://localhost:9000/api/advisory \
     -H "Content-Type: application/json" \
     -d '{"command": "set_override_state", "parameters": {"state": "YELLOW"}, "zone_id": "4A"}'
   ```
   *Expected*: HTTP 200 OK with dispatched sequence audit records.

---

## 3. Scenario S6 Lateral Coordination Verification

Perform this manual execution to confirm that fog nodes cooperatively publish, receive, align, and act on downwind warnings:

1. **Access local Control Center for Zone 4B**:
   - Open `http://localhost:1883` in your browser (local broker web console or control center client).
2. **Trigger Scenario S6**:
   - Click the **S6 - Lateral Spread** simulation button.
   - The simulator overrides Zone 4B's edge nodes (`4B-E1` to `4B-E3`) to model an escalating wildfire with wind blowing South (180.0°).
3. **Verify Zone 4B Escalation**:
   - Open the Central NOC Operations Dashboard at `http://localhost:9000`.
   - Under the Zone Select dropdown, choose **Zone 4B**.
   - Observe the Max WHI rise and the zone card transition through **YELLOW** $\rightarrow$ **ORANGE** $\rightarrow$ **RED**.
4. **Verify Pre-emptive Escalation in Zone 4C**:
   - Select **Zone 4C** in the focus selector or observe the top cards overview.
   - Because Zone 4C lies directly downwind of Zone 4B (relative bearing 180°), and the wind is aligned (180.0°), **Zone 4C should automatically elevate to YELLOW**.
   - Confirm that a warning flag is displayed: `[WARNING] Pre-emptive Escalation: Warning from Zone 4B`.
   - Verify that Zone 4C's own edge simulator nodes continue to report GREEN telemetry.
5. **Verify Lateral Timeline Logs**:
   - Check the **Fog-to-Fog Lateral Timeline** ticker panel on the Central NOC Dashboard.
   - Validate that the propagation sequence is logged sequentially.
6. **Reset Stack**:
   - Click **RESET SYSTEM TO BASELINE** in the local Control Center interface to restore the nodes.
