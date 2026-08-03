# IGNIS — Repository Structure

> **I**ntelligent **G**eo-distributed **N**etwork for **I**gnition **S**urveillance  
> A fog-computing wildfire detection simulation platform.

This document provides a complete map of the repository, organized by
functional area. Every directory and file is listed with its primary role so
that any newcomer can orient themselves quickly.

---

## Root Directory

```
IGNIS/
│
├── .env                        # Runtime environment variables (MQTT hosts, ports, etc.)
├── .env.example                # Template showing required env-var keys
├── .gitignore                  # Git-ignored paths (caches, results, .env, etc.)
├── Dockerfile                  # Container image for Edge / Fog / worker services
├── docker-compose.yml          # Multi-service orchestration (brokers, edges, fogs, cloud)
├── requirements.txt            # Python dependency manifest (paho-mqtt, Flask, matplotlib, …)
├── README.md                   # Project overview, setup guide, and quick-start instructions
├── run_phase_a.py              # CLI entry-point — runs Phase-A local (non-Docker) simulation
│
├── config/                     # Centralised configuration files
├── src/                        # All production source code
├── scenarios/                  # YAML scenario definition files
├── tests/                      # Automated test suite
├── docs/                       # Project documentation (you are here)
├── experiment_repository/      # Persistent experiment run archive
├── results/                    # Latest / active experiment output
├── reports/                    # Generated report assets & exports
├── historical/                 # Historical seasonal baseline datasets
├── dummy_charts_dir/           # Placeholder directory for chart generation tests
│
│  ── Reference / Planning Files (root-level) ──
├── Simulation_Ideation_v1.pdf                              # Early-stage simulation design notes
├── hardware_ideation_v1.pdf                                # Hardware / IoT ideation document
├── project title .pdf                                      # Project title & abstract sheet
├── IGNIS TESTING AND VERIFICATION DOCUMENTATION.docx       # Full testing & verification report
├── Final_Testing_Experiment_Scenario_Failure_Report.md     # Post-experiment failure analysis
└── emojis_found.txt                                        # Audit log of emoji usage across codebase
```

---

## `config/` — Centralised Configuration

```
config/
├── zones_config.json           # Zone definitions: sensor weights, limits, state thresholds,
│                               #   lateral-warning timeouts, and per-zone overrides (Z-WEST, Z-EAST)
├── regression_rules.yaml       # Rules engine config for cross-run regression detection
├── mosquitto.conf              # Mosquitto MQTT broker config — local (edge/fog) broker
└── mosquitto_cloud.conf        # Mosquitto MQTT broker config — cloud-tier broker
```

---

## `src/` — Production Source Code

### Top-Level Modules

```
src/
├── edge_node.py                # EdgeNode class — packages raw sensor data into the
│                               #   standardised IGNIS telemetry schema
├── edge_sim.py                 # Edge Simulator — generates synthetic sensor readings via
│                               #   pluggable TelemetryProviders (RandomWalk, ScenarioDriven)
│                               #   and publishes them over MQTT
├── fog_node.py                 # FogNode class — the "local brain" for a forest zone;
│                               #   orchestrates the modular wildfire risk decision pipeline
│                               #   (normalise → WHI → confirmation → state evaluation)
├── fog_node_runner.py          # Fog Node Runner daemon — bridges local + cloud MQTT brokers,
│                               #   manages state escalation, lateral warnings, and buffered
│                               #   cloud publishing
├── buffered_publisher.py       # BufferedPublisher — resilient MQTT publisher with offline
│                               #   buffering and automatic flush-on-reconnect
├── clock.py                    # Clock / MockClock — injectable time abstraction for
│                               #   deterministic testing
├── events.py                   # Structured event dataclasses: DecisionEvent, AlertEvent,
│                               #   ActionEvent, CloudReportEvent, ScenarioEvent
├── scenario.py                 # ScenarioGenerator — programmatic builder for predefined
│                               #   sensor-data sequences (S1–S7)
├── presenter.py                # ConsolePresenter — styled ANSI terminal output for decision
│                               #   traces and scenario headers
├── metrics_collector.py        # Post-run metrics computation: response latency, detection
│                               #   accuracy, state-transition correctness, confidence intervals
├── report_generator.py         # Matplotlib chart generation + Markdown/HTML report assembly
│                               #   from raw experiment results
└── run_experiment.py           # Experiment Orchestrator — end-to-end CLI that validates YAML,
                                #   runs scenarios, collects metrics, generates reports, and
                                #   archives results
```

