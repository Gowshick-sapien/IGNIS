# Phase G5 — Analytics, Side-by-Side Comparison & Automatic Regression Detection: Sub-Phase Implementation Plan

Phase G5 equips IGNIS with comprehensive experimentation analytics, enabling researchers to perform side-by-side comparisons of historical experiment runs, track metric regressions automatically using configurable rule sets (`config/regression_rules.yaml`), and orchestrate result services via a unified `ResultManager`.

---

## Overview & Objectives

Following Phase G1 (Interactive HTML Reporting), Phase G2 (Subprocess Lifecycle FSM), Phase G3 (Live Progress Streaming), and Phase G4 (Experiment Repository & SQLite Indexing), Phase G5 completes the analytical and comparative capabilities of IGNIS.

### Key Objectives
1. **Unified Result Manager (`ResultManager`)**: Create `src/cloud_dashboard/services/result_manager.py` as an orchestrator service that delegates result operations to `ReportService`, `ComparisonService`, `ExportService`, and `BundleService`.
2. **Report Generation Wrapper (`ReportService`)**: Create `src/cloud_dashboard/services/report_service.py` wrapping Markdown (`report_generator.py`) and interactive HTML (`html_generator.py`) rendering engines.
3. **Side-by-Side Comparison Engine (`ComparisonService`)**: Create `src/cloud_dashboard/services/comparison_service.py` to compare two experiment runs (`exp_a` vs. `exp_b`), producing structured deltas for verdicts (PASS/FAIL/INVALID), metrics (mean, median, 95% CI bounds, percentage change), environments (Python, OS, Docker, Git commit), and manifests. Incorporates 95% CI overlap checks and statistical significance testing.
4. **Configurable Regression Detector (`RegressionDetector`)**: Create `src/cloud_dashboard/services/regression_detector.py` and `config/regression_rules.yaml` to evaluate completed experiments against an explicit baseline selection strategy.
5. **Fail-Fast Rules Validation**: Validate `config/regression_rules.yaml` schema at application startup (`app.py` lifespan) to fail fast on malformed YAML configuration.
6. **Regression Rules Versioning & Storage**: Include SHA-256 integrity hash (`regression_rules_hash`) in experiment manifests and SQLite `experiments` table. Write `regression_summary.json` directly into `experiment_repository/YYYY-MM-DD_HH-MM-SS_{exp_id}/` immediately after detection.
7. **Versioned Comparison REST API (`/api/v1/experiments/compare`)**: Create `src/cloud_dashboard/routes/comparison.py` providing endpoints to compute diffs and fetch regression summaries.
8. **Interactive Comparison UI (`comparison.html`)**: Build a two-column Jinja2 template (`src/cloud_dashboard/templates/comparison.html`) inheriting `base.html` and `navbar.html`, featuring synchronized scrolling, experiment selectors, strongly-typed delta indicators (`ComparisonIndicator`), and metric tables.

---

## Refined Architecture & Rules

### 1. Explicit Baseline Selection Strategy

When automatic regression detection runs for a newly completed experiment (and no explicit baseline ID is passed):

```
                       ┌───────────────────────────────┐
                       │  New Completed Experiment B   │
                       └───────────────┬───────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        1. Find most recent archive            2. Find most recent archive
        with SAME Git commit                      OVERALL in metadata.db
                    │                                     │
             [Found archive?]                      [Found archive?]
              ├─ YES ──> Use as Baseline            ├─ YES ──> Use as Baseline
              └─ NO  ──> Fallback to 2.             └─ NO  ──> Skip Analysis
```

1. **Strategy 1 (Same Commit Baseline)**: Select the most recent archived experiment sharing the **exact same Git commit hash**.
2. **Strategy 2 (Overall Fallback Baseline)**: If no matching commit exists, select the most recent archived experiment **overall** in `metadata.db`.
3. **Strategy 3 (No Baseline)**: If no previous archives exist in `metadata.db`, gracefully skip regression analysis (`regression_summary.json` written with `status: "SKIPPED_NO_BASELINE"`).

---

### 2. Missing Metric Handling (`NOT_COMPARABLE`)

