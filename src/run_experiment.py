import os
import sys
import json
import time
import random
import logging
import argparse
import shutil

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scenarios.yaml_validator import YamlValidator
from src.scenarios.scenario_runner import ScenarioRunner
from src.metrics_collector import compute_metrics, get_git_commit, get_platform_metadata
from src.report_generator import generate_charts, generate_report

def setup_orchestrator_logger(output_dir: str):
    log_dir = os.path.join(output_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "experiment.log")
    
    logger = logging.getLogger("experiment_orchestrator")
    logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup is run multiple times
    if logger.handlers:
        logger.handlers.clear()
        
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger

def clean_outputs(output_dir: str, report_dir: str, logger):
    logger.info("Stage 2: Cleaning previous outputs...")
    
    # Clean output results directory
    if os.path.exists(output_dir):
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if item == "logs":
                for log_file in os.listdir(item_path):
                    if log_file != "experiment.log":
                        try:
                            os.remove(os.path.join(item_path, log_file))
                        except Exception:
                            pass
            elif item == "progress_events.jsonl":
                pass
            else:
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception as e:
                    logger.warning(f"Failed to remove {item_path}: {e}")
                    
    # Clean report output directory
    charts_dir = os.path.join(report_dir, "charts")
    report_file = os.path.join(report_dir, "project_results_report.md")
    
    if os.path.exists(charts_dir):
        try:
            shutil.rmtree(charts_dir)
        except Exception as e:
            logger.warning(f"Failed to remove charts directory: {e}")
            
    if os.path.exists(report_file):
        try:
            os.remove(report_file)
        except Exception as e:
            logger.warning(f"Failed to remove report file: {e}")

