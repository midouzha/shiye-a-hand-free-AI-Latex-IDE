from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class QuestionOption:
    key: str
    label: str
    value: Any


@dataclass
class Question:
    field: str
    text: str
    options: List[QuestionOption]
    allow_manual_input: bool = True


@dataclass
class QuestionnaireMetrics:
    question_count: int
    duration_seconds: float
    required_completeness: float
    max_duration_seconds: float = 300.0
    timed_out: bool = False
    rejection_count: int = 0
    fallback_used: bool = False


@dataclass
class QuestionnaireResult:
    requirement: Dict[str, Any] = field(default_factory=dict)
    answers: Dict[str, Any] = field(default_factory=dict)
    asked_fields: List[str] = field(default_factory=list)
    metrics: QuestionnaireMetrics = None
    warnings: List[str] = field(default_factory=list)
    stopped_early: bool = False
    stop_reason: str = ""
