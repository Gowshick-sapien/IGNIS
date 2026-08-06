# IGNIS — Simulation Architecture

**Edge-Fog-Cloud (EFC) Software Simulation — Detailed Architecture Document (v1)**
**Parent concept:** Autonomous Wildfire Early Warning and Pre-Suppression Using Edge-Fog-Cloud Architecture in Indian Forest Ecosystems

---

## 1. Purpose

This document translates the Simulation Ideation (v1) into a concrete, buildable software architecture. It is a **decision-architecture validation testbed** — every physical component (sensors, LoRa radios, solar fog servers, actuators) is replaced with a containerized software surrogate that reproduces the same data flow, decision logic, and failure modes. Nothing here drives real hardware; the goal is to produce measurable evidence for the risk-scoring, state-machine, lateral-coordination, and offline-resilience claims of the parent design before any capital is spent.

---

## 2. System Context

```mermaid
flowchart TB
    subgraph Physical["Reference: Physical System (Parent Paper — NOT built here)"]
        direction LR
        PS[Weatherproof Sensors + LoRa]
        PF[Jetson Orin NX Fog Server]
        PC[MeghRaj Cloud]
        PA[Actuators: mist / drone / acoustic]
    end

    subgraph Sim["This Project: Pure-Software Simulation"]
        direction LR
        ES[edge-sim containers]
        FN[fog-node containers]
        CB[cloud-broker + timeseries-db + dashboard]
        AL[Logged action records — no real actuation]
    end

    Physical -. "1:1 conceptual mapping, see Section 11" .-> Sim
    Sim -. "validated interface contracts feed" .-> Physical
```

---

## 3. Three-Tier Container Architecture

```mermaid
flowchart TB
    subgraph EdgeTier["EDGE TIER — per zone, N nodes"]
        E1[edge-sim: node E1]
        E2[edge-sim: node E2]
        E3[edge-sim: node E_n]
    end

    subgraph EdgeFogLink["EDGE↔FOG LINK — LoRa surrogate"]
        MB[mqtt-broker-local<br/>Eclipse Mosquitto, 1 per zone]
        IMP[[optional impairment sidecar<br/>tc netem: latency / jitter / loss]]
    end

    subgraph FogTier["FOG TIER — 1 fog-node per zone"]
        FN1[fog-node: Zone 4A]
        FN2[fog-node: Zone 4B]
        FN3[fog-node: Zone 4C]
    end

    subgraph LateralLink["FOG↔FOG LATERAL CHANNEL"]
        LT[region/lateral/#123;zone_id#125;<br/>shared MQTT topic namespace]
    end

    subgraph CloudLink["FOG↔CLOUD LINK — interruptible on demand"]
        CBK[cloud-broker<br/>Mosquitto / Kafka]
    end

    subgraph CloudTier["CLOUD TIER"]
        TSDB[(timeseries-db<br/>TimescaleDB / InfluxDB)]
        DASH[dashboard<br/>Grafana]
        CTRL[Control Center View<br/>Report A feed]
    end

    subgraph Harness["TEST & FAULT HARNESS"]
        SI[scenario-injector]
        CC[chaos-controller]
    end

    E1 & E2 & E3 -->|"publish: zone/{z}/edge/{n}/reading"| MB
    MB -.-> IMP
    MB -->|subscribe| FN1
    MB -->|subscribe| FN2
    MB -->|subscribe| FN3

    FN1 <-->|"publish/subscribe risk state + wind vector"| LT
    FN2 <-->|"publish/subscribe risk state + wind vector"| LT
    FN3 <-->|"publish/subscribe risk state + wind vector"| LT

    FN1 -->|"Report A: zone/{z}/fog/alert"| CTRL
    FN1 -->|"Report B: cloud/{z}/report"| CBK
    FN2 -->|"Report A + B"| CBK
    FN3 -->|"Report A + B"| CBK
    CBK -->|"command: cloud/{z}/command"| FN1
    CBK -->|"command: cloud/{z}/command"| FN2
    CBK -->|"command: cloud/{z}/command"| FN3

    CBK --> TSDB --> DASH
    DASH --> CTRL

    SI -.->|drives trajectories| E1 & E2 & E3
    CC -.->|"docker network disconnect / iptables"| CBK
    CC -.->|sensor fault injection| E1 & E2 & E3
```

---

### 3.1. Simulated Forest Region & Zone Naming Hierarchy (Region 4)

IGNIS V1 models a **single simulated forest region** assigned the internal identifier **Region 4**.

> [!IMPORTANT]
> **Explicit Clarification:** Region 4 is an internal simulation identifier and should not be interpreted as an official administrative designation of the Simlipal Biosphere Reserve or any real forest management jurisdiction.

#### Spatial Partitioning & Naming Hierarchy