If a metric is missing in either Experiment A or Experiment B (e.g., INVALID scenario, unexecuted scenario, or missing metric key):

- Comparison status for that metric is set to `ComparisonIndicator.NOT_COMPARABLE`.
- Delta and percentage change evaluate to `None`.
- **No regression alert** is generated for that missing metric, preventing misleading comparison alerts.

---

### 3. Comparison Indicator Enum (`schemas.py`)

Metrics and verdict diffs use a strongly-typed Enum rather than ad-hoc string literals:

```python
class ComparisonIndicator(str, Enum):
    IMPROVED = "IMPROVED"
    REGRESSED = "REGRESSED"
    UNCHANGED = "UNCHANGED"
    NOT_COMPARABLE = "NOT_COMPARABLE"
```

---

### 4. Statistical Methodology: Confidence Interval & Overlap

Aligning with Phase F statistical methodology:

- **CI Overlap Analysis**: Evaluates whether 95% Confidence Intervals `[ci_low_a, ci_high_a]` and `[ci_low_b, ci_high_b]` overlap.
- **Statistical Significance Flag**: If 95% CIs do **not** overlap and mean delta exceeds the configured threshold percentage, `significant_difference` is set to `true`.

---

### 5. Fail-Fast Startup Rule Validation

At FastAPI lifespan startup in `app.py`:
- `RegressionDetector.validate_config("config/regression_rules.yaml")` executes.
- If YAML is missing, malformed, or contains invalid metric paths/directions, app initialization raises a `ValueError` with clear diagnostics, preventing runtime failures during experiment execution.

---

### 6. Regression Summary Storage Lifecycle

Immediately after regression analysis finishes:
1. `regression_summary.json` is written to `results/regression_summary.json`.
2. `RepositoryManager.archive_experiment()` includes `regression_summary.json` in the immutable folder `experiment_repository/YYYY-MM-DD_HH-MM-SS_{exp_id}/regression_summary.json`.
3. SQLite `experiments` table updates `regression_rules_hash` column.

---

## Technical Deliverables & File Manifest

