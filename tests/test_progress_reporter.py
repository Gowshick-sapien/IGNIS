"""Unit tests for ProgressReporter structured event emission (Phase G3)."""

import os
import json
import asyncio
import pytest
from src.cloud_dashboard.services.progress_reporter import ProgressReporter


def test_progress_reporter_event_structure():
    reporter = ProgressReporter()
    reporter.reset("exp-20260731T140000Z-test")
    
    evt = reporter.emit_scenario_started(scenario_id="S3", scenario_index=3, total_scenarios=7)
    
    assert evt["schema_version"] == "1.0"
    assert evt["event"] == "SCENARIO_STARTED"
    assert evt["sequence"] == 1
    assert evt["event_id"] == "exp-20260731T140000Z-test-000001"
    assert evt["experiment_id"] == "exp-20260731T140000Z-test"
    assert evt["scenario_id"] == "S3"
    assert evt["scenario_index"] == 3
    assert evt["total_scenarios"] == 7
    assert "timestamp" in evt


def test_progress_reporter_jsonl_persistence(tmp_path):
    workspace = str(tmp_path)
    reporter = ProgressReporter(workspace_dir=workspace)
    reporter.reset("exp-jsonl-test")

    reporter.emit_experiment_started(
        experiment_id="exp-jsonl-test",
        config={"trials": 10},
        total_scenarios=7,
        total_trials=10
    )
    reporter.emit_trial_progress(
        scenario_id="S1",
        trial=1,
        total_trials=10,
        scenario_index=1,
        total_scenarios=7,
        elapsed_sec=1.5,
        progress_pct=1.4,
        eta_sec=100.0
    )

    jsonl_file = os.path.join(workspace, "results", "progress_events.jsonl")
    assert os.path.exists(jsonl_file)

    with open(jsonl_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    assert len(lines) == 2
    data1 = json.loads(lines[0])
    data2 = json.loads(lines[1])

    assert data1["event"] == "EXPERIMENT_STARTED"
    assert data1["sequence"] == 1
    assert data2["event"] == "TRIAL_PROGRESS"
    assert data2["sequence"] == 2


@pytest.mark.asyncio
async def test_progress_reporter_queue_emission():
    queue = asyncio.Queue()
    reporter = ProgressReporter(main_event_queue=queue)
    reporter.reset("exp-queue-test")

    reporter.emit_scenario_started("S4", 4, 7)

    assert not queue.empty()
    evt = queue.get_nowait()
    assert evt["event"] == "SCENARIO_STARTED"
    assert evt["scenario_id"] == "S4"
