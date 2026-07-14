# Walkthrough — Phase D, Sub-Phase D2: Docker Compose Multi-Zone Infrastructure

Sub-Phase D2 implements a 3-zone Docker Compose layout leveraging YAML anchors to maintain clean, DRY container definitions.

---

## Technical Implementations & Codebase Changes

### 1. Unified Multi-Zone Compose File
- **[MODIFY] [docker-compose.yml](file:///d:/projects/IGNIS/docker-compose.yml)**:
  - Introduced YAML anchors (`x-edge-template`, `x-fog-template`, `x-broker-template`) for standardization.
  - Scaled the infrastructure into 3 distinct zones representing Simlipal Tiger Reserve:
    - **Zone 4A (North)**: `mqtt-broker-4a` (port `1881`), `fog-node-4a`, and three edge simulator nodes (`4A-E1`, `4A-E2`, `4A-E3`).
    - **Zone 4B (Core)**: `mqtt-broker-4b` (port `1883`), `fog-node-4b`, three edge simulator nodes (`4B-E1`, `4B-E2`, `4B-E3`), and the Local Control Center (port `8000`).
    - **Zone 4C (South)**: `mqtt-broker-4c` (port `1885`), `fog-node-4c`, and three edge simulator nodes (`4C-E1`, `4C-E2`, `4C-E3`).
  - Standardized all edge nodes and fog runners to connect to their respective local brokers, while fog nodes and central ingest/dashboard connect to the shared central `cloud-broker` (port `1884`).
  - Standardized naming structure to use zone-prefixed node identifiers (`4A-E*`, `4B-E*`, `4C-E*`).

### 2. Environment Variables Clean Up
- **[MODIFY] [.env](file:///d:/projects/IGNIS/.env)**:
  - Removed localized variables like `LOCAL_MQTT_HOST` and `ZONE_ID`.
  - Retained central shared variables (`CLOUD_MQTT_HOST`, `CLOUD_MQTT_PORT`, InfluxDB authentication keys, orgs, and buckets).

---

## Verification & Validation Results

### YAML Syntax Verification
Verified the schema structure using:
```bash
docker compose config
```
This parsed successfully and expanded the YAML anchors into complete container service configurations without errors.