```
Region (Simulated Study Area)
   Zone (Ecological Sector)
         Edge Node (Microclimate Sensor Array)
```

The simulated study region is partitioned into three neighboring ecological zones:

| Zone | Description | Spatial / Ecological Profile |
| :--- | :--- | :--- |
| **`4A`** | **Northern Zone** | Simlipal North — Peer fog node for lateral warning propagation. |
| **`4B`** | **Core Zone** | Simlipal Core — Primary high-risk biosphere sector under active test scenarios (S1–S5). |
| **`4C`** | **Southern Zone** | Simlipal South — Peer fog node for multi-zone cross-talk isolation testing (S7). |

```
Region 4
 Zone 4A (Northern Zone)
       Edge E1 (4A-E1)
       Edge E2 (4A-E2)
       Edge E3 (4A-E3)
 Zone 4B (Core Zone)
       Edge E1 (4B-E1)
       Edge E2 (4B-E2)
       Edge E3 (4B-E3)
 Zone 4C (Southern Zone)
        Edge E1 (4C-E1)
        Edge E2 (4C-E2)
        Edge E3 (4C-E3)
```

An identifier such as **`4B-E2`** resolves hierarchically to:
- **Region 4**: Simulated study region
- **Zone B**: Core ecological zone
- **Edge Node 2**: Sensor node instance #2

#### MQTT Topic Namespace Mapping
The structural hierarchy is reflected directly in the versioned MQTT namespace:
- `ignis/v1/telemetry/zone/4B/edge/4B-E1` $\rightarrow$ Telemetry from Edge Node 1, Zone B, Region 4.
- `ignis/v1/fog/zone/4B/state` $\rightarrow$ Decision state for Fog Node responsible for Zone 4B in Region 4.

#### Rationale & Scalability
- The numeric prefix (**`4`**) groups related zones belonging to the same simulated forest region.
- The alphabetic suffix (**`A`**, **`B`**, **`C`**) distinguishes neighboring ecological zones within that region.
- This design scales naturally if additional simulated regions are added in future versions (e.g., Region 1: `1A,1B,1C`; Region 2: `2A,2B,2C`; Region 3: `3A,3B,3C`; Region 4: `4A,4B,4C`).

---

## 4. Container Inventory

| Container | Image Basis | Role | Scale |
|---|---|---|---|
| `edge-sim` | `python:slim` | Synthetic sensor generator | N per zone (5–10) |
| `mqtt-broker-local` | `eclipse-mosquitto` | Edge↔fog bus (LoRa surrogate) | 1 per zone |
| `fog-node` | `python:slim` / `node:slim` | Risk scoring, state machine, lateral coordination | 1 per zone |
| `cloud-broker` | `eclipse-mosquitto` or `bitnami/kafka` | Fog↔cloud bus | 1 shared |
| `timeseries-db` | `timescale/timescaledb` or `influxdb` | Historical + live store | 1 shared |
| `dashboard` | `grafana/grafana` | Visualization | 1 shared |
| `scenario-injector` | `python:slim` | Drives test scenarios | on demand |
| `chaos-controller` | `python:slim` + `iproute2` | Network/sensor fault injection | on demand |

All orchestrated via a single `docker-compose.yml`; per-zone services parameterized through Compose's `deploy`/environment-variable pattern so adding a zone is a config change, not a code change.

---

## 5. Fog-Node Internal Pipeline

The fog node is the core logic under test. Its six-step pipeline:

```mermaid
flowchart LR
    A["Step 1: Ingestion<br/>subscribe to zone edge topics,<br/>rolling 30-min buffer per sensor"] --> B["Step 2: Composite Risk Scoring<br/>weighted rule-based function<br/>w1..w8, config per zone"]
    B --> C["Step 3: State Classification<br/>GREEN/YELLOW/ORANGE/RED<br/>+ 3-sensor confirmation rule"]
    C --> D{"State ≥ ORANGE?"}
    D -->|yes| E["Step 4: Simulated Autonomous Action<br/>immutable JSON action log<br/>(no real actuator)"]
    D -->|no| F["Step 5: Dual Reporting"]
    E --> F
    F --> G["Report A → local control-center feed"]
    F --> H["Report B → cloud (raw + score + decisions)"]
    F --> I["Step 6: Cloud Command Handling<br/>adjust local thresholds<br/>OR persist last-known config if offline"]
```

**Composite risk score:**
```
risk_score = w1·f(temperature) + w2·f(humidity) + w3·f(wind_speed)
           + w4·f(soil_moisture) + w5·f(gas_level) + w6·f(thermal_anomaly)
           + w7·f(time_of_day) + w8·f(seasonal_baseline)
```
Weights and normalization functions are configurable per zone (YAML/JSON), enabling dry-deciduous vs. moist-Himalayan profiles without code changes. Phase 1 is fully rule-based/auditable; a stub interface allows a later ML classifier swap without touching the surrounding architecture.

