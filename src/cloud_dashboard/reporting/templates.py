"""
Report Template Utilities for IGNIS Interactive Reports (Phase G1 Revision 1 & Scenario Validation Improvements)

Provides HTML structure, Plotly wrappers, badge generators, metric classification rendering,
and vendored asset inlining.
Strictly offline with zero external CDN dependencies, zero emoji usage, and 3-decimal float precision.
"""

import os
import json
import logging
from typing import Dict, Any, Union

logger = logging.getLogger("ignis.reporting.templates")


def load_dev_asset(asset_path: str) -> str:
    """Read static CSS, JS, or vendor asset from disk."""
    if os.path.exists(asset_path):
        with open(asset_path, "r", encoding="utf-8") as f:
            return f.read()
    logger.error(f"Asset missing: {asset_path}")
    return ""


def get_plotly_js_bundle() -> str:
    """Return inline vendored Plotly.js script string.

    Strictly reads from reports/assets/vendor/plotly-2.27.0.min.js.
    No CDN or external URL reference allowed.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    vendor_plotly = os.path.join(project_root, "reports", "assets", "vendor", "plotly-2.27.0.min.js")
    
    if os.path.exists(vendor_plotly):
        with open(vendor_plotly, "r", encoding="utf-8") as f:
            js_content = f.read()
            return f"<script>\n{js_content}\n</script>"
    
    raise RuntimeError(f"Missing required vendored Plotly bundle at: {vendor_plotly}")


def render_badge(status: str) -> str:
    """Render status badge with clean CSS styling (no emoji)."""
    status_upper = str(status).upper()
    if status_upper == "PASS":
        return '<span class="badge badge-pass">PASS</span>'
    elif status_upper == "FAIL":
        return '<span class="badge badge-fail">FAIL</span>'
    elif status_upper == "INVALID":
        return '<span class="badge badge-invalid">INVALID</span>'
    elif status_upper == "INCOMPLETE":
        return '<span class="badge badge-incomplete">INCOMPLETE</span>'
    else:
        return f'<span class="badge badge-invalid">{status_upper}</span>'


def format_float(val: Any) -> str:
    """Format numeric values to exactly 3 decimal places."""
    if isinstance(val, (int, float)):
        return f"{float(val):.3f}"
    return str(val) if val is not None else "N/A"


def format_confidence_interval(metric: Dict[str, Any]) -> str:
    """Format 95% confidence interval bounds [lower, upper] to 3 decimal places."""
    if "confidence95" in metric and isinstance(metric["confidence95"], (list, tuple)) and len(metric["confidence95"]) == 2:
        l, u = metric["confidence95"]
        return f"[{format_float(l)}, {format_float(u)}]"
    elif "ci_95_lower" in metric and "ci_95_upper" in metric:
        return f"[{format_float(metric['ci_95_lower'])}, {format_float(metric['ci_95_upper'])}]"
    return "N/A"


def format_metric_title(name: str) -> str:
    """Convert snake_case metric names to Title Case."""
    return name.replace("_", " ").title()


def render_metric_card(metric_name: str, metric: Dict[str, Any]) -> str:
    """Render individual metric as an independent card based on its schema type.

    Classification logic:
    - Type 1 (Statistical): "mean" in metric
    - Type 2 (Assertion): "value" in metric (and "mean" not in metric)
    - Type 3 (Invalid/Unavailable): neither "mean" nor "value" in metric
    """
    title = format_metric_title(metric_name)

    if "mean" in metric:
        # Type 1: Statistical Metric
        mean = format_float(metric.get("mean", 0.0))
        median = format_float(metric.get("median", 0.0))
        std_dev = format_float(metric.get("std_dev", 0.0))
        ci_str = format_confidence_interval(metric)
        samples = metric.get("sample_count", "N/A")
        status = metric.get("status", "UNKNOWN")
        badge = render_badge(status)
        reason = metric.get("reason", f"Mean {mean} == threshold {metric.get('threshold', 'N/A')}")

        table_html = f"""
        <table class="data-table">
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Mean</th>
                    <th>Median</th>
                    <th>Std Dev</th>
                    <th>95% Confidence Interval</th>
                    <th>Samples</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>{title}</strong></td>
                    <td>{mean}</td>
                    <td>{median}</td>
                    <td>{std_dev}</td>
                    <td><code>{ci_str}</code></td>
                    <td>{samples}</td>
                    <td>{badge}</td>
                </tr>
            </tbody>
        </table>
        """
        tag = '<span class="metric-type-tag">Statistical Metric</span>'

    elif "value" in metric:
        # Type 2: Assertion Metric
        val = str(metric.get("value", ""))
        threshold = str(metric.get("threshold", "N/A"))
        operator = str(metric.get("operator", "=="))
        status = metric.get("status", "UNKNOWN")
        badge = render_badge(status)
        reason = metric.get("reason", f"{val} {operator} threshold {threshold}")

        table_html = f"""
        <table class="data-table">
            <thead>
                <tr>
                    <th>Property</th>
                    <th>Value</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>Observed Value</td><td><strong>{val}</strong></td></tr>
                <tr><td>Expected Threshold</td><td><code>{threshold}</code></td></tr>
                <tr><td>Comparison Operator</td><td><code>{operator}</code></td></tr>
                <tr><td>Validation Status</td><td>{badge}</td></tr>
            </tbody>
        </table>
        """
        tag = '<span class="metric-type-tag">Assertion Metric</span>'

    else:
        # Type 3: Invalid / Unavailable Metric
        status = metric.get("status", "INVALID")
        badge = render_badge(status)
        reason = metric.get("reason", "No matching events found or metric unavailable")

        table_html = f"""
        <table class="data-table">
            <thead>
                <tr>
                    <th>Field</th>
                    <th>Value</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>Status</td><td>{badge}</td></tr>
                <tr><td>Reason</td><td>{reason}</td></tr>
            </tbody>
        </table>
        """
        tag = '<span class="metric-type-tag metric-type-invalid">Invalid / Unavailable</span>'

    return f"""
    <div class="metric-card-detail">
        <div class="metric-card-header">
            <h4>{title}</h4>
            {tag}
        </div>
        {table_html}
        <div class="metric-reason">
            <strong>Reason:</strong> {reason}
        </div>
    </div>
    """


def render_plotly_container(chart_id: str, title: str, chart_spec: Dict[str, Any]) -> str:
    """Render container div and script tag for a Plotly.js chart."""
    data_json = json.dumps(chart_spec.get("data", []))
    layout_json = json.dumps(chart_spec.get("layout", {}))
    config_json = json.dumps(chart_spec.get("config", {"responsive": True}))

    return f"""
    <div id="{chart_id}" class="chart-container"></div>
    <script>
        (function() {{
            const data = {data_json};
            const layout = {layout_json};
            const config = {config_json};
            Plotly.newPlot('{chart_id}', data, layout, config);
        }})();
    </script>
    """


def render_sidebar_toc(scenarios: Dict[str, Any]) -> str:
    """Render Table of Contents sidebar navigation links (no emoji)."""
    toc_items = [
        '<li class="toc-item"><a href="#summary">Executive Summary</a></li>',
        '<li class="toc-item"><a href="#key-findings">Key Findings</a></li>'
    ]

    for sid in scenarios:
        toc_items.append(f'<li class="toc-item toc-subitem"><a href="#scenario-{sid.lower()}">Scenario {sid}</a></li>')

    toc_items.extend([
        '<li class="toc-item"><a href="#charts">Interactive Analytics</a></li>',
        '<li class="toc-item"><a href="#appendix">Appendix & Metadata</a></li>'
    ])

    return "\n".join(toc_items)
