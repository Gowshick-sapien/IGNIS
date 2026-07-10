# Walkthrough — Phase C: Centralized Cloud Layer

Phase C implements the Centralized Cloud layer of the IGNIS architecture, introducing:
1. A simulated **Cloud MQTT Broker** (port `1884`).
2. An **InfluxDB v2 Database** (port `8086`) structured around optimized measurements to capture telemetry, zone states, incident alerts, action logs, audit trails, and performance metrics.
3. An independent background **Cloud Ingestor service** decoupled from visual rendering to guarantee telemetry storage resilience with offline buffering.
4. A stateless **Central Operations NOC Dashboard** (port `9000`) with dynamic baseline comparison charts (using seasonal datasets for summer, winter, and monsoon) and system topology health checks.
5. A secure **Advisory-Command Path** with replay protection, duplicate prevention, and monotonic sequence checking inside the local Fog Node runner.

---

## Technical Implementations & Codebase Changes

### 1. Project-wide Configuration
- **[.env](file:///d:/projects/IGNIS/.env)**: Centralized environment variables mapping local/cloud brokers, InfluxDB endpoints, orgs, buckets, tokens, and target zone IDs.
- **[requirements.txt](file:///d:/projects/IGNIS/requirements.txt)**: Appended `influxdb-client` and `python-dotenv` packages.
- **[config/mosquitto_cloud.conf](file:///d:/projects/IGNIS/config/mosquitto_cloud.conf)**: Configured the cloud broker to handle regional pub/sub.
- **[docker-compose.yml](file:///d:/projects/IGNIS/docker-compose.yml)**: Standardized services using `.env` file contexts and added `cloud-broker`, `influxdb`, `cloud-ingestor`, and `cloud-dashboard` containers.

### 2. Standardized Topic Taxonomy
Reorganized local and cloud topics to match a clean hierarchical design:
- Telemetry: `ignis/v1/telemetry/zone/{zone}/edge/{node}`
- Fog Node State: `ignis/v1/fog/zone/{zone}/state`
- Fog Alerts: `ignis/v1/fog/zone/{zone}/alert`
- Fog Actions: `ignis/v1/fog/zone/{zone}/action_log`
- Advisory commands: `ignis/v1/advisory/zone/{zone}/command` & `ignis/v1/advisory/zone/{zone}/response`
- Heartbeats: `ignis/v1/system/fog/zone/{zone}/heartbeat` & `ignis/v1/system/cloud/ingestor/heartbeat`

Updated files:
- **[src/edge_sim.py](file:///d:/projects/IGNIS/src/edge_sim.py)**
- **[src/fog_node_runner.py](file:///d:/projects/IGNIS/src/fog_node_runner.py)**
- **[src/control_center/mqtt_listener.py](file:///d:/projects/IGNIS/src/control_center/mqtt_listener.py)**
- **[src/control_center/scenario_service.py](file:///d:/projects/IGNIS/src/control_center/scenario_service.py)**

### 3. Upgraded Fog Node Runner
- **[src/fog_node_runner.py](file:///d:/projects/IGNIS/src/fog_node_runner.py)**:
  - Manages dual `paho.mqtt.client` instances (`client_local` and `client_cloud`).
  - Forwards edge telemetry to the Cloud Broker in real-time.
  - Subscribes to the Advisory topic on the cloud broker.
  - Executes replay protection checking: validates UUID duplication against in-memory cache, checks command timestamp against `ttl`, and enforces monotonic sequence numbers.
  - Decouples policy adjustments (threshold limits) from manual overrides (GREEN/YELLOW/ORANGE/RED clamp).
  - Publishes command responses back to the cloud broker.

### 4. Decentralized Cloud Ingestor Service
- **[src/cloud_ingestor/database.py](file:///d:/projects/IGNIS/src/cloud_ingestor/database.py)**: Connection logic and point writes mapping fields and timestamps.
- **[src/cloud_ingestor/mqtt_service.py](file:///d:/projects/IGNIS/src/cloud_ingestor/mqtt_service.py)**: Listens for incoming messages, calculates network transmission latencies, and writes them to InfluxDB. Implements in-memory database buffering during network/service disconnects and auto-flushes once restored.
- **[src/cloud_ingestor/main.py](file:///d:/projects/IGNIS/src/cloud_ingestor/main.py)**: Startup loop with exponential backoff connection retries.

### 5. Stateless Cloud Dashboard
- **[src/cloud_dashboard/database.py](file:///d:/projects/IGNIS/src/cloud_dashboard/database.py)**: Read-only query wrapper retrieving snapshots, latencies, alert lines, and audit logs.
- **[src/cloud_dashboard/routes.py](file:///d:/projects/IGNIS/src/cloud_dashboard/routes.py)**: REST API mapping polling snapshot routes and handling one-off transient advisory command publishes.
- **[src/cloud_dashboard/app.py](file:///d:/projects/IGNIS/src/cloud_dashboard/app.py)**: Bootstraps the stateless FastAPI instance.
- **[src/cloud_dashboard/templates/index.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/index.html)**: Dark glassmorphic interface showing topological health pings, live metrics streams vs historical seasonal averages, and the Operator Advisory Override console.

---

## Verification & Validation Results

### 1. Automated Testing

We developed a dedicated test suite covering the dual client routing, duplicate command rejection, expired TTL check, and database connection loss buffering.

#### Tests Executed:
- `test_advisory_command_valid`: Confirms clamp command overrides the local Fog Node state and registers SUCCESS.
- `test_advisory_command_duplicate_rejected`: Confirms duplicate command UUIDs are identified and ignored.
- `test_advisory_command_expired_rejected`: Confirms command timestamps exceeding the TTL are rejected as expired.
- `test_ingestor_offline_buffering_and_flush`: Confirms that when database ping returns False, ingestor safely appends telemetry points to its offline list, and then flushes them to InfluxDB upon database recovery.

#### Test Execution Logs:
```bash
> python -m unittest discover tests
.2026-07-10 10:42:18,833 [INFO] fog_node_runner: ZONE 4B STATE TRANSITION: GREEN -> YELLOW
.2026-07-10 10:42:18,833 [INFO] fog_node_runner: ZONE 4B STATE TRANSITION: GREEN -> RED
.2026-07-10 10:42:18,833 [INFO] fog_node_runner: Received Cloud Advisory payload: {'command_id': 'cmd-dup-999', 'sequence_number': 2, 'zone_id': '4B', 'timestamp': '2026-07-10T05:12:18Z', 'ttl': 300, 'command': 'set_override_state', 'parameters': {'state': 'RED'}}
2026-07-10 10:42:18,833 [INFO] fog_node_runner: Published command response to cloud: FAILED | Duplicate command ID detected
.2026-07-10 10:42:18,833 [INFO] fog_node_runner: Received Cloud Advisory payload: {'command_id': 'cmd-expired-777', 'sequence_number': 3, 'zone_id': '4B', 'timestamp': '1783656738', 'ttl': 300, 'command': 'set_override_state', 'parameters': {'state': 'RED'}}
2026-07-10 10:42:18,834 [INFO] fog_node_runner: Published command response to cloud: FAILED | Command expired. Elapsed time: 3600.0s, TTL: 300s
.2026-07-10 10:42:18,834 [INFO] fog_node_runner: Received Cloud Advisory payload: {'command_id': 'cmd-12345', 'sequence_number': 1, 'zone_id': '4B', 'issued_by': 'operator_alpha', 'timestamp': '2026-07-10T05:12:18Z', 'ttl': 300, 'command': 'set_override_state', 'parameters': {'state': 'RED'}}
2026-07-10 10:42:18,834 [INFO] fog_node_runner: FOG MANUAL STATE OVERRIDE: Clamped to RED
2026-07-10 10:42:18,834 [INFO] fog_node_runner: Published command response to cloud: SUCCESS | State successfully overridden to RED
.2026-07-10 10:42:18,835 [WARNING] cloud_ingestor_mqtt: InfluxDB write failed. Buffering record. Error: InfluxDB ping failed.
2026-07-10 10:42:18,835 [WARNING] cloud_ingestor_mqtt: InfluxDB write failed. Buffering record. Error: InfluxDB ping failed.
2026-07-10 10:42:18,835 [INFO] cloud_ingestor_mqtt: InfluxDB is back online. Flushing 2 buffered records.
2026-07-10 10:42:18,835 [INFO] cloud_ingestor_mqtt: Successfully flushed 2 records.
......
----------------------------------------------------------------------
Ran 12 tests in 0.005s

OK
```

### 2. Manual Scenarios Verification

#### S8 — Cloud Advisory Override
- **Trigger**: Click **RED** on the override state dropdown in the Central Cloud Dashboard and hit **Clamp**.
- **Action**: Dashboard publishes a command payload to the Cloud Broker, writes a PENDING audit log, and pings the Fog Node.
- **Fog Reaction**: Local Fog node clamps its dynamic WHI calculation and locks state to RED. It outputs pre-suppression action logs ( perimeter mist actuate, emergency notify) and replies with SUCCESS.
- **Result**: The local dashboard and central dashboard update in sync to show RED and display the active override badge. The audit feed displays a `SUCCESS` badge.

#### S9 — Dynamic Threshold Adjustment
- **Trigger**: Increase temperature threshold to `50.0°C` in the Central Dashboard and hit **Set**.
- **Fog Reaction**: Local Fog Node runner processes the adjustment command, updates the `temperature_c` confirmation limit directly in its memory context, and registers success.
- **Verification**: Simulating a scenario with `45°C` temperature (exceeds default `40.0` but below new `50.0`) registers as GREEN/YELLOW dynamic warnings, avoiding false red escalations because the threshold was successfully adjusted at runtime.
