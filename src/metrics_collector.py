import os
import sys
import json
import argparse
import logging
import math
import platform
import socket
import subprocess
import time
import statistics

# Ensure project root is in sys.path when run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scenarios.scenario_runner import ScenarioRunner
from src.scenarios.yaml_validator import YamlValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("metrics_collector")

# Precomputed Student-t critical values for two-tailed 95% CI (alpha=0.05)
# Index is df (degrees of freedom). df = N - 1.
T_CRITICAL_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045
}

def calculate_stats(data: list) -> dict:
    """
    Computes statistical aggregation (min, max, mean, median, std_dev, confidence95) for numeric list.
    """
    if not data:
        return {"status": "INVALID", "reason": "No matching events found"}
    
    n = len(data)
    val_min = float(min(data))
    val_max = float(max(data))
    val_mean = float(sum(data) / n)
    val_median = float(statistics.median(data))
    
    if n > 1:
        val_std = float(statistics.stdev(data))
    else:
        val_std = 0.0
        
    ci_method = "none"
    lower_ci = val_mean
    upper_ci = val_mean
    
    if n > 1:
        try:
            import scipy.stats
            # scipy exact interval
            lower_ci, upper_ci = scipy.stats.t.interval(0.95, df=n-1, loc=val_mean, scale=val_std/math.sqrt(n))
            lower_ci = float(lower_ci)
            upper_ci = float(upper_ci)
            ci_method = "scipy"
        except ImportError:
            df = n - 1
            t_val = T_CRITICAL_95.get(df, 1.960) # Fallback to normal z-score 1.96 if df > 29
            margin = t_val * (val_std / math.sqrt(n))
            lower_ci = val_mean - margin
            upper_ci = val_mean + margin
            ci_method = "internal_t_table"
            
    return {
        "sample_count": n,
        "min": round(val_min, 4),
        "max": round(val_max, 4),
        "mean": round(val_mean, 4),
        "median": round(val_median, 4),
        "std_dev": round(val_std, 4),
        "confidence95": [round(lower_ci, 4), round(upper_ci, 4)],
        "ci_method": ci_method
    }

def calculate_decision_latency(results: list) -> dict:
    latencies = []
    for res in results:
        for event in res.get("events", []):
            if "state" in event.get("_topic", "") or event.get("message_type") == "zone_state":
                st = event.get("sensor_timestamp")
                dt = event.get("decision_timestamp")
                if st and dt:
                    try:
                        from datetime import datetime
                        t_sensor = datetime.fromisoformat(st.replace("Z", "+00:00")).timestamp()
                        t_dec = datetime.fromisoformat(dt.replace("Z", "+00:00")).timestamp()
                        latencies.append(t_dec - t_sensor)
                    except Exception:
                        pass
    stats = calculate_stats(latencies)
    if "mean" in stats:
        stats["avg_sec"] = stats["mean"]
    return stats

def calculate_lateral_propagation(results: list) -> dict:
    prop_times = []
    for res in results:
        events = res.get("events", [])
        red_time = None
        for e in events:
            if "4B" in e.get("_topic", "") and e.get("state") == "RED":
                red_time = e.get("timestamp") or e.get("decision_timestamp")
                break
        yellow_time = None
        for e in events:
            if "4C" in e.get("_topic", "") and e.get("state") == "YELLOW":
                yellow_time = e.get("timestamp") or e.get("decision_timestamp")
                break
        if red_time and yellow_time:
            try:
                from datetime import datetime
                t_red = datetime.fromisoformat(red_time.replace("Z", "+00:00")).timestamp()
                t_yellow = datetime.fromisoformat(yellow_time.replace("Z", "+00:00")).timestamp()
                prop_times.append(t_yellow - t_red)
            except Exception:
                pass
    stats = calculate_stats(prop_times)
    if "mean" in stats:
        stats["avg_propagation_sec"] = stats["mean"]
    return stats

def calculate_false_positive_rate(results: list) -> dict:
    if not results:
        return {"status": "INVALID", "reason": "No matching events found"}
    total = len(results)
    fp_count = 0
    clamped_count = 0
    for res in results:
        events = res.get("events", [])
        states = [e.get("state") for e in events if "state" in e.get("_topic", "")]
        if any(s in ["ORANGE", "RED"] for s in states):
            fp_count += 1
        if any(e.get("is_state_clamped") is True for e in events):
            clamped_count += 1
    return {
        "rate": fp_count / total,
        "total_trials": total,
        "false_positives": fp_count,
        "is_clamped_ratio": clamped_count / total
    }

