"""The custom indicator routes on port 8001 (docs/architecture/assistant.md 25.3.3, indicator.md section 23.10.6).

The browser client calls port 8000 with the fake assistant service. The assistant client calls port 8001 with the
conversation header, as the assistant service does.
"""

from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.app.test_assistant_port import CONVERSATION_HEADER, open_both_clients
from tests.app.test_assistant_screens import start_conversation
from tests.fakes.clock import FixedClock

BASE_PATH = "/api/custom-indicators"
RATIO = {
    "name": "Distance to SMA",
    "expression": "close / sma(50) - 1",
    "chart_placement": "own",
    "value_description": "The close over SMA(50), minus 1, as a fraction.",
}


def changed_ratio() -> dict[str, str]:
    return {**RATIO, "expression": "close / sma(20) - 1"}


async def create_on_port_8001(assistant: httpx.AsyncClient, headers: dict[str, str]) -> dict[str, Any]:
    response = await assistant.post(BASE_PATH, json=RATIO, headers=headers)
    assert response.status_code == httpx.codes.CREATED, response.text
    return response.json()


@pytest.mark.anyio
async def test_a_new_custom_indicator_on_port_8001_records_the_conversation_and_is_not_kept(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        created = await create_on_port_8001(assistant, headers)
        catalog = (await assistant.get("/api/screen-indicators")).json()
        listed = (await assistant.get(BASE_PATH)).json()
        read = (await assistant.get(f"{BASE_PATH}/{created['custom_indicator_id']}")).json()

    assert created["kept"] is False
    assert created["assistant_conversation_id"] == int(headers[CONVERSATION_HEADER])
    # A name has no parentheses, so port 8001 adds no " (AI)" (indicator.md section 23.10.6).
    assert created["name"] == RATIO["name"]
    assert listed == [created]
    assert read == created
    assert catalog[-1]["key"] == created["key"]
    assert catalog[-1]["formula"]["expression"] == RATIO["expression"]


@pytest.mark.anyio
async def test_a_custom_indicator_of_the_user_is_kept_and_has_no_conversation(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, _):
        created = (await browser.post(BASE_PATH, json=RATIO)).json()

    assert created["kept"] is True
    assert created["assistant_conversation_id"] is None


@pytest.mark.anyio
async def test_a_create_on_port_8001_needs_a_conversation_that_exists(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (_, assistant):
        without_header = await assistant.post(BASE_PATH, json=RATIO)
        unknown = await assistant.post(BASE_PATH, json=RATIO, headers={CONVERSATION_HEADER: "999"})
        listed = (await assistant.get(BASE_PATH)).json()

    assert without_header.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert unknown.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert listed == []


@pytest.mark.anyio
async def test_the_ai_changes_its_own_custom_indicator_while_the_user_has_not_kept_it(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        created = await create_on_port_8001(assistant, headers)

        changed = await assistant.put(
            f"{BASE_PATH}/{created['custom_indicator_id']}", json=changed_ratio(), headers=headers
        )

    assert changed.status_code == httpx.codes.OK
    assert changed.json() == {**created, "expression": "close / sma(20) - 1"}


@pytest.mark.anyio
async def test_keep_marks_the_custom_indicator_kept_and_port_8001_cannot_change_it_after_that(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        created = await create_on_port_8001(assistant, headers)
        path = f"{BASE_PATH}/{created['custom_indicator_id']}"

        kept = await browser.post(f"{path}/keep")
        kept_again = await browser.post(f"{path}/keep")
        refused = await assistant.put(path, json=changed_ratio(), headers=headers)
        keep_on_port_8001 = await assistant.post(f"{path}/keep", headers=headers)
        missing = await browser.post(f"{BASE_PATH}/999/keep")
        after = (await browser.get(path)).json()

    assert kept.status_code == httpx.codes.OK
    assert kept.json() == {**created, "kept": True}
    assert kept_again.status_code == httpx.codes.OK
    assert refused.status_code == httpx.codes.FORBIDDEN
    assert f"custom indicator {created['custom_indicator_id']}" in refused.json()["detail"]
    assert keep_on_port_8001.status_code in {httpx.codes.NOT_FOUND, httpx.codes.METHOD_NOT_ALLOWED}
    assert missing.status_code == httpx.codes.NOT_FOUND
    assert after["expression"] == RATIO["expression"]


@pytest.mark.anyio
async def test_port_8001_cannot_change_a_custom_indicator_of_another_conversation_or_of_the_user(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        first_headers = await start_conversation(browser, "First")
        second_headers = await start_conversation(browser, "Second")
        created = await create_on_port_8001(assistant, first_headers)
        of_user = (await browser.post(BASE_PATH, json={**RATIO, "name": "Of the user"})).json()

        other_conversation = await assistant.put(
            f"{BASE_PATH}/{created['custom_indicator_id']}", json=changed_ratio(), headers=second_headers
        )
        user_indicator = await assistant.put(
            f"{BASE_PATH}/{of_user['custom_indicator_id']}",
            json={**changed_ratio(), "name": "Of the user"},
            headers=first_headers,
        )
        unknown = await assistant.put(f"{BASE_PATH}/999", json=RATIO, headers=first_headers)
        # The refusal comes before the check: a wrong expression gets the same answer.
        wrong_expression = await assistant.put(
            f"{BASE_PATH}/{of_user['custom_indicator_id']}",
            json={**RATIO, "expression": "foo"},
            headers=first_headers,
        )
        listed = (await browser.get(BASE_PATH)).json()

    assert other_conversation.status_code == httpx.codes.FORBIDDEN
    assert user_indicator.status_code == httpx.codes.FORBIDDEN
    assert wrong_expression.status_code == httpx.codes.FORBIDDEN
    assert unknown.status_code == httpx.codes.NOT_FOUND
    assert {row["expression"] for row in listed} == {RATIO["expression"]}


@pytest.mark.anyio
async def test_a_delete_of_the_conversation_keeps_the_custom_indicator_and_port_8001_cannot_change_it(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        other_headers = await start_conversation(browser, "Other")
        created = await create_on_port_8001(assistant, headers)
        path = f"{BASE_PATH}/{created['custom_indicator_id']}"

        deleted = await browser.delete(f"/api/assistant/conversations/{headers[CONVERSATION_HEADER]}")
        after = (await browser.get(path)).json()
        refused = await assistant.put(path, json=changed_ratio(), headers=other_headers)

    assert deleted.status_code == httpx.codes.NO_CONTENT
    assert after == {**created, "assistant_conversation_id": None}
    assert refused.status_code == httpx.codes.FORBIDDEN


@pytest.mark.anyio
async def test_the_check_on_port_8001_gives_located_problems_and_saves_nothing(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        correct = await assistant.post(f"{BASE_PATH}/check", json=RATIO)
        wrong = await assistant.post(f"{BASE_PATH}/check", json={**RATIO, "expression": "close + foo"})
        created = await create_on_port_8001(assistant, headers)
        same_name = await assistant.post(f"{BASE_PATH}/check", json=RATIO)
        own_name = await assistant.post(
            f"{BASE_PATH}/check", json=RATIO, params={"custom_indicator_id": created["custom_indicator_id"]}
        )
        listed = (await browser.get(BASE_PATH)).json()

    assert correct.status_code == httpx.codes.OK
    assert correct.json()["problems"] == []
    assert correct.json()["look_back_bars"] == 50
    problem = wrong.json()["problems"][0]
    assert problem["location"] == ["expression"]
    assert "Column" in problem["message"]
    assert wrong.json()["look_back_bars"] is None
    assert same_name.json()["problems"][0]["location"] == ["name"]
    assert own_name.json()["problems"] == []
    assert listed == [created]


@pytest.mark.anyio
async def test_a_create_or_a_change_on_port_8001_gives_the_problem_list(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        created = await create_on_port_8001(assistant, headers)
        same_name = await assistant.post(BASE_PATH, json=RATIO, headers=headers)
        wrong = await assistant.put(
            f"{BASE_PATH}/{created['custom_indicator_id']}", json={**RATIO, "expression": "foo"}, headers=headers
        )

    assert same_name.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert same_name.json()["problems"][0]["location"] == ["name"]
    assert wrong.status_code == httpx.codes.UNPROCESSABLE_ENTITY
    assert wrong.json()["problems"][0]["location"] == ["expression"]


@pytest.mark.anyio
async def test_port_8001_has_no_delete_route_for_a_custom_indicator(
    database_url: str, clock: FixedClock, frontend_build_dir: Path
) -> None:
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        headers = await start_conversation(browser)
        created = await create_on_port_8001(assistant, headers)
        path = f"{BASE_PATH}/{created['custom_indicator_id']}"

        refused = await assistant.delete(path, headers=headers)
        after = await browser.get(path)

    assert refused.status_code == httpx.codes.METHOD_NOT_ALLOWED
    assert after.status_code == httpx.codes.OK