| Action | Path | Description |
|---|---|---|
| **[NEW]** | [config/regression_rules.yaml](file:///d:/projects/IGNIS/config/regression_rules.yaml) | YAML configuration defining metric regression thresholds, direction rules, and verdict transitions |
| **[NEW]** | [src/cloud_dashboard/services/report_service.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/report_service.py) | Service wrapping Markdown and HTML report generation engines |
| **[NEW]** | [src/cloud_dashboard/services/comparison_service.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/comparison_service.py) | Side-by-side experiment diff engine with CI overlap testing and `ComparisonIndicator` enums |
| **[NEW]** | [src/cloud_dashboard/services/regression_detector.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/regression_detector.py) | Automatic regression analyzer with baseline selection strategy and fail-fast startup validation |
| **[NEW]** | [src/cloud_dashboard/services/result_manager.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/result_manager.py) | Orchestrator service delegating result requests to specialized services |
| **[NEW]** | [src/cloud_dashboard/routes/comparison.py](file:///d:/projects/IGNIS/src/cloud_dashboard/routes/comparison.py) | REST API endpoints for experiment comparison (`/api/v1/experiments/compare*`) and view route (`/comparison`) |
| **[NEW]** | [src/cloud_dashboard/templates/comparison.html](file:///d:/projects/IGNIS/src/cloud_dashboard/templates/comparison.html) | Interactive comparison UI with side-by-side selectors, diff tables, and regression indicators |
| **[MODIFY]** | [src/cloud_dashboard/schemas.py](file:///d:/projects/IGNIS/src/cloud_dashboard/schemas.py) | Pydantic request/response schemas including `ComparisonIndicator` Enum |
| **[MODIFY]** | [src/cloud_dashboard/app.py](file:///d:/projects/IGNIS/src/cloud_dashboard/app.py) | Lifespan rule validation, service registration, and comparison router mounting |
| **[MODIFY]** | [src/cloud_dashboard/services/process_manager.py](file:///d:/projects/IGNIS/src/cloud_dashboard/services/process_manager.py) | Trigger automatic regression analysis and summary persistence upon experiment completion |
| **[NEW]** | [docs/phase-g/g5/implementation_plan.md](file:///d:/projects/IGNIS/docs/phase-g/g5/implementation_plan.md) | Sub-phase G5 specification document in repository |
| **[NEW]** | [tests/test_comparison_service.py](file:///d:/projects/IGNIS/tests/test_comparison_service.py) | Unit tests for side-by-side metric diffs, CI overlap, `ComparisonIndicator` Enum, and `NOT_COMPARABLE` handling |
| **[NEW]** | [tests/test_regression_detector.py](file:///d:/projects/IGNIS/tests/test_regression_detector.py) | Unit tests for baseline selection hierarchy, YAML rule validation, and regression summary generation |
| **[NEW]** | [tests/test_result_manager.py](file:///d:/projects/IGNIS/tests/test_result_manager.py) | Unit tests for `ResultManager` delegation and orchestration |
| **[NEW]** | [tests/test_comparison_api.py](file:///d:/projects/IGNIS/tests/test_comparison_api.py) | Integration tests for `/api/v1/experiments/compare` endpoints |
| **[NEW]** | [tests/test_comparison_ui.py](file:///d:/projects/IGNIS/tests/test_comparison_ui.py) | Integration tests for `/comparison` view rendering and navbar active highlighting |

---

## Detailed Architectural Specifications

### 1. Regression Rules Schema (`config/regression_rules.yaml`)

```yaml
rules:
  decision_latency:
    metric_path: "scenario_results.S3.metrics.fog_decision_latency.mean"
    threshold_pct: 10
    direction: lower
    unit: "seconds"

  lateral_propagation:
    metric_path: "scenario_results.S6.metrics.lateral_propagation_time.mean"
    threshold_pct: 10
    direction: lower
    unit: "seconds"

  false_positive_count:
    metric_path: "scenario_results.S4.metrics.false_positive_count.mean"
    threshold_pct: 0
    direction: lower
    zero_tolerance: true

  message_loss:
    metric_path: "scenario_results.S7.metrics.message_loss_pct.mean"
    threshold_pct: 0
    direction: lower
    zero_tolerance: true

  scenario_verdicts:
    type: "verdict_transition"
    alert_on: "PASS_TO_FAIL"

  overall_verdict:
    type: "verdict_transition"
    alert_on: "PASS_TO_FAIL"
```

---

### 2. Side-by-Side Comparison Output Schema

`ComparisonService.compare(exp_a_id, exp_b_id)` produces:

```json
{
  "experiment_a": "exp-20260731T131510Z-ecbf",
  "experiment_b": "exp-20260801T042743Z-655c",
  "verdict_delta": {
    "overall_a": "PASS",
    "overall_b": "PASS",
    "changed": false,
    "scenarios": {
      "S3": {"verdict_a": "PASS", "verdict_b": "PASS", "status": "UNCHANGED"}
    }
  },
  "metrics_diff": {
    "S3": {
      "fog_decision_latency": {
        "mean_a": 0.65,
        "mean_b": 0.63,
        "ci_a": [0.25, 1.05],
        "ci_b": [0.23, 1.03],
        "ci_overlap": true,
        "significant_difference": false,
        "delta": -0.02,
        "pct_change": -3.07,
        "indicator": "IMPROVED"
      }
    }
  },
  "environment_diff": {
    "os_match": true,
    "python_match": true,
    "git_commit_a": "2b503f8",
    "git_commit_b": "2b503f8",
    "same_commit": true
  }
}
```

---

### 3. REST API Contract (`/api/v1/experiments/compare*`)

1. **`GET /api/v1/experiments/compare?a={exp_a}&b={exp_b}`**
   - Returns full side-by-side diff including verdict deltas, per-scenario metric comparisons with CI overlap, and environment diffs.

2. **`GET /api/v1/experiments/compare/summary?a={exp_a}&b={exp_b}`**
   - Returns high-level executive summary diff for quick dashboard display.

3. **`GET /comparison`**
   - Renders the interactive Jinja2 comparison view with two experiment selector dropdowns and synchronized metric tables.
