"""The multi-instrument code templates M1 to M4 (docs/architecture/strategy.md section 9.9.3, #202)."""

from typing import Any

import httpx
import pytest

from atrade.strategy.code_checks import check_strategy_code
from atrade.strategy.strategy_templates import STRATEGY_TEMPLATES, TEMPLATES_BY_ID

CODE_TEMPLATE_IDS = ["m1", "m2", "m3", "m4"]


def load_template_namespace(template_id: str) -> dict[str, Any]:
    code = TEMPLATES_BY_ID[template_id].code
    assert code is not None
    namespace: dict[str, Any] = {}
    exec(compile(code, f"{template_id}.py", "exec"), namespace)  # noqa: S102 - the template code of the platform.
    return namespace


@pytest.mark.anyio
async def test_the_template_list_has_m1_to_m4_after_s1_to_s3(web_client: httpx.AsyncClient) -> None:
    templates = (await web_client.get("/api/strategy-templates")).json()

    assert [(template["id"], template["kind"]) for template in templates[3:]] == [
        ("m1", "code"),
        ("m2", "code"),
        ("m3", "code"),
        ("m4", "code"),
    ]
    assert [template["name"] for template in templates[3:]] == [
        "Cross-sectional momentum",
        "Low volatility",
        "52-week high",
        "Volatility-adjusted momentum",
    ]
    for template in templates[3:]:
        assert template["market"] == "US top 500"
        assert template["bar_period"] == "1-DAY"
        assert template["exit"] == ""
        assert all(source["url"].startswith("https://doi.org/") for source in template["sources"])


@pytest.mark.anyio
@pytest.mark.parametrize("template_id", CODE_TEMPLATE_IDS)
async def test_a_code_template_makes_version_1_with_its_code(web_client: httpx.AsyncClient, template_id: str) -> None:
    strategy = (await web_client.post("/api/strategies", json={"name": "Start", "start_from": template_id})).json()

    version = (await web_client.get(f"/api/strategies/{strategy['id']}/versions/1")).json()

    assert (version["code"], version["source"], version["rules"]) == (TEMPLATES_BY_ID[template_id].code, "user", None)


@pytest.mark.anyio
@pytest.mark.parametrize("template_id", CODE_TEMPLATE_IDS)
async def test_the_code_of_a_code_template_starts_with_its_docstring_and_passes_the_checks(template_id: str) -> None:
    template = TEMPLATES_BY_ID[template_id]
    code = template.code
    assert code is not None

    assert code.startswith('"""')
    docstring = code.split('"""')[1]
    for part in (
        f"{template.id.upper()} {template.name}",
        "Sources:",
        "https://doi.org/",
        f"Evidence: {template.evidence}",
        "Market: US top 500",
        "Bar period: 1-DAY",
        "Differences from the sources:",
    ):
        assert part in docstring, part
    assert await check_strategy_code(code) == []


def test_only_m4_scales_the_total_position() -> None:
    assert [template.target_volatility for template in STRATEGY_TEMPLATES if template.kind == "code"] == [
        None,
        None,
        None,
        0.12,
    ]


@pytest.mark.parametrize(
    "equity_values",
    [
        [100.0, 100.0, 100.0],
        [100.0, 100.01, 100.02, 100.03],
        [100.0, 120.0, 90.0, 130.0, 80.0],
        [100.0 + index * 0.001 for index in range(200)],
    ],
)
def test_the_m4_total_position_is_at_most_100_percent(equity_values: list[float]) -> None:
    find_position_scale = load_template_namespace("m4")["find_position_scale"]

    scale = find_position_scale(equity_values)

    assert 0 < scale <= 1


def test_the_m4_total_position_goes_down_when_the_volatility_goes_up() -> None:
    find_position_scale = load_template_namespace("m4")["find_position_scale"]

    assert find_position_scale([100.0, 120.0, 90.0, 130.0, 80.0]) < 0.2