def run_stages():
    parser = argparse.ArgumentParser(description="IGNIS Experiment Orchestrator CLI")
    parser.add_argument("--trials", type=int, default=10, help="Number of trials per scenario")
    parser.add_argument("--scenarios", default="all", help="Comma-separated scenario IDs to run (default: all)")
    parser.add_argument("--output-dir", default="results", help="Directory for raw and computed results")
    parser.add_argument("--report-dir", default="results", help="Directory for reports and charts")
    parser.add_argument("--clean", action="store_true", help="Delete previous output files before execution")
    parser.add_argument("--skip-validation", action="store_true", help="Skip YAML schema validation")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for deterministic replay")
    parser.add_argument("--load-existing", action="store_true", help="Use existing raw_results.json instead of executing scenarios")
    
    args = parser.parse_args()
    
    # Initialize directory structure and logging
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.report_dir, exist_ok=True)
    
    logger = setup_orchestrator_logger(args.output_dir)
    
    logger.info("=========================================")
    logger.info("IGNIS Experiment Orchestrator Pipeline")
    logger.info("=========================================")
    
    pipeline_start = time.time()
    
    try:
        from src.cloud_dashboard.services.progress_reporter import ProgressReporter
        reporter = ProgressReporter(workspace_dir=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except Exception:
        reporter = None

    # Stage 1: Validate YAML Scenarios
    if reporter:
        reporter.emit_stage_progress(1, "Validating Scenarios", 2.0, "Validating YAML configurations")
    if not args.skip_validation:
        logger.info("Stage 1: Validating YAML configurations...")
        validator = YamlValidator()
        validation_results = validator.validate_all("scenarios")
        has_errors = False
        for res in validation_results:
            scenario_id = res.get("scenario_id") or "Unknown"
            if not res.get("valid"):
                logger.error(f"Scenario {scenario_id} validation failed: {res.get('errors')}")
                has_errors = True
        if has_errors:
            logger.error("Pipeline aborted due to schema validation errors.")
            sys.exit(1)
        logger.info("All scenarios passed validation schema checks.")
    else:
        logger.info("Stage 1: Skipped YAML schema validation.")

    # Stage 2: Clean outputs
    if reporter:
        reporter.emit_stage_progress(2, "Cleaning Outputs", 5.0, "Cleaning previous output files")
    if args.clean:
        clean_outputs(args.output_dir, args.report_dir, logger)
    else:
        logger.info("Stage 2: Previous outputs preserved (use --clean to purge).")

    # Stage 3: Run Scenarios
    raw_results = {}
    raw_results_path = os.path.join(args.output_dir, "raw_results.json")
    
    # Parse scenarios filter
    if args.scenarios.lower() == "all":
        target_scenarios = ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]
    else:
        target_scenarios = [s.strip().upper() for s in args.scenarios.split(",") if s.strip()]
        
    # Seeding
    seed = args.seed
    if seed is None:
        seed = random.randint(0, 2**31 - 1)
    random.seed(seed)
    logger.info(f"Using random seed: {seed}")
    
    scenarios_start_time = time.time()
    
    if args.load_existing:
        logger.info(f"Stage 3: Loading existing raw results from {raw_results_path}...")
        if not os.path.exists(raw_results_path):
            logger.error(f"Cannot load existing results: {raw_results_path} not found.")
            sys.exit(1)
        with open(raw_results_path, "r", encoding="utf-8") as f:
            raw_results = json.load(f)
    else:
        logger.info(f"Stage 3: Running scenarios {target_scenarios} for {args.trials} trials...")
        runner = ScenarioRunner(mqtt_host="localhost", mqtt_port=1883)
        total_scenarios_count = len(target_scenarios)

        for s_idx, sid in enumerate(target_scenarios, start=1):
            if reporter:
                reporter.emit_scenario_started(sid, s_idx, total_scenarios_count)

            def on_trial(trial_num, total_t, res):
                elapsed = time.time() - scenarios_start_time
                completed_trials_so_far = (s_idx - 1) * args.trials + trial_num
                total_trials_overall = total_scenarios_count * args.trials
                trial_prog_pct = (completed_trials_so_far / total_trials_overall) * 100.0
                pipeline_prog_pct = 5.0 + (completed_trials_so_far / total_trials_overall) * 65.0
                eta = (elapsed / (trial_prog_pct / 100.0) - elapsed) if trial_prog_pct > 0 else 0.0
                
                if reporter:
                    reporter.emit_trial_progress(
                        scenario_id=sid,
                        trial=trial_num,
                        total_trials=args.trials,
                        scenario_index=s_idx,
                        total_scenarios=total_scenarios_count,
                        elapsed_sec=elapsed,
                        progress_pct=pipeline_prog_pct,
                        eta_sec=max(0.0, eta)
                    )

            try:
                logger.info(f"Running scenario {sid}...")
                results = runner.run_scenario(sid, trials=args.trials, seed=seed, callback=on_trial)
                import dataclasses
                raw_results[sid] = [dataclasses.asdict(r) for r in results]
                
                elapsed = time.time() - scenarios_start_time
                if reporter:
                    reporter.emit_scenario_complete(
                        scenario_id=sid,
                        status="PASS" if len(results) > 0 else "INVALID",
                        duration_sec=elapsed
                    )
            except Exception as e:
                logger.error(f"Failed execution of scenario {sid}: {e}")
                raw_results[sid] = []
                if reporter:
                    reporter.emit_scenario_complete(sid, "INVALID", 0.0, {"error": str(e)})

        # Write raw_results.json
        with open(raw_results_path, "w", encoding="utf-8") as f:
            json.dump(raw_results, f, indent=2)
        logger.info(f"Raw scenario outcomes written to {raw_results_path}")
        
    scenarios_duration = time.time() - scenarios_start_time

    # Stage 4: Verify completeness
    logger.info("Stage 4: Verifying completeness of trials...")
    completeness_warnings = []
    for sid in target_scenarios:
        trials_list = raw_results.get(sid, [])
        if not trials_list:
            logger.warning(f"Scenario {sid} is missing from the outcomes or generated 0 trials.")
            completeness_warnings.append(sid)
        else:
            empty_trials = [t for t in trials_list if not t.get("events")]
            if len(empty_trials) == len(trials_list):
                logger.warning(f"Scenario {sid} was executed but recorded 0 event messages across all trials.")
                
    # Stage 5: Compute Metrics
    if reporter:
        reporter.emit_stage_progress(5, "Computing Metrics & Assertions", 75.0, "Computing Section 7 experiment metrics")
    logger.info("Stage 5: Computing statistics aggregates and asserting rules...")
    metrics = compute_metrics(raw_results)
    
    # Inject active execution parameters into metadata
    exp_id = os.environ.get("IGNIS_EXPERIMENT_ID", "")
    if exp_id:
        metrics["experiment_metadata"]["experiment_id"] = exp_id
    metrics["experiment_metadata"]["random_seed"] = seed
    metrics["experiment_metadata"]["total_duration_sec"] = round(scenarios_duration, 4)
    
    metrics_path = os.path.join(args.output_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Computed metrics written to {metrics_path}")

    # Stage 6: Generate Charts (Best Effort)
    if reporter:
        reporter.emit_stage_progress(6, "Generating Matplotlib Charts", 85.0, "Generating publication-ready Matplotlib charts")
    logger.info("Stage 6: Generating publication-ready Matplotlib charts...")
    charts_dir = os.path.join(args.report_dir, "charts")
    try:
        generate_charts(metrics, charts_dir)
        logger.info(f"Matplotlib charts generated under {charts_dir}")
    except Exception as e:
        logger.error(f"Failed to generate charts: {e}")

    # Stage 7: Generate Manifest
    if reporter:
        reporter.emit_stage_progress(7, "Generating Experiment Manifest", 90.0, "Generating experiment manifest metadata")
    logger.info("Stage 7: Generating experiment manifest metadata...")
    validator = YamlValidator()
    
    report_file = os.path.join(args.output_dir, "report.md")
    output_files = [
        os.path.join(args.output_dir, "raw_results.json"),
        os.path.join(args.output_dir, "metrics.json"),
        os.path.join(args.output_dir, "experiment_manifest.json"),
        os.path.join(args.output_dir, "logs/experiment.log")
    ]
    if os.path.exists(report_file):
        output_files.append(report_file)
    if os.path.exists(charts_dir):
        output_files.append(os.path.join(charts_dir, "*.png"))
        
    manifest = {
        "experiment_id": exp_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": get_git_commit(),
        "trial_count": args.trials if not args.load_existing else metrics["experiment_metadata"].get("trial_count", 0),
        "random_seed": seed,
        "execution_duration_sec": round(time.time() - pipeline_start, 4),
        "ci_method": metrics["experiment_metadata"].get("ci_method", "internal_t_table"),
        "platform": get_platform_metadata(),
        "scenarios_executed": target_scenarios,
        "scenario_versions": metrics["experiment_metadata"].get("scenario_versions", {}),
        "scenario_checksums": validator.checksum_all("scenarios"),
        "container_images": {
            "fog-node": "python:3.11-slim",
            "edge-sim": "python:3.11-slim",
            "mqtt-broker": "eclipse-mosquitto:2",
            "influxdb": "influxdb:2.7"
        },
        "output_files": output_files
    }
    
    manifest_path = os.path.join(args.output_dir, "experiment_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Experiment manifest successfully generated at {manifest_path}")

    # Stage 8: Generate Reports (Best Effort)
    if reporter:
        reporter.emit_stage_progress(8, "Compiling Summary Reports", 95.0, "Compiling Markdown and interactive HTML reports")
    logger.info("Stage 8: Compiling final summary reports...")
    try:
        generate_report(metrics, report_file)
        logger.info(f"Final project summary report compiled at {report_file}")
    except Exception as e:
        logger.error(f"Failed to compile report: {e}")

    try:
        from src.cloud_dashboard.reporting import generate_html_report
        html_out = os.path.join(args.output_dir, "report.html")
        raw_path = os.path.join(args.output_dir, "raw_results.json")
        generate_html_report(
            metrics_path=metrics_path,
            raw_results_path=raw_path,
            manifest_path=manifest_path,
            output_path=html_out
        )
        logger.info(f"Interactive self-contained HTML report generated at {html_out}")
    except Exception as e:
        logger.warning(f"Could not generate interactive HTML report: {e}")

    # Stage 9: Summary Table
    if reporter:
        reporter.emit_stage_progress(9, "Pipeline Completed", 100.0, "Pipeline completed successfully")
    logger.info("Stage 9: Pipeline completed. Summary Results:")
    logger.info("-" * 80)
    logger.info(f"{'Scenario':<12} | {'Trials':<8} | {'Status':<10} | {'Reason'}")
    logger.info("-" * 80)
    for sid in target_scenarios:
        res = metrics["scenario_results"].get(sid, {})
        status = res.get("status", "INCOMPLETE")
        trials_count = res.get("trials", 0)
        reason = res.get("reason", "No results calculated.")
        logger.info(f"{sid:<12} | {trials_count:<8} | {status:<10} | {reason}")
    logger.info("-" * 80)
    logger.info(f"Overall Pipeline Execution Verdict: {metrics['summary'].get('overall_verdict', 'INCOMPLETE')}")
    logger.info(f"Total Pipeline Execution Time: {round(time.time() - pipeline_start, 2)}s")

if __name__ == "__main__":
    run_stages()