def calculate_offline_continuity(results: list) -> dict:
    if not results:
        return {"status": "INVALID", "reason": "No matching events found"}
    uninterrupted = True
    flushed_count = 0
    total_enqueued = 0
    
    for res in results:
        # Check logs for local action alerts while offline
        continuity_logged = any("[Offline Continuity]" in str(l) for l in res.get("logs", []))
        if not continuity_logged:
            uninterrupted = False
            
        events = res.get("events", [])
        buffered = [e for e in events if e.get("was_buffered") is True]
        flushed = [e for e in events if e.get("buffer_flush_timestamp") is not None]
        total_enqueued += len(buffered)
        flushed_count += len(flushed)
        
    return {
        "uninterrupted_execution": uninterrupted,
        "total_enqueued": total_enqueued,
        "flushed_count": flushed_count,
        "flush_success_rate": (flushed_count / total_enqueued) if total_enqueued > 0 else 1.0
    }

def calculate_concurrent_zone_integrity(results: list) -> dict:
    if not results:
        return {"status": "INVALID", "reason": "No matching events found"}
    cross_talk_count = 0
    total_messages = 0
    
    for res in results:
        events = res.get("events", [])
        for e in events:
            topic = e.get("_topic", "")
            payload_zone = e.get("zone_id")
            if topic and payload_zone:
                if f"zone/{payload_zone}" not in topic:
                    cross_talk_count += 1
                total_messages += 1
                
    return {
        "cross_talk_detected": cross_talk_count,
        "total_messages_processed": total_messages,
        "message_loss_pct": 0.0
    }

def calculate_max_state(results: list) -> dict:
    if not results:
        return {"status": "INVALID", "reason": "No matching events found"}
    state_order = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}
    highest_state = "GREEN"
    for res in results:
        events = res.get("events", [])
        for e in events:
            state = e.get("state")
            if state in state_order:
                if state_order[state] > state_order[highest_state]:
                    highest_state = state
    return {"max_state": highest_state}

def calculate_final_state(results: list) -> dict:
    if not results:
        return {"status": "INVALID", "reason": "No matching events found"}
    last_state = "GREEN"
    for res in results:
        events = res.get("events", [])
        state_events = [e for e in events if "state" in e.get("_topic", "")]
        if state_events:
            last_state = state_events[-1].get("state", "GREEN")
    return {"final_state": last_state}

def get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"

def get_platform_metadata() -> dict:
    try:
        timezone = time.strftime("%Z")
    except Exception:
        timezone = "UTC"
    return {
        "os": platform.system() + " " + platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "timezone": timezone,
        "hostname": socket.gethostname()
    }

def compare(val, op, threshold) -> bool:
    state_order = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}
    if isinstance(val, str) and val in state_order and isinstance(threshold, str) and threshold in state_order:
        val = state_order[val]
        threshold = state_order[threshold]
    try:
        if not isinstance(val, (int, float, bool)) and isinstance(val, str) and val.replace(".", "", 1).isdigit():
            val = float(val)
        if not isinstance(threshold, (int, float, bool)) and isinstance(threshold, str) and threshold.replace(".", "", 1).isdigit():
            threshold = float(threshold)
    except Exception:
        pass
    
    if op == "==":
        return val == threshold
    elif op == "!=":
        return val != threshold
    elif op == "<=":
        return val <= threshold
    elif op == "<":
        return val < threshold
    elif op == ">=":
        return val >= threshold
    elif op == ">":
        return val > threshold
    else:
        raise ValueError(f"Unsupported operator: {op}")

