"""IGNIS Structured Progress Reporter (Phase G3).

Emits typed JSON progress events to an in-memory asyncio.Queue and appends to results/progress_events.jsonl.
"""

import os
import json
import logging
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger("progress_reporter")


class ProgressReporter:
    """Structured progress reporter producing standardized, versioned progress events."""

    def __init__(self, workspace_dir: Optional[str] = None, main_event_queue: Optional[asyncio.Queue] = None):
        self.workspace_dir = os.path.abspath(workspace_dir or os.getcwd())
        self.results_dir = os.path.join(self.workspace_dir, "results")
        self.jsonl_path = os.path.join(self.results_dir, "progress_events.jsonl")
        self.main_event_queue = main_event_queue
        
        self._sequence = 0
        self._experiment_id: Optional[str] = None
        self._lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    def set_event_queue(self, queue: asyncio.Queue, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Assign or update shared asyncio event queue."""
        self.main_event_queue = queue
        if loop:
            self._loop = loop

    def reset(self, experiment_id: str) -> None:
        """Reset sequence counter for a new experiment."""
        with self._lock:
            self._sequence = 0
            self._experiment_id = experiment_id
            os.makedirs(self.results_dir, exist_ok=True)
            # Truncate / recreate progress_events.jsonl for new experiment
            try:
                with open(self.jsonl_path, "w", encoding="utf-8") as f:
                    pass
            except Exception as e:
                logger.warning(f"Could not truncate progress_events.jsonl: {e}")

    def _next_event_meta(self, event_type: str) -> Dict[str, Any]:
        with self._lock:
            self._sequence += 1
            seq = self._sequence
            exp_id = self._experiment_id or "exp-unknown"
            evt_id = f"{exp_id}-{seq:06d}"
            ts = datetime.now(timezone.utc).isoformat()
            return {
                "schema_version": "1.0",
                "event": event_type,
                "event_id": evt_id,
                "sequence": seq,
                "experiment_id": exp_id,
                "timestamp": ts
            }

    def _emit(self, event_payload: Dict[str, Any]) -> None:
        """Appends event to jsonl file and puts it onto the shared asyncio queue."""
        # 1. Append to results/progress_events.jsonl
        try:
            os.makedirs(self.results_dir, exist_ok=True)
            with open(self.jsonl_path, "a", encoding="utf-8", buffering=1) as f:
                f.write(json.dumps(event_payload) + "\n")
                f.flush()
        except Exception as e:
            logger.error(f"Failed writing event to progress_events.jsonl: {e}")

        # 2. Put on asyncio queue for real-time SSE broadcasting
        if self.main_event_queue is not None:
            try:
                self.main_event_queue.put_nowait(event_payload)
            except Exception as e:
                logger.debug(f"Could not put event onto queue: {e}")

    def _safe_queue_put(self, payload: Dict[str, Any]) -> None:
        if self.main_event_queue is not None:
            try:
                self.main_event_queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("Main event queue full, dropping progress event.")
            except Exception as e:
                logger.debug(f"Queue put exception: {e}")

    def emit_experiment_started(self, experiment_id: str, config: Dict[str, Any], total_scenarios: int, total_trials: int) -> Dict[str, Any]:
        self.reset(experiment_id)
        meta = self._next_event_meta("EXPERIMENT_STARTED")
        meta.update({
            "config": config,
            "total_scenarios": total_scenarios,
            "total_trials": total_trials
        })
        self._emit(meta)
        return meta

    def emit_scenario_started(self, scenario_id: str, scenario_index: int, total_scenarios: int) -> Dict[str, Any]:
        meta = self._next_event_meta("SCENARIO_STARTED")
        meta.update({
            "scenario_id": scenario_id,
            "scenario_index": scenario_index,
            "total_scenarios": total_scenarios
        })
        self._emit(meta)
        return meta

    def emit_trial_progress(self, scenario_id: str, trial: int, total_trials: int, scenario_index: int, total_scenarios: int, elapsed_sec: float, progress_pct: float, eta_sec: float) -> Dict[str, Any]:
        meta = self._next_event_meta("TRIAL_PROGRESS")
        meta.update({
            "scenario_id": scenario_id,
            "trial": trial,
            "total_trials": total_trials,
            "scenario_index": scenario_index,
            "total_scenarios": total_scenarios,
            "elapsed_sec": round(elapsed_sec, 2),
            "progress_pct": round(progress_pct, 1),
            "eta_sec": round(eta_sec, 1)
        })
        self._emit(meta)
        return meta

    def emit_scenario_complete(self, scenario_id: str, status: str, duration_sec: float, metrics: Dict[str, Any] = None) -> Dict[str, Any]:
        meta = self._next_event_meta("SCENARIO_COMPLETE")
        meta.update({
            "scenario_id": scenario_id,
            "status": status,
            "duration_sec": round(duration_sec, 2),
            "metrics": metrics or {}
        })
        self._emit(meta)
        return meta

    def emit_experiment_complete(self, overall_verdict: str, duration_sec: float, summary_stats: Dict[str, Any] = None) -> Dict[str, Any]:
        meta = self._next_event_meta("EXPERIMENT_COMPLETE")
        meta.update({
            "overall_verdict": overall_verdict,
            "duration_sec": round(duration_sec, 2),
            "summary_stats": summary_stats or {}
        })
        self._emit(meta)
        return meta

    def emit_experiment_failed(self, error_code: str, error_message: str, failed_at_scenario: Optional[str] = None) -> Dict[str, Any]:
        meta = self._next_event_meta("EXPERIMENT_FAILED")
        meta.update({
            "error_code": error_code,
            "error_message": error_message,
            "failed_at_scenario": failed_at_scenario
        })
        self._emit(meta)
        return meta

    def emit_stage_progress(self, stage_num: int, stage_name: str, progress_pct: float, message: str = "") -> Dict[str, Any]:
        meta = self._next_event_meta("STAGE_PROGRESS")
        meta.update({
            "stage_num": stage_num,
            "stage_name": stage_name,
            "progress_pct": round(progress_pct, 1),
            "message": message
        })
        self._emit(meta)
        return meta
