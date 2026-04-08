import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.models.validation import Step1RunResult
from app.workflow.requirement_validator import RequirementValidator


EXPECTED_SUCCESS_STAGES = [
    "Intake",
    "Clarify",
    "Ready",
    "Generate",
    "Render",
    "Compile",
    "Success",
]


class Step1StateMachine:
    def __init__(self, validator: RequirementValidator, max_fix_rounds: int = 2) -> None:
        self.validator = validator
        self.max_fix_rounds = max_fix_rounds

    def run_case(self, case: Dict[str, Any], output_dir: Path) -> Step1RunResult:
        case_name = case["case_name"]
        requirement = case.get("requirement", {})
        compile_outcomes = case.get("compile_outcomes", [True])

        stage_logs: List[Dict[str, Any]] = []
        start = time.perf_counter()
        retries = 0

        def transition(from_state: str, to_state: str, note: str = "") -> None:
            stage_logs.append(
                {
                    "from": from_state,
                    "to": to_state,
                    "at": time.time(),
                    "note": note,
                }
            )

        transition("Start", "Intake")
        transition("Intake", "Clarify")

        validation_result = self.validator.validate(requirement)
        if not validation_result.valid:
            note = "missing={0}; errors={1}".format(
                validation_result.missing_fields, validation_result.error_messages
            )
            transition("Clarify", "Failed", note)
            return self._result(
                case_name=case_name,
                success=False,
                error_code="E1",
                pdf_path="",
                start=start,
                retry_count=retries,
                stage_logs=stage_logs,
            )

        transition("Clarify", "Ready")

        if case.get("force_generate_fail", False):
            transition("Ready", "Generate")
            transition("Generate", "Failed", "LLM output invalid")
            return self._result(
                case_name=case_name,
                success=False,
                error_code="E2",
                pdf_path="",
                start=start,
                retry_count=retries,
                stage_logs=stage_logs,
            )

        transition("Ready", "Generate")

        if case.get("force_render_fail", False):
            transition("Generate", "Render")
            transition("Render", "Failed", "template variable mismatch")
            return self._result(
                case_name=case_name,
                success=False,
                error_code="E3",
                pdf_path="",
                start=start,
                retry_count=retries,
                stage_logs=stage_logs,
            )

        transition("Generate", "Render")

        compile_try = 0
        transition("Render", "Compile")
        while True:
            compile_ok = self._compile_ok(compile_outcomes, compile_try)
            if compile_ok:
                transition("Compile", "Success")
                pdf_path = str((output_dir / "{0}.pdf".format(case_name)).as_posix())
                # Simulate a generated PDF artifact for DoD checks.
                (output_dir / "{0}.pdf".format(case_name)).write_text(
                    "pdf-bytes-placeholder", encoding="utf-8"
                )
                return self._result(
                    case_name=case_name,
                    success=True,
                    error_code="",
                    pdf_path=pdf_path,
                    start=start,
                    retry_count=retries,
                    stage_logs=stage_logs,
                )

            retries += 1
            if retries > self.max_fix_rounds:
                transition("Compile", "Fix", "retry limit exceeded")
                transition("Fix", "Fallback")
                return self._result(
                    case_name=case_name,
                    success=False,
                    error_code="E4",
                    pdf_path="",
                    start=start,
                    retry_count=retries,
                    stage_logs=stage_logs,
                )

            transition("Compile", "Fix", "compile failed, attempt repair")
            transition("Fix", "Compile", "retry={0}".format(retries))
            compile_try += 1

    @staticmethod
    def _compile_ok(outcomes: List[bool], compile_try: int) -> bool:
        if compile_try < len(outcomes):
            return outcomes[compile_try]
        return outcomes[-1]

    @staticmethod
    def _result(
        case_name: str,
        success: bool,
        error_code: str,
        pdf_path: str,
        start: float,
        retry_count: int,
        stage_logs: List[Dict[str, Any]],
    ) -> Step1RunResult:
        end = time.perf_counter()
        seen_to_states = [entry["to"] for entry in stage_logs]
        has_complete_stage_log = all(
            state in seen_to_states for state in EXPECTED_SUCCESS_STAGES[:-1]
        ) and (success and "Success" in seen_to_states or not success)

        return Step1RunResult(
            case_name=case_name,
            success=success,
            error_code=error_code,
            pdf_path=pdf_path,
            total_seconds=round(end - start, 4),
            retry_count=retry_count,
            has_complete_stage_log=has_complete_stage_log,
            stage_logs=stage_logs,
        )