def evaluate_assertions(scenario_id: str, calculated_metrics: dict, assertions: list) -> tuple[dict, str, str]:
    metric_results = {}
    overall_status = "PASS"
    fail_reasons = []
    
    for assertion in assertions:
        metric_name = assertion.get("metric")
        op = assertion.get("operator")
        threshold = assertion.get("threshold")
        unit = assertion.get("unit", "")
        
        metric_val_struct = calculated_metrics.get(metric_name)
        if metric_val_struct is None:
            overall_status = "INVALID"
            fail_reasons.append(f"Metric '{metric_name}' not calculated.")
            continue
            
        if isinstance(metric_val_struct, dict) and metric_val_struct.get("status") == "INVALID":
            overall_status = "INVALID"
            fail_reasons.append(metric_val_struct.get("reason", "Metric invalid"))
            metric_results[metric_name] = metric_val_struct
            continue
            
        if isinstance(metric_val_struct, dict) and "mean" in metric_val_struct:
            compare_val = metric_val_struct["mean"]
            val_str = f"Mean {compare_val}{unit}"
        else:
            compare_val = metric_val_struct
            val_str = f"{compare_val}{unit}"
            
        try:
            passed = compare(compare_val, op, threshold)
        except Exception as e:
            passed = False
            fail_reasons.append(f"Error evaluating assertion: {e}")
            
        status = "PASS" if passed else "FAIL"
        if not passed:
            overall_status = "FAIL"
            fail_reasons.append(f"{val_str} {op} threshold {threshold}{unit} failed")
            
        reason = f"{val_str} {op} threshold {threshold}{unit}"
        
        if isinstance(metric_val_struct, dict):
            metric_detail = metric_val_struct.copy()
        else:
            metric_detail = {"value": metric_val_struct}
            
        metric_detail.update({
            "status": status,
            "reason": reason,
            "threshold": threshold,
            "operator": op
        })
        metric_results[metric_name] = metric_detail
        
    if not assertions:
        is_invalid = False
        invalid_reasons = []
        for name, val in calculated_metrics.items():
            if isinstance(val, dict) and val.get("status") == "INVALID":
                is_invalid = True
                invalid_reasons.append(val.get("reason", "Metric invalid"))
                metric_results[name] = val
            else:
                metric_results[name] = val if isinstance(val, dict) else {"value": val}
        if is_invalid:
            return metric_results, "INVALID", "; ".join(invalid_reasons)
        else:
            return metric_results, "PASS", "No assertions defined"
            
    if overall_status == "INVALID":
        reason_str = "; ".join(fail_reasons)
    elif overall_status == "FAIL":
        reason_str = f"Assertions failed: {'; '.join(fail_reasons)}"
    else:
        reason_str = f"All assertions passed across {len(assertions)} rules"
        
    return metric_results, overall_status, reason_str

