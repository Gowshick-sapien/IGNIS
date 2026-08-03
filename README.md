# IGNIS
### Intelligent Geo-distributed Network for Wildfire Intervention and Surveillance

> A distributed Edge–Fog–Cloud wildfire early warning and pre-suppression architecture designed to reduce response latency through localized autonomous intelligence.

---

## Overview

IGNIS is a research-oriented software simulation that explores how **Edge Computing**, **Fog Computing**, and **Cloud Computing** can work together to improve wildfire early warning systems.

Conventional wildfire monitoring primarily relies on satellite observations and centralized cloud processing. While effective for large-scale monitoring, this introduces latency before actionable decisions reach field responders.

IGNIS proposes a hierarchical architecture where **local Fog Nodes** perform real-time environmental analysis, execute safe autonomous pre-suppression actions, and coordinate with higher-level control centers.

This repository implements **IGNIS Version 1**:

- [PASS] Phase A – Core Decision Pipeline
- [PASS] Phase B – Distributed Containerized Architecture & MQTT
- [PASS] Phase C – Cloud Integration & InfluxDB Telemetry Persistence
- [PASS] Phase D – Multi-Zone & Peer-to-Peer Lateral Coordination
- [PASS] Phase E – Fault & Chaos Resilience Testing
- [PASS] Phase F – Scenario Library (S1–S7) & Metric Derivation Engine
- [PASS] Phase G – Unified Web Dashboard Framework, Repository Archive, Regression Detector & Reproducibility Exporter

