"""The screen routes on port 8001 (docs/architecture/assistant.md 25.3.3, docs/architecture/screen.md 24.8).

The browser client calls port 8000 with the fake assistant service. The assistant client calls port 8001 with the
conversation header, as the assistant service does.
"""

from typing import Any

import httpx
import pytest

from tests.app.test_assistant_port import CONVERSATION_HEADER, open_both_clients
from tests.assistant.assistant_app import create_conversation, create_strategy
from tests.backtest.test_backtest_routes import save_test_strategy_version
from tests.backtest.universe_data import make_universe_request, save_universe_test_data
from tests.fakes.clock import FixedClock
from tests.screen.test_screen_routes import momentum_definition
from tests.screen.test_screen_run_routes import add_to_watchlist, make_definition, save_daily_bars, stock


def screen_body(name: str = "Momentum leaders") -> dict[str, Any]:
    return {"name": name, "market": "US", "definition": momentum_definition()}


async def start_conversation(browser: httpx.AsyncClient, strategy_name: str = "Moving average") -> dict[str, str]:
    strategy_id = await create_strategy(browser, strategy_name)
    conversation_id = await create_conversation(browser, strategy_id)
    return {CONVERSATION_HEADER: str(conversation_id)}


@pytest.mark.anyio
async def test_a_new_screen_on_port_8001_records_the_conversation_and_is_not_kept(
    database_url: str, clock: FixedClock, frontend_build_dir: Any
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)

        response = await assistant.post("/api/screens", json=screen_body(), headers=headers)

    assert response.status_code == httpx.codes.CREATED, response.text
    screen = response.json()
    assert (screen["name"], screen["kept"], screen["assistant_conversation_id"]) == (
        "Momentum leaders (AI)",
        False,
        int(headers[CONVERSATION_HEADER]),
    )


