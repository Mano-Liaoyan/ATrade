"""The start points and the template list (docs/architecture/strategy.md section 9.9, #175).

The defaults are the parameters of the source research (section 9.9.2). Section 9.9.4 records what was checked
against the papers.
"""

from dataclasses import dataclass
from typing import Any, Literal

from atrade.strategy.strategy_rules import StrategyRules

BLANK_CODE = "blank_code"
BLANK_RULES_START = "blank_rules"
US_INDEX_ETFS = "US index ETFs"
ONE_DAY = "1-DAY"
NINETY_FIVE_PERCENT_OF_EQUITY = {"type": "percent_of_equity", "percent": 95}
BROCK_1992 = ("Brock, Lakonishok & LeBaron 1992", "https://doi.org/10.1111/j.1540-6261.1992.tb04681.x")
FABER_2007 = ("Faber 2007", "https://doi.org/10.3905/jwm.2007.674809")
MOSKOWITZ_2012 = ("Moskowitz, Ooi & Pedersen 2012", "https://doi.org/10.1016/j.jfineco.2011.11.003")
EACH_BAR = "The rule builder checks the rules at the close of each bar."
POSITION = "Long only, with a position of 95% of equity."


@dataclass(frozen=True)
class StrategyTemplate:
    """A rule template: a named start point with sources in published research (section 9.9.2)."""

    id: str
    name: str
    kind: Literal["rules", "code"]
    entry: str
    exit: str
    defaults: str
    market: str
    bar_period: str
    evidence: str
    sources: tuple[tuple[str, str], ...]
    differs_from_source: str
    rules: StrategyRules

    def write_docstring(self) -> str:
        """The docstring at the top of the template code (section 9.9.2)."""
        sources = "\n".join(f"- {label}: {url}" for label, url in self.sources)
        return (
            f"{self.id.upper()} {self.name}: {self.entry}. Exit: {self.exit}. Defaults: {self.defaults}.\n\n"
            f"Sources:\n{sources}\n\n"
            f"Evidence: {self.evidence}\n"
            f"Market: {self.market}\n"
            f"Bar period: {self.bar_period}\n\n"
            f"Differences from the sources: {self.differs_from_source}"
        )


def make_template_rules(
    template_id: str | None, entry_items: list[dict[str, Any]], exits: dict[str, Any]
) -> StrategyRules:
    return StrategyRules.model_validate(
        {
            "format_version": 1,
            "settings": {"position_size": NINETY_FIVE_PERCENT_OF_EQUITY, "template_id": template_id},
            "entry": {"type": "group", "match": "all_of", "items": entry_items},
            "exits": exits,
        }
    )


def make_condition(left: dict[str, Any], comparison: str, right: dict[str, Any]) -> dict[str, Any]:
    return {"type": "condition", "left": left, "comparison": comparison, "right": right}


def make_indicator(key: str, parameters: dict[str, int], output: str | None = None) -> dict[str, Any]:
    return {"type": "indicator", "indicator": key, "parameters": parameters, "output": output}


# "Blank rules": no conditions, so it never buys. The position size is the one of the rule templates.
BLANK_RULES = make_template_rules(None, [], {})

STRATEGY_TEMPLATES = (
    StrategyTemplate(
        id="s1",
        name="200-day trend",
        kind="rules",
        entry="Close above SMA",
        exit="Entry conditions no longer true",
        defaults="SMA 200",
        market=US_INDEX_ETFS,
        bar_period=ONE_DAY,
        evidence="B (index), C (single stock)",
        sources=(BROCK_1992, FABER_2007),
        differs_from_source=(
            f"{EACH_BAR} Faber checks the 10-month average 1 time each month. Brock et al. test the Dow Jones "
            f"index, not an ETF. {POSITION}"
        ),
        rules=make_template_rules(
            "s1",
            [make_condition({"type": "price", "price": "close"}, "above", make_indicator("sma", {"period": 200}))],
            {"exit_when_entry_is_false": True},
        ),
    ),
    StrategyTemplate(
        id="s2",
        name="50-day range break",
        kind="rules",
        entry="High at or above Donchian channel upper",
        exit="Exit after N bars",
        defaults="Donchian 50, N = 10",
        market=US_INDEX_ETFS,
        bar_period=ONE_DAY,
        evidence="B (index), C (single stock)",
        sources=(BROCK_1992,),
        differs_from_source=(
            f"{EACH_BAR} The break uses the high of the bar, because the Donchian upper value includes the high of "
            f"this bar. Brock et al. test the Dow Jones index, not an ETF. {POSITION}"
        ),
        rules=make_template_rules(
            "s2",
            [
                make_condition(
                    {"type": "price", "price": "high"},
                    "at_or_above",
                    make_indicator("donchian_channel", {"period": 50}, "upper"),
                )
            ],
            {"exit_after_bars": 10},
        ),
    ),
    StrategyTemplate(
        id="s3",
        name="12-month time-series momentum",
        kind="rules",
        entry="12-month momentum above 0",
        exit="Entry conditions no longer true",
        defaults="Look back 252 days, skip 0 days",
        market=US_INDEX_ETFS,
        bar_period=ONE_DAY,
        evidence="B (index and futures), C (single stock)",
        sources=(MOSKOWITZ_2012,),
        differs_from_source=(
            f"{EACH_BAR} Moskowitz et al. check 1 time each month and hold for 1 month. They use the excess return, "
            "sell short when it is below 0, and scale each position to a volatility target. ATrade uses the price "
            f"return and does not sell short. {POSITION}"
        ),
        rules=make_template_rules(
            "s3",
            [
                make_condition(
                    make_indicator("momentum_12_1", {"look_back": 252, "skip": 0}),
                    "above",
                    {"type": "number", "value": 0},
                )
            ],
            {"exit_when_entry_is_false": True},
        ),
    ),
)

TEMPLATES_BY_ID = {template.id: template for template in STRATEGY_TEMPLATES}
# The values of `start_from` (section 9.6). A test checks that they match the template list.
type StartPoint = Literal["blank_code", "blank_rules", "s1", "s2", "s3"]


def find_start_rules(start_from: str) -> StrategyRules | None:
    """The rules of version 1 for a rules start point, or None for "Blank code"."""
    if start_from == BLANK_RULES_START:
        return BLANK_RULES
    template = TEMPLATES_BY_ID.get(start_from)
    return None if template is None else template.rules
