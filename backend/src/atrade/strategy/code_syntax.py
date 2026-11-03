"""The parts of the checks before save that other strategy modules share (docs/architecture/strategy.md 9.3)."""

import ast
from dataclasses import dataclass


@dataclass(frozen=True)
class CodeProblem:
    line: int
    message: str


def has_base_class(class_node: ast.ClassDef, base_class_name: str) -> bool:
    for base in class_node.bases:
        if isinstance(base, ast.Name) and base.id == base_class_name:
            return True
        if isinstance(base, ast.Attribute) and base.attr == base_class_name:
            return True
    return False
