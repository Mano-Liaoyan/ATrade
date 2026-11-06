"""The parts of the checks before save that other strategy modules share (docs/architecture/strategy.md 9.3), and the
order check of a forward test start (forward_test.md section 12.19).
"""

import ast
from dataclasses import dataclass

# The calls that send or make an order that the ATrade execution client does not send. They work only in a backtest.
BACKTEST_ONLY_ORDER_CALLS = frozenset(
    {
        "bracket",
        "limit_if_touched",
        "market_if_touched",
        "market_to_limit",
        "stop_limit",
        "stop_market",
        "submit_order_list",
        "trailing_stop_limit",
        "trailing_stop_market",
    }
)


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


def find_backtest_only_orders(code: str) -> list[CodeProblem]:
    """The calls of `BACKTEST_ONLY_ORDER_CALLS` in code that passed the checks before save, first line first."""
    problems = [
        CodeProblem(
            line=node.lineno,
            message=f"{node.func.attr} works only in a backtest. A forward test sends only market and limit orders.",
        )
        for node in ast.walk(ast.parse(code))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in BACKTEST_ONLY_ORDER_CALLS
    ]
    return sorted(problems, key=lambda problem: problem.line)