---

## 6. State Machine (per Fog Node)

```mermaid
stateDiagram-v2
    [*] --> GREEN
    GREEN --> YELLOW: risk_score crosses threshold\nOR lateral pre-emptive signal
    YELLOW --> ORANGE: risk_score crosses threshold\nAND ≥3 independent sensors confirm
    ORANGE --> RED: risk_score crosses threshold\nAND ≥3 independent sensors confirm
    RED --> ORANGE: sustained readings drop
    ORANGE --> YELLOW: sustained readings drop
    YELLOW --> GREEN: sustained readings drop
    ORANGE --> ORANGE: log action_log record\n(activate_mist_perimeter, notify_control_center)
    RED --> RED: log action_log record

    note right of ORANGE
        Multi-sensor confirmation rule (Sec 8.4)
        is enforced BEFORE entering ORANGE/RED —
        primary false-positive control, tested
        as first-class logic (not just a score gate)
    end note
```

---

## 7. Lateral Fog-to-Fog Coordination (Sequence)

The most novel, and highest-priority-to-validate, logic path:

```mermaid
sequenceDiagram
    participant SensorsB as Zone 4B Sensors
    participant FogB as fog-node (Zone 4B)
    participant Lateral as region/lateral/{zone_id}
    participant FogC as fog-node (Zone 4C, downwind)
    participant Cloud as cloud-broker

    SensorsB->>FogB: readings (temp↑, humidity↓, gas↑)
    FogB->>FogB: risk_score crosses YELLOW+
    FogB->>Lateral: publish {zone: 4B, state: YELLOW, wind_vector: 220°}
    Lateral->>FogC: broadcast received
    FogC->>FogC: check adjacency + bearing:\ndoes 220° point at Zone 4C?
    alt wind points toward 4C
        FogC->>FogC: raise own state one step\n(GREEN → YELLOW) pre-emptively
        FogC->>Cloud: Report B (state change, reason: lateral)
    else wind does not point toward 4C
        FogC->>FogC: no change
    end
    FogB->>Cloud: Report A + Report B (own state change)
```

---

## 8. Offline-Resilience Behavior

```mermaid
sequenceDiagram
    participant Fog as fog-node
    participant Cloud as cloud-broker
    participant Chaos as chaos-controller

    Fog->>Cloud: heartbeat + reports (normal operation)
    Chaos->>Cloud: docker network disconnect (simulate link loss)
    Note over Fog: cloud_connected = false
    Fog->>Fog: continue ingestion, scoring,\nstate transitions, action logging\n(last-known config retained)
    Fog->>Fog: queue unsent reports locally
    Chaos->>Cloud: restore link
    Fog->>Cloud: flush queued Report B packets
    Cloud-->>Fog: any pending command (e.g. sensitivity adjustment)
```

---

## 9. Data Model

**Edge reading**
```json
{
  "node_id": "E12", "zone_id": "4B", "timestamp": "...",
  "temperature_c": 34.2, "humidity_pct": 21.5,
  "wind_speed_kmh": 14.0, "wind_dir_deg": 220,
  "soil_moisture_pct": 9.1, "gas_ppm": 12,
  "thermal_anomaly_c": 2.1, "light_lux": 41000,
  "rain_mm": 0.0, "gps": [21.94, 86.32]
}
```

**Fog decision record**
```json
{
  "zone_id": "4B", "timestamp": "...",
  "risk_score": 0.78, "state": "ORANGE",
  "confirming_sensors": ["gas_ppm", "thermal_anomaly_c", "soil_moisture_pct"],
  "actions_logged": ["activate_mist_perimeter", "notify_control_center"],
  "cloud_connected": false
}
```

---

## 10. Topic / Message Naming Convention

| Topic | Purpose |
|---|---|
| `zone/{zone_id}/edge/{node_id}/reading` | edge sensor readings |
| `zone/{zone_id}/fog/state` | fog risk state heartbeat |
| `zone/{zone_id}/fog/alert` | control-center alert (Report A) |
| `zone/{zone_id}/fog/action_log` | simulated autonomous action record |
| `region/lateral/{zone_id}` | lateral coordination broadcast |
| `cloud/{zone_id}/report` | full data packet to cloud (Report B) |
| `cloud/{zone_id}/command` | advisory command from cloud to fog |

---

## 11. Test Scenario Matrix

