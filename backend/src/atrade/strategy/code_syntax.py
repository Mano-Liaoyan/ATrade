"""The parts of the checks before save that other strategy modules share (docs/architecture/strategy.md 9.3), and the
order check of a forward test start (forward_test.md section 12.19).
"""

import ast
from dataclasses import dataclass

# The `order_factory` calls that make an order that the ATrade execution client does not send, and the strategy call
# that sends an order list. They work only in a backtest.
BACKTEST_ONLY_FACTORY_CALLS = frozenset(
    {
        "bracket",
        "limit_if_touched",
        "market_if_touched",
        "market_to_limit",
        "stop_limit",
        "stop_market",
        "trailing_stop_limit",
        "trailing_stop_market",
    }
)
BACKTEST_ONLY_STRATEGY_CALL = "submit_order_list"
ORDER_FACTORY_NAME = "order_factory"


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


def is_order_factory(node: ast.expr) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == ORDER_FACTORY_NAME) or (
        isinstance(node, ast.Name) and node.id == ORDER_FACTORY_NAME
    )


def is_backtest_only_order(function: ast.Attribute) -> bool:
    """A method of the user can have the same name as an `order_factory` call. Only the real API counts."""
    return function.attr == BACKTEST_ONLY_STRATEGY_CALL or (
        function.attr in BACKTEST_ONLY_FACTORY_CALLS and is_order_factory(function.value)
    )


def find_backtest_only_orders(code: str) -> list[CodeProblem]:
    """The backtest-only order calls in code that passed the checks before save, first line first."""
    problems = [
        CodeProblem(
            line=node.lineno,
            message=f"{node.func.attr} works only in a backtest. A forward test sends only market and limit orders.",
        )
        for node in ast.walk(ast.parse(code))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and is_backtest_only_order(node.func)
    ]
    return sorted(problems, key=lambda problem: problem.line)
