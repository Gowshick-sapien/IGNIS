"""IGNIS Process Lifecycle Manager (Phase G2).

Subprocess lifecycle state machine managing run_experiment.py execution, logging, PID tracking, and Windows cooperative pause/resume capabilities.
"""

import os
import sys
import time
import uuid
import shutil
import logging
import threading
import subprocess
from enum import Enum
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("process_manager")


class ExperimentState(str, Enum):
    IDLE = "IDLE"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class InvalidStateTransition(Exception):
    """Raised when an illegal state transition is requested."""
    pass


class ProcessManager:
    """Singleton manager controlling the lifecycle of experiment executions."""
    
    _instance: Optional["ProcessManager"] = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super(ProcessManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, workspace_dir: Optional[str] = None):
        if getattr(self, "_initialized", False):
            return
        
        self.workspace_dir = os.path.abspath(workspace_dir or os.getcwd())
        self.pause_flag_file = os.path.join(self.workspace_dir, ".pause_flag")
        self.results_dir = os.path.join(self.workspace_dir, "results")
        self.logs_dir = os.path.join(self.results_dir, "logs")
        self.log_file_path = os.path.join(self.logs_dir, "experiment.log")
        
        self._state = ExperimentState.IDLE
        self._process: Optional[subprocess.Popen] = None
        self._experiment_id: Optional[str] = None
        self._pid: Optional[int] = None
        self._start_time: Optional[str] = None
        self._config: Dict[str, Any] = {}
        self._lock = threading.Lock()
        
        self._initialized = True
        logger.info(f"ProcessManager singleton initialized. Workspace: {self.workspace_dir}")

    @property
    def state(self) -> ExperimentState:
        with self._lock:
            self._update_process_status_locked()
            return self._state

    def _update_process_status_locked(self) -> None:
        """Internal helper to poll process status and handle async exit transitions."""
        if self._process is not None:
            poll_res = self._process.poll()
            if poll_res is not None:
                # Subprocess exited
                if self._state in (ExperimentState.RUNNING, ExperimentState.PAUSING, ExperimentState.PAUSED, ExperimentState.STOPPING, ExperimentState.STARTING):
                    if poll_res == 0:
                        self._state = ExperimentState.COMPLETED
                        logger.info(f"Subprocess for {self._experiment_id} completed successfully (exit 0).")
                    else:
                        self._state = ExperimentState.FAILED
                        logger.error(f"Subprocess for {self._experiment_id} failed with exit code {poll_res}.")
                self._process = None

    def _generate_experiment_id(self) -> str:
        now_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        hex_suffix = uuid.uuid4().hex[:4]
        return f"exp-{now_str}-{hex_suffix}"

    def start_experiment(self, trials: int = 30, seed: int = 4321, clean: bool = True, scenarios: str = "all") -> Dict[str, Any]:
        with self._lock:
            self._update_process_status_locked()
            if self._state in (ExperimentState.RUNNING, ExperimentState.STARTING, ExperimentState.PAUSING, ExperimentState.PAUSED, ExperimentState.STOPPING):
                raise InvalidStateTransition(f"Cannot start experiment: Current state is {self._state.value}")
            
            self._state = ExperimentState.STARTING
            self._experiment_id = self._generate_experiment_id()
            self._start_time = datetime.now(timezone.utc).isoformat()
            self._config = {
                "trials": trials,
                "seed": seed,
                "clean": clean,
                "scenarios": scenarios
            }
            
            # Clean pause flag if present
            if os.path.exists(self.pause_flag_file):
                try:
                    os.remove(self.pause_flag_file)
                except Exception as e:
                    logger.warning(f"Could not remove pause flag file: {e}")

            # Ensure logs directory exists
            os.makedirs(self.logs_dir, exist_ok=True)

            # Build command string
            cmd = [
                sys.executable,
                os.path.join(self.workspace_dir, "run_phase_a.py") if os.path.exists(os.path.join(self.workspace_dir, "run_phase_a.py")) else os.path.join(self.workspace_dir, "src", "run_experiment.py"),
            ]
            
            # Note: run_experiment flags
            if os.path.exists(os.path.join(self.workspace_dir, "src", "run_experiment.py")):
                cmd = [sys.executable, os.path.join(self.workspace_dir, "src", "run_experiment.py")]
                cmd.extend(["--trials", str(trials)])
                cmd.extend(["--seed", str(seed)])
                cmd.extend(["--output-dir", self.results_dir])
                cmd.extend(["--report-dir", self.results_dir])
                if clean:
                    cmd.append("--clean")
                if scenarios and scenarios != "all":
                    cmd.extend(["--scenarios", scenarios])

            logger.info(f"Launching subprocess: {' '.join(cmd)}")
            
            try:
                # Open log file for stdout and stderr redirection
                log_fd = open(self.log_file_path, "w", encoding="utf-8")
                log_fd.write(f"=== Experiment Started: {self._experiment_id} at {self._start_time} ===\n")
                log_fd.write(f"Command: {' '.join(cmd)}\n\n")
                log_fd.flush()
                
                self._process = subprocess.Popen(
                    cmd,
                    cwd=self.workspace_dir,
                    stdout=log_fd,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                )
                self._pid = self._process.pid
                self._state = ExperimentState.RUNNING
                logger.info(f"Experiment {self._experiment_id} launched with PID {self._pid}.")
                
                return {
                    "experiment_id": self._experiment_id,
                    "state": self._state.value,
                    "pid": self._pid,
                    "start_time": self._start_time
                }
            except Exception as e:
                self._state = ExperimentState.FAILED
                logger.error(f"Failed to launch experiment subprocess: {e}")
                raise RuntimeError(f"Failed to launch experiment subprocess: {e}")

    def stop_experiment(self) -> Dict[str, Any]:
        with self._lock:
            self._update_process_status_locked()
            if self._state not in (ExperimentState.RUNNING, ExperimentState.PAUSING, ExperimentState.PAUSED, ExperimentState.STARTING):
                raise InvalidStateTransition(f"Cannot stop experiment: Current state is {self._state.value}")
            
            self._state = ExperimentState.STOPPING
            
            # Remove pause flag if it exists
            if os.path.exists(self.pause_flag_file):
                try:
                    os.remove(self.pause_flag_file)
                except Exception:
                    pass

            if self._process is not None:
                try:
                    self._process.terminate()
                    # Wait up to 3 seconds for graceful shutdown
                    try:
                        self._process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self._process.kill()
                        self._process.wait(timeout=2)
                except Exception as e:
                    logger.warning(f"Error terminating subprocess: {e}")
            
            self._state = ExperimentState.COMPLETED
            self._process = None
            
            return {
                "experiment_id": self._experiment_id,
                "state": self._state.value
            }

    def pause_experiment(self) -> Dict[str, Any]:
        with self._lock:
            self._update_process_status_locked()
            if self._state != ExperimentState.RUNNING:
                raise InvalidStateTransition(f"Cannot pause experiment: Current state is {self._state.value}")
            
            self._state = ExperimentState.PAUSING
            # Cooperative pause file creation
            try:
                with open(self.pause_flag_file, "w") as f:
                    f.write(f"PAUSE {self._experiment_id} {datetime.now(timezone.utc).isoformat()}")
                self._state = ExperimentState.PAUSED
                logger.info(f"Cooperative pause flag written for experiment {self._experiment_id}.")
            except Exception as e:
                logger.error(f"Failed to write pause flag file: {e}")
                self._state = ExperimentState.RUNNING
                raise RuntimeError(f"Could not pause experiment: {e}")

            return {
                "experiment_id": self._experiment_id,
                "state": self._state.value
            }

    def resume_experiment(self) -> Dict[str, Any]:
        with self._lock:
            self._update_process_status_locked()
            if self._state not in (ExperimentState.PAUSED, ExperimentState.PAUSING):
                raise InvalidStateTransition(f"Cannot resume experiment: Current state is {self._state.value}")
            
            if os.path.exists(self.pause_flag_file):
                try:
                    os.remove(self.pause_flag_file)
                except Exception as e:
                    logger.warning(f"Error removing pause flag file: {e}")

            self._state = ExperimentState.RUNNING
            logger.info(f"Resumed experiment {self._experiment_id}.")
            return {
                "experiment_id": self._experiment_id,
                "state": self._state.value
            }

    def restart_experiment(self, trials: int = 30, seed: int = 4321, clean: bool = True, scenarios: str = "all") -> Dict[str, Any]:
        """Stop any active experiment run, clear state, and spawn a brand new experiment run."""
        with self._lock:
            self._update_process_status_locked()
            if self._state in (ExperimentState.RUNNING, ExperimentState.PAUSED, ExperimentState.PAUSING, ExperimentState.STARTING):
                # Issue stop internally
                if self._process is not None:
                    try:
                        self._process.terminate()
                        self._process.wait(timeout=3)
                    except Exception:
                        pass
                    self._process = None

            self._state = ExperimentState.IDLE
        
        # Start new experiment with new ID
        return self.start_experiment(trials=trials, seed=seed, clean=clean, scenarios=scenarios)

    def clean_results(self) -> Dict[str, Any]:
        with self._lock:
            self._update_process_status_locked()
            if self._state in (ExperimentState.RUNNING, ExperimentState.PAUSED, ExperimentState.PAUSING, ExperimentState.STARTING):
                raise InvalidStateTransition(f"Cannot clean results while experiment is in state {self._state.value}")
            
            # Clean results folder except logs if locked
            if os.path.exists(self.results_dir):
                for item in os.listdir(self.results_dir):
                    item_path = os.path.join(self.results_dir, item)
                    if item == "logs":
                        continue
                    try:
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception as e:
                        logger.warning(f"Error removing {item_path}: {e}")

            return {"state": "CLEANED", "results_dir": self.results_dir}

    def load_results(self, source_path: str) -> Dict[str, Any]:
        with self._lock:
            self._update_process_status_locked()
            if self._state in (ExperimentState.RUNNING, ExperimentState.PAUSED, ExperimentState.PAUSING, ExperimentState.STARTING):
                raise InvalidStateTransition(f"Cannot load external results while experiment is in state {self._state.value}")

            abs_source = os.path.abspath(source_path)
            if not os.path.exists(abs_source):
                raise FileNotFoundError(f"Source results path does not exist: {source_path}")

            os.makedirs(self.results_dir, exist_ok=True)

            if os.path.isfile(abs_source):
                # Copy single json file to results/raw_results.json
                dest = os.path.join(self.results_dir, "raw_results.json")
                shutil.copy2(abs_source, dest)
            elif os.path.isdir(abs_source):
                # Copy directory files into results_dir
                for item in os.listdir(abs_source):
                    s_item = os.path.join(abs_source, item)
                    d_item = os.path.join(self.results_dir, item)
                    if os.path.isfile(s_item):
                        shutil.copy2(s_item, d_item)
                    elif os.path.isdir(s_item) and item != "logs":
                        if os.path.exists(d_item):
                            shutil.rmtree(d_item)
                        shutil.copytree(s_item, d_item)

            return {"state": "LOADED", "source_path": abs_source}

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            self._update_process_status_locked()
            return {
                "experiment_id": self._experiment_id,
                "state": self._state.value,
                "pid": self._pid,
                "start_time": self._start_time,
                "config": self._config
            }

    def get_logs(self, tail: int = 100) -> Tuple[List[str], int, int]:
        with self._lock:
            if not os.path.exists(self.log_file_path):
                return ([], tail, 0)
            
            try:
                with open(self.log_file_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                total_lines = len(lines)
                tail_lines = [line.rstrip("\r\n") for line in lines[-tail:]]
                return (tail_lines, tail, total_lines)
            except Exception as e:
                logger.error(f"Error reading log file: {e}")
                return ([f"Error reading log file: {e}"], tail, 0)
