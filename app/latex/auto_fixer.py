from copy import deepcopy
from typing import Iterable

from app.core.models.latex import LatexDocument, LatexSection
from app.latex.error_parser import LatexLogAnalysis
from app.latex.template_renderer import LatexTemplateRenderer


class LatexAutoFixer:
    def __init__(self) -> None:
        self.renderer = LatexTemplateRenderer()

    def can_fix(self, analysis: LatexLogAnalysis) -> bool:
        return analysis.fixable

    def fix(self, document: LatexDocument, analysis: LatexLogAnalysis) -> LatexDocument:
        fixed_document = deepcopy(document)
        if not analysis.issues:
            return fixed_document

        for issue in analysis.issues:
            if issue.category in {"special_characters", "undefined_control_sequence", "missing_package"}:
                fixed_document.sections = [
                    LatexSection(
                        title=self.renderer._escape_tex(section.title),
                        content=self.renderer._escape_tex(section.content),
                    )
                    for section in fixed_document.sections
                ]
                fixed_document.title = self.renderer._escape_tex(fixed_document.title)
                fixed_document.author = self.renderer._escape_tex(fixed_document.author)
                break

        return fixed_document
