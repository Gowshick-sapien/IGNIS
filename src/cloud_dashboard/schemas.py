"""IGNIS Cloud Dashboard API Schemas (Phase G2).

Pydantic request and response models for versioned REST API endpoints.
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
