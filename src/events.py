from dataclasses import dataclass, asdict
from typing import List, Optional

@dataclass
class DecisionEvent:
    scenario: str
    zone_id: str
    node_id: str
    sensor_timestamp: str
    decision_timestamp: str
    previous_state: str
    new_state: str
    whi: float
    confirmation_count: int
    is_clamped: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**d)

@dataclass
class AlertEvent:
    scenario: str
    zone_id: str
    timestamp: str
    severity: str
    source_node: str
    whi: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**d)

@dataclass
class ActionEvent:
    scenario: str
    zone_id: str
    timestamp: str
    actions: List[str]
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**d)

@dataclass
class CloudReportEvent:
    scenario: str
    zone_id: str
    node_id: str
    timestamp: str
    was_buffered: bool
    buffer_flush_timestamp: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**d)

@dataclass
class ScenarioEvent:
    scenario: str
    event_type: str
    timestamp: str
    step_index: int
    total_steps: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**d)
