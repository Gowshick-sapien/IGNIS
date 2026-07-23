import os
import sys
import unittest
import shutil
import json
from unittest.mock import patch, MagicMock

# Adjust path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.scenarios.results import ScenarioResult

class TestRunExperiment(unittest.TestCase):
    
    def setUp(self):
        self.test_output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_experiment_results"))
        self.test_report_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "temp_experiment_reports"))
        os.makedirs(self.test_output_dir, exist_ok=True)
        os.makedirs(self.test_report_dir, exist_ok=True)
        
    def tearDown(self):
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)
        if os.path.exists(self.test_report_dir):
            shutil.rmtree(self.test_report_dir)

    @patch('src.scenarios.scenario_runner.ScenarioRunner.run_scenario')
    def test_pipeline_clean_removes_old_files(self, mock_run):
        mock_run.return_value = []
        # Create some stale files
        stale_file = os.path.join(self.test_output_dir, "stale_result.json")
        with open(stale_file, "w") as f:
            f.write("{}")
        stale_chart = os.path.join(self.test_report_dir, "project_results_report.md")
        with open(stale_chart, "w") as f:
            f.write("# Legacy Report")
            
        from src.run_experiment import clean_outputs
        logger = MagicMock()
        clean_outputs(self.test_output_dir, self.test_report_dir, logger)
        
        self.assertFalse(os.path.exists(stale_file))
        self.assertFalse(os.path.exists(stale_chart))

    @patch('sys.argv', ['run_experiment.py', '--trials', '1', '--scenarios', 'S3', '--output-dir', 'temp_experiment_results', '--report-dir', 'temp_experiment_reports', '--skip-validation'])
    @patch('src.scenarios.scenario_runner.ScenarioRunner.run_scenario')
    @patch('src.report_generator.generate_charts')
    @patch('src.report_generator.generate_report')
    def test_run_experiment_full_pipeline(self, mock_report, mock_charts, mock_run):
        # Mock run returns a valid S3 result
        mock_run.return_value = [
            ScenarioResult(
                scenario="S3",
                passed=True,
                duration_sec=1.5,
                start_time="2026-07-16T09:00:00Z",
                end_time="2026-07-16T09:00:01.5Z",
                metrics=[],
                events=[
                    {
                        "_topic": "ignis/v1/fog/zone/4B/state",
                        "sensor_timestamp": "2026-07-16T09:00:00.000Z",
                        "decision_timestamp": "2026-07-16T09:00:00.120Z",
                        "state": "RED"
                    }
                ],
                logs=["Started scenario S3"],
                errors=[],
                zone_ids=["4B"]
            )
        ]
        
        # Override paths to avoid cluttering local repo
        with patch('src.run_experiment.setup_orchestrator_logger') as mock_logger_setup:
            logger = MagicMock()
            mock_logger_setup.return_value = logger
            
            # Temporarily redirect the working paths inside run_stages
            with patch('argparse.ArgumentParser.parse_args') as mock_args:
                mock_args.return_value = argparse_mock = MagicMock()
                argparse_mock.trials = 1
                argparse_mock.scenarios = "S3"
                argparse_mock.output_dir = self.test_output_dir
                argparse_mock.report_dir = self.test_report_dir
                argparse_mock.clean = True
                argparse_mock.skip_validation = True
                argparse_mock.seed = 42
                argparse_mock.load_existing = False
                
                from src.run_experiment import run_stages
                run_stages()
                
        # Assert manifest and metrics files are generated
        manifest_path = os.path.join(self.test_output_dir, "experiment_manifest.json")
        metrics_path = os.path.join(self.test_output_dir, "metrics.json")
        raw_results_path = os.path.join(self.test_output_dir, "raw_results.json")
        
        self.assertTrue(os.path.exists(manifest_path))
        self.assertTrue(os.path.exists(metrics_path))
        self.assertTrue(os.path.exists(raw_results_path))
        
        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)
            self.assertEqual(manifest_data["random_seed"], 42)
            self.assertEqual(manifest_data["trial_count"], 1)
            self.assertIn("platform", manifest_data)
            
        with open(metrics_path, "r") as f:
            metrics_data = json.load(f)
            self.assertEqual(metrics_data["scenario_results"]["S3"]["status"], "PASS")

if __name__ == "__main__":
    unittest.main()
