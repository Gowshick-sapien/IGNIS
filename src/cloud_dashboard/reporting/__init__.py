"""
IGNIS Cloud Dashboard Reporting Package (Phase G1)

Provides self-contained interactive HTML report generation and Plotly chart configuration engine.
"""

from .chart_engine import ChartEngine
from .html_generator import generate_html_report, ReportGenerationError

__all__ = ["ChartEngine", "generate_html_report", "ReportGenerationError"]
