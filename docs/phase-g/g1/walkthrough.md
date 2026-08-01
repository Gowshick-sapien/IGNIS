# Phase G1 — Interactive Reporting Walkthrough (Revision 1 & Event Derivation Fix)

Phase G1 replaces static Markdown/PNG report artifacts with a rich, interactive, self-contained HTML report platform ([results/report.html](file:///d:/projects/IGNIS/results/report.html)) powered by a locally vendored Plotly.js library (~3.6MB) with strictly offline asset bundling, event stream metric derivation, classified metric card rendering, and clean academic presentation.

## Accomplishments

1. **Event Stream Metric Derivation Layer ([src/metrics_collector.py](file:///d:/projects/IGNIS/src/metrics_collector.py))**:
   - Classified metrics into `DIRECT_METRICS`, `DERIVED_METRICS`, and `ASSERTION_METRICS`.
   - Introduced `derive_metric(events, metric_name)` layer:
     - `compute_fog_decision_latency(events)`: Parses ISO 8601 timestamps from initial escalation alert event (`message_type == "alert"`) and decision state event (`message_type == "zone_state"`) to derive decision latency.
     - `compute_lateral_propagation(events)`: Parses ISO 8601 timestamps from source warning transition (`4B`/`4A`) and destination warning transition (`4C`/`4D`) to derive lateral propagation time.
   - Derived metric values flow directly into `calculate_stats()`, producing statistical aggregates (`mean`, `median`, `std_dev`, `confidence95`, `sample_count`) for `fog_decision_latency` and `lateral_propagation_time`.
   - Added unit test suite in [tests/test_metric_derivation.py](file:///d:/projects/IGNIS/tests/test_metric_derivation.py) (9 passed).

2. **Metric Classification & Independent Card Layout**:
   - Classifies every metric in `metrics.json` into 3 layout types based on schema:
     - **Type 1 (Statistical Metrics)**: `"mean" in metric` -> Displays Mean, Median, Std Dev, 95% Confidence Interval `[lower, upper]`, Samples, Status badge, and Reason callout. Formatted to 3 decimal places (`0.000`).
     - **Type 2 (Assertion Metrics)**: `"value" in metric` -> Displays Observed Value, Expected Threshold, Comparison Operator, Validation Status, and Reason callout. Statistical placeholders (`N/A`) completely omitted.
     - **Type 3 (Invalid / Unavailable Metrics)**: Neither `"mean"` nor `"value"` -> Displays Status badge and Reason callout explaining why data could not be computed.

3. **Vendored Plotly Asset Management**:
   - Vendored [plotly-2.27.0.min.js](file:///d:/projects/IGNIS/reports/assets/vendor/plotly-2.27.0.min.js) under `reports/assets/vendor/`.
   - Guaranteed **100% offline report compilation** with zero external network requests or CDN dependencies (`ERR_NAME_NOT_RESOLVED` completely eliminated).

4. **Academic Presentation & Zero Emoji Rule**:
   - Removed all emojis and decorative icons from button labels (`Light Mode`/`Dark Mode`), headers, sidebar navigation, badges, search bars, and metadata sections.

5. **CLI Integration & Testing**:
   - Updated [src/report_generator.py](file:///d:/projects/IGNIS/src/report_generator.py) with `--html` flag to automatically produce `results/report.html`.
   - Complete test suite in [tests/test_metric_derivation.py](file:///d:/projects/IGNIS/tests/test_metric_derivation.py), [tests/test_chart_engine.py](file:///d:/projects/IGNIS/tests/test_chart_engine.py), and [tests/test_html_generator.py](file:///d:/projects/IGNIS/tests/test_html_generator.py) passed 100% cleanly (16 passed).

---

## Verification Results

### Automated Tests Execution
```bash
python -m pytest tests/test_metric_derivation.py tests/test_chart_engine.py tests/test_html_generator.py
```

**Output**:
```
collected 16 items
tests/test_metric_derivation.py .........                                [ 56%]
tests/test_chart_engine.py ..                                            [ 68%]
tests/test_html_generator.py .....                                       [100%]
======================== 16 passed, 1 warning in 1.78s ========================
```

---

## Complete Acceptance Criteria Checklist Matrix (1–28)

| # | Verification Criterion | Status |
|---|---|---|
| 1 | `results/report.html` is generated automatically alongside Markdown report | [PASS] |
| 2 | Report opens successfully without internet connectivity | [PASS] |
| 3 | CSS, JS, and Plotly.js are embedded into generated HTML | [PASS] |
| 4 | All 10 interactive Plotly charts render correctly | [PASS] |
| 5 | Sidebar navigation and TOC function correctly | [PASS] |
| 6 | Full-text search locates headings, tables, and metrics | [PASS] |
| 7 | Keyboard shortcuts (`Ctrl+F`, `/`, `Esc`, `Enter`, `Shift+Enter`) work | [PASS] |
| 8 | Expand All / Collapse All controls operate on all scenario sections | [PASS] |
| 9 | Light/Dark mode preference persists across sessions | [PASS] |
| 10 | Existing Markdown report generation remains backward compatible | [PASS] |
| 11 | Generated report contains no external CDN references | [PASS] |
| 12 | Report renders correctly from a local `file://` URL | [PASS] |
| 13 | Browser network tab shows zero requests | [PASS] |
| 14 | Browser console reports zero JavaScript errors | [PASS] |
| 15 | All Plotly charts render using embedded Plotly.js | [PASS] |
| 16 | Report contains no emoji or decorative icons | [PASS] |
| 17 | Report maintains a professional academic appearance | [PASS] |
| 18 | Statistical metrics display Mean, Median, Standard Deviation, Confidence Interval, Sample Count, and Status | [PASS] |
| 19 | Assertion metrics display Observed Value, Expected Threshold, Comparison Operator, Status, and Reason | [PASS] |
| 20 | Invalid metrics display Status and Reason only | [PASS] |
| 21 | No metric incorrectly displays `N/A` for unsupported statistical fields | [PASS] |
| 22 | Metric renderer automatically selects the correct layout based on the JSON schema | [PASS] |
| 23 | Every metric displays its validation reason | [PASS] |
| 24 | Each metric is rendered as an independent card for improved readability | [PASS] |
| 25 | Floating-point values are consistently formatted to three decimal places | [PASS] |
| 26 | No emoji or decorative icons appear in metric rendering | [PASS] |
| 27 | Derived metrics (`fog_decision_latency`, `lateral_propagation_time`) are derived from raw event streams | [PASS] |
| 28 | Derived metrics flow through statistical aggregation pipeline (mean, median, std_dev, 95% CI) | [PASS] |
