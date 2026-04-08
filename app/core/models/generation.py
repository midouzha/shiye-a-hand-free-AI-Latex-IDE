from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class GenerationRequest:
    requirement: Dict[str, Any]
    template_id: str
    project_name: str = "师爷LaTeX排版工具"


@dataclass
class GeneratedSection:
    title: str
    content: str


@dataclass
class GenerationResult:
    ok: bool
    model: str = ""
    outline: List[str] = field(default_factory=list)
    sections: List[GeneratedSection] = field(default_factory=list)
    latex_body: str = ""
    raw_text: str = ""
    error_message: str = ""
    usage: Dict[str, Any] = field(default_factory=dict)
