# IGNIS -- Project Definition

**Intelligent Geo-distributed Network for Wildfire Intervention and Surveillance**

---

## 1. System Identity

IGNIS is a distributed wildfire early warning and autonomous pre-suppression platform built on a hierarchical Edge-Fog-Cloud (EFC) computing architecture. It decentralizes decision intelligence from remote cloud data centers to locally deployed fog computing nodes stationed directly within forest administrative ranges, enabling autonomous threat assessment, multi-sensor confirmation, peer-to-peer lateral coordination, and pre-suppression action triggering in sub-second timeframes -- independent of wide-area network availability.

IGNIS Version 1 delivers:

- A **fully functional distributed decision architecture** implemented as a Docker microservice platform with MQTT-based asynchronous messaging, real-time InfluxDB telemetry persistence, and a 9-page unified web dashboard for operations and research.
- A **rigorous pre-hardware simulation environment** where every physical component (weatherproof sensors, LoRa radio transceivers, solar-powered fog servers, mist/drone/acoustic actuators) is replaced with a containerized software surrogate reproducing identical data flows, decision logic, and failure modes. This simulation validates all architectural claims with statistical rigor (Student-t 95% confidence intervals across 30-trial sweeps) before any hardware capital expenditure.
- A **1:1 hardware migration path** -- the transition from V1 software to V2 field hardware is a data-source swap at the edge tier, not a redesign of decision logic.

---

## 2. Problem Domain

### 2.1. The Wildfire Early Warning Challenge

Wildfires in tropical deciduous and dry-forest ecosystems represent an escalating threat to biodiversity, carbon sequestration, human habitation, and wildlife conservation. In Indian forest landscapes -- characterized by high biodiversity, remote hilly terrain, and severe seasonal droughts -- traditional wildfire detection suffers from three structural failure modes.

### 2.2. Detection and Response Latency

Centralized satellite-based surveillance (MODIS, VIIRS, Sentinel-3) relies on periodic orbital passes with revisit intervals of 6 to 12 hours and is subject to cloud-masking vulnerabilities. By the time a thermal anomaly pixel is confirmed and routed through state forest department hierarchies, an incipient ignition has often escalated into an uncontrollable crown fire. The fundamental constraint is that detection and response decisions are made far from the point of origin, introducing unavoidable communication and processing latency.

### 2.3. Fragile Centralized Dependencies

Conventional IoT surveillance architectures route raw sensor telemetry across cellular or satellite uplinks directly to a centralized cloud platform for processing and decision-making. This creates a single point of failure: when monsoon winds, storm fronts, or remote geography cause wide-area network (WAN) partitions, field stations lose all monitoring and decision-making capability. The forest is unprotected precisely when conditions are most dangerous.

### 2.4. False Positive Vulnerability

Simplistic single-sensor threshold triggers (temperature exceeding a fixed value, for example) cannot distinguish between a genuine ignition event and benign environmental causes -- direct sunlight on heated rocks, localized non-fire thermal drift, or a malfunctioning sensor. These false alarms exhaust forestry field staff and induce alert fatigue, ultimately undermining trust in the entire detection system.

---

## 3. Proposed Solution

### 3.1. The IGNIS Architecture

IGNIS resolves these structural failures through a three-tier distributed computing hierarchy:

**Edge Tier (Sensor Arrays):** Low-power microclimate sensor nodes deployed across forest zones provide high-frequency multi-parameter environmental readings (temperature, humidity, wind speed/direction, soil moisture, gas/smoke concentration, thermal anomaly, ambient light). Each edge node packages structured telemetry and publishes it to the local fog tier over MQTT at configurable intervals (default: every 3.0 seconds).

**Fog Tier (Autonomous Local Intelligence):** Solar-powered local fog servers stationed within each forest administrative range. Each fog node is an autonomous decision engine that:

- Normalizes raw sensor values into unified 0.0-1.0 risk coefficients using parameter-specific clamping and inversion
- Computes a continuous composite Wildfire Hazard Index (WHI) from weighted multi-factor equations calibrated for specific forest fuel types
- Enforces multi-sensor temporal confirmation: at least 3 independent sensor modalities must cross emergency thresholds before escalation to intervention states
- Maintains a deterministic state machine (GREEN, YELLOW, ORANGE, RED) with hysteresis safety gates
- Triggers autonomous pre-suppression actions (mist perimeter activation, drone reconnaissance dispatch, acoustic wildlife deterrents) within milliseconds of confirmed threat detection
- Coordinates laterally with adjacent fog nodes over peer-to-peer MQTT channels, broadcasting danger vectors and wind headings so downwind zones can pre-emptively elevate alert postures before their own sensors detect the threat
- Buffers all events locally during WAN outages and flushes automatically on reconnection with zero message loss

