# Phase G5 — Analytics, Side-by-Side Comparison & Automatic Regression Detection: Testing & Verification Plan

This document outlines the automated test suite details and manual verification steps for Phase G5.

---

## Overview of Phase G5 Capabilities

Phase G5 equips IGNIS with advanced analytics capabilities:
1. **Configurable Regression Rules (`config/regression_rules.yaml`)**: Rule set defining metric regression thresholds (latency deltas, false-positive emergence, message loss bounds, and verdict transitions) with fail-fast startup validation.
2. **Unified `ResultManager` (`src/cloud_dashboard/services/result_manager.py`)**: Public API orchestrator delegating result tasks to `ReportService`, `ComparisonService`, `ExportService`, and `BundleService`.
3. **Side-by-Side Comparison Engine (`ComparisonService`)**: Computes structured deltas between two historical runs (verdicts, metrics, 95% confidence interval overlap, statistical significance, environment, and manifests).
4. **Baseline Selection Strategy & Regression Analyzer (`RegressionDetector`)**: Evaluates completed experiments using a 3-tier baseline selection hierarchy (1. Same Git commit, 2. Recent overall, 3. Skip). Handles missing metrics with `ComparisonIndicator.NOT_COMPARABLE`.
5. **Regression Summary Storage**: Persists `regression_summary.json` directly into `experiment_repository/YYYY-MM-DD_HH-MM-SS_{exp_id}/` immediately after detection.
6. **Comparison REST API (`/api/v1/experiments/compare*`)**: Versioned endpoints for querying comparison deltas and regression summaries.
7. **Interactive Comparison UI (`comparison.html`)**: Two-column responsive view with synchronized scrolling, experiment selectors, color-coded delta badges ([GREEN]/[YELLOW]//), and environment diff tables.

---

## Automated Pytest Suite

The Phase G5 test suite consists of 11 dedicated tests across 5 new test modules in `tests/`:

```powershell
python -m pytest tests/test_comparison_service.py tests/test_regression_detector.py tests/test_result_manager.py tests/test_comparison_api.py tests/test_comparison_ui.py -v
```

### Module Breakdown:
1. **`tests/test_comparison_service.py`**:
   - `test_comparison_service_valid`: Verifies side-by-side metric diff calculation, `ComparisonIndicator` Enum values (`IMPROVED`, `REGRESSED`, `UNCHANGED`), and environment match checks.
   - `test_comparison_service_missing_experiment`: Verifies HTTP 404 / ValueError handling on non-existent experiment IDs.
2. **`tests/test_regression_detector.py`**:
   - `test_regression_detector_config_validation`: Verifies fail-fast schema validation of `config/regression_rules.yaml`.
   - `test_regression_detector_baseline_selection`: Verifies 3-tier baseline selection hierarchy (Same Commit -> Recent Overall -> Skip).
3. **`tests/test_result_manager.py`**:
   - `test_result_manager_delegation`: Verifies `ResultManager` orchestrator delegation to `ReportService`, `ComparisonService`, and `RegressionDetector`.
4. **`tests/test_comparison_api.py`**:
   - `test_compare_endpoint`: Verifies `GET /api/v1/experiments/compare?a={id}&b={id}` returns HTTP 200 with full diff structure.
   - `test_compare_summary_endpoint`: Verifies `GET /api/v1/experiments/compare/summary` returns executive summary diff.
   - `test_compare_not_found_endpoint`: Verifies HTTP 404 on missing experiment IDs.
5. **`tests/test_comparison_ui.py`**:
   - `test_comparison_page_rendering`: Verifies `GET /comparison` returns HTTP 200 with HTML DOM elements and selectors.
   - `test_comparison_navbar_active_state`: Verifies navbar Comparison link active class highlighting.

---

## Manual Verification Walkthrough

### Step 1: Start IGNIS Dashboard Server

```powershell
python -m uvicorn src.cloud_dashboard.app:app --port 9000
```

---

### Step 2: Open Comparison Page

1. Open `http://localhost:9000/comparison` (or click **Comparison** in sidebar navbar).
2. Confirm:
   - The **Comparison** sidebar link is highlighted as active.
   - Two experiment dropdown selectors (**Experiment A Baseline** and **Experiment B Target**) are populated with archived experiment runs from `metadata.db`.

---

### Step 3: Execute Side-by-Side Comparison

1. Select **Experiment A** (e.g. `exp-20260731T131510Z-ecbf`) and **Experiment B** (e.g. `exp-20260801T042743Z-655c`).
2. Click **Compare Experiments**.
3. Verify:
   - **Overall Verdict Delta**: Badges render for Baseline A and Target B with overall verdict status description.
   - **Environment Parity**: Git commits A and B render side-by-side with match indicators.
   - **Scenario Verdict Matrix**: Displays per-scenario verdict status (`UNCHANGED`, `PASS_TO_FAIL`, `FAIL_TO_PASS`).
   - **Detailed Metric Diffs**: Renders Mean A, Mean B, Delta, % Change, 95% CI Overlap, and strongly-typed `ComparisonIndicator` badges (`IMPROVED`, `REGRESSED`, `UNCHANGED`, `NOT_COMPARABLE`).

---

### Step 4: Verify Automatic Regression Detection & Storage

1. Execute a new experiment run from `http://localhost:9000/experiments`.
2. After completion, inspect the newly created folder in `experiment_repository/YYYY-MM-DD_HH-MM-SS_{exp_id}/`.
3. Confirm `regression_summary.json` is present in the archive folder with `baseline_strategy`, `baseline_experiment_id`, `regression_rules_hash`, and `rule_evaluations`.