@pytest.mark.anyio
async def test_a_new_screen_on_port_8001_adds_a_number_when_the_name_is_in_use(
    database_url: str, clock: FixedClock, frontend_build_dir: Any
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        await browser.post("/api/screens", json=screen_body())

        names = [
            (await assistant.post("/api/screens", json=screen_body(), headers=headers)).json()["name"] for _ in range(3)
        ]

    assert names == ["Momentum leaders (AI)", "Momentum leaders (AI 2)", "Momentum leaders (AI 3)"]


@pytest.mark.anyio
async def test_a_new_screen_on_port_8001_without_a_known_conversation_is_refused(
    database_url: str, clock: FixedClock, frontend_build_dir: Any
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (_browser, assistant):
        without_header = await assistant.post("/api/screens", json=screen_body())
        unknown = await assistant.post("/api/screens", json=screen_body(), headers={CONVERSATION_HEADER: "999"})

    assert without_header.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert unknown.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert unknown.json() == {"detail": "Conversation 999 does not exist."}


@pytest.mark.anyio
async def test_a_change_on_port_8001_is_only_for_an_unkept_screen_of_the_same_conversation(
    database_url: str, clock: FixedClock, frontend_build_dir: Any
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        other_headers = await start_conversation(browser, "Breakout")
        user_screen = (await browser.post("/api/screens", json=screen_body("Value"))).json()["id"]
        own_screen = (await assistant.post("/api/screens", json=screen_body(), headers=headers)).json()["id"]
        other_screen = (await assistant.post("/api/screens", json=screen_body(), headers=other_headers)).json()["id"]
        kept_screen = (await assistant.post("/api/screens", json=screen_body("Kept"), headers=headers)).json()["id"]
        assert (await browser.post(f"/api/screens/{kept_screen}/keep")).status_code == httpx.codes.OK
        change = {"name": "Momentum leaders (AI)", "definition": momentum_definition()}

        statuses = {
            name: (await assistant.put(f"/api/screens/{screen_id}", json=change, headers=headers)).status_code
            for name, screen_id in [
                ("user", user_screen),
                ("kept", kept_screen),
                ("other conversation", other_screen),
                ("own", own_screen),
            ]
        }
        refused = await assistant.put(f"/api/screens/{user_screen}", json=change, headers=headers)
        user_screen_after = (await browser.get(f"/api/screens/{user_screen}")).json()

    assert statuses == {
        "user": httpx.codes.FORBIDDEN,
        "kept": httpx.codes.FORBIDDEN,
        "other conversation": httpx.codes.FORBIDDEN,
        "own": httpx.codes.OK,
    }
    assert refused.json()["detail"].startswith(f"The AI assistant cannot change screen {user_screen}.")
    assert user_screen_after["name"] == "Value"


@pytest.mark.anyio
async def test_a_change_on_port_8001_of_a_screen_that_does_not_exist_gives_404(
    database_url: str, clock: FixedClock, frontend_build_dir: Any
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        response = await assistant.put(
            "/api/screens/999", json={"name": "X", "definition": momentum_definition()}, headers=headers
        )

    assert response.status_code == httpx.codes.NOT_FOUND


async def run_on_port_8001(
    database_url: str, browser: httpx.AsyncClient, assistant: httpx.AsyncClient, headers: dict[str, str]
) -> dict[str, Any]:
    apple, microsoft = stock("AAPL"), stock("MSFT")
    await save_daily_bars(database_url, apple, "30")
    await save_daily_bars(database_url, microsoft, "20")
    add_to_watchlist(database_url, apple, microsoft)
    body = {"name": "Watchlist", "market": "US", "definition": make_definition()}
    screen_id = (await assistant.post("/api/screens", json=body, headers=headers)).json()["id"]
    response = await assistant.post(f"/api/screens/{screen_id}/runs", headers=headers)
    assert response.status_code == httpx.codes.CREATED, response.text
    result: dict[str, Any] = response.json()
    return result


@pytest.mark.anyio
async def test_a_run_on_port_8001_records_the_conversation_on_the_screen_result(
    database_url: str, clock: FixedClock, frontend_build_dir: Any
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        result = await run_on_port_8001(database_url, browser, assistant, headers)
        read = (await assistant.get(f"/api/screen-results/{result['id']}")).json()

    assert result["assistant_conversation_id"] == int(headers[CONVERSATION_HEADER])
    assert read["assistant_conversation_id"] == int(headers[CONVERSATION_HEADER])
    assert [row["symbol"] for row in read["rows"]] == ["AAPL", "MSFT"]


@pytest.mark.anyio
async def test_a_delete_of_the_conversation_keeps_its_screens_and_screen_results(
    database_url: str, clock: FixedClock, frontend_build_dir: Any
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        result = await run_on_port_8001(database_url, browser, assistant, headers)

        deleted = await browser.delete(f"/api/assistant/conversations/{headers[CONVERSATION_HEADER]}")
        screen = (await browser.get(f"/api/screens/{result['screen_id']}")).json()
        read = (await browser.get(f"/api/screen-results/{result['id']}")).json()

    assert deleted.status_code == httpx.codes.NO_CONTENT
    assert (screen["name"], screen["assistant_conversation_id"]) == ("Watchlist (AI)", None)
    assert read["assistant_conversation_id"] is None


@pytest.mark.anyio
async def test_a_new_screen_on_port_8001_with_no_room_for_the_ai_suffix_gives_a_name_problem(
    database_url: str, clock: FixedClock, frontend_build_dir: Any
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)

        too_long = await assistant.post("/api/screens", json=screen_body("M" * 96), headers=headers)
        fits = await assistant.post("/api/screens", json=screen_body("M" * 95), headers=headers)
        no_room_for_number = await assistant.post("/api/screens", json=screen_body("M" * 95), headers=headers)

    assert too_long.status_code == httpx.codes.UNPROCESSABLE_ENTITY, too_long.text
    assert [problem["location"] for problem in too_long.json()["problems"]] == [["name"]]
    assert fits.status_code == httpx.codes.CREATED, fits.text
    assert fits.json()["name"] == "M" * 95 + " (AI)"
    assert no_room_for_number.status_code == httpx.codes.UNPROCESSABLE_ENTITY, no_room_for_number.text
    assert [problem["location"] for problem in no_room_for_number.json()["problems"]] == [["name"]]


@pytest.mark.anyio
async def test_keep_marks_the_screen_kept_and_port_8001_cannot_change_it_after_that(
    database_url: str, clock: FixedClock, frontend_build_dir: Any
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        screen_id = (await assistant.post("/api/screens", json=screen_body(), headers=headers)).json()["id"]

        kept = await browser.post(f"/api/screens/{screen_id}/keep")
        kept_again = await browser.post(f"/api/screens/{screen_id}/keep")
        change = await assistant.put(
            f"/api/screens/{screen_id}",
            json={"name": "Momentum leaders (AI)", "definition": momentum_definition()},
            headers=headers,
        )
        keep_on_port_8001 = await assistant.post(f"/api/screens/{screen_id}/keep", headers=headers)
        missing = await browser.post("/api/screens/999/keep")

    assert kept.status_code == httpx.codes.OK, kept.text
    assert (kept.json()["id"], kept.json()["kept"]) == (screen_id, True)
    assert kept_again.status_code == httpx.codes.OK
    assert change.status_code == httpx.codes.FORBIDDEN
    assert keep_on_port_8001.status_code in {httpx.codes.NOT_FOUND, httpx.codes.METHOD_NOT_ALLOWED}
    assert missing.status_code == httpx.codes.NOT_FOUND


@pytest.mark.anyio
async def test_discard_deletes_the_screen_of_the_ai_assistant_and_its_old_backtest_keeps_a_copy(
    database_url: str, clock: FixedClock, frontend_build_dir: Any
) -> None:
    save_universe_test_data(database_url)
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        body = {"name": "Quarter", "market": "US", "definition": make_definition(start="quarter_universe")}
        screen_id = (await assistant.post("/api/screens", json=body, headers=headers)).json()["id"]
        saved = await save_test_strategy_version(browser)
        started = await browser.post(
            "/api/backtests",
            json=make_universe_request(saved["strategy_version_id"], universe_kind="screen", screen_id=screen_id),
        )
        assert started.status_code == httpx.codes.CREATED, started.text

        discarded = await browser.delete(f"/api/screens/{screen_id}")
        screen = await browser.get(f"/api/screens/{screen_id}")
        backtest = (await browser.get(f"/api/backtests/{started.json()['id']}")).json()

    assert discarded.status_code == httpx.codes.NO_CONTENT
    assert screen.status_code == httpx.codes.NOT_FOUND
    assert backtest["universe_screen"] == started.json()["universe_screen"]
    assert backtest["universe_screen"]["name"] == "Quarter (AI)"
