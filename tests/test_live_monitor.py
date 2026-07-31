"""Unit tests for LiveMonitor SSE broadcaster (Phase G3)."""

import os
import json
import asyncio
import pytest
from src.cloud_dashboard.services.live_monitor import LiveMonitor


def test_live_monitor_registration_and_fanout():
    monitor = LiveMonitor()
    q1 = monitor.register_client(maxsize=100)
    q2 = monitor.register_client(maxsize=100)
    
    evt = {"schema_version": "1.0", "event": "TRIAL_PROGRESS", "event_id": "test-1", "sequence": 1}
    monitor.broadcast_event(evt)

    assert not q1.empty()
    assert not q2.empty()

    assert q1.get_nowait() == evt
    assert q2.get_nowait() == evt

    monitor.unregister_client(q1)
    monitor.unregister_client(q2)


def test_heartbeat_payload():
    monitor = LiveMonitor()
    hb = monitor.get_heartbeat_payload()
    assert hb["schema_version"] == "1.0"
    assert hb["event"] == "HEARTBEAT"
    assert "timestamp" in hb


def test_active_experiment_replay(tmp_path):
    workspace = str(tmp_path)
    results_dir = os.path.join(workspace, "results")
    os.makedirs(results_dir, exist_ok=True)
    jsonl_path = os.path.join(results_dir, "progress_events.jsonl")

    events = [
        {"experiment_id": "exp-old", "event": "EXPERIMENT_STARTED", "sequence": 1},
        {"experiment_id": "exp-active", "event": "EXPERIMENT_STARTED", "sequence": 1},
        {"experiment_id": "exp-active", "event": "TRIAL_PROGRESS", "sequence": 2},
    ]

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    monitor = LiveMonitor(workspace_dir=workspace)
    q = monitor.register_client()

    replayed = monitor.replay_active_experiment(q, "exp-active")
    assert replayed == 2

    e1 = q.get_nowait()
    e2 = q.get_nowait()
    assert e1["experiment_id"] == "exp-active"
    assert e2["experiment_id"] == "exp-active"

    monitor.unregister_client(q)
