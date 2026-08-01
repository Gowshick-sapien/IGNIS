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


# ============================================================================
# Repository Pydantic Schemas (Phase G4)
# ============================================================================

class RepositoryScenarioSummary(BaseModel):
    scenario_id: str
    verdict: str
    duration_sec: Optional[float] = 0.0
    trial_count: Optional[int] = 0
    latency_mean: Optional[float] = None
    latency_ci_low: Optional[float] = None
    latency_ci_high: Optional[float] = None


class RepositoryExperimentSummary(BaseModel):
    experiment_id: str
    directory: str
    timestamp: str
    archived_at: str
    seed: Optional[int] = 4321
    git_commit: Optional[str] = "unknown"
    trial_count: Optional[int] = 0
    overall_verdict: str
    execution_duration_sec: Optional[float] = 0.0
    manifest_sha256: str
    archive_schema_version: str = "1.0"
    scenarios_summary: List[RepositoryScenarioSummary] = Field(default_factory=list)


class RepositoryListResponseData(BaseModel):
    experiments: List[RepositoryExperimentSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class RepositoryListResponse(BaseModel):
    status: str = "success"
    data: RepositoryListResponseData


class RepositoryExperimentDetail(BaseModel):
    experiment_id: str
    directory: str
    directory_path: str
    timestamp: str
    archived_at: str
    seed: Optional[int] = 4321
    git_commit: Optional[str] = "unknown"
    trial_count: Optional[int] = 0
    overall_verdict: str
    execution_duration_sec: Optional[float] = 0.0
    platform_os: Optional[str] = "unknown"
    platform_python: Optional[str] = "unknown"
    platform_docker: Optional[str] = "unknown"
    hostname: Optional[str] = "unknown"
    manifest_sha256: str
    archive_schema_version: str = "1.0"
    scenarios: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    manifest: Dict[str, Any] = Field(default_factory=dict)
    has_html_report: bool = False
    has_md_report: bool = False
    charts: List[str] = Field(default_factory=list)


# ============================================================================
# Phase G5 — Analytics & Comparison Schemas
# ============================================================================

from enum import Enum

class ComparisonIndicator(str, Enum):
    IMPROVED = "IMPROVED"
    REGRESSED = "REGRESSED"
    UNCHANGED = "UNCHANGED"
    NOT_COMPARABLE = "NOT_COMPARABLE"


class MetricDiff(BaseModel):
    mean_a: Optional[float] = None
    mean_b: Optional[float] = None
    ci_a: Optional[List[float]] = None
    ci_b: Optional[List[float]] = None
    ci_overlap: Optional[bool] = None
    significant_difference: Optional[bool] = None
    delta: Optional[float] = None
    pct_change: Optional[float] = None
    indicator: ComparisonIndicator = ComparisonIndicator.UNCHANGED
    details: Optional[str] = None


class VerdictDelta(BaseModel):
    overall_a: str
    overall_b: str
    changed: bool
    scenarios: Dict[str, Dict[str, str]] = Field(default_factory=dict)


class EnvironmentDiff(BaseModel):
    os_match: bool
    python_match: bool
    git_commit_a: str
    git_commit_b: str
    same_commit: bool


class ComparisonResponseData(BaseModel):
    experiment_a: str
    experiment_b: str
    verdict_delta: VerdictDelta
    metrics_diff: Dict[str, Dict[str, MetricDiff]] = Field(default_factory=dict)
    environment_diff: EnvironmentDiff


class ComparisonResponse(BaseModel):
    status: str = "success"
    data: ComparisonResponseData


# ============================================================================
# Phase G6 — Export & Publication Schemas
# ============================================================================

class ExportOptionalFormatStatus(BaseModel):
    available: bool
    reason: Optional[str] = None


class ExportFormatCapabilityResponseData(BaseModel):
    available: List[str]
    optional_status: Dict[str, ExportOptionalFormatStatus]


class ExportFormatCapabilityResponse(BaseModel):
    status: str = "success"
    data: ExportFormatCapabilityResponseData


class ReproducibilityBundleResponseData(BaseModel):
    experiment_id: str
    bundle_path: str
    file_size_bytes: int
    sha256_hash: str
    manifest: Dict[str, Any] = Field(default_factory=dict)


class ReproducibilityBundleResponse(BaseModel):
    status: str = "success"
    data: ReproducibilityBundleResponseData