**Cloud Tier (Regional Operations):** The centralized regional operations layer provides persistent time-series telemetry storage (InfluxDB v2), stateless data querying, operator advisory command dispatch with security verification gates, and a unified web dashboard consolidating real-time monitoring, experiment orchestration, historical analysis, regression detection, and reproducibility publishing.

### 3.2. Why This Architecture Works

The core principle is **localized autonomy with optional centralized oversight**:

- **Latency is eliminated** because decision intelligence resides at the forest edge. Fog nodes evaluate sensor data and trigger actions locally, achieving confirmed threat response in under 150 milliseconds -- compared to minutes or hours for satellite-dependent systems.
- **Centralized failure is irrelevant** because fog nodes operate independently of cloud connectivity. During WAN outages, all risk scoring, state evaluation, and action logging continue uninterrupted. The cloud tier enhances the system with historical analytics and operator overrides but is not required for safety-critical operation.
- **False positives are suppressed** because multi-sensor confirmation demands corroboration from at least 3 independent sensor types before any escalation to intervention states. A single faulty sensor -- or even two -- cannot generate a false alarm.
- **Fire spread is anticipated** because fog nodes communicate laterally, broadcasting risk state and wind vectors. Downwind zones are warned before smoke or flame physically crosses administrative borders.

---

## 4. Core Capabilities

### 4.1. Real-Time Wildfire Risk Scoring

The fog node computes a continuous Wildfire Hazard Index (WHI) from 8 environmental parameters using weighted multi-factor equations. Raw sensor readings are normalized into dimensionless 0.0-1.0 risk coefficients and combined via a weighted dot product. Weights and normalization boundaries are configurable per zone through JSON configuration files, enabling distinct forest-type profiles (dry-deciduous, moist-Himalayan) without code changes. See [Mathematical Framework](mathematical_framework.md) for complete derivations.

### 4.2. Multi-Sensor Confirmation and False Positive Suppression

A high WHI score alone is insufficient for state escalation. IGNIS enforces a multi-sensor temporal confirmation rule: at least 3 independent sensor modalities (out of 6 confirmable types: temperature, humidity, wind speed, soil moisture, gas/smoke, thermal anomaly) must simultaneously exceed their individual confirmation thresholds before the system can transition into ORANGE or RED states. If the WHI exceeds the ORANGE or RED threshold but fewer than 3 sensors confirm, the state is clamped to YELLOW. This guarantees 0.0% false positive rate under single or dual sensor failure.

### 4.3. Deterministic Zone State Machine

Each fog node maintains a deterministic 4-state machine (GREEN, YELLOW, ORANGE, RED) with defined transition rules based on WHI thresholds and confirmation counts. The state machine incorporates hysteresis safety gates -- requiring sustained improvement in readings before de-escalating -- to prevent dangerous oscillation during borderline conditions. Zone-level state is derived using a max-state aggregation operator across all edge nodes, ensuring localized threats are never diluted by benign readings from distant sensors.

### 4.4. Autonomous Pre-Suppression Action Triggering

Upon entering ORANGE or RED state, the fog node automatically generates structured action records (water mist perimeter activation, drone reconnaissance dispatch, acoustic wildlife deterrents, control center notification) in under 150 milliseconds. In V1, these are immutable JSON log records; in V2 hardware deployment, they map directly to relay actuators and MAVLink drone commands.

### 4.5. Peer-to-Peer Lateral Fog Coordination

Fog nodes communicate directly over regional MQTT channels without cloud intervention. When a fog node escalates to YELLOW or above, it broadcasts its zone state and vector-averaged wind heading to all peer fog nodes. Receiving nodes evaluate wind-bearing alignment against their own geographic position using circular trigonometric calculations with configurable angular tolerance. If the wind points toward the receiving zone, that zone pre-emptively elevates its monitoring state one level. This enables predictive fire spread alerting in under 5.0 seconds -- downwind zones are warned before their own sensors detect any anomaly.

### 4.6. Offline Resilience and Data Continuity

Fog nodes interface with the cloud tier through a thread-safe BufferedPublisher. During cloud disconnection, the publisher queues all unsent events to a local deque (capacity: 5,000 items, approximately 4 hours of offline telemetry). Upon reconnection, the queue flushes automatically, injecting `was_buffered` and `buffer_flush_timestamp` metadata into each record for SLA auditing. During the entire outage period, all local decision-making, state evaluation, and action logging continue without interruption.

### 4.7. Chaos and Fault Resilience Testing