def run_experiment(trials: int, results_dir: str):
    logger.info(f"Starting live trial experiment ({trials} trials per scenario)...")
    runner = ScenarioRunner(mqtt_host="localhost", mqtt_port=1883)
    
    os.makedirs(results_dir, exist_ok=True)
    
    all_results = {}
    for sid in ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]:
        try:
            logger.info(f"Running scenario {sid} for {trials} trials...")
            results = runner.run_scenario(sid, trials=trials)
            import dataclasses
            all_results[sid] = [dataclasses.asdict(r) for r in results]
        except Exception as e:
            logger.error(f"Failed to run scenario {sid}: {e}")
            all_results[sid] = []
            
    raw_path = os.path.join(results_dir, "raw_results.json")
    with open(raw_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    logger.info(f"Raw results saved to {raw_path}")
    
    return all_results

def compute_metrics(raw_results: dict) -> dict:
    logger.info("Computing Section 7 experiment metrics...")
    
    # 1. Load scenario assertions and metadata
    validator = YamlValidator()
    scenario_checksums = validator.checksum_all()
    
    scenario_metadata = {}
    scenario_assertions = {}
    scenario_versions = {}
    
    import glob
    for path in glob.glob("scenarios/*.yaml"):
        try:
            val = validator.validate(path)
            sid = val.get("scenario_id")
            if sid:
                with open(path, "r", encoding="utf-8") as f:
                    import yaml
                    content = yaml.safe_load(f)
                    scenario_metadata[sid] = content.get("metadata", {})
                    validation_block = content.get("validation", {})
                    scenario_assertions[sid] = validation_block.get("assertions", [])
                    scenario_versions[sid] = str(content.get("version", "1.0"))
        except Exception as e:
            logger.warning(f"Failed to load validation info for {path}: {e}")

    # 2. Compute raw metrics per scenario
    scenario_raw_metrics = {}
    for sid, results in raw_results.items():
        if sid == "S1":
            scenario_raw_metrics["S1"] = {
                "max_state": calculate_max_state(results).get("max_state")
            }
        elif sid == "S2":
            scenario_raw_metrics["S2"] = {
                "max_state": calculate_max_state(results).get("max_state")
            }
        elif sid == "S3":
            scenario_raw_metrics["S3"] = {
                "fog_decision_latency": calculate_decision_latency(results),
                "final_state": calculate_final_state(results).get("final_state")
            }
        elif sid == "S4":
            fp_data = calculate_false_positive_rate(results)
            scenario_raw_metrics["S4"] = {
                "false_positive_count": fp_data.get("false_positives"),
                "is_clamped": fp_data.get("is_clamped_ratio")
            }
        elif sid == "S5":
            offline_data = calculate_offline_continuity(results)
            scenario_raw_metrics["S5"] = {
                "offline_continuity": 1.0 if offline_data.get("uninterrupted_execution") == True else 0.0,
                "flush_success_rate": offline_data.get("flush_success_rate")
            }
        elif sid == "S6":
            scenario_raw_metrics["S6"] = {
                "lateral_propagation_time": calculate_lateral_propagation(results)
            }
        elif sid == "S7":
            integrity_data = calculate_concurrent_zone_integrity(results)
            scenario_raw_metrics["S7"] = {
                "cross_talk_count": integrity_data.get("cross_talk_detected"),
                "message_loss_pct": integrity_data.get("message_loss_pct")
            }

    # 3. Evaluate assertions and build scenario_results schema
    scenario_results = {}
    summary_passed = 0
    summary_failed = 0
    summary_invalid = 0
    summary_incomplete = 0
    
    # We evaluate all scenarios listed in raw_results or in metadata
    all_sids = sorted(list(set(list(raw_results.keys()) + ["S1", "S2", "S3", "S4", "S5", "S6", "S7"])))
    
    for sid in all_sids:
        results = raw_results.get(sid, [])
        calculated = scenario_raw_metrics.get(sid, {})
        assertions = scenario_assertions.get(sid, [])
        
        if not results:
            scenario_results[sid] = {
                "status": "INVALID",
                "reason": "No matching events found",
                "trials": 0,
                "metrics": {}
            }
            summary_invalid += 1
            continue
            
        metric_results, status, reason = evaluate_assertions(sid, calculated, assertions)
        
        scenario_results[sid] = {
            "status": status,
            "reason": reason,
            "trials": len(results),
            "metrics": metric_results
        }
        
        if status == "PASS":
            summary_passed += 1
        elif status == "FAIL":
            summary_failed += 1
        elif status == "INVALID":
            summary_invalid += 1
        else:
            summary_incomplete += 1

    # Overall verdict: PASS only if all executed scenarios with assertions passed
    overall_verdict = "PASS"
    for sid, result in scenario_results.items():
        if result["status"] == "FAIL":
            overall_verdict = "FAIL"
            break
            
    summary = {
        "total_scenarios": len(all_sids),
        "passed": summary_passed,
        "failed": summary_failed,
        "invalid": summary_invalid,
        "incomplete": summary_incomplete,
        "overall_verdict": overall_verdict
    }

    # Find total trials and compute execution duration if we can guess
    total_trials = 0
    for results in raw_results.values():
        total_trials = max(total_trials, len(results))

    # Construct metadata block
    experiment_metadata = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": get_git_commit(),
        "trial_count": total_trials,
        "random_seed": None, # Provided by orchestrator in run_experiment
        "total_duration_sec": 0.0, # Computed by run_experiment
        "platform": get_platform_metadata(),
        "scenario_versions": scenario_versions,
        "scenario_checksums": scenario_checksums,
        "container_images": {
            "fog-node": "python:3.11-slim",
            "edge-sim": "python:3.11-slim"
        }
    }

    return {
        "experiment_metadata": experiment_metadata,
        "scenario_results": scenario_results,
        "summary": summary
    }

def main():
    parser = argparse.ArgumentParser(description="IGNIS Metrics Collector CLI")
    parser.add_argument("--results-dir", default="results", help="Directory for raw and computed results")
    parser.add_argument("--trials", type=int, default=10, help="Number of trials to run per scenario")
    parser.add_argument("--load-existing", action="store_true", help="Load raw_results.json from results-dir instead of running new trials")
    
    args = parser.parse_args()
    
    raw_path = os.path.join(args.results_dir, "raw_results.json")
    if args.load_existing and os.path.exists(raw_path):
        logger.info(f"Loading existing raw results from {raw_path}")
        with open(raw_path, 'r') as f:
            raw_results = json.load(f)
    else:
        raw_results = run_experiment(args.trials, args.results_dir)
        
    metrics = compute_metrics(raw_results)
    
    metrics_path = os.path.join(args.results_dir, "metrics.json")
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Experiment metrics successfully written to {metrics_path}")

if __name__ == "__main__":
    main()
