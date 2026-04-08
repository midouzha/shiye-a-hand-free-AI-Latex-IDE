import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class LatexIssue:
    category: str
    message: str
    matched_line: str = ""


@dataclass
class LatexLogAnalysis:
    issues: List[LatexIssue] = field(default_factory=list)

    @property
    def fixable(self) -> bool:
        return any(issue.category in {"special_characters", "undefined_control_sequence", "missing_package"} for issue in self.issues)

    @property
    def primary_category(self) -> str:
        return self.issues[0].category if self.issues else ""


class LatexErrorParser:
    PATTERNS = [
        (re.compile(r"Missing \$ inserted"), "special_characters", "text contains characters that need escaping"),
        (re.compile(r"Undefined control sequence"), "undefined_control_sequence", "a command is not recognized"),
        (re.compile(r"LaTeX Error: File `([^`]+)` not found"), "missing_package", "missing file or package"),
        (re.compile(r"Emergency stop"), "fatal_error", "latex stopped unexpectedly"),
        (re.compile(r"Runaway argument"), "special_characters", "likely malformed text or unescaped braces"),
    ]

    def analyze(self, log_text: str) -> LatexLogAnalysis:
        issues: List[LatexIssue] = []
        lines = log_text.splitlines()
        for line in lines:
            for pattern, category, message in self.PATTERNS:
                if pattern.search(line):
                    issues.append(LatexIssue(category=category, message=message, matched_line=line.strip()))
                    break
        if not issues and log_text.strip():
            if "!" in log_text:
                issues.append(LatexIssue(category="unknown", message="compilation failed but no known pattern matched"))
        return LatexLogAnalysis(issues=issues)
