# IGNIS
### Intelligent Geo-distributed Network for Wildfire Intervention and Surveillance

> A distributed Edge–Fog–Cloud wildfire early warning and pre-suppression architecture designed to reduce response latency through localized autonomous intelligence.

---

## Overview

IGNIS is a research-oriented software simulation that explores how **Edge Computing**, **Fog Computing**, and **Cloud Computing** can work together to improve wildfire early warning systems.

Conventional wildfire monitoring primarily relies on satellite observations and centralized cloud processing. While effective for large-scale monitoring, this introduces latency before actionable decisions reach field responders.

IGNIS proposes a hierarchical architecture where **local Fog Nodes** perform real-time environmental analysis, execute safe autonomous pre-suppression actions, and coordinate with higher-level control centers.

This repository currently implements:

- [PASS] Phase A – Core Decision Pipeline
- [PASS] Phase B – Distributed Containerized Architecture

---

# Current Architecture

```

                   
                         Control Center        
                    FastAPI + SSE Dashboard    
                   
                                 
                                  MQTT
                                 
                    
                         MQTT Broker         
                      Eclipse Mosquitto      
                    
                                 
          
                                                      
                                                      
     Edge Node E11         Edge Node E12         Edge Node E13
                                                      
          
                         
                  Fog Node (Zone 4B)
                         
                         
          Wildfire Decision Pipeline
```

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
| Phase C | [PENDING] | Cloud integration |
| Phase D | [PENDING] | Multi-zone coordination |
| Phase E | [PENDING] | Hardware integration |

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



 mqtt-broker

 edge-sim-e11

 edge-sim-e12

 edge-sim-e13

 fog-node

 control-center

```

---

## MQTT Topic Hierarchy

```

ignis/v1/

 zone/{zone}/edge/{node}/reading

 zone/{zone}/edge/{node}/control

 zone/{zone}/fog/state

 zone/{zone}/fog/alert

 zone/{zone}/fog/action_log

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

 config/

  zone_config.json

  mosquitto.conf



 src/

  scoring/

  control_center/

  edge_sim.py

  fog_node.py

  fog_node_runner.py

  scenario.py

  presenter.py



 tests/



 Dockerfile

 docker-compose.yml

 requirements.txt

 run_phase_a.py

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

## Open Dashboard

```
http://localhost:8000
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
