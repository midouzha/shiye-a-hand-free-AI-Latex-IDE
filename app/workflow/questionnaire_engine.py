import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

from app.core.models.questionnaire import (
    Question,
    QuestionOption,
    QuestionnaireMetrics,
    QuestionnaireResult,
)

AnswerProvider = Callable[[Question], Dict[str, Any]]


class QuestionnaireEngine:
    """Step2 pre-clarification engine.

    Each question offers 3-5 options and also supports manual input.
    """

    def __init__(self, schema_path: Path) -> None:
        self.schema_path = schema_path
        self.schema = self._load_json(schema_path)
        self.required_fields = list(self.schema.get("required", []))
        self.questions = self._build_questions()

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _build_questions(self) -> Dict[str, Question]:
        return {
            "doc_type": Question(
                field="doc_type",
                text="文档类型是什么？",
                options=[
                    QuestionOption("paper", "论文", "paper"),
                    QuestionOption("report", "报告", "report"),
                    QuestionOption("summary", "总结", "summary"),
                    QuestionOption("resume", "简历", "resume"),
                    QuestionOption("other", "其他（手动输入）", "other"),
                ],
            ),
            "tone": Question(
                field="tone",
                text="你希望整体语气是？",
                options=[
                    QuestionOption("formal", "正式", "formal"),
                    QuestionOption("academic", "学术", "academic"),
                    QuestionOption("concise", "简洁", "concise"),
                    QuestionOption("friendly", "亲和", "friendly"),
                ],
            ),
            "length_target": Question(
                field="length_target",
                text="篇幅目标是？",
                options=[
                    QuestionOption("short", "短", "short"),
                    QuestionOption("medium", "中", "medium"),
                    QuestionOption("long", "长", "long"),
                ],
            ),
            "structure_mode": Question(
                field="structure_mode",
                text="章节结构如何生成？",
                options=[
                    QuestionOption("auto", "自动生成", "auto"),
                    QuestionOption("custom", "我来指定", "custom"),
                    QuestionOption("other", "其他（手动输入）", "other"),
                ],
            ),
            "template_id": Question(
                field="template_id",
                text="选择模板（可手填模板ID）：",
                options=[
                    QuestionOption("tpl_default", "通用模板", "tpl_default"),
                    QuestionOption("tpl_weekly", "周报模板", "tpl_weekly"),
                    QuestionOption("tpl_academic", "学术模板", "tpl_academic"),
                    QuestionOption("other", "其他（手动输入）", "other"),
                ],
            ),
            "audience": Question(
                field="audience",
                text="主要读者是谁？",
                options=[
                    QuestionOption("teacher", "老师", "teacher"),
                    QuestionOption("manager", "主管", "manager"),
                    QuestionOption("peer", "同事/同学", "peer"),
                    QuestionOption("public", "公开读者", "public"),
                    QuestionOption("other", "其他（手动输入）", "other"),
                ],
            ),
            "language": Question(
                field="language",
                text="输出语言？",
                options=[
                    QuestionOption("zh-CN", "中文", "zh-CN"),
                    QuestionOption("en-US", "英文", "en-US"),
                    QuestionOption("other", "其他（手动输入）", "other"),
                ],
            ),
            "has_images": Question(
                field="has_images",
                text="是否包含图片？",
                options=[
                    QuestionOption("yes", "是", True),
                    QuestionOption("no", "否", False),
                    QuestionOption("other", "其他（手动输入）", "other"),
                ],
            ),
            "has_tables": Question(
                field="has_tables",
                text="是否包含表格？",
                options=[
                    QuestionOption("yes", "是", True),
                    QuestionOption("no", "否", False),
                    QuestionOption("other", "其他（手动输入）", "other"),
                ],
            ),
            "references_required": Question(
                field="references_required",
                text="是否需要参考文献？",
                options=[
                    QuestionOption("yes", "需要", True),
                    QuestionOption("no", "不需要", False),
                    QuestionOption("other", "其他（手动输入）", "other"),
                ],
            ),
        }

    def run_session(self, answer_provider: AnswerProvider) -> QuestionnaireResult:
        start = time.perf_counter()
        requirement: Dict[str, Any] = {}
        raw_answers: Dict[str, Any] = {}
        asked_fields: List[str] = []
        warnings: List[str] = []

        # Required fields first.
        for field in self.required_fields:
            question = self.questions.get(field)
            if not question:
                warnings.append("missing question definition for field: {0}".format(field))
                continue
            answer = self._normalize_answer(question, answer_provider(question))
            requirement[field] = answer
            raw_answers[field] = answer
            asked_fields.append(field)

            # If user wants custom structure, ask one extra guided field.
            if field == "structure_mode" and answer == "custom":
                requirement["custom_sections"] = ["引言", "正文", "结论"]
                warnings.append("custom_sections auto-filled with default placeholders")

        # Ask optional but high-value fields.
        for field in ["has_images", "has_tables", "references_required"]:
            question = self.questions[field]
            answer_payload = answer_provider(question)
            if not answer_payload:
                continue
            answer = self._normalize_answer(question, answer_payload)
            requirement[field] = answer
            raw_answers[field] = answer
            asked_fields.append(field)

        end = time.perf_counter()
        completeness = self._required_completeness(requirement)

        return QuestionnaireResult(
            requirement=requirement,
            answers=raw_answers,
            asked_fields=asked_fields,
            warnings=warnings,
            metrics=QuestionnaireMetrics(
                question_count=len(asked_fields),
                duration_seconds=round(end - start, 4),
                required_completeness=completeness,
            ),
        )

    def _normalize_answer(self, question: Question, payload: Dict[str, Any]) -> Any:
        if not payload:
            return ""

        selected = payload.get("selected")
        manual = payload.get("manual_input")

        if selected == "other":
            return self._manual_or_empty(question, manual)

        option_map = {x.key: x for x in question.options}
        if selected in option_map:
            selected_value = option_map[selected].value
            if selected_value == "other":
                return self._manual_or_empty(question, manual)
            return selected_value

        # If selected option is invalid, fallback to manual input.
        if manual is not None:
            return self._manual_or_empty(question, manual)

        return ""

    @staticmethod
    def _manual_or_empty(question: Question, manual: Any) -> Any:
        if not question.allow_manual_input:
            return ""
        if manual is None:
            return ""
        text = str(manual).strip()
        if text.lower() in {"true", "false"}:
            return text.lower() == "true"
        return text

    def _required_completeness(self, requirement: Dict[str, Any]) -> float:
        if not self.required_fields:
            return 1.0

        present = 0
        for field in self.required_fields:
            value = requirement.get(field)
            if isinstance(value, str):
                if value.strip() != "":
                    present += 1
            elif value is not None:
                present += 1

        return round(present / float(len(self.required_fields)), 4)
