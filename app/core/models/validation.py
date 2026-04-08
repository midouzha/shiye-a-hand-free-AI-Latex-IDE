from dataclasses import dataclass, field
from typing import List


@dataclass
class ValidationResult:
    valid: bool
    missing_fields: List[str] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)


@dataclass
class Step1RunResult:
    case_name: str
    success: bool
    error_code: str
    pdf_path: str
    total_seconds: float
    retry_count: int
    has_complete_stage_log: bool
    stage_logs: list
