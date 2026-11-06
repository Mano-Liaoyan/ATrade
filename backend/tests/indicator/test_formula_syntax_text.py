"""The expression syntax in the tool descriptions of the AI assistant stays equal to the parser (issue #374).

The tools are TypeScript and the parser is Python, so this test reads `FORMULA_SYNTAX` from the tool file.
"""

import re
from pathlib import Path

from atrade.indicator import check_expression
from atrade.indicator.formula_indicator import (
    BAR_FIELDS,
    MAX_CALCULATION_BARS,
    MAX_DEPTH,
    MAX_EXPONENT,
    MAX_EXPRESSION_LENGTH,
    MAX_LOOK_BACK_BARS,
    MIN_STD_WINDOW,
    ROLLING_FUNCTIONS,
    SCALAR_FUNCTIONS,
)
from atrade.indicator.indicator_catalog import MAXIMUM_PERIOD

TOOL_FILE = Path(__file__).resolve().parents[3] / "assistant" / "src" / "custom_indicator_tools.ts"


def read_syntax_text() -> str:
    source = TOOL_FILE.read_text()
    match = re.search(r"const FORMULA_SYNTAX =\n(.*?);\n", source, re.DOTALL)
    assert match is not None
    return "".join(re.findall(r"'([^']*)'", match.group(1)))


def test_the_text_names_each_bar_field_and_each_function_of_the_parser() -> None:
    text = read_syntax_text()

    for name in BAR_FIELDS:
        assert re.search(rf"\b{name}\b", text), name
    for name in [*ROLLING_FUNCTIONS, *SCALAR_FUNCTIONS]:
        assert f"{name}(" in text, name


def test_the_text_gives_each_limit_of_the_parser() -> None:
    text = read_syntax_text()

    assert f"1 to {MAXIMUM_PERIOD}" in text
    assert f"at least {MIN_STD_WINDOW}" in text
    assert f"-{MAX_EXPONENT} to {MAX_EXPONENT}" in text
    assert f"{MAX_EXPRESSION_LENGTH} characters" in text
    assert f"{MAX_DEPTH} levels" in text
    assert f"{MAX_LOOK_BACK_BARS} bars" in text
    assert f"{MAX_CALCULATION_BARS}" in text


def test_each_example_of_the_text_passes_the_check() -> None:
    examples = re.findall(r"`([^`]+)`", read_syntax_text().split("Examples:")[1])

    assert examples
    for example in examples:
        assert check_expression(example) == [], example
