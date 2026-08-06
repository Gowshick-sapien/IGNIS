# Phase E6 Walkthrough: Metrics Collector & Report Generator

Phase E6 introduces automated metrics collection, raw result parsing, Matplotlib chart visualization, and compilation of dissertation-ready documentation.

## Processing Pipeline

```
ScenarioRunner Trials
    ↓ (raw_results.json)
Metrics Collector (src/metrics_collector.py)
    ↓ (metrics.json)
Report Generator (src/report_generator.py)
     docs/phase-e/section7_metrics_report.md
     docs/phase-e/charts/ (5 plotted PNGs)
```

---

## 1. Metrics Collector (`src/metrics_collector.py`)

The CLI computes five core Section 7 dissertation metrics from raw scenario trial results:
1. **Decision Latency (S3)**: Formats `decision_timestamp` and `sensor_timestamp` to evaluate the fog state machine response delay (calculates average, min, and max delay).
2. **Lateral Propagation Time (S6)**: Tracks the time elapsed between Zone 4B RED fire escalation warning broadcasts and neighbor Zone 4C's preemptive YELLOW transition.
3. **False-Positive Rate (S4)**: Measures state clamping logic reliability under single sensor failures (percentage of S4 trials that erroneously escalated to ORANGE/RED).
4. **Offline Continuity (S5)**: Checks for on-site local stdout continuity log alerts and validates successful BufferedPublisher flush percentages on recovery.
5. **Concurrent-Zone Integrity (S7)**: Scans for message loss or cross-talk (payload `zone_id` mismatching the publishing topic).

Saves computed metrics to `results/metrics.json`.

---

## 2. Visual Reporting CLI (`src/report_generator.py`)

Using the raw metric counts from `metrics.json`, it renders five dissertation-ready visualizations:
- **`decision_latency.png`**: Line plot of trial-by-trial latencies.
- **`lateral_propagation.png`**: Bar chart of propagation times.
- **`false_positive_rate.png`**: Bar comparison of clamped vs allowed rates.
- **`offline_continuity.png`**: Caching vs flushing message counts.
- **`message_integrity.png`**: Cross-talk and loss ratios.

Generates the final formatted report at `docs/phase-e/section7_metrics_report.md`, embedding the generated charts directly.
