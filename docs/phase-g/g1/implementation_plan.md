# Phase G1 — Interactive Reporting: Implementation Plan (Revision 1 & Event Stream Derivation)

Transform the IGNIS reporting workflow from static Markdown + PNG images into a rich, interactive, self-contained HTML reporting platform powered by Plotly.js with strictly offline vendored asset bundling, an event stream derivation layer, classified metric card rendering, and a clean, professional academic aesthetic.

## Overview & Goal

Phase G1 replaces static chart image outputs with an interactive HTML report engine. The generated report (`report.html`) is completely self-contained (working 100% offline with embedded Plotly.js and CSS/JS) and features navigation sidebars, TOC, client-side live search, expandable scenario details, light/dark mode, 10 interactive Plotly.js charts, and metric-type classification backed by an event stream metric derivation pipeline.

---

## Technical Deliverables

| Deliverable | Location | Description |
|---|---|---|
| **Event Derivation Layer** | [src/metrics_collector.py](file:///d:/projects/IGNIS/src/metrics_collector.py) | Analyzes raw event payloads to derive `fog_decision_latency` and `lateral_propagation_time` |
| **Derivation Tests** | [tests/test_metric_derivation.py](file:///d:/projects/IGNIS/tests/test_metric_derivation.py) | Unit test suite for `derive_metric()`, timestamp parsing, and event sequence handling |
| **Vendored Plotly Bundle** | [reports/assets/vendor/plotly-2.27.0.min.js](file:///d:/projects/IGNIS/reports/assets/vendor/plotly-2.27.0.min.js) | Local vendored Plotly.js minified bundle (~3.6MB) embedded during generation |
| **Package Init** | [src/cloud_dashboard/reporting/__init__.py](file:///d:/projects/IGNIS/src/cloud_dashboard/reporting/__init__.py) | Package initialization exposing `generate_html_report` and `ChartEngine` |
| **HTML Report Generator** | [src/cloud_dashboard/reporting/html_generator.py](file:///d:/projects/IGNIS/src/cloud_dashboard/reporting/html_generator.py) | Engine to build single-file self-contained HTML reports from `metrics.json` & `raw_results.json` |
| **Plotly Chart Engine** | [src/cloud_dashboard/reporting/chart_engine.py](file:///d:/projects/IGNIS/src/cloud_dashboard/reporting/chart_engine.py) | Generates Plotly.js specs (traces, layout, config) for all 10 experiment charts |
| **Template Utilities** | [src/cloud_dashboard/reporting/templates.py](file:///d:/projects/IGNIS/src/cloud_dashboard/reporting/templates.py) | HTML structure, Plotly embedding helper, badge builders, classified metric card renderers (`render_metric_card`), and inline CSS/JS bundler |
| **Dev CSS Stylesheet** | [reports/assets/css/report.css](file:///d:/projects/IGNIS/reports/assets/css/report.css) | Dark/Light glassmorphism theme, responsive sidebar layout, metric card styles, print stylesheet |
| **Dev JS Interactivity** | [reports/assets/js/report.js](file:///d:/projects/IGNIS/reports/assets/js/report.js) | Navigation highlight (`IntersectionObserver`), live search, keyboard shortcuts (`Ctrl+F`, `/`, `Esc`), collapse/expand controls |
| **CLI Generator Integration** | [src/report_generator.py](file:///d:/projects/IGNIS/src/report_generator.py) | Updated report generator to invoke HTML generation alongside Markdown report |
| **Generated HTML Output** | [results/report.html](file:///d:/projects/IGNIS/results/report.html) | Self-contained output file generated during runs |

---

## Event Stream Metric Derivation Architecture

Inside `metrics_collector.py`, metrics are classified into 3 sets:
- **`DIRECT_METRICS`**: Explicitly recorded during simulation (`false_positive_count`, `offline_continuity`, `flush_success_rate`, `cross_talk_count`, `message_loss_pct`, `is_clamped`).
- **`DERIVED_METRICS`**: Computed by analyzing raw event payload streams (`fog_decision_latency`, `lateral_propagation_time`).
  - `compute_fog_decision_latency(events)`: Computes time delta between initial escalation alert (`message_type == "alert"`) and decision level reaching `zone_state`.
  - `compute_lateral_propagation(events)`: Computes time delta between source zone warning transition (`4B`/`4A`) and destination zone warning transition (`4C`/`4D`).
- **`ASSERTION_METRICS`**: Categorical validation assertions (`max_state`, `final_state`).

Derived metric values flow directly through the existing statistical pipeline (`calculate_stats`), producing `sample_count`, `mean`, `median`, `std_dev`, and Student-t `confidence95` intervals.

---

## Acceptance Criteria Checklist

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
| 27 | Derived metrics (`fog_decision_latency`, `lateral_propagation_time`) are correctly derived from raw event streams | [PASS] |
| 28 | Derived metrics flow through statistical aggregation pipeline (mean, median, std_dev, 95% CI) | [PASS] |
