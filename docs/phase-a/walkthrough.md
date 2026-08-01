# IGNIS — Phase A: Core Decision Pipeline

> **IGNIS** (Intelligent Geo-distributed Network for Wildfire Intervention and Surveillance)

Phase A implements the **core wildfire decision pipeline** of the IGNIS architecture.

At this stage, the project validates the **fog-level decision-making logic** without introducing networking, Docker, MQTT, databases, or cloud infrastructure.

The objective is to prove that the proposed wildfire decision architecture correctly computes a **Wildfire Hazard Index (WHI)**, applies the **multi-sensor confirmation rule**, and produces the appropriate wildfire state (`GREEN`, `YELLOW`, `ORANGE`, `RED`).

---

# Project Goal

The complete IGNIS project proposes an **Edge–Fog–Cloud architecture** for autonomous wildfire early warning and pre-suppression.

Phase A focuses only on the **local pipeline**:

```

Scenario → Edge Node → Fog Node → Decision → Console

```

No distributed communication is implemented yet.

---

# Phase A Scope

Implemented:

- Synthetic wildfire scenarios
- Edge node simulation
- Wildfire Hazard Index (WHI)
- Sensor normalization
- Multi-sensor confirmation logic
- State machine
- Structured decision records
- Console presentation
- Unit tests

Not implemented yet:

- MQTT communication
- Docker containers
- Multiple fog nodes
- Cloud layer
- Databases
- Grafana dashboard
- Network failures
- Lateral fog coordination

---

# Project Structure

```

IGNIS/
│
├── config/
│   └── zone_config.json
│
├── src/
│   │
│   ├── scoring/
│   │   ├── normalization.py
│   │   ├── hazard_index.py
│   │   ├── confirmation.py
│   │   └── state_machine.py
│   │
│   ├── edge_node.py
│   ├── fog_node.py
│   ├── scenario.py
│   └── presenter.py
│
├── tests/
│   └── test_scoring.py
│
└── run_phase_a.py

```

---

# Architecture

```

                 Scenario Generator
                        │
                        ▼
                 Sensor Readings
                        │
                        ▼
                   Edge Node
                        │
                        ▼
                   Fog Node
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
  Normalization        WHI      Confirmation
         └──────────────┼──────────────┘
                        ▼
                 State Machine
                        ▼
                Decision Record
                        ▼
                   Presenter

```

---

# Data Flow

The entire Phase A pipeline is deterministic and synchronous.

## Step 1 — Load Configuration

`run_phase_a.py`

- loads `zone_config.json`
- initializes the `FogNode`
- loads sensor limits
- loads WHI weights
- loads confirmation thresholds
- loads state thresholds

---

## Step 2 — Generate Scenario

`ScenarioGenerator`

Produces synthetic environmental data representing one of the supported scenarios.

Example:

```python
{
    "temperature_c": 38,
    "humidity_pct": 19,
    "gas_ppm": 140,
    ...
}
```

---

## Step 3 — Edge Node

The `EdgeNode` simulates a physical sensor cluster.

Responsibilities:

- attaches node metadata
- timestamps the reading
- returns a structured sensor reading

Output:

```python
{
    "node_id": "E01",
    "zone_id": "4B",
    "timestamp": "...",
    "temperature_c": 38,
    ...
}
```

---

## Step 4 — Fog Node

The Fog Node coordinates the complete decision pipeline.

It does **not** implement the mathematics directly.

Instead it calls the scoring modules sequentially.

---

### 4.1 Normalization

Converts heterogeneous sensor values into a common range:

```
0.0 → No Risk
1.0 → Maximum Risk
```

Example:

```
Temperature

38°C

↓

0.84
```

---

### 4.2 Wildfire Hazard Index (WHI)

Computes a weighted hazard score using the normalized sensor values.

```
WHI = Σ(weight × normalized_sensor)
```

Output:

```
WHI = 0.81
```

---

### 4.3 Confirmation

Evaluates which independent sensors exceed their individual confirmation thresholds.

Example:

```
Temperature 

Humidity 

Gas 

Wind 

Thermal 

Confirmation Count = 4
```

---

### 4.4 State Machine

Determines the wildfire state using:

- Wildfire Hazard Index
- Confirmation Count

Rules:

```
WHI >= RED threshold
AND
Confirmation >= 3

↓

RED
```

If the confirmation count is below three:

```
RED

↓

YELLOW (clamped)
```

This prevents false positives caused by isolated faulty sensors.

---

### 4.5 Decision Record

The Fog Node produces a structured decision record.

Example:

```python
{
    "zone": "4B",
    "whi": 0.84,
    "confirmation_count": 4,
    "state": "ORANGE",
    "actions": [
        "activate_mist_perimeter",
        "notify_control_center"
    ]
}
```

---

## Step 5 — Presenter

The Presenter receives the decision record and renders a human-readable console output.

The Presenter contains **no decision logic**.

---

# Configuration

`config/zone_config.json`

Contains all configurable parameters:

- normalization ranges
- WHI weights
- sensor confirmation thresholds
- wildfire state thresholds

Different forest types can therefore be simulated without modifying the source code.

---

# Supported Scenarios

| Scenario | Description | Expected State |
|----------|-------------|----------------|
| S1 | Normal Day | GREEN |
| S2 | Slow-Building Risk | YELLOW |
| S3 | Sudden Ignition | RED |
| S4 | Single Sensor Fault | YELLOW (clamped) |

---

# Running Phase A

Clone the repository.

Install Python 3.11+.

Run:

```bash
python run_phase_a.py
```

The program executes every scenario sequentially and prints the resulting wildfire decisions.

---

# Running Tests

Execute:

```bash
python -m unittest discover tests
```

or

```bash
pytest
```

(if pytest is installed)

The tests verify:

- normalization
- WHI computation
- confirmation logic
- state transitions
- false-positive clamping

---

# Design Principles

Phase A intentionally separates responsibilities.

| Module | Responsibility |
|---------|---------------|
| Scenario | Environmental data generation |
| Edge Node | Sensor interface |
| Fog Node | Pipeline orchestration |
| Normalization | Sensor scaling |
| Hazard Index | WHI computation |
| Confirmation | Threshold validation |
| State Machine | Final decision |
| Presenter | Console visualization |

Each module performs **one responsibility only**.

---

# Current Limitations

Phase A intentionally excludes:

- MQTT
- Docker
- Cloud communication
- Databases
- Multi-zone simulation
- Lateral fog coordination
- Network failures
- Hardware integration

These features are introduced in subsequent phases.

---

# Next Phase

Phase B introduces the first distributed components:

- Docker containerization
- MQTT communication
- Multiple edge nodes
- Local message broker
- Event-driven architecture

The decision pipeline implemented in Phase A remains unchanged; only the communication mechanism evolves.

---

## License

This project is part of the IGNIS research and simulation framework for validating distributed Edge–Fog–Cloud wildfire intelligence architectures.
