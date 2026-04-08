import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List

from app.workflow.requirement_validator import RequirementValidator
from app.workflow.state_machine import Step1StateMachine


def run_replay(project_root: Path) -> Dict[str, object]:
    schema_path = project_root / "docs" / "step1" / "最小字段定义.json"
    samples_dir = project_root / "docs" / "step1" / "samples"
    logs_dir = project_root / "artifacts" / "step1" / "logs"

    logs_dir.mkdir(parents=True, exist_ok=True)

    validator = RequirementValidator(schema_path=schema_path)
    state_machine = Step1StateMachine(validator=validator, max_fix_rounds=2)

    results = []
    for sample_file in sorted(samples_dir.glob("*.json")):
        with sample_file.open("r", encoding="utf-8") as f:
            case = json.load(f)

        run_result = state_machine.run_case(case=case, output_dir=logs_dir)
        result_dict = asdict(run_result)
        result_dict["sample_file"] = str(sample_file.as_posix())
        results.append(result_dict)

        per_case_log = logs_dir / "{0}.log.json".format(case["case_name"])
        with per_case_log.open("w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)

    summary = {
        "case_count": len(results),
        "success_count": sum(1 for x in results if x["success"]),
        "failure_count": sum(1 for x in results if not x["success"]),
        "results": results,
    }

    summary_path = project_root / "artifacts" / "step1" / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary
