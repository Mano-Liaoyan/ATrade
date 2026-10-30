"""The rules of the rule builder and their format check (docs/architecture/strategy.md section 9.8.2, #172).

Pydantic checks the format. A rule that does not match it gives `422` on the routes. An indicator operand is a
stored indicator reference (docs/architecture/indicator.md section 23.6): `check_indicator_reference` checks it.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, model_validator

from atrade.indicator import check_indicator_reference

RULES_FORMAT_VERSION = 1
MAX_TEMPLATE_ID_LENGTH = 100

type Number = StrictInt | StrictFloat
type Comparison = Literal["above", "below", "at_or_above", "at_or_below", "crosses_above", "crosses_below"]
type PriceName = Literal["close", "open", "high", "low"]
type GroupMatch = Literal["all_of", "any_of"]


class RuleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PriceOperand(RuleModel):
    type: Literal["price"]
    price: PriceName


class NumberOperand(RuleModel):
    type: Literal["number"]
    value: Annotated[Number, Field(allow_inf_nan=False)]


class IndicatorOperand(RuleModel):
    """A stored indicator reference. A single-line indicator without `output` uses `value`."""

    type: Literal["indicator"]
    indicator: str
    parameters: dict[str, Number] = Field(default_factory=dict[str, Number])
    output: str | None = None

    @model_validator(mode="after")
    def check_reference(self) -> IndicatorOperand:
        problems = check_indicator_reference(self.model_dump(exclude={"type"}, exclude_none=True))
        if problems:
            messages = [f"{'.'.join(problem.location) or 'indicator'}: {problem.message}" for problem in problems]
            raise ValueError(" ".join(messages))
        return self


type LeftOperand = Annotated[PriceOperand | IndicatorOperand, Field(discriminator="type")]
type RightOperand = Annotated[PriceOperand | IndicatorOperand | NumberOperand, Field(discriminator="type")]


class RuleCondition(RuleModel):
    type: Literal["condition"]
    left: LeftOperand
    comparison: Comparison
    right: RightOperand


class InnerRuleGroup(RuleModel):
    """A group in a group. It holds conditions only, so the maximum depth is 1 nested group."""

    type: Literal["group"]
    match: GroupMatch
    items: list[RuleCondition]


class RuleGroup(RuleModel):
    type: Literal["group"]
    match: GroupMatch
    items: list[Annotated[RuleCondition | InnerRuleGroup, Field(discriminator="type")]]


class FixedShares(RuleModel):
    type: Literal["fixed_shares"]
    shares: Annotated[StrictInt, Field(ge=1)]


class PercentOfEquity(RuleModel):
    """The quantity is equity x percent / close price, rounded down to whole shares."""

    type: Literal["percent_of_equity"]
    percent: Annotated[Number, Field(gt=0, le=100)]


class RuleSettings(RuleModel):
    position_size: Annotated[FixedShares | PercentOfEquity, Field(discriminator="type")]
    template_id: Annotated[str, Field(min_length=1, max_length=MAX_TEMPLATE_ID_LENGTH)] | None = None


class RuleExits(RuleModel):
    """The exit items. Each item that is not null (or `true`) is selected."""

    stop_loss_percent: Annotated[Number, Field(gt=0, lt=100)] | None = None
    take_profit_percent: Annotated[Number, Field(gt=0)] | None = None
    exit_after_bars: Annotated[StrictInt, Field(ge=1)] | None = None
    exit_when_entry_is_false: bool = False
    exit_group: RuleGroup | None = None


class StrategyRules(RuleModel):
    format_version: Literal[1]
    settings: RuleSettings
    entry: RuleGroup
    exits: RuleExits
