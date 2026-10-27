"""Checks that strategy code must pass before it is saved (docs/architecture/strategy.md section 9.3).

The checks do not import or run the user code: they use ast.parse, an AST check of the class bases,
and the ruff F rules.
"""

import ast
import asyncio
import sys
from dataclasses import dataclass

from pydantic import BaseModel, TypeAdapter

REQUIRED_BASE_CLASSES = ("Strategy", "StrategyConfig")
RUFF_ARGUMENTS = (
    "check",
    "--isolated",
    "--no-cache",
    "--select",
    "F",
    "--output-format",
    "json",
    "--stdin-filename",
    "strategy.py",
    "-",
)
# ruff exits with 0 when there are no errors and with 1 when it found errors. Other codes are failures of ruff itself.
RUFF_EXIT_CODES_WITH_REPORT = (0, 1)
FIRST_LINE = 1


@dataclass(frozen=True)
class CodeProblem:
    line: int
    message: str


class RuffLocation(BaseModel):
    row: int


class RuffDiagnostic(BaseModel):
    code: str | None
    message: str
    location: RuffLocation


RUFF_REPORT = TypeAdapter(list[RuffDiagnostic])


async def check_strategy_code(code: str) -> list[CodeProblem]:
    try:
        module = ast.parse(code)
    except SyntaxError as error:
        # readability-exception: ast.parse reports a syntax error only as an exception.
        return [CodeProblem(line=error.lineno or FIRST_LINE, message=f"Syntax error: {error.msg}.")]
    class_problems = find_class_count_problems(module)
    ruff_problems = await find_ruff_problems(code)
    all_problems = class_problems + ruff_problems
    return sorted(all_problems, key=lambda problem: problem.line)


def find_class_count_problems(module: ast.Module) -> list[CodeProblem]:
    problems: list[CodeProblem] = []
    for base_class_name in REQUIRED_BASE_CLASSES:
        subclasses = [
            node for node in module.body if isinstance(node, ast.ClassDef) and has_base_class(node, base_class_name)
        ]
        if not subclasses:
            message = f"The code must have exactly 1 {base_class_name} subclass. It has none."
            problems.append(CodeProblem(line=FIRST_LINE, message=message))
        for extra_subclass in subclasses[1:]:
            message = f"The code must have exactly 1 {base_class_name} subclass. {extra_subclass.name} is one more."
            problems.append(CodeProblem(line=extra_subclass.lineno, message=message))
    return problems


def has_base_class(class_node: ast.ClassDef, base_class_name: str) -> bool:
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base.id == base_class_name:
            return True
        if isinstance(base, ast.Attribute) and base.attr == base_class_name:
            return True
    return False


async def find_ruff_problems(code: str) -> list[CodeProblem]:
    ruff_process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "ruff",
        *RUFF_ARGUMENTS,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    report_bytes, error_bytes = await ruff_process.communicate(code.encode())
    if ruff_process.returncode not in RUFF_EXIT_CODES_WITH_REPORT:
        message = f"ruff failed with exit code {ruff_process.returncode}: {error_bytes.decode()}"
        raise RuntimeError(message)
    diagnostics = RUFF_REPORT.validate_json(report_bytes)
    return [
        CodeProblem(line=diagnostic.location.row, message=f"{diagnostic.code} {diagnostic.message}")
        for diagnostic in diagnostics
    ]
