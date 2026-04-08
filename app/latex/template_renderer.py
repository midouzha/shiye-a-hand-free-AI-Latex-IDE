from pathlib import Path
from typing import Optional

from app.core.models.generation import GenerationResult
from app.core.models.latex import LatexDocument, LatexSection


class LatexTemplateRenderer:
    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        self.templates_dir = templates_dir or Path(__file__).resolve().parent / "templates"

    def render(self, document: LatexDocument, escape_content: bool = False) -> str:
        template = self._load_template(document.template_id)
        body = self._build_body(document, escape_content=escape_content)
        return (
            template.replace("<<TITLE>>", self._escape_tex(document.title) if escape_content else document.title)
            .replace("<<AUTHOR>>", self._escape_tex(document.author) if escape_content else document.author)
            .replace("<<DATE>>", document.date)
            .replace("<<BODY>>", body)
        )

    def from_generation_result(self, generation_result: GenerationResult, document_title: str = "自动生成文档") -> LatexDocument:
        sections = [LatexSection(title=item.title, content=item.content) for item in generation_result.sections]
        if not sections and generation_result.latex_body:
            sections = [LatexSection(title="正文", content=generation_result.latex_body)]
        return LatexDocument(
            title=document_title,
            template_id="default",
            sections=sections,
            metadata={
                "outline": list(generation_result.outline),
                "raw_text": generation_result.raw_text,
            },
        )

    def _load_template(self, template_id: str) -> str:
        template_path = self.templates_dir / "default.tex"
        if template_id and (self.templates_dir / "{0}.tex".format(template_id)).exists():
            template_path = self.templates_dir / "{0}.tex".format(template_id)
        return template_path.read_text(encoding="utf-8")

    def _build_body(self, document: LatexDocument, escape_content: bool = False) -> str:
        parts = []
        for section in document.sections:
            title = self._escape_tex(section.title) if escape_content else section.title
            content = self._escape_tex(section.content) if escape_content else section.content
            parts.append("\\section*{{{0}}}\n{1}".format(title, content))
        return "\n\n".join(parts) if parts else "\\section*{正文}\n暂无内容。"

    @staticmethod
    def _escape_tex(text: str) -> str:
        replacements = {
            "\\": r"\textbackslash{}",
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        escaped = text
        for source, target in replacements.items():
            escaped = escaped.replace(source, target)
        return escaped