An integrated Chaos Controller service injects realistic failure modes into the running system: network latency and jitter, packet loss, MQTT broker crashes, sensor dropouts, and cloud WAN disconnection during active fire events. These validate that safety guarantees hold under adversarial conditions, not just during clean-path operation.

### 4.8. Standardized Scenario Library

Seven standardized test scenarios (S1-S7) exercise every capability claim. Each scenario is defined as a versioned, schema-validated YAML configuration file specifying sensor data trajectories, chaos actions, expected state outcomes, and benchmark metric targets. See [Scenario Reference](scenario_reference.md) for the complete catalog.

### 4.9. Automated Experiment Orchestration and Statistical Validation

The experiment orchestrator automates the end-to-end validation pipeline: YAML schema validation, scenario execution, event stream metric derivation, and statistical computation of sample counts, mean, median, min, max, standard deviation, and Student-t 95% confidence intervals for every scenario metric across configurable trial counts.

### 4.10. Regression Detection and Comparison

An automated regression detector evaluates experiment runs against configurable threshold rules. It computes side-by-side metric differentials, verdict deltas (PASS to FAIL transitions), confidence interval overlap analysis, and automated regression/improvement classification.

### 4.11. Reproducibility Publishing

Every experiment run can be exported as a self-contained reproducibility bundle: a ZIP archive containing the code snapshot at the exact commit, random seeds, scenario configurations, environment manifest (Python version, dependency versions), and a run script to re-execute the experiment identically. Additional export formats include Markdown, standalone HTML with vendored Plotly.js charts, CSV, JSON, PDF, and Word DOCX.

---

## 5. Benchmark Performance

Across rigorous multi-trial validation sweeps (N=30 automated trials per scenario), IGNIS V1 achieved 100% compliance with all architectural performance targets:

| Benchmark | Metric | Target SLA | Measured Result | Verdict |
| :--- | :--- | :--- | :--- | :---: |
| Fog Decision Latency | Sensor threshold breach to logged action | under 150 ms | 88.4 ms +/- 4.2 ms | PASS |
| Lateral Alert Propagation | Adjacent downwind fog node escalation | under 5.0 s | 3.24 s +/- 0.18 s | PASS |
| False Positive Rate (S4) | Invalid ORANGE/RED escalations on sensor fault | 0.0% | 0.0% (0/30 trials) | PASS |
| Offline Continuity (S5) | Buffered events recovered post-WAN reconnect | 100.0% | 100.0% (30/30 trials) | PASS |
| Crosstalk Isolation (S7) | Cross-zone message leakage | 0 messages | 0 messages (0/30 trials) | PASS |

---

## 6. Simlipal Case Study

### 6.1. Ecological Context

IGNIS V1 is calibrated against the environmental conditions of the **Simlipal Tiger Reserve / Biosphere Reserve**, Mayurbhanj district, Odisha, India (centered at approximately 21 deg 56' N, 86 deg 20' E). The reserve is a UNESCO Biosphere Reserve encompassing approximately 5,569 sq km of tropical deciduous forest, home to Bengal tigers, Asian elephants, and over 1,000 plant species.

### 6.2. Why Simlipal

| Ecological Factor | Physical Condition | IGNIS Modeling Response |
| :--- | :--- | :--- |
| Fuel Bed | Dense Sal (Shorea robusta) cover sheds thick, dry, resinous leaves in late winter/spring | High weight assigned to soil moisture (w=0.15) and humidity (w=0.15) |
| Diurnal Thermal Surge | Pre-monsoon temperatures regularly exceed 40 deg C between 12:00-15:00 | Time-of-day normalization peaks at 14:00 with symmetric 12-hour decay |
| Anthropogenic Ignition | NTFP harvesting involves lighting leaf litter, frequently escaping | Gas/smoke (w=0.15) and thermal anomaly (w=0.15) calibrated for early smoldering detection |
| Microclimate Dryness | Pre-monsoon soil moisture below 10%, humidity below 25% | Confirmation thresholds set at these boundaries to prevent false alarms during normal dry days |
| Wind Corridors | North-South mountain ridges channel dry high-velocity winds | Lateral peer topology configured N-S with +/-45 deg tolerance |

### 6.3. Spatial Hierarchy

The Simlipal ecosystem is modeled as **Region 4** with three neighboring ecological zones:

| Zone | Description | Ecological Profile |
| :--- | :--- | :--- |
| 4A | Northern Zone (Simlipal North) | Tourist/buffer area, deciduous hill forest, Baripada/Jashipur range border |
| 4B | Core Zone (Simlipal Core) | Strict protected biosphere core, high Sal density, primary simulation target |
| 4C | Southern Zone (Simlipal South) | Pithabata/Udala southern foothills, dry mixed deciduous scrubland |

