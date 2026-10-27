"""Checks before save through the HTTP route: each failed check blocks the save and names the line and the reason."""

import httpx
import pytest

VALID_CODE = """from nautilus_trader.config import StrategyConfig
from nautilus_trader.trading import Strategy


class EmptyConfig(StrategyConfig):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class EmptyStrategy(Strategy):
    pass
"""


async def create_strategy(web_client: httpx.AsyncClient) -> int:
    response = await web_client.post("/api/strategies", json={"name": "Checked"})
    return response.json()["id"]


async def save_code(web_client: httpx.AsyncClient, code: str) -> httpx.Response:
    strategy_id = await create_strategy(web_client)
    return await web_client.post(f"/api/strategies/{strategy_id}/versions", json={"code": code})


@pytest.mark.anyio
async def test_saves_code_that_passes_all_checks(web_client: httpx.AsyncClient) -> None:
    response = await save_code(web_client, VALID_CODE)

    assert response.status_code == 201
    assert response.json()["version_number"] == 2


@pytest.mark.anyio
async def test_refuses_code_with_a_syntax_error(web_client: httpx.AsyncClient) -> None:
    code = VALID_CODE + "\n\ndef broken(:\n    pass\n"

    response = await save_code(web_client, code)

    assert response.status_code == 422
    assert response.json() == {"problems": [{"line": 14, "message": "Syntax error: invalid syntax."}]}


@pytest.mark.anyio
async def test_refuses_code_without_a_strategy_subclass(web_client: httpx.AsyncClient) -> None:
    code = VALID_CODE.replace("class EmptyStrategy(Strategy):\n    pass\n", "")
    code = code.replace("from nautilus_trader.trading import Strategy\n", "")

    response = await save_code(web_client, code)

    assert response.status_code == 422
    assert response.json() == {
        "problems": [{"line": 1, "message": "The code must have exactly 1 Strategy subclass. It has none."}]
    }


@pytest.mark.anyio
async def test_refuses_code_with_two_strategy_subclasses(web_client: httpx.AsyncClient) -> None:
    code = VALID_CODE + "\n\nclass SecondStrategy(Strategy):\n    pass\n"

    response = await save_code(web_client, code)

    assert response.status_code == 422
    assert response.json() == {
        "problems": [
            {"line": 14, "message": "The code must have exactly 1 Strategy subclass. SecondStrategy is one more."}
        ]
    }


@pytest.mark.anyio
async def test_refuses_code_with_two_config_subclasses(web_client: httpx.AsyncClient) -> None:
    code = VALID_CODE + "\n\nclass SecondConfig(StrategyConfig):\n    pass\n"

    response = await save_code(web_client, code)

    assert response.status_code == 422
    assert response.json() == {
        "problems": [
            {"line": 14, "message": "The code must have exactly 1 StrategyConfig subclass. SecondConfig is one more."}
        ]
    }


@pytest.mark.anyio
async def test_refuses_code_without_a_config_subclass(web_client: httpx.AsyncClient) -> None:
    code = VALID_CODE.replace("class EmptyConfig(StrategyConfig):", "class EmptyConfig:")
    code = code.replace("from nautilus_trader.config import StrategyConfig\n", "")

    response = await save_code(web_client, code)

    assert response.status_code == 422
    assert response.json() == {
        "problems": [{"line": 1, "message": "The code must have exactly 1 StrategyConfig subclass. It has none."}]
    }


@pytest.mark.anyio
async def test_refuses_code_with_ruff_f_errors(web_client: httpx.AsyncClient) -> None:
    code = "import os\n" + VALID_CODE.replace("    pass\n", "    limit = undefined_limit\n")

    response = await save_code(web_client, code)

    assert response.status_code == 422
    assert response.json() == {
        "problems": [
            {"line": 1, "message": "F401 `os` imported but unused"},
            {"line": 12, "message": "F821 Undefined name `undefined_limit`"},
        ]
    }


@pytest.mark.anyio
async def test_refused_code_makes_no_version(web_client: httpx.AsyncClient) -> None:
    strategy_id = await create_strategy(web_client)

    await web_client.post(f"/api/strategies/{strategy_id}/versions", json={"code": "def broken(:\n"})

    strategy = (await web_client.get(f"/api/strategies/{strategy_id}")).json()
    assert [version["version_number"] for version in strategy["versions"]] == [1]
