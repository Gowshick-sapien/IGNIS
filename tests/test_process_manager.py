"""Unit tests for ProcessManager singleton state machine (Phase G2)."""

import os
import time
import pytest
from src.cloud_dashboard.services.process_manager import (
    ProcessManager,
    ExperimentState,
    InvalidStateTransition
)


def test_process_manager_singleton():
    pm1 = ProcessManager()
    pm2 = ProcessManager()
    assert pm1 is pm2
    assert pm1.state == ExperimentState.IDLE


def test_invalid_transitions():
    pm = ProcessManager()

    # Cannot pause/resume/stop when IDLE
    with pytest.raises(InvalidStateTransition):
        pm.pause_experiment()

    with pytest.raises(InvalidStateTransition):
        pm.resume_experiment()

    with pytest.raises(InvalidStateTransition):
        pm.stop_experiment()


def test_experiment_start_and_status():
    pm = ProcessManager()
    
    # Start small trial run (using 1 trial)
    status_info = pm.start_experiment(trials=1, seed=42, clean=True, scenarios="S1")
    assert status_info["state"] == ExperimentState.RUNNING.value
    assert status_info["pid"] is not None
    assert "exp-" in status_info["experiment_id"]

    # Starting while running should raise InvalidStateTransition
    with pytest.raises(InvalidStateTransition):
        pm.start_experiment(trials=1, seed=42, clean=True)

    # Clean up by stopping
    stop_info = pm.stop_experiment()
    assert stop_info["state"] in (ExperimentState.COMPLETED.value, ExperimentState.FAILED.value)


def test_cooperative_pause_resume():
    pm = ProcessManager()
    
    pm.start_experiment(trials=2, seed=42, clean=False, scenarios="S1")
    assert pm.state == ExperimentState.RUNNING

    # Pause
    pause_info = pm.pause_experiment()
    assert pause_info["state"] == ExperimentState.PAUSED.value
    assert os.path.exists(pm.pause_flag_file)

    # Resume
    resume_info = pm.resume_experiment()
    assert resume_info["state"] == ExperimentState.RUNNING.value
    assert not os.path.exists(pm.pause_flag_file)

    pm.stop_experiment()


def test_restart_semantics():
    pm = ProcessManager()
    
    res1 = pm.start_experiment(trials=1, seed=10, scenarios="S1")
    exp_id_1 = res1["experiment_id"]

    res2 = pm.restart_experiment(trials=1, seed=20, scenarios="S1")
    exp_id_2 = res2["experiment_id"]

    assert exp_id_1 != exp_id_2
    assert res2["state"] == ExperimentState.RUNNING.value

    pm.stop_experiment()


def test_log_tail_reading():
    pm = ProcessManager()
    lines, tail, total = pm.get_logs(tail=50)
    assert isinstance(lines, list)
    assert tail == 50
