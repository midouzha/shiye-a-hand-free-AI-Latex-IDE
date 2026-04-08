import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.models.questionnaire import (
    Question,
    QuestionnaireMetrics,
    QuestionnaireResult,
)
from app.workflow.questionnaire_engine import QuestionnaireEngine

AnswerProvider = Callable[[Question], Dict[str, Any]]


@dataclass
class QuestionnairePolicy:
    max_duration_seconds: float = 300.0
    max_rejections: int = 2
    required_retry_limit: int = 2


class QuestionnaireSession:
    """Reusable questionnaire session for CLI and PyQt.

    Supports timeout tracking, rejection handling, and fallback defaults.
    """

    def __init__(self, engine: QuestionnaireEngine, policy: Optional[QuestionnairePolicy] = None) -> None:
        self.engine = engine
        self.policy = policy or QuestionnairePolicy()
        self.start_time = time.perf_counter()
        self.rejection_count = 0
        self.timed_out = False
        self.stopped_early = False
        self.stop_reason = ""
        self.requirement: Dict[str, Any] = {}
        self.answers: Dict[str, Any] = {}
        self.asked_fields: List[str] = []
        self.warnings: List[str] = []

    def run(self, answer_provider: AnswerProvider) -> QuestionnaireResult:
        for field in self.engine.required_fields:
            if self._should_stop():
                break
            question = self.engine.questions.get(field)
            if not question:
                self.warnings.append("missing question definition for field: {0}".format(field))
                continue

            answer, accepted = self._ask_with_retries(question, answer_provider)
            if not accepted:
                self._stop("required field unresolved: {0}".format(field))
                break

            self.requirement[field] = answer
            self.answers[field] = answer
            self.asked_fields.append(field)

            if field == "structure_mode" and answer == "custom":
                self.requirement["custom_sections"] = ["引言", "正文", "结论"]
                self.warnings.append("custom_sections auto-filled with default placeholders")

        for field in ["has_images", "has_tables", "references_required"]:
            if self._should_stop():
                break
            question = self.engine.questions[field]
            answer_payload = answer_provider(question)
            if not answer_payload:
                continue
            answer = self.engine._normalize_answer(question, answer_payload)
            if answer == "" and answer_payload.get("selected") == "skip":
                self.rejection_count += 1
                continue
            self.requirement[field] = answer
            self.answers[field] = answer
            self.asked_fields.append(field)

        duration_seconds = round(time.perf_counter() - self.start_time, 4)
        if duration_seconds > self.policy.max_duration_seconds:
            self.timed_out = True
            self._stop("timeout exceeded")

        completeness = self.engine._required_completeness(self.requirement)
        metrics = QuestionnaireMetrics(
            question_count=len(self.asked_fields),
            duration_seconds=duration_seconds,
            required_completeness=completeness,
            max_duration_seconds=self.policy.max_duration_seconds,
            timed_out=self.timed_out,
            rejection_count=self.rejection_count,
            fallback_used=self.stopped_early,
        )
        return QuestionnaireResult(
            requirement=self.requirement,
            answers=self.answers,
            asked_fields=self.asked_fields,
            warnings=self.warnings,
            metrics=metrics,
            stopped_early=self.stopped_early,
            stop_reason=self.stop_reason,
        )

    def _ask_with_retries(
        self,
        question: Question,
        answer_provider: AnswerProvider,
    ) -> Tuple[Any, bool]:
        attempts = 0
        while attempts <= self.policy.required_retry_limit:
            if self._should_stop():
                return "", False
            payload = answer_provider(question)
            answer = self.engine._normalize_answer(question, payload)
            if answer != "":
                return answer, True
            attempts += 1
            self.rejection_count += 1
            if attempts > self.policy.required_retry_limit:
                fallback = self._fallback_for_question(question)
                if fallback is not None:
                    self.warnings.append("fallback used for field: {0}".format(question.field))
                    self.stopped_early = True
                    self.stop_reason = "fallback applied: {0}".format(question.field)
                    return fallback, True
                return "", False
        return "", False

    def _fallback_for_question(self, question: Question) -> Any:
        field = question.field
        defaults = {
            "doc_type": "report",
            "tone": "formal",
            "length_target": "medium",
            "structure_mode": "auto",
            "template_id": "tpl_default",
            "audience": "public",
            "language": "zh-CN",
            "has_images": False,
            "has_tables": False,
            "references_required": False,
        }
        return defaults.get(field)

    def _should_stop(self) -> bool:
        if self.timed_out:
            return True
        elapsed = time.perf_counter() - self.start_time
        if elapsed > self.policy.max_duration_seconds:
            self.timed_out = True
            self._stop("timeout exceeded")
            return True
        return False

    def _stop(self, reason: str) -> None:
        self.stopped_early = True
        if not self.stop_reason:
            self.stop_reason = reason