Each zone contains 3 edge sensor nodes (e.g., 4B-E1, 4B-E2, 4B-E3), totaling 9 edge nodes across the deployment. The identifier `4B-E2` resolves hierarchically to Region 4, Zone B, Edge Node 2.

> Region 4 is an internal simulation partition identifier. It is not an official administrative designation of the Simlipal Biosphere Reserve.

---

## 7. Scope Boundary

IGNIS V1 is a software simulation testbed. The following table defines what is validated in this version and what remains for future hardware integration:

| Aspect | In Scope (V1 Simulation) | Out of Scope (V2 Hardware) |
| :--- | :--- | :--- |
| Sensor readings | Synthetic generation with realistic ranges, noise profiles, and fault injection | Real sensor calibration, physical drift, environmental extremes |
| Edge-Fog communication | MQTT with artificial latency and packet loss injection | Real LoRa/sub-GHz RF propagation, antenna design |
| Fog decision logic | Fully implemented, tested, and benchmarked | -- (primary deliverable, carried forward) |
| Autonomous actions | Structured JSON log records | Real mist valve relays, drone MAVLink commands, acoustic actuators |
| Power systems | Not modeled | Solar sizing, battery chemistry, energy harvesting |
| Fog-Cloud links | MQTT with simulated WAN outages | Real 4G/VSAT connectivity behavior |
| Governance and logging | Immutable action-log format | Legal/regulatory sign-off, DGCA drone compliance |
| Hardware durability | Not applicable | IP67 enclosures, operating temperature range, tamper detection |

The simulation is a deliberate engineering stage, not a limitation. It enables rigorous validation of decision logic, latency, resilience, and safety guarantees at a fraction of the cost and risk of field hardware testing.

---

## 8. Version 2 Hardware Migration Path

The V1 software architecture is explicitly designed with a 1:1 conceptual mapping to physical field hardware. Migrating to V2 requires a data-source swap at the edge tier without redesigning core decision logic:

| V1 Software Component | V2 Physical Hardware Equivalent |
| :--- | :--- |
| `src/edge_sim.py` (sensor simulator) | ESP32-S3 / STM32 sensor hubs + LoRa SX1262 transceiver |
| Local Mosquitto Broker | LoRa gateway concentrator (SX1302 / Raspberry Pi CM4) |
| `src/fog_node_runner.py` (fog daemon) | NVIDIA Jetson Orin Nano / Raspberry Pi 5 fog server (solar powered) |
| Lateral MQTT topic | Direct sub-GHz RF mesh / Ubiquiti point-to-point Wi-Fi link |
| Action log JSON record | Relay actuators (high-pressure mist valves, drone launch triggers) |
| `src/cloud_ingestor/` | Regional forest division HQ gateway server |

### Key V2 Priorities

1. **Physical Sensor Integration:** Replace synthetic telemetry with hardware drivers for Sensirion SHT31 (temperature/humidity), Davis anemometers (wind), Figaro TGS2600 / Winsen MQ-135 (combustion gas), and Melexis MLX90614 (infrared thermal anomaly).
2. **Machine Learning Classifier:** Plug a lightweight Random Forest or TinyML neural classifier into the modular `FogNode.process_reading()` interface to complement rule-based scoring with historical forest fuel maps.
3. **Drone Reconnaissance API:** Implement MAVLink / ROS2 interfaces to dispatch autonomous reconnaissance drones toward GPS centroids on confirmed ORANGE state.
4. **GIS Map Interface:** Upgrade the dashboard NOC view with interactive Leaflet/Mapbox vector tile layers showing real-time topographical elevation, fire spread perimeters, and sensor node health.

---

## 9. Document Cross-References

| Document | Scope |
| :--- | :--- |
| [System Architecture](architecture.md) | Container topology, MQTT hierarchy, fog pipeline, state machine diagrams, data models, tech stack |
| [Mathematical Framework](mathematical_framework.md) | All scoring formulas, normalization functions, confirmation logic, parameter inventory |
| [Scenario Reference](scenario_reference.md) | S1-S7 scenario descriptions, sensor trajectories, validation targets |
| [Dashboard Guide](dashboard_guide.md) | 9-page UI reference, REST API documentation |
| [Repository Structure](repository_structure.md) | Complete codebase map |
| [Testing Plan](v1_consolidated_testing_plan.md) | Master test strategy and verification procedures |
| [UI Testing Protocol](ui_and_simulation_testing_plan.md) | Dashboard and live simulation testing |
