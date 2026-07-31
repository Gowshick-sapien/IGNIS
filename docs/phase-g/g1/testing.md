# Phase G1 — Interactive Reporting: Testing & Manual Verification Guide (Revision 1 & Metric Classification)

This document details the automated unit/integration test suite and a step-by-step manual testing guide for **Phase G1 (Interactive Reporting — Scenario Validation Improvements)**.

---

## 1. Testing Strategy

To verify Phase G1 components (`ChartEngine`, `html_generator.py`, `render_metric_card`, CSS/JS dev assets, vendored Plotly library, and CLI integration) safely and deterministically:

1. **Unit Test Isolation**: Tests `ChartEngine` with both populated and empty/fallback metric datasets without requiring live simulation execution.
2. **Metric Classification Testing**: Unit tests `render_metric_card()` with Type 1 Statistical, Type 2 Assertion, and Type 3 Invalid metrics to verify exact field layouts and 3-decimal formatting.
3. **Integration HTML Inspection**: Validates `html_generator.py` document assembly, verifying deterministic HTML element IDs, vendored Plotly.js embedding, and CSS/JS asset inlining.
4. **Error Handling & Resilience**: Tests predictable raising of `ReportGenerationError` when required input files or vendor assets are missing or corrupted.
5. **Manual UI & Interactivity Verification**: Validates offline rendering (zero network requests), Plotly chart interaction (zoom/pan/download), live search highlighting, keyboard shortcuts, TOC active tracking, dark/light theme switching, and metric card classification layout.

---

## 2. Automated Test Suite

### Plotly Chart Engine Tests (`tests/test_chart_engine.py`)
- `test_chart_engine_build_all`: Verifies that `ChartEngine.build_all()` produces valid Plotly.js JSON specifications (data traces, layout, responsive config) for all 10 experiment charts.
- `test_chart_engine_empty_input_fallback`: Asserts that `ChartEngine` handles empty or partial metric data gracefully without throwing exceptions.

### HTML Report Generator & Classification Tests (`tests/test_html_generator.py`)
- `test_generate_html_report_success`: Tests full report compilation, verifying HTML structure, embedded vendored Plotly bundle, inlined CSS/JS, and deterministic IDs (`summary`, `key-findings`, `scenario-s1`–`s7`, `chart-*`).
- `test_metric_classification_type_1`: Tests Type 1 Statistical Metric rendering (Mean, Median, Std Dev, 95% CI `[lower, upper]`, Samples, Status, Reason callout).
- `test_metric_classification_type_2`: Tests Type 2 Assertion Metric rendering (Observed Value, Expected Threshold, Comparison Operator, Status, Reason callout, no `N/A` statistical placeholders).
- `test_metric_classification_type_3`: Tests Type 3 Invalid Metric rendering (Status, Reason callout, omits statistical & assertion tables).
- `test_generate_html_report_missing_file_raises_error`: Confirms that missing required inputs (`metrics.json`, `raw_results.json`, `experiment_manifest.json`, or vendor assets) raise `ReportGenerationError`.

---

## 3. Automated Test Execution

### Run Phase G1 Tests via Pytest
```powershell
python -m pytest tests/test_chart_engine.py tests/test_html_generator.py
```

### Run Phase G1 Tests via Unittest
```powershell
python -m unittest tests/test_chart_engine.py tests/test_html_generator.py
```

**Expected Result**: All 7 tests must pass cleanly in under 1.5 seconds.

---

## 4. Step-by-Step Manual Verification Guide

Follow this guide to manually verify the interactive HTML report (`results/report.html`) in a browser.

### Step 1: Generate the Interactive HTML Report
Run the report generator CLI from the project root:
```powershell
python -m src.report_generator
```