> [Master Specification] For the complete detailed technical stack, architectural breakdown, scenario benchmarks, and full capabilities reference, see [docs/ignis_v1_capabilities_and_tech_stack.md](file:///d:/projects/IGNIS/docs/ignis_v1_capabilities_and_tech_stack.md).

---

# Current Architecture

```

                   ┌────────────────────────────┐
                   │      Control Center        │
                   │ FastAPI + SSE Dashboard    │
                   └─────────────┬──────────────┘
                                 │
                                 │ MQTT
                                 │
                    ┌────────────▼────────────┐
                    │     MQTT Broker         │
                    │  Eclipse Mosquitto      │
                    └────────────┬────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
     Edge Node E11         Edge Node E12         Edge Node E13
          │                      │                      │
          └──────────────┬───────┴──────────────┬──────┘
                         ▼
                  Fog Node (Zone 4B)
                         │
                         ▼
          Wildfire Decision Pipeline
```

---

## Zone & Region Naming Hierarchy (Region 4)

IGNIS V1 models a **single simulated forest region** assigned the internal identifier **Region 4**.

> **Explicit Clarification:** Region 4 is an internal simulation identifier and should not be interpreted as an official administrative designation of the Simlipal Biosphere Reserve or any real forest management jurisdiction.

```
Region (Simulated Area)
    ↓
Zone (Ecological Sector)
    ↓
Edge Node (Sensor Array)
```

- **Region 4**: Assigned study area.
- **Zone 4A** (Simlipal North), **Zone 4B** (Simlipal Core), **Zone 4C** (Simlipal South): Partitioned ecological sectors.
- **Edge Node (e.g., `4B-E2`)**: Region 4 $\rightarrow$ Zone B $\rightarrow$ Sensor Node 2.
- **MQTT Namespace**: `ignis/v1/telemetry/zone/4B/edge/4B-E1` represents Region 4, Zone B, Edge Node 1.

---

# Project Objectives

- Develop a distributed wildfire early warning architecture.
- Validate localized Fog-level decision making.
- Reduce dependence on centralized cloud processing.
- Demonstrate asynchronous communication using MQTT.
- Build a scalable architecture that can later integrate:
  - multiple forest zones
  - cloud coordination
  - hardware sensors
  - drone systems
  - real-world deployments

---

# Project Phases

| Phase | Status | Description |
|---------|:------:|------------|
| Phase A | [PASS] | Core wildfire decision pipeline |
| Phase B | [PASS] | MQTT communication & Docker architecture |
| Phase C | [PASS] | Cloud integration layer |
| Phase D | [PASS] | Multi-zone & lateral coordination |
| Phase E | [PASS] | Fault & chaos resilience testing |
| Phase F | [PASS] | Scenario library & consolidated reporting |
| Phase G | [PASS] | Unified web dashboard framework, experiment repository, regression engine & reproducibility publishing |

---

# Phase A

Phase A validates the **local wildfire decision engine**.

No networking or distributed components are involved.

Pipeline:

```

Scenario
↓
Edge Node
↓
Fog Node
↓
Normalization
↓
Wildfire Hazard Index (WHI)
↓
Confirmation Logic
↓
State Machine
↓
Decision
↓
Console

```

---

## Phase A Components

### Scenario Provider

Generates synthetic environmental conditions.

Supported scenarios:

- S1 – Normal Day
- S2 – Slow-Building Risk
- S3 – Sudden Ignition
- S4 – Single Sensor Fault

---

### Edge Node

Represents a physical sensor cluster.

Responsibilities:

- package sensor readings
- attach metadata
- publish structured telemetry

---

### Fog Node

Acts as the local decision-making brain.

Responsibilities:

- normalize sensor values
- compute WHI
- evaluate confirmation logic
- determine wildfire state
- generate autonomous actions

---

### Decision Pipeline

```

Raw Sensors
↓
Normalization
↓
Wildfire Hazard Index (WHI)
↓
Confirmation Rule
↓
State Machine
↓
Decision Record

```

---

# Phase B

Phase B transforms the local pipeline into a distributed system.

Instead of Python function calls, components communicate through **MQTT**.

---

## Distributed Architecture

Every component runs inside its own Docker container.

```

docker-compose

│

├── mqtt-broker

├── edge-sim-e11

├── edge-sim-e12

├── edge-sim-e13

├── fog-node

└── control-center

```

---

## MQTT Topic Hierarchy

```

ignis/v1/

├── zone/{zone}/edge/{node}/reading

├── zone/{zone}/edge/{node}/control

├── zone/{zone}/fog/state

├── zone/{zone}/fog/alert

└── zone/{zone}/fog/action_log

```

---

## MQTT Message Flow

### Telemetry

```

Edge Node
↓

MQTT Broker
↓

Fog Node

```

---

### Zone State

```

Fog Node
↓

MQTT Broker
↓

Control Center

```

---

### Scenario Injection

```

Browser
↓

FastAPI
↓

Scenario Service
↓

MQTT Broker
↓

Edge Node

```

---

# Phase C

Phase C introduces the central cloud coordinator and data storage layers. Local zone events are split into Report A (high-priority alerts to the local NOC) and Report B (telemetry updates pushed to the central cloud broker for storage in InfluxDB and visualization via Grafana).

---

# Phase D

Phase D scales the topology to a multi-zone configuration (Zones 4A, 4B, 4C). Local fog nodes coordinate laterally on topic `region/lateral/{zone_id}` to broadcast active warnings and evaluate fire propagation speeds based on local wind bearing.

---

# Phase E

Phase E implements the fault injection infrastructure. A host-side Chaos Controller REST API disconnects fog nodes from the cloud network or stops containers dynamically to test local offline buffering continuity and clamp sensor failures to prevent false alarms.

---

# Phase F

Phase F establishes the experimental validation framework. All scenario trajectories are hardened as YAML configuration files, validated against schema checks, orchestrated by a single-command test harness, and analyzed using Matplotlib graphs and a 9-section report.

---

# Data Flow

The complete system executes the following pipeline:

```

Scenario Provider
↓

Telemetry Provider
↓

Edge Node
↓

MQTT Broker
↓

Fog Node

↓

Normalization

↓

Wildfire Hazard Index

↓

Confirmation Rule

↓

State Machine

↓

Zone Aggregator

↓

MQTT Broker

↓

Control Center

↓

Server Sent Events

↓

Web Dashboard

```

---

# Telemetry Providers

Each Edge Node can dynamically switch between telemetry providers.

### RandomWalkProvider

Simulates normal environmental drift.

Used during baseline monitoring.

---

### ScenarioProvider

Produces deterministic telemetry for predefined wildfire scenarios.

Used during demonstrations.

---

### FaultInjectionProvider

Produces faulty or corrupted sensor readings.

Used to validate false-positive protection.

---

# Wildfire Hazard Index (WHI)

Sensor readings are first normalized to a common scale.

```

Temperature

↓

0.87

Humidity

↓

0.92

Wind

↓

0.63

...

↓

Weighted Hazard Index

```

WHI represents the current wildfire hazard level.

---

# Confirmation Rule

A high WHI alone is not sufficient.

At least **three independent sensors** must exceed their confirmation thresholds before the system can escalate to:

- ORANGE
- RED

Otherwise the state is clamped to **YELLOW**.

This prevents isolated faulty sensors from generating false alarms.

---

# Zone Aggregation

Each Edge Node is evaluated independently.

```

E11 → GREEN

E12 → RED

E13 → GREEN

```

The Zone State becomes

```

RED

```

using maximum-state aggregation.

This prevents localized wildfire events from being diluted through averaging.

---

# Control Center

The Local Control Center is implemented using:

- FastAPI
- Server-Sent Events (SSE)
- MQTT Listener
- Scenario Service

Features include:

- Live telemetry
- Zone status
- Edge status
- Alert feed
- Action logs
- Scenario execution
- Fault injection

---

# Project Structure

```

IGNIS/
├── config/
│   ├── zone_config.json
│   └── mosquitto.conf
├── docs/
│   ├── phase-f/
│   │   ├── f1/
│   │   ├── f2/
│   │   ├── f3/
│   │   ├── f4/
│   │   ├── walkthrough.md
│   │   └── testing.md
│   └── architecture.md
├── scenarios/
│   ├── s1_normal.yaml
│   └── ...
├── src/
│   ├── scoring/
│   ├── control_center/
│   ├── scenarios/
│   │   └── yaml_validator.py
│   ├── edge_sim.py
│   ├── fog_node.py
│   ├── fog_node_runner.py
│   ├── run_experiment.py
│   └── ...
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── ...

```

---

# Running the Project

## Requirements

- Docker Desktop
- Docker Compose v2

No local Python installation is required.

---

## Build and Start

```bash
docker compose up --build
```

---

## Accessing the IGNIS Central Operations & Research Dashboard

The unified **IGNIS Cloud Dashboard** serves both real-time regional NOC operations and research experiment management across 9 dedicated web views:

* **Local Dev Server:** `http://localhost:8000` (when running `uvicorn src.cloud_dashboard.app:app --reload`)
* **Docker Environment:** `http://localhost:9000` (when running `docker compose up`)
* **Interactive OpenAPI / Swagger Docs:** `http://localhost:8000/docs`

### Dashboard Pages Summary

| Page Name | URL Route | Primary Role & Core Purpose |
| :--- | :--- | :--- |
| **Regional Operations NOC** | `/` | Real-time zone monitoring, InfluxDB health, lateral event timeline, MQTT advisory command overrides. |
| **Experiment Control Center** | `/experiments` | Interactive simulation execution control, parameter tuning, SSE progress streaming, live console log viewer. |
| **Historical Report Browser** | `/reports` | Discovers and renders generated HTML and Markdown research reports (sorted Newest First). |
| **Historical Repository** | `/repository` | Read-only multi-field search, verdict/scenario filters, sorting, pagination, and experiment metadata inspection drawer. |
| **Side-by-Side Comparison** | `/comparison` | Side-by-side metric diffs, verdict deltas, confidence interval overlap, and automated regression detection. |
| **Interactive Chart Gallery** | `/charts` | Visual gallery of performance distributions, decision latency curves, lateral timelines, and false positive rates. |
| **Real-Time Benchmarks** | `/metrics` | Executive KPI dashboard summarizing research validation targets (latency <150ms, propagation <5s, continuity 100%). |
| **Scenario Browser** | `/scenarios` | Read-only catalog of YAML scenario specifications (S1–S7) with assertions and raw spec viewer. |
| **Settings & Export Hub** | `/settings` | Platform configuration, export format exporter (MD, HTML, CSV, JSON, ZIP, PDF, DOCX), and reproducibility bundle builder. |

For detailed documentation on all pages, visual components, REST API endpoints, and architectural principles, see [docs/dashboard_guide.md](file:///d:/projects/IGNIS/docs/dashboard_guide.md).

---

## Running the Experiment Orchestrator

The orchestrator pipeline runs all validation checks, scenario trials, and generates the reports and charts:

```bash
python -m src.run_experiment --trials 10 --clean
```

---

# Running Tests

Execute:

```bash
python -m unittest discover tests
```

or inside Docker

```bash
docker compose run --rm fog-node python -m unittest discover tests
```

> [Master Testing Plan] For the complete consolidated test strategy, verification tables, benchmark scenarios (S1–S7), REST API testing, and step-by-step acceptance procedures, see [docs/v1_consolidated_testing_plan.md](file:///d:/projects/IGNIS/docs/v1_consolidated_testing_plan.md).

---

# Demonstration Scenarios

| Scenario | Description |
|----------|-------------|
| S1 | Normal Day |
| S2 | Slow-Building Risk |
| S3 | Sudden Ignition |
| S4 | Single Sensor Fault |

---

# Design Principles

The project follows strict separation of responsibilities.

| Component | Responsibility |
|-----------|----------------|
| Telemetry Provider | Generates environmental data |
| Edge Node | Sensor interface & telemetry publishing |
| MQTT Broker | Message routing |
| Fog Node | Local decision making |
| Zone Aggregator | Zone-level state computation |
| Control Center | Visualization |
| Scenario Service | Scenario orchestration |

Each component performs a single well-defined responsibility.

---

# Future Work

Upcoming phases will introduce:

- Cloud coordination
- Multi-zone communication
- Fog-to-Fog coordination
- Persistent databases
- Digital Twin
- Hardware sensor integration
- Real drone communication
- Cloud analytics
- Long-term wildfire intelligence

---

# Research Focus

This project investigates:

- Distributed Edge–Fog–Cloud Computing
- Wildfire Early Warning Systems
- IoT Sensor Networks
- MQTT-based Distributed Systems
- Cyber-Physical Systems
- Autonomous Decision Making
- Disaster Response Architectures

---

# License

This repository is intended for academic research, experimentation, and educational purposes.
