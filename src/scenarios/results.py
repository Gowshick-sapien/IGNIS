from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ScenarioMetric:
    name: str                  # e.g. "fog_decision_latency"
    value: float
    unit: str                  # e.g. "seconds"
    passed: bool
    threshold: float           # target value for pass/fail
    details: str = ""

@dataclass
class ScenarioResult:
    scenario: str              # e.g. "S4"
    passed: bool
    duration_sec: float
    start_time: str
    end_time: str
    metrics: List[ScenarioMetric]
    events: List[dict]         # serialized DecisionEvent/AlertEvent list
    logs: List[str]
    errors: List[str]
    zone_ids: List[str]
    trial_index: int = 0       # for multi-trial runs
