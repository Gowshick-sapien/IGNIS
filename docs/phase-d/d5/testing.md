# Testing Guidelines — Phase D, Sub-Phase D5: Scenario S6 & Test Suite

This document describes the testing requirements and validation procedures for **Phase D, Sub-Phase D5 (Scenario S6 & Test Suite)** of the IGNIS system.

---

## Testing Prerequisites
- **Docker Stack**: Ensure the Docker daemon is active.
- **Python**: A local Python environment should be present to run unit tests.

---

## Verification Procedures

### 1. Automated Tests Run
To verify the math parsing, configuration merge, and scenario generator code:
```bash
python -m unittest discover tests
```
Ensure all 26 tests pass successfully.

### 2. Manual Integration Walkthrough
To verify the lateral spread scenario S6 propagation on the running multi-zone cluster:

1. **Start the Multi-Zone stack**:
   ```bash
   docker compose up --build -d
   ```
2. **Access local Range Control Center (Zone 4B)**:
   - Navigate to `http://localhost:1883` (or the control center port mapped for Zone 4B if running locally. Note: `http://localhost:9000` is the central cloud dashboard).
3. **Trigger Scenario S6**:
   - In the Control Center UI panel, click the button for **S6 - Lateral Spread**.
   - The scenario status bar will show "S6 Execution (Step 1/6)" and begin updating Zone 4B's simulator nodes.
4. **Observe the Central NOC Dashboard**:
   - Open the central dashboard at `http://localhost:9000`.
   - Select **Zone 4B (Simlipal Core)** in the detail panel or dropdown. You will see Zone 4B's telemetry escalate to **YELLOW**, then **ORANGE**, and finally **RED**.
   - As Zone 4B goes RED with wind blowing south (180°), select **Zone 4C (Simlipal South)** or watch the top Zone Overview cards.
   - **Zone 4C** should transition to **YELLOW** status with the warning flag showing: `[WARNING] WARNING WIND FROM 4B`, even though Zone 4C's own edge sensors report normal GREEN conditions.
   - **Lateral Timeline**: The "Fog-to-Fog Lateral Timeline" panel on the right should display the broadcast event logs captured dynamically.
5. **Reset the Scenario**:
   - Click **RESET SYSTEM TO BASELINE** in the local Control Center to clear overrides.
