from pathlib import Path
from typing import Dict, List, Optional

from app.core.models.generation import GenerationRequest
from app.core.models.ui import GenerationJobResult
from app.llm.content_generator import ContentGenerator
from app.latex.pipeline import LatexPipeline
from app.workflow.questionnaire_facade import QuestionnaireFacade
from app.workflow.questionnaire_session import QuestionnairePolicy


class GenerationController:
    def __init__(self, project_root: Path, model_name: str = "gpt-4o-mini") -> None:
        self.project_root = project_root
        schema_path = self.project_root / "docs" / "step1" / "最小字段定义.json"
        self.questionnaire = QuestionnaireFacade(
            schema_path=schema_path,
            policy=QuestionnairePolicy(max_duration_seconds=300.0, max_rejections=2, required_retry_limit=2),
        )
        self.generator = ContentGenerator(model_name=model_name)
        self.pipeline = LatexPipeline(max_fix_rounds=2)

    def available_templates(self) -> List[str]:
        templates_dir = self.project_root / "app" / "latex" / "templates"
        return sorted(path.stem for path in templates_dir.glob("*.tex"))

    def run_with_requirement(self, requirement: Dict[str, object], output_name: str = "ui_document") -> GenerationJobResult:
        template_id = str(requirement.get("template_id", "tpl_default"))
        generation_request = GenerationRequest(requirement=requirement, template_id=template_id)
        generation_result = self.generator.generate(generation_request)
        if not generation_result.ok:
            return GenerationJobResult(
                success=False,
                message="内容生成失败：{0}".format(generation_result.error_message),
                errors=[generation_result.error_message],
                metadata={"stage": "generate"},
            )

        pipeline_result = self.pipeline.run(
            generation_result=generation_result,
            work_root=self.project_root / "artifacts" / "step5" / output_name,
            document_title="师爷自动生成文档",
        )

        if not pipeline_result.ok:
            error_message = pipeline_result.error_message or "LaTeX编译失败"
            return GenerationJobResult(
                success=False,
                message="编译失败：{0}".format(error_message),
                tex_path=pipeline_result.tex_path,
                errors=[error_message],
                logs=[attempt.error_message for attempt in pipeline_result.attempts if attempt.error_message],
                metadata={"stage": "compile"},
            )

        return GenerationJobResult(
            success=True,
            message="生成完成",
            pdf_path=pipeline_result.pdf_path,
            tex_path=pipeline_result.tex_path,
            outline=list(generation_result.outline),
            logs=["fix_applied={0}".format(pipeline_result.fix_applied)],
            metadata={"stage": "done", "template_id": template_id},
        )
