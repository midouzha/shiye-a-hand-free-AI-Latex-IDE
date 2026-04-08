from dataclasses import asdict
from pathlib import Path
from typing import List

from app.core.models.generation import GenerationResult
from app.core.models.latex import LatexCompileAttempt, LatexDocument, LatexPipelineResult
from app.latex.auto_fixer import LatexAutoFixer
from app.latex.compiler import LatexCompiler
from app.latex.error_parser import LatexErrorParser
from app.latex.template_renderer import LatexTemplateRenderer


class LatexPipeline:
    def __init__(self, max_fix_rounds: int = 2) -> None:
        self.max_fix_rounds = max_fix_rounds
        self.renderer = LatexTemplateRenderer()
        self.compiler = LatexCompiler()
        self.error_parser = LatexErrorParser()
        self.auto_fixer = LatexAutoFixer()

    def run(self, generation_result: GenerationResult, work_root: Path, document_title: str = "自动生成文档") -> LatexPipelineResult:
        work_root.mkdir(parents=True, exist_ok=True)
        document = self.renderer.from_generation_result(generation_result, document_title=document_title)
        current_document = document
        attempts: List[LatexCompileAttempt] = []
        fix_applied = False

        for attempt_index in range(self.max_fix_rounds + 1):
            tex_path = work_root / "document.tex"
            rendered_tex = self.renderer.render(current_document, escape_content=False)
            tex_path.write_text(rendered_tex, encoding="utf-8")

            compile_output = self.compiler.compile(tex_path)
            if compile_output.success:
                attempts.append(
                    LatexCompileAttempt(
                        attempt_index=attempt_index + 1,
                        success=True,
                        log_path=compile_output.log_path,
                        stdout_path=compile_output.stdout_path,
                        stderr_path=compile_output.stderr_path,
                    )
                )
                return LatexPipelineResult(
                    ok=True,
                    pdf_path=compile_output.pdf_path,
                    tex_path=str(tex_path.as_posix()),
                    work_dir=str(work_root.as_posix()),
                    attempts=attempts,
                    fix_applied=fix_applied,
                )

            combined_log = compile_output.stdout + "\n" + compile_output.stderr
            analysis = self.error_parser.analyze(combined_log)
            attempts.append(
                LatexCompileAttempt(
                    attempt_index=attempt_index + 1,
                    success=False,
                    error_category=analysis.primary_category,
                    error_message="; ".join(issue.message for issue in analysis.issues),
                    log_path=compile_output.log_path,
                    stdout_path=compile_output.stdout_path,
                    stderr_path=compile_output.stderr_path,
                )
            )

            if attempt_index >= self.max_fix_rounds or not self.auto_fixer.can_fix(analysis):
                return LatexPipelineResult(
                    ok=False,
                    tex_path=str(tex_path.as_posix()),
                    work_dir=str(work_root.as_posix()),
                    attempts=attempts,
                    error_message="compilation failed after retries",
                    log_excerpt=(combined_log[-2000:] if combined_log else ""),
                    fix_applied=fix_applied,
                )

            current_document = self.auto_fixer.fix(current_document, analysis)
            fix_applied = True

        return LatexPipelineResult(
            ok=False,
            attempts=attempts,
            error_message="compilation failed",
            fix_applied=fix_applied,
        )
