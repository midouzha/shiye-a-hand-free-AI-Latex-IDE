import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class LatexCompileOutput:
    success: bool
    pdf_path: str = ""
    log_path: str = ""
    stdout_path: str = ""
    stderr_path: str = ""
    return_code: int = 0
    stdout: str = ""
    stderr: str = ""


class LatexCompiler:
    def __init__(self, compiler_name: str = "latexmk") -> None:
        self.compiler_name = compiler_name

    def compile(self, tex_path: Path) -> LatexCompileOutput:
        work_dir = tex_path.parent
        command = [
            self.compiler_name,
            "-xelatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            tex_path.name,
        ]
        process = subprocess.run(
            command,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        pdf_path = tex_path.with_suffix(".pdf")
        log_path = tex_path.with_suffix(".log")
        stdout_path = tex_path.with_suffix(".compile.stdout.txt")
        stderr_path = tex_path.with_suffix(".compile.stderr.txt")

        stdout_path.write_text(process.stdout or "", encoding="utf-8")
        stderr_path.write_text(process.stderr or "", encoding="utf-8")
        combined_log = (process.stdout or "") + "\n" + (process.stderr or "")
        log_path.write_text(combined_log, encoding="utf-8")

        return LatexCompileOutput(
            success=process.returncode == 0 and pdf_path.exists(),
            pdf_path=str(pdf_path.as_posix()) if pdf_path.exists() else "",
            log_path=str(log_path.as_posix()),
            stdout_path=str(stdout_path.as_posix()),
            stderr_path=str(stderr_path.as_posix()),
            return_code=process.returncode,
            stdout=process.stdout,
            stderr=process.stderr,
        )
