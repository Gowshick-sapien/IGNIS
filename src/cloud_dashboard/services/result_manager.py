"""IGNIS Result Manager Orchestrator (Phase G5 & Phase G6).

Public orchestrator API for all result, report, comparison, and export operations.
Delegates to specialized services — contains no business logic itself.
"""

import logging
from typing import Dict, Any, Optional

from .report_service import ReportService
from .comparison_service import ComparisonService
from .regression_detector import RegressionDetector
from .export_service import ExportService
from .bundle_service import BundleService

logger = logging.getLogger("result_manager")


class ResultManager:
    """Orchestrator delegating result processing, reporting, comparison, export, and bundle calls."""

    def __init__(
        self,
        report_service: Optional[ReportService] = None,
        comparison_service: Optional[ComparisonService] = None,
        regression_detector: Optional[RegressionDetector] = None,
        export_service: Optional[ExportService] = None,
        bundle_service: Optional[BundleService] = None
    ):
        self.report_service = report_service or ReportService()
        self.comparison_service = comparison_service or ComparisonService()
        self.regression_detector = regression_detector or RegressionDetector()
        self.export_service = export_service or ExportService()
        self.bundle_service = bundle_service or BundleService()

    def generate_markdown(self, metrics: Dict[str, Any], output_path: str) -> str:
        """Delegate Markdown report compilation to ReportService."""
        return self.report_service.generate_markdown(metrics, output_path)

    def generate_html(
        self,
        metrics_path: str,
        raw_results_path: str,
        manifest_path: str,
        output_path: str,
        theme: str = "dark"
    ) -> str:
        """Delegate interactive HTML report compilation to ReportService."""
        return self.report_service.generate_html(
            metrics_path=metrics_path,
            raw_results_path=raw_results_path,
            manifest_path=manifest_path,
            output_path=output_path,
            theme=theme
        )

    def compare(self, experiment_a: str, experiment_b: str) -> Dict[str, Any]:
        """Delegate side-by-side experiment comparison to ComparisonService."""
        return self.comparison_service.compare(experiment_a, experiment_b)

    def detect_regressions(self, experiment_id: str, source_results_dir: Optional[str] = None) -> Dict[str, Any]:
        """Delegate automatic regression detection to RegressionDetector."""
        return self.regression_detector.detect_regressions(experiment_id, source_results_dir=source_results_dir)

    def export(self, experiment_id: str, format: str) -> str:
        """Delegate format export to ExportService."""
        return self.export_service.export(experiment_id, format)

    def get_export_capabilities(self) -> Dict[str, Any]:
        """Delegate export capabilities query to ExportService."""
        return self.export_service.get_format_capabilities()

    def build_reproducibility_bundle(self, experiment_id: str) -> Dict[str, Any]:
        """Delegate reproducibility bundle generation to BundleService."""
        return self.bundle_service.build_bundle(experiment_id)