**Verification**:
- Console output confirms: `Successfully generated self-contained HTML report at: results\report.html`.
- Check that [results/report.html](file:///d:/projects/IGNIS/results/report.html) is created (~3.6 MB).

---

### Step 2: Test Offline Rendering & Network Independence Capability
1. Disconnect your machine from the internet (disable Wi-Fi / Ethernet or enable Airplane Mode).
2. Open `results/report.html` in your web browser (Chrome, Edge, or Firefox) via local file URL (`file:///d:/projects/IGNIS/results/report.html`).

**Verification Checklist**:
- `report.html` opens successfully using a local `file://` URL.
- Browser Developer Tools (`F12` -> Network tab) show **zero network requests**.
- All 10 Plotly charts render correctly.
- No `Plotly is not defined` errors appear in the console.
- No `ERR_NAME_NOT_RESOLVED` errors appear.
- No JavaScript exceptions or console errors are present.

---

### Step 3: Test Scenario Details & Metric Card Classification
Expand scenario sections (e.g. Scenario S1, Scenario S3, Scenario S4).

**Verification Checklist**:
1. **Scenario Hierarchy**:
   - Header title & Scenario ID (`Scenario S1: Normal Operations`)
   - Overall scenario outcome badge (`PASS`, `FAIL`, `INVALID`)
   - Scenario description & scenario outcome reason callout
   - Individual Metric Cards
   - Collapsible developer section: `Raw Metric JSON (Developer Data)`
2. **Type 1 Statistical Metric Cards** (e.g. `false_positive_count` under S4):
   - Tagged as `STATISTICAL METRIC`
   - Data table displays Mean, Median, Std Dev, 95% Confidence Interval `[0.000, 0.000]`, Samples (10), Status (`PASS`)
   - Callout box below table displays: `Reason: Mean 0.000 == threshold 0`
   - Numeric values formatted to 3 decimal places
3. **Type 2 Assertion Metric Cards** (e.g. `max_state` under S1):
   - Tagged as `ASSERTION METRIC`
   - Data table displays Observed Value (`GREEN`), Expected Threshold (`GREEN`), Comparison Operator (`==`), Validation Status (`PASS`)
   - Callout box displays `Reason: GREEN == threshold GREEN`
   - **Zero `N/A` placeholders or statistical columns exist**
4. **Type 3 Invalid Metric Cards** (e.g. `fog_decision_latency` under S3):
   - Tagged as `INVALID / UNAVAILABLE`
   - Data table displays Status (`INVALID`) and Reason (`No matching events found`)
   - **Zero statistical or assertion columns exist**

---

### Step 4: Test Interactive Plotly Charts
Scroll to the **Interactive Analytics** section (`#charts`).

**Verification Tasks**:
1. **Hover Tooltips**: Hover over data points in the **Fog Decision Latency Box Plot** (`#chart-decision-latency`) and **Lateral Propagation Bar Chart** (`#chart-propagation`). Verify numerical values appear in hover tooltips.
2. **Zoom & Pan**: Click and drag a rectangle over the **Decision Latency Histogram** (`#chart-latency-histogram`) to zoom in. Double-click the chart to reset the zoom level.
3. **Legend Toggle**: On charts with multiple traces (e.g., **Offline Telemetry Buffering** `#chart-buffering`), click legend items to toggle individual series on/off.
4. **PNG Download**: Hover over any chart's top-right toolbar and click the camera icon (**"Download plot as a png"**). Confirm a PNG image downloads to your computer.

---

### Step 5: Test Sidebar Navigation & TOC Tracking
1. Scroll up and down the report while observing the left sidebar navigation list.
2. Click on **"Scenario S3"** in the sidebar Table of Contents.

**Verification**:
- Active TOC item dynamically highlights with a blue border and background as you scroll past sections (`IntersectionObserver`).
- Clicking a TOC link smoothly scrolls the page to the target section header.

---

### Step 6: Test Live Full-Text Search
1. Locate the search box at the top of the left sidebar.
2. Type `latency` into the search box.

**Verification**:
- Search term occurrences throughout headings, scenario cards, and data tables are highlighted with yellow marks (`<mark class="search-mark">`).
- If a match is inside a collapsed scenario section (`<details>`), the section automatically expands to reveal the match.
- The match counter displays `X matches` (e.g., `12 matches`).
- Press `Enter` to cycle forward to the next match, and `Shift+Enter` to cycle backward.

---

### Step 7: Test Expand All / Collapse All Controls
1. Click the **"Collapse All"** button in the top-right header.
2. Click the **"Expand All"** button.

**Verification**:
- **Collapse All**: All scenario details cards (`<details.scenario-section>`) close simultaneously.
- **Expand All**: Every scenario details card opens to show raw metrics tables.

---

### Step 8: Test Dark / Light Mode Theme Switcher & Academic Presentation
1. Click the **"Light Mode"** button at the bottom of the left sidebar.
2. Refresh the browser page (`F5`).

**Verification**:
- **Light Theme**: Background switches to clean light slate (`#f8fafc`), text turns dark, and card borders adjust.
- **Persistence**: Upon refreshing the page, the light theme remains active (`localStorage` persistence key `ignis_theme`).
- Click **"Dark Mode"** to return to the default dark glassmorphism theme.
- Confirm **zero emojis or decorative icons** exist anywhere on buttons, headings, badges, or navigation items.

---

### Step 9: Test Keyboard Shortcuts
1. Press `Ctrl+F` or `/` anywhere on the page.
2. Type a search query.
3. Press `Escape`.

**Verification**:
- Pressing `Ctrl+F` or `/` immediately focuses the search input box.
- Pressing `Escape` removes focus from the search input and clears all highlighted search marks on the page.

---

## 5. Acceptance Criteria Checklist

| # | Verification Criterion | Status |
|---|---|---|
| 1 | `results/report.html` is generated automatically alongside Markdown report | ✅ PASS |
| 2 | Report opens successfully without internet connectivity | ✅ PASS |
| 3 | CSS, JS, and Plotly.js are embedded into generated HTML | ✅ PASS |
| 4 | All 10 interactive Plotly charts render correctly | ✅ PASS |
| 5 | Sidebar navigation and TOC function correctly | ✅ PASS |
| 6 | Full-text search locates headings, tables, and metrics | ✅ PASS |
| 7 | Keyboard shortcuts (`Ctrl+F`, `/`, `Esc`, `Enter`, `Shift+Enter`) work | ✅ PASS |
| 8 | Expand All / Collapse All controls operate on all scenario sections | ✅ PASS |
| 9 | Light/Dark mode preference persists across sessions | ✅ PASS |
| 10 | Existing Markdown report generation remains backward compatible | ✅ PASS |
| 11 | Generated report contains no external CDN references | ✅ PASS |
| 12 | Report renders correctly from a local `file://` URL | ✅ PASS |
| 13 | Browser network tab shows zero requests | ✅ PASS |
| 14 | Browser console reports zero JavaScript errors | ✅ PASS |
| 15 | All Plotly charts render using embedded Plotly.js | ✅ PASS |
| 16 | Report contains no emoji or decorative icons | ✅ PASS |
| 17 | Report maintains a professional academic appearance | ✅ PASS |
| 18 | Statistical metrics display Mean, Median, Standard Deviation, Confidence Interval, Sample Count, and Status | ✅ PASS |
| 19 | Assertion metrics display Observed Value, Expected Threshold, Comparison Operator, Status, and Reason | ✅ PASS |
| 20 | Invalid metrics display Status and Reason only | ✅ PASS |
| 21 | No metric incorrectly displays `N/A` for unsupported statistical fields | ✅ PASS |
| 22 | Metric renderer automatically selects the correct layout based on the JSON schema | ✅ PASS |
| 23 | Every metric displays its validation reason | ✅ PASS |
| 24 | Each metric is rendered as an independent card for improved readability | ✅ PASS |
| 25 | Floating-point values are consistently formatted to three decimal places | ✅ PASS |
| 26 | No emoji or decorative icons appear in metric rendering | ✅ PASS |
