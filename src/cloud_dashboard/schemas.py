"""IGNIS Cloud Dashboard API Schemas (Phase G2 & Phase G3).

Pydantic request, response, and progress event models for REST and SSE streaming APIs.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ExperimentRunRequest(BaseModel):
    trials: int = Field(default=30, ge=1, le=1000, description="Number of trials to execute per scenario")
    seed: int = Field(default=4321, description="Base random seed")
    clean: bool = Field(default=True, description="Whether to clean previous result output directory")
    scenarios: str = Field(default="all", description="Target scenarios: 'all', 'failed', 'S3', or comma-separated 'S4,S5,S6'")


class ExperimentStatusResponse(BaseModel):
    experiment_id: Optional[str] = None
    state: str = Field(..., description="Current state: IDLE, STARTING, RUNNING, PAUSING, PAUSED, STOPPING, COMPLETED, FAILED")
    pid: Optional[int] = None
    current_scenario: Optional[str] = None
    current_trial: Optional[int] = None
    total_trials: Optional[int] = None
    start_time: Optional[str] = None


class ExperimentLogResponse(BaseModel):
    lines: List[str] = Field(default_factory=list, description="Trailing log lines")
    tail: int = Field(..., description="Requested tail length")
    total_lines: int = Field(..., description="Total line count in log file")


class ExperimentLoadRequest(BaseModel):
    path: str = Field(..., description="Absolute or relative path to raw_results.json or experiment folder")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error classification code")
    message: str = Field(..., description="Human readable explanation")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional diagnostic context")


# ============================================================================
# Phase G3 — Structured Progress Event Schemas
# ============================================================================

class ProgressEventBase(BaseModel):
    schema_version: str = Field(default="1.0", description="Event schema version")
    event: str = Field(..., description="Event classification type")
    event_id: str = Field(..., description="Unique event ID: exp-ID-seq")
    sequence: int = Field(..., description="Monotonic sequence number starting from 1")
    experiment_id: str = Field(..., description="Target experiment execution ID")
    timestamp: str = Field(..., description="ISO8601 UTC timestamp")


class ExperimentStartedPayload(ProgressEventBase):
    config: Dict[str, Any] = Field(default_factory=dict)
    total_scenarios: int
    total_trials: int


class ScenarioStartedPayload(ProgressEventBase):
    scenario_id: str
    scenario_index: int
    total_scenarios: int


class TrialProgressPayload(ProgressEventBase):
    scenario_id: str
    trial: int
    total_trials: int
    scenario_index: int
    total_scenarios: int
    elapsed_sec: float
    progress_pct: float
    eta_sec: float


class ScenarioCompletePayload(ProgressEventBase):
    scenario_id: str
    status: str = Field(..., description="PASS, FAIL, or INVALID")
    duration_sec: float
    metrics: Dict[str, Any] = Field(default_factory=dict)


class ExperimentCompletePayload(ProgressEventBase):
    overall_verdict: str = Field(..., description="PASS or FAIL")
    duration_sec: float
    summary_stats: Dict[str, Any] = Field(default_factory=dict)


class ExperimentFailedPayload(ProgressEventBase):
    error_code: str
    error_message: str
    failed_at_scenario: Optional[str] = None


class HeartbeatPayload(BaseModel):
    schema_version: str = Field(default="1.0")
    event: str = Field(default="HEARTBEAT")
    timestamp: str