---

### `src/scoring/` — Wildfire Hazard Scoring Pipeline

The modular scoring engine used by FogNode to evaluate fire risk.

```
src/scoring/
├── __init__.py                 # Public API exports: normalize_reading, calculate_whi,
│                               #   evaluate_confirmations, evaluate_state
├── normalization.py            # Sensor value normalisation (min-max scaling) and
│                               #   time-of-day risk factor derivation
├── hazard_index.py             # Weighted Hazard Index (WHI) calculation from normalised
│                               #   sensor dimensions
├── confirmation.py             # Multi-sensor confirmation logic — counts how many sensors
│                               #   exceed their individual thresholds
└── state_machine.py            # State evaluation — maps WHI + confirmation count to a
                                #   risk state (GREEN → YELLOW → ORANGE → RED)
```

---

### `src/scenarios/` — Scenario Framework

The YAML-driven scenario execution framework.

```
src/scenarios/
├── __init__.py                 # Package exports (BaseScenario, ScenarioRunner, registry)
├── yaml_validator.py           # Schema validation for scenario YAML files — enforces
│                               #   required fields, value ranges, and structural rules
├── base_scenario.py            # Abstract base class defining the scenario lifecycle:
│                               #   setup → inject → tick → verify → teardown
├── scenario_runner.py          # ScenarioRunner — loads validated YAML, instantiates
│                               #   edge/fog nodes, executes steps, records events & results
├── scenario_registry.py        # Dynamic scenario class registry (maps scenario IDs to
│                               #   their Python implementations)
├── results.py                  # Result dataclass for per-scenario pass/fail outcomes
├── scenario_s1_s2_s3.py        # Implementations for S1 (Normal Day), S2 (Slow Risk Build),
│                               #   S3 (Sudden Ignition)
├── scenario_s4.py              # S4: Sensor Fault — partial sensor failure handling
├── scenario_s5.py              # S5: Cloud Outage — fog resilience under cloud disconnect
├── scenario_s6.py              # S6: Lateral Spread — cross-zone fire propagation
└── scenario_s7.py              # S7: Multi-Zone Coordination — simultaneous multi-zone event
```

---

### `src/chaos_controller/` — Chaos Engineering Service

Flask micro-service that injects controlled faults during experiments.

```
src/chaos_controller/
├── __init__.py                 # Package marker
├── app.py                      # Flask application factory
├── routes.py                   # REST API endpoints: inject faults (network, broker, sensor)
└── docker_adapter.py           # Docker SDK adapter — pauses/unpauses/kills containers to
                                #   simulate infrastructure failures
```

---

### `src/cloud_ingestor/` — Cloud Data Ingestion Service

Consumes fog-published MQTT data at the cloud tier and persists it.

```
src/cloud_ingestor/
├── main.py                     # Entry-point — connects to cloud MQTT broker and starts
│                               #   ingestion loop
├── mqtt_service.py             # MQTT subscription handler — parses incoming telemetry,
│                               #   decision events, and alerts; writes to database
└── database.py                 # SQLite persistence layer for ingested cloud-tier data
```

---

### `src/control_center/` — Operator Control Panel

Flask web UI for live scenario management and monitoring.

```
src/control_center/
├── __init__.py                 # Package marker
├── app.py                      # Flask application factory
├── routes.py                   # Web routes: scenario listing, launch, status
├── mqtt_listener.py            # Background MQTT listener for real-time decision events
├── scenario_service.py         # Business logic: scenario CRUD, lifecycle management
└── templates/
    └── index.html              # Single-page operator dashboard (HTML + embedded JS)
```

