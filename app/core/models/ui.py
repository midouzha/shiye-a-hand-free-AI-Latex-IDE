from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class GenerationJobResult:
    success: bool
    message: str
    pdf_path: str = ""
    tex_path: str = ""
    outline: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class UIState:
    selected_template_id: str = "tpl_default"
    last_message: str = ""
    last_pdf_path: str = ""
    last_tex_path: str = ""
    busy: bool = False
    error_message: str = ""
    questionnaire_step: int = 0
    questionnaire_total: int = 0
    questionnaire_complete: bool = False
    generated_items: List[Dict[str, str]] = field(default_factory=list)
