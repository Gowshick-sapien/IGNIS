"""IGNIS Report Generation Service (Phase G5).

Wraps Markdown and self-contained interactive HTML report rendering logic.
"""

import os
import logging
from typing import Dict, Any, Optional

from ...report_generator import generate_report
from ..reporting.html_generator import generate_html_report

logger = logging.getLogger("report_service")


class ReportService:
    """Service wrapper for generating Markdown and self-contained HTML reports."""

    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = os.path.abspath(workspace_dir or os.getcwd())

    def generate_markdown(self, metrics: Dict[str, Any], output_path: str) -> str:
        """Generate Markdown summary report."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            generate_report(metrics, output_path)
            logger.info(f"Markdown report generated successfully at: {output_path}")
            return os.path.abspath(output_path)
        except Exception as e:
            logger.error(f"Failed to generate Markdown report: {e}")
            raise e

    def generate_html(
        self,
        metrics_path: str,
        raw_results_path: str,
        manifest_path: str,
        output_path: str,
        theme: str = "dark"
    ) -> str:
        """Generate self-contained interactive HTML report."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            out_file = generate_html_report(
                metrics_path=metrics_path,
                raw_results_path=raw_results_path,
                manifest_path=manifest_path,
                output_path=output_path,
                theme=theme
            )
            logger.info(f"Interactive HTML report generated successfully at: {out_file}")
            return out_file
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
            raise e