| ID | Scenario | Exercises | Expected Result |
|---|---|---|---|
| S1 | Normal day | Baseline operation | State stays GREEN; periodic telemetry only |
| S2 | Slow-building risk | Gradual multi-parameter drift | GREEN→YELLOW transition; sampling rate increases |
| S3 | Sudden ignition | Rapid multi-sensor spike | ORANGE/RED within seconds; action log populated |
| S4 | Single sensor fault | Fault-mode edge node | No escalation from one faulty sensor (validates 3-sensor rule) |
| S5 | Cloud outage during event | Chaos-controller cuts fog↔cloud mid-scenario | Fog continues locally; reports flush on reconnect |
| S6 | Lateral spread prediction | S3 + wind vector toward neighbor | Neighbor pre-emptively raises state before its own sensors trigger |
| S7 | Concurrent multi-zone escalation | S3 in 2+ zones simultaneously | No dropped messages, no cross-talk, dashboard reflects both |

---

## 12. Validation Metrics

| Metric | Measurement | Validates |
|---|---|---|
| Fog decision latency | last confirming reading → state-change timestamp delta | Section 7.1 latency claim (fog-level) |
| Lateral alert propagation time | source escalation → neighbor pre-emptive change | Section 6.3 predictive capability |
| False-positive rate under fault injection | unwarranted ORANGE/RED count across S4 trials | Section 8.4 multi-sensor design |
| Offline continuity | uninterrupted decisioning/logging during S5 | Sections 2.3, 8.2 offline resilience |
| Concurrent-zone integrity | message loss / cross-talk count during S7 | Message-bus scalability |

---

## 13. Development Phases

```mermaid
flowchart LR
    A["Phase A<br/>Core pipeline:<br/>single edge → single fog,<br/>direct calls, no MQTT"] --> B["Phase B<br/>Containerize + MQTT,<br/>multi-node per zone,<br/>control-center feed"]
    B --> C["Phase C<br/>Cloud layer:<br/>broker + TSDB + dashboard,<br/>dual reporting + commands"]
    C --> D["Phase D<br/>Multi-zone + lateral:<br/>3+ zones, adjacency/bearing<br/>config, S6 logic"]
    D --> E["Phase E<br/>Fault/chaos testing:<br/>S4, S5, S7, metric collection"]
    E --> F["Phase F<br/>Scenario validation & reporting:<br/>hardened YAML schemas,<br/>automated orchestrator,<br/>statistical reports + charts"]
```

Phase F serves as the **experimental validation and reporting layer**. By formalizing test cases as versioned, tamper-evident YAML configurations, the orchestrator computes 95% Student-t confidence intervals across multi-trial sweeps and asserts exact pass/fail metrics. The output report maps these statistical aggregates directly to architecture validation claims, confirming the real-time latencies and resilient continuity targets.

---

## 14. Technology Stack

- **Languages:** Python (edge sims, fog logic, scenario/chaos scripts); optional Node.js for fog service
- **Messaging:** Eclipse Mosquitto (MQTT); optional Kafka for higher-throughput cloud ingestion
- **Storage:** TimescaleDB or InfluxDB
- **Visualization:** Grafana; static page fallback for control-center view
- **Orchestration:** Docker Compose (no Kubernetes needed at this scale)
- **Fault injection:** `tc netem`, `iptables`/`docker network disconnect`, scripted via Python
- **Testing:** Versioned YAML scenarios + a test runner asserting on Section 12 metrics

---

## 15. Explicit Scope Boundary

| Aspect | In scope | Out of scope (hardware phase) |
|---|---|---|
| Sensor readings | Synthetic generation, realistic ranges + faults | Real calibration, drift, physical fault behavior |
| Edge↔fog comms | MQTT + optional artificial latency/loss | Real LoRa RF propagation, antenna design |
| Fog decision logic | Fully implemented and tested | — (main deliverable) |
| Autonomous actions | Logged structured records only | Real mist/drone/acoustic actuation |
| Power system | Not modeled | Solar sizing, battery chemistry |
| Fog↔fog / fog↔cloud links | MQTT + simulated outages | Real 4G/VSAT/sub-GHz RF behavior |
| Governance/logging | Immutable action-log format | Legal/regulatory sign-off, DGCA compliance |
| Hardware durability | N/A | IP67 enclosures, temperature range, tamper detection |
| Institutional integration | N/A | RFO workflows, FSI/NRSC data-sharing agreements |

---

## 16. Path Back to Hardware

Once metrics in Section 12 are stable against Section 7 targets, the natural next step (outside this project) is the Phase 1 field pilot: 5–10 real edge nodes + 1 real fog node in a single forest division, advisory-only mode, reusing the simulation's message schemas and risk-scoring config as-is — a data-source swap, not a redesign.

---

## 17. Known Limitations

- Cannot validate RF propagation, power sizing, or hardware durability — field testing is still required regardless of simulation quality.
- Synthetic sensor data won't capture the full statistical texture of real forest conditions; the measured false-positive rate is a **lower bound**, not a real-world prediction.
- "Autonomous action" outputs are logged intentions only — real actuator control is unverified until hardware integration.
- Human-factors questions (would an RFO trust and act on this alert format) cannot be tested in simulation.
