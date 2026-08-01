"""
Self-Contained Interactive HTML Report Generator for IGNIS (Phase G1 Revision 1 & Scenario Validation Improvements)

Assembles executive summaries, classified scenario metrics (Type 1 Statistical, Type 2 Assertion, Type 3 Invalid),
and Plotly.js charts into a single portable offline report.html document with ZERO external network dependencies,
zero decorative emojis, 3-decimal float precision, and metric card classification.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .chart_engine import ChartEngine
from .templates import (
    load_dev_asset,
    get_plotly_js_bundle,
    render_badge,
    render_metric_card,
    render_plotly_container,
    render_sidebar_toc
)

logger = logging.getLogger("ignis.reporting.html_generator")


class ReportGenerationError(Exception):
    """Raised when HTML report generation fails due to missing or invalid data."""
    pass


def generate_html_report(
    metrics_path: str,
    raw_results_path: str,
    manifest_path: str,
    output_path: str,
    theme: str = "dark"
) -> str:
    """Generate a self-contained interactive HTML report.

    Args:
        metrics_path: Absolute or relative path to metrics.json
        raw_results_path: Absolute or relative path to raw_results.json
        manifest_path: Absolute or relative path to experiment_manifest.json
        output_path: Target path to write report.html
        theme: Default theme ('dark' or 'light')

    Returns:
        Absolute path to the generated HTML file.
    """
    logger.info("Starting interactive HTML report generation (Revision 1 - Classified Metric Rendering)...")

    # Load and validate input files
    metrics = _load_json(metrics_path, "metrics.json")
    raw_results = _load_json(raw_results_path, "raw_results.json")
    manifest = _load_json(manifest_path, "experiment_manifest.json")

    # Load dev CSS and JS assets
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    css_path = os.path.join(project_root, "reports", "assets", "css", "report.css")
    js_path = os.path.join(project_root, "reports", "assets", "js", "report.js")

    css_content = load_dev_asset(css_path)
    js_content = load_dev_asset(js_path)

    if not css_content or not js_content:
        raise ReportGenerationError("Missing required dev assets (report.css or report.js)")

    try:
        plotly_bundle = get_plotly_js_bundle()
    except Exception as e:
        raise ReportGenerationError(f"Failed to load vendored Plotly library: {e}")

    # Generate Plotly charts
    chart_engine = ChartEngine(theme=theme)
    charts = chart_engine.build_all(metrics, raw_results)

    # Build HTML sections
    scenarios = metrics.get("scenario_results", {})
    exp_meta = metrics.get("experiment_metadata", {})
    summary_info = metrics.get("summary", {})
    exp_id = manifest.get("experiment_id") or exp_meta.get("experiment_id", "N/A")

    toc_html = render_sidebar_toc(scenarios)
    summary_html = _render_executive_summary(metrics, manifest)
    key_findings_html = _render_key_findings(metrics)
    scenarios_html = _render_scenarios(scenarios, raw_results)
    charts_section_html = _render_charts_section(charts)
    metadata_html = _render_metadata(manifest)

    # Assemble complete HTML document with zero external URLs
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IGNIS Experiment Report — {exp_id}</title>
    {plotly_bundle}
    <style>
    {css_content}
    </style>
</head>
<body data-theme="{theme}">
    <!-- Sidebar Navigation -->
    <aside class="sidebar">
        <div class="sidebar-header">
            <a href="#" class="sidebar-brand">
                IGNIS Analytics
            </a>
        </div>
        <div class="search-box">
            <div class="search-input-wrapper">
                <input type="text" id="report-search" class="search-input" placeholder="Search metrics... (Ctrl+F)">
            </div>
            <div class="search-counter">
                <span id="search-match-count">0 matches</span>
                <span>Shortcuts: / , Esc</span>
            </div>
        </div>
        <nav class="toc-nav">
            <ul class="toc-list">
                {toc_html}
            </ul>
        </nav>
        <div class="sidebar-footer">
            <button id="theme-toggle" class="theme-toggle-btn">
                {'Light Mode' if theme == 'dark' else 'Dark Mode'}
            </button>
        </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
        <div class="top-bar">
            <div class="report-title">
                <h1>IGNIS Experimentation & Validation Report</h1>
                <p>Experiment ID: <code>{exp_id}</code> | Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            </div>
            <div class="controls-group">
                <button id="expand-all" class="btn">Expand All</button>
                <button id="collapse-all" class="btn">Collapse All</button>
            </div>
        </div>

        {summary_html}

        {key_findings_html}

        <section id="scenarios-container">
            <h2 style="font-size: 1.4rem; margin-bottom: 1rem;">Scenario Validation Details</h2>
            {scenarios_html}
        </section>

        {charts_section_html}

        {metadata_html}
    </main>

    <script>
    {js_content}
    </script>
</body>
</html>
"""

    # Ensure target directory exists and write output
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    logger.info(f"Successfully generated self-contained HTML report at: {output_path}")
    return os.path.abspath(output_path)