---

### `src/cloud_dashboard/` — Cloud Analytics Dashboard

Full-featured Flask web application for experiment management, reporting,
comparison, and data export.

```
src/cloud_dashboard/
├── app.py                      # Flask application factory, blueprint registration, SSE setup
├── database.py                 # SQLite database layer: experiment metadata, run results,
│                               #   metrics storage, comparison snapshots
├── schemas.py                  # Marshmallow/dataclass schemas for API request/response
│                               #   validation and serialisation
│
├── routes/                     # ── HTTP Route Blueprints ──
│   ├── __init__.py             # Blueprint aggregation & registration helper
│   ├── dashboard_routes.py     # Main dashboard views: homepage, metrics, charts, settings
│   ├── experiments.py          # Experiment CRUD API: create, run, list, detail, delete
│   ├── comparison.py           # Cross-experiment comparison endpoints
│   ├── export_routes.py        # Data export endpoints (JSON, CSV, PDF bundles)
│   └── repository.py           # Experiment repository browsing & management
│
├── services/                   # ── Business Logic Services ──
│   ├── process_manager.py      # Subprocess lifecycle manager — spawns & monitors experiment
│   │                           #   worker processes
│   ├── result_manager.py       # Result file I/O — loads and caches run outputs
│   ├── repository_manager.py   # Repository CRUD — manages the experiment archive
│   ├── repository_migrations.py# Schema migrations for the repository database
│   ├── bundle_service.py       # Bundles experiment artifacts into downloadable archives
│   ├── comparison_service.py   # Cross-run diff & comparison analytics engine
│   ├── export_service.py       # Multi-format export pipeline (CSV, JSON, HTML, PDF)
│   ├── report_service.py       # Report rendering orchestration
│   ├── live_monitor.py         # SSE (Server-Sent Events) stream for real-time experiment
│   │                           #   progress updates
│   ├── progress_reporter.py    # Progress tracking: step counts, ETA estimation, event log
│   └── regression_detector.py  # Automated regression detection across experiment runs
│
├── reporting/                  # ── Report Generation Engine ──
│   ├── __init__.py             # Package exports
│   ├── chart_engine.py         # Matplotlib chart builders: timelines, heatmaps, bar charts,
│   │                           #   radar plots for experiment visualisation
│   ├── html_generator.py       # Self-contained HTML report generator (inline CSS + charts)
│   └── templates.py            # Jinja2 HTML template strings for report sections
│
└── templates/                  # ── Jinja2 Web Templates ──
    ├── base.html               # Base layout: nav, footer, CSS/JS imports
    ├── index.html              # Dashboard homepage — system overview & quick actions
    ├── experiments.html         # Experiment listing and launch interface
    ├── metrics.html            # Detailed metrics display with charts
    ├── charts.html             # Full-page chart viewer
    ├── comparison.html         # Side-by-side experiment comparison view
    ├── repository.html         # Experiment repository browser
    ├── reports.html            # Generated reports listing and viewer
    ├── scenarios.html          # Scenario catalogue and details
    ├── settings.html           # Dashboard configuration panel
    └── partials/
        └── navbar.html         # Reusable navigation bar partial
```

---

## `scenarios/` — Scenario Definition Files (YAML)

Each file defines a complete experiment scenario: metadata, zone config,
sensor data sequences, expected state transitions, and pass/fail criteria.

```
scenarios/
├── s1_normal.yaml              # S1: Normal Day — all readings within safe bounds; GREEN throughout
├── s2_slow_risk.yaml           # S2: Slow Risk Build-up — gradual escalation to YELLOW/ORANGE
├── s3_sudden_ignition.yaml     # S3: Sudden Ignition — rapid spike triggering RED alert
├── s4_sensor_fault.yaml        # S4: Sensor Fault — one or more sensors report anomalous data
├── s5_cloud_outage.yaml        # S5: Cloud Outage — fog must operate autonomously, buffer data
├── s6_lateral_spread.yaml      # S6: Lateral Spread — fire propagates across zone boundaries
└── s7_multi_zone.yaml          # S7: Multi-Zone Coordination — concurrent events in multiple zones
```

