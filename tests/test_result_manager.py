"""Unit tests for ResultManager orchestrator (Phase G5)."""

from src.cloud_dashboard.services.result_manager import ResultManager


class MockReportService:
    def generate_markdown(self, metrics, out):
        return "md_ok"

    def generate_html(self, metrics_path, raw_results_path, manifest_path, output_path, theme="dark"):
        return "html_ok"


class MockComparisonService:
    def compare(self, exp_a, exp_b):
        return {"experiment_a": exp_a, "experiment_b": exp_b}


class MockRegressionDetector:
    def detect_regressions(self, exp_id, source_results_dir=None):
        return {"experiment_id": exp_id, "status": "NO_REGRESSION"}


def test_result_manager_delegation():
    rm = ResultManager(
        report_service=MockReportService(),
        comparison_service=MockComparisonService(),
        regression_detector=MockRegressionDetector()
    )

    assert rm.generate_markdown({}, "out.md") == "md_ok"
    assert rm.generate_html("m", "r", "man", "out.html") == "html_ok"

    comp = rm.compare("exp-1", "exp-2")
    assert comp["experiment_a"] == "exp-1"
    assert comp["experiment_b"] == "exp-2"

    reg = rm.detect_regressions("exp-1")
    assert reg["status"] == "NO_REGRESSION"