def _load_json(file_path: str, name: str) -> Dict[str, Any]:
    """Helper to load and validate JSON files."""
    if not os.path.exists(file_path):
        raise ReportGenerationError(f"Required file '{name}' not found at: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise ReportGenerationError(f"Failed to parse '{name}': {str(e)}")


def _render_executive_summary(metrics: Dict[str, Any], manifest: Dict[str, Any]) -> str:
    summary_info = metrics.get("summary", {})
    verdict = summary_info.get("overall_verdict", metrics.get("overall_verdict", "UNKNOWN"))
    badge = render_badge(verdict)
    exp_meta = metrics.get("experiment_metadata", {})
    
    total_trials = manifest.get("trial_count", exp_meta.get("trial_count", metrics.get("total_trials", 0)))
    passed_scenarios = summary_info.get("passed", metrics.get("passed_scenarios", 0))
    total_scenarios = summary_info.get("total_scenarios", metrics.get("total_scenarios", len(metrics.get("scenario_results", {}))))
    duration = round(manifest.get("execution_duration_sec", exp_meta.get("total_duration_sec", metrics.get("total_execution_duration_sec", 0.0))), 2)

    return f"""
    <section id="summary" class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h2 class="card-title" style="margin-bottom: 0;">Executive Summary</h2>
            {badge}
        </div>
        <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">
            Experiment execution completed with overall status <strong>{verdict}</strong> across {total_scenarios} validation scenarios and {total_trials} total trial runs.
        </p>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Overall Verdict</div>
                <div class="metric-value">{verdict}</div>
                <div class="metric-sub">{passed_scenarios} of {total_scenarios} scenarios passed</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Trials</div>
                <div class="metric-value">{total_trials}</div>
                <div class="metric-sub">Monte Carlo sample runs</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Execution Duration</div>
                <div class="metric-value">{duration}s</div>
                <div class="metric-sub">Pipeline wall clock time</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Git Commit</div>
                <div class="metric-value" style="font-size: 1.1rem; font-family: monospace;">{manifest.get('git_commit', 'N/A')[:8]}</div>
                <div class="metric-sub">Branch: {manifest.get('git_branch', 'main')}</div>
            </div>
        </div>
    </section>
    """


def _render_key_findings(metrics: Dict[str, Any]) -> str:
    scenario_results = metrics.get("scenario_results", {})
    s3_lat = scenario_results.get("S3", {}).get("metrics", {}).get("fog_decision_latency", {}).get("mean", "N/A")
    s6_prop = scenario_results.get("S6", {}).get("metrics", {}).get("lateral_propagation_time", {}).get("mean", "N/A")
    s4_fp = scenario_results.get("S4", {}).get("metrics", {}).get("false_positive_count", {}).get("mean", 0)

    return f"""
    <section id="key-findings" class="card">
        <h2 class="card-title">Key Experimental Findings</h2>
        <ul style="padding-left: 1.5rem; color: var(--text-secondary); display: flex; flex-direction: column; gap: 0.5rem;">
            <li><strong>Fog Decision Latency (S3):</strong> Measured under emergency state transitions.</li>
            <li><strong>Lateral Propagation (S6):</strong> Zone-to-zone hazard propagation measured across trial executions.</li>
            <li><strong>False-Positive Immunity (S4):</strong> State clamping evaluated for false alarm prevention.</li>
            <li><strong>Offline Resilience (S5):</strong> Telemetry event buffering and flush recovery verified.</li>
            <li><strong>Cross-Zone Communication (S7):</strong> Message integrity and crosstalk evaluated.</li>
        </ul>
    </section>
    """


def _render_scenarios(scenarios: Dict[str, Any], raw_results: Dict[str, Any]) -> str:
    scenario_cards = []

    for sid, data in scenarios.items():
        verdict = data.get("status", data.get("verdict", "UNKNOWN"))
        badge = render_badge(verdict)
        name = data.get("name", f"Scenario {sid}")
        trials = data.get("trials", 0)
        duration = round(data.get("execution_duration_sec", 0.0), 2)
        metric_dict = data.get("metrics", {})
        scenario_reason = data.get("reason", "")
        description = data.get("description", "")

        # Build metric cards based on classification
        metric_cards_html_list = []
        if metric_dict:
            for m_name, m_data in metric_dict.items():
                metric_cards_html_list.append(render_metric_card(m_name, m_data))
        else:
            metric_cards_html_list.append('<p style="color: var(--text-muted);">No metric objects recorded for this scenario.</p>')

        metric_cards_html = "\n".join(metric_cards_html_list)
        formatted_raw_json = json.dumps(data, indent=2)

        scenario_cards.append(f"""
        <details id="scenario-{sid.lower()}" class="scenario-section">
            <summary>
                <span><strong>{sid}:</strong> {name}</span>
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <span style="font-size: 0.85rem; color: var(--text-muted);">{trials} trials | {duration}s</span>
                    {badge}
                </div>
            </summary>
            <div class="scenario-content">
                <div class="scenario-meta-bar">
                    {f'<p style="color: var(--text-secondary); margin-bottom: 0.5rem;">{description}</p>' if description else ''}
                    {f'<p class="scenario-reason"><strong>Scenario Outcome Reason:</strong> {scenario_reason}</p>' if scenario_reason else ''}
                </div>
                
                <h4 style="font-size: 1rem; color: var(--text-primary); margin-bottom: 1rem;">Metric Validations & Classification</h4>
                <div class="metric-cards-container">
                    {metric_cards_html}
                </div>

                <details class="raw-json-details" style="margin-top: 1.5rem;">
                    <summary style="font-size: 0.85rem; color: var(--text-muted); cursor: pointer;">Raw Metric JSON (Developer Data)</summary>
                    <pre class="json-code"><code>{formatted_raw_json}</code></pre>
                </details>
            </div>
        </details>
        """)

    return "\n".join(scenario_cards)


def _render_charts_section(charts: Dict[str, Dict[str, Any]]) -> str:
    chart_ids = [
        ("chart-decision-latency", "Fog Decision Latency Distribution (S3)", charts["decision_latency_boxplot"]),
        ("chart-latency-histogram", "Decision Latency Frequency Histogram", charts["decision_latency_histogram"]),
        ("chart-propagation", "Lateral Hazard Propagation Comparison (S6)", charts["lateral_propagation_bar"]),
        ("chart-ci", "Lateral Propagation 95% Confidence Interval", charts["lateral_propagation_ci"]),
        ("chart-false-positive", "False-Positive Immunity Trend (S4)", charts["false_positive_trend"]),
        ("chart-buffering", "Offline Telemetry Buffering vs Flushed Events (S5)", charts["offline_buffering_timeline"]),
        ("chart-integrity", "Multi-Zone Message Integrity Heatmap (S7)", charts["message_integrity_heatmap"]),
        ("chart-summary", "Cross-Scenario Verdict & Duration Summary", charts["cross_scenario_summary"]),
        ("chart-state", "Hazard State Progression Step Timeline", charts["state_transition_timeline"]),
        ("chart-execution", "Pipeline Execution Timeline Gantt", charts["execution_timeline"])
    ]

    containers = []
    for cid, title, spec in chart_ids:
        containers.append(render_plotly_container(cid, title, spec))

    return f"""
    <section id="charts" class="card">
        <h2 class="card-title">Interactive Experiment Analytics</h2>
        <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">
            Explore trial distributions, confidence intervals, heatmaps, and state timelines using interactive Plotly.js controls (zoom, pan, hover, PNG download).
        </p>
        {''.join(containers)}
    </section>
    """


def _render_metadata(manifest: Dict[str, Any]) -> str:
    platform_info = manifest.get("platform", manifest.get("environment", {}))
    exp_id = manifest.get("experiment_id", "N/A")
    seed_val = manifest.get("random_seed", manifest.get("seed", "N/A"))
    py_ver = platform_info.get("python_version", "N/A")
    os_ver = platform_info.get("os", platform_info.get("os_platform", "N/A"))

    return f"""
    <section id="appendix" class="card">
        <h2 class="card-title">Appendix & Reproducibility Metadata</h2>
        <table class="data-table">
            <tbody>
                <tr><td><strong>Experiment ID</strong></td><td><code>{exp_id}</code></td></tr>
                <tr><td><strong>Execution Timestamp</strong></td><td>{manifest.get('timestamp', 'N/A')}</td></tr>
                <tr><td><strong>Git Commit / Branch</strong></td><td><code>{manifest.get('git_commit', 'N/A')}</code> ({manifest.get('git_branch', 'main')})</td></tr>
                <tr><td><strong>Python Version</strong></td><td>{py_ver}</td></tr>
                <tr><td><strong>Platform OS</strong></td><td>{os_ver}</td></tr>
                <tr><td><strong>Seed</strong></td><td><code>{seed_val}</code></td></tr>
            </tbody>
        </table>
    </section>
    """
