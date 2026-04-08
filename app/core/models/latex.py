from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class LatexSection:
    title: str
    content: str


@dataclass
class LatexDocument:
    title: str
    template_id: str = "default"
    author: str = "师爷系统"
    date: str = r"\today"
    sections: List[LatexSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LatexCompileAttempt:
    attempt_index: int
    success: bool
    error_category: str = ""
    error_message: str = ""
    log_path: str = ""
    stdout_path: str = ""
    stderr_path: str = ""


@dataclass
class LatexPipelineResult:
    ok: bool
    pdf_path: str = ""
    tex_path: str = ""
    work_dir: str = ""
    compiler: str = "latexmk"
    attempts: List[LatexCompileAttempt] = field(default_factory=list)
    error_message: str = ""
    log_excerpt: str = ""
    fix_applied: bool = False