---

## `tests/` — Automated Test Suite

Comprehensive pytest test suite covering every layer of the system.

```
tests/
│
│  ── Core Logic ──
├── test_scoring.py                 # Scoring pipeline: normalisation, WHI, confirmations, state machine
├── test_aggregation.py             # Metric aggregation and statistical computation
├── test_metric_derivation.py       # Derived metric calculations (confidence intervals, trends)
├── test_run_experiment.py          # End-to-end experiment orchestration flow
├── test_yaml_validator.py          # YAML scenario schema validation rules
│
│  ── Resilience & Chaos ──
├── test_chaos_resilience.py        # Chaos fault-injection and system recovery verification
├── test_cloud_resilience.py        # Cloud-outage buffering and reconnection behaviour
├── test_lateral_coordination.py    # Cross-zone lateral warning propagation
│
│  ── Metrics & Reporting ──
├── test_metrics_collector.py       # Metrics collector computation correctness
├── test_report_consistency.py      # Report output determinism and cross-format consistency
├── test_report_pipeline.py         # Full report generation pipeline integration
├── test_chart_engine.py            # Chart rendering (Matplotlib) correctness
├── test_html_generator.py          # HTML report generator output validation
├── test_regression_detector.py     # Regression detection rule matching
│
│  ── Dashboard API & Services ──
├── test_dashboard_routes.py        # Dashboard HTTP route responses
├── test_experiment_api.py          # Experiment CRUD API endpoints
├── test_comparison_api.py          # Comparison API endpoint responses
├── test_comparison_service.py      # Comparison service business logic
├── test_export_api.py              # Export API endpoint responses
├── test_export_service.py          # Export service multi-format pipeline
├── test_repository_api.py          # Repository API endpoint responses
├── test_repository_manager.py      # Repository manager CRUD operations
├── test_repository_migrations.py   # Database migration correctness
├── test_bundle_integrity.py        # Bundle archive integrity & contents
├── test_bundle_service.py          # Bundle service packaging logic
├── test_result_manager.py          # Result file loading and caching
├── test_process_manager.py         # Subprocess lifecycle management
├── test_progress_reporter.py       # Progress tracking and ETA accuracy
├── test_live_monitor.py            # SSE live-monitor stream validation
├── test_sse_api.py                 # Server-Sent Events API behaviour
├── test_report_service.py          # (referenced via test_report_pipeline)
│
│  ── Dashboard UI ──
├── test_scenario_routes.py         # Scenario page route responses
├── test_navigation.py              # Dashboard navigation link integrity
├── test_comparison_ui.py           # Comparison page rendering
├── test_repository_ui.py           # Repository page rendering
├── test_live_ui.py                 # Live-monitor page rendering
├── test_settings_ui.py             # Settings page rendering
└── test_report_service.py          # Report service integration
```

---

## `experiment_repository/` — Experiment Archive

Persistent store of all completed experiment runs. Each run is stored in a
timestamped subdirectory.

```
experiment_repository/
├── metadata.db                                     # SQLite index of all archived runs
│                                                   #   (timestamps, scenario, status, metrics)
└── <YYYY-MM-DD_HH-MM-SS_exp-…-ID>/                # One directory per experiment run
    ├── experiment_manifest.json                    # Run manifest: scenario, config, timestamps
    ├── raw_results.json                            # Complete per-step decision records
    ├── metrics.json                                # Computed aggregate metrics
    ├── regression_summary.json                     # Regression detection results
    ├── progress_events.jsonl                       # Timestamped progress event stream
    ├── report.md                                   # Markdown summary report
    ├── report.html                                 # Self-contained HTML report with inline charts
    ├── charts/                                     # Generated chart images (PNG)
    └── logs/                                       # Experiment execution logs
```

---

## `results/` — Active Experiment Output

Working directory for the most recent / in-progress experiment.
Structure mirrors a single `experiment_repository/` run.

```
results/
├── charts/         # Chart output for the current run
├── logs/           # Execution logs for the current run
├── raw_results.json
├── metrics.json
├── report.md
└── report.html
```

---

## `reports/` — Generated Reports & Exports

```
reports/
├── assets/         # Static assets (images, CSS) referenced by reports
└── exports/        # Exported bundles (ZIP, CSV, PDF) from the dashboard
```

---

## `historical/` — Seasonal Baseline Data

Pre-computed seasonal risk baselines used by the scoring pipeline.

```
historical/
├── summer.json     # Summer season baseline parameters
├── monsoon.json    # Monsoon season baseline parameters
└── winter.json     # Winter season baseline parameters
```

---

## `docs/` — Project Documentation

```
docs/
├── repository_structure.md                     # ← This file
├── architecture.md                             # System architecture: layers, data flow, protocols
├── dashboard_guide.md                          # Cloud Dashboard user guide
├── ignis_v1_capabilities_and_tech_stack.md     # V1 capabilities overview and technology stack
├── v1_consolidated_testing_plan.md             # Master testing plan across all phases
│
│  ── Phase Documentation (A → G) ──
│  Each phase directory contains:
│    • implementation_plan.md  — Technical design & proposed changes
│    • walkthrough.md          — Post-implementation summary of what was built
│    • testing.md              — Phase-specific test plan & results
│    • (Phase E–G also contain sub-task directories & chart assets)
│
├── phase-a/                    # Phase A: Core decision pipeline (Edge → Fog → scoring)
│   ├── implementation_plan.md
│   ├── walkthrough.md
│   └── testing.md
│
├── phase-b/                    # Phase B: MQTT integration & Docker orchestration
│   ├── implementation_plan.md
│   ├── walkthrough.md
│   └── testing.md
│
├── phase-c/                    # Phase C: YAML scenarios, validation & experiment runner
│   ├── implementation_plan.md
│   ├── walkthrough.md
│   └── testing.md
│
├── phase-d/                    # Phase D: Cloud dashboard, repository & reporting
│   ├── implementation_plan.md
│   ├── walkthrough.md
│   ├── testing.md
│   └── d1/ … d5/              # Sub-task breakdowns
│
├── phase-e/                    # Phase E: Metrics, charts, regression & comparison
│   ├── implementation_plan.md
│   ├── walkthrough.md
│   ├── testing.md
│   ├── section7_metrics_report.md
│   ├── charts/
│   └── e1/ … e7/              # Sub-task breakdowns
│
├── phase-f/                    # Phase F: End-to-end integration, chaos testing & exports
│   ├── implementation_plan.md
│   ├── walkthrough.md
│   ├── testing.md
│   ├── project_results_report.md
│   ├── charts/
│   ├── run_a/ , run_b/        # Multi-run experiment outputs
│   └── f1/ … f6/              # Sub-task breakdowns
│
└── phase-g/                    # Phase G: Polish, hardening & final documentation
    ├── implementation_plan.md
    └── g1/ … g6/              # Sub-task breakdowns
```

---

## Quick Reference — Data Flow

```
┌─────────────┐   MQTT (local)   ┌───────────────┐   MQTT (cloud)   ┌─────────────────┐
│  edge_sim   │ ───────────────→ │ fog_node_runner│ ───────────────→ │ cloud_ingestor  │
│  (sensors)  │                  │  (decisions)   │                  │  (persistence)  │
└─────────────┘                  └───────┬────────┘                  └────────┬────────┘
                                         │ lateral warnings                   │
                                         ↓                                    ↓
                                 ┌───────────────┐                   ┌─────────────────┐
                                 │control_center │                   │ cloud_dashboard  │
                                 │  (operator UI)│                   │ (analytics UI)   │
                                 └───────────────┘                   └─────────────────┘
```

---

*Last updated: August 2026*
