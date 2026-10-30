"""Strategy versions saved by the AI assistant and the discarded mark (docs/architecture/assistant.md 25.5).

The tests save AI assistant versions with `save_ai_assistant_version`, the function that port 8001 calls (#181).
No real model provider runs: the conversations come from the routes with the fake assistant service.
"""

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import psycopg
import pytest

from atrade.strategy import CodeProblem, save_ai_assistant_version
from tests.assistant.assistant_app import create_conversation, create_strategy, open_assistant_client
from tests.fakes.assistant import FakeAssistantService
from tests.fakes.clock import FixedClock


@pytest.fixture
async def client(database_url: str, clock: FixedClock, frontend_build_dir: Path) -> AsyncIterator[httpx.AsyncClient]:
    async with open_assistant_client(
        database_url=database_url,
        clock=clock,
        frontend_build_dir=frontend_build_dir,
        assistant_service=FakeAssistantService(),
    ) as assistant_client:
        yield assistant_client


async def read_template(client: httpx.AsyncClient, strategy_id: int) -> str:
    code: str = (await client.get(f"/api/strategies/{strategy_id}/versions/1")).json()["code"]
    return code


async def save_assistant_version(client: httpx.AsyncClient, *, database_url: str, clock: FixedClock) -> tuple[int, int]:
    """Saves version 2 of a new strategy as the AI assistant. Returns the strategy ID and the conversation ID."""
    strategy_id = await create_strategy(client, "Moving average")
    conversation_id = await create_conversation(client, strategy_id)
    code = (await read_template(client, strategy_id)).replace("average_period: int = 20", "average_period: int = 30")
    saved = await save_ai_assistant_version(
        database_url=database_url,
        strategy_id=strategy_id,
        code=code,
        conversation_id=conversation_id,
        created_at_utc=clock.read_now_utc(),
    )
    assert saved is not None
    assert not isinstance(saved, list)
    return strategy_id, conversation_id


@pytest.mark.anyio
async def test_an_ai_assistant_save_records_the_source_ai_assistant_and_the_conversation(
    client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    strategy_id, conversation_id = await save_assistant_version(client, database_url=database_url, clock=clock)

    version_2 = (await client.get(f"/api/strategies/{strategy_id}/versions/2")).json()
    assert (version_2["source"], version_2["conversation_id"], version_2["discarded"]) == (
        "ai_assistant",
        conversation_id,
        False,
    )
    summaries = (await client.get(f"/api/strategies/{strategy_id}")).json()["versions"]
    assert [(summary["source"], summary["conversation_id"]) for summary in summaries] == [
        ("user", None),
        ("ai_assistant", conversation_id),
    ]


@pytest.mark.anyio
async def test_an_ai_assistant_save_gets_the_problems_of_the_checks_before_save(
    client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    strategy_id = await create_strategy(client, "Moving average")
    conversation_id = await create_conversation(client, strategy_id)

    saved = await save_ai_assistant_version(
        database_url=database_url,
        strategy_id=strategy_id,
        code="def broken(:\n",
        conversation_id=conversation_id,
        created_at_utc=clock.read_now_utc(),
    )

    assert isinstance(saved, list)
    assert all(isinstance(problem, CodeProblem) for problem in saved)
    assert len((await client.get(f"/api/strategies/{strategy_id}")).json()["versions"]) == 1


@pytest.mark.anyio
async def test_a_code_save_on_port_8000_records_the_source_user_and_no_conversation(
    client: httpx.AsyncClient,
) -> None:
    strategy_id = await create_strategy(client, "Moving average")
    code = (await read_template(client, strategy_id)).replace("average_period: int = 20", "average_period: int = 30")

    saved = (await client.post(f"/api/strategies/{strategy_id}/versions", json={"code": code})).json()

    assert (saved["source"], saved["conversation_id"], saved["discarded"]) == ("user", None, False)


@pytest.mark.anyio
async def test_a_delete_of_the_conversation_keeps_the_version_and_its_backtests_without_the_conversation(
    client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    strategy_id, conversation_id = await save_assistant_version(client, database_url=database_url, clock=clock)
    version_id = (await client.get(f"/api/strategies/{strategy_id}/versions/2")).json()["id"]
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO backtest (strategy_version_id, symbol, exchange, currency, bar_period, start_utc, end_utc,
                paper_capital_usd, status, created_at_utc, conversation_id)
            VALUES (%(version_id)s, 'BTEST', 'ARCA', 'USD', '1-DAY', %(now)s, %(now)s + interval '1 day', 10000,
                'queued', %(now)s,
                %(conversation_id)s)
            """,
            {"version_id": version_id, "now": clock.read_now_utc(), "conversation_id": conversation_id},
        )

    response = await client.delete(f"/api/assistant/conversations/{conversation_id}")

    assert response.status_code == httpx.codes.NO_CONTENT
    version_2 = (await client.get(f"/api/strategies/{strategy_id}/versions/2")).json()
    assert (version_2["source"], version_2["conversation_id"]) == ("ai_assistant", None)
    backtests = (await client.get("/api/backtests")).json()
    assert [(backtest["strategy_version_id"], backtest["conversation_id"]) for backtest in backtests] == [
        (version_id, None)
    ]


@pytest.mark.anyio
async def test_discard_marks_an_ai_assistant_version_and_keeps_the_row(
    client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    strategy_id, conversation_id = await save_assistant_version(client, database_url=database_url, clock=clock)
    before = (await client.get(f"/api/strategies/{strategy_id}/versions/2")).json()

    response = await client.post(f"/api/strategies/{strategy_id}/versions/2/discard")

    assert response.status_code == httpx.codes.OK
    assert response.json() == {**before, "discarded": True}
    assert (await client.get(f"/api/strategies/{strategy_id}/versions/2")).json()["discarded"] is True
    summaries = (await client.get(f"/api/strategies/{strategy_id}")).json()["versions"]
    assert [summary["discarded"] for summary in summaries] == [False, True]
    assert [summary["conversation_id"] for summary in summaries] == [None, conversation_id]


@pytest.mark.anyio
async def test_a_second_discard_answers_200_with_the_discarded_version(
    client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    strategy_id, _ = await save_assistant_version(client, database_url=database_url, clock=clock)
    await client.post(f"/api/strategies/{strategy_id}/versions/2/discard")

    response = await client.post(f"/api/strategies/{strategy_id}/versions/2/discard")

    assert response.status_code == httpx.codes.OK
    assert response.json()["discarded"] is True


@pytest.mark.anyio
async def test_discard_of_a_missing_version_answers_404(client: httpx.AsyncClient) -> None:
    strategy_id = await create_strategy(client, "Moving average")

    response = await client.post(f"/api/strategies/{strategy_id}/versions/9/discard")

    assert response.status_code == httpx.codes.NOT_FOUND
    assert response.json() == {"detail": "Strategy version not found."}


@pytest.mark.anyio
async def test_discard_of_a_version_that_the_ai_assistant_did_not_save_answers_409(client: httpx.AsyncClient) -> None:
    strategy_id = await create_strategy(client, "Moving average")

    response = await client.post(f"/api/strategies/{strategy_id}/versions/1/discard")

    assert response.status_code == httpx.codes.CONFLICT
    assert response.json() == {"detail": "Only a strategy version that the AI assistant saved can be discarded."}
    assert (await client.get(f"/api/strategies/{strategy_id}/versions/1")).json()["discarded"] is False


@pytest.mark.anyio
async def test_the_trigger_refuses_each_update_of_a_strategy_version(
    client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    await save_assistant_version(client, database_url=database_url, clock=clock)

    for assignment in ("code = 'x = 1'", "rules = '{}'", "source = 'user'", "conversation_id = NULL"):
        with (
            psycopg.connect(database_url, autocommit=True) as connection,
            pytest.raises(psycopg.errors.RaiseException, match="append-only"),
        ):
            connection.execute(f"UPDATE strategy_version SET {assignment}")  # pyright: ignore[reportArgumentType]


@pytest.mark.anyio
async def test_a_strategy_delete_deletes_its_ai_assistant_versions_discard_marks_and_conversations(
    client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    strategy_id, _ = await save_assistant_version(client, database_url=database_url, clock=clock)
    await client.post(f"/api/strategies/{strategy_id}/versions/2/discard")

    response = await client.delete(f"/api/strategies/{strategy_id}")

    assert response.status_code == httpx.codes.NO_CONTENT
    with psycopg.connect(database_url) as connection:
        counts = connection.execute(
            """
            SELECT (SELECT count(*) FROM strategy_version), (SELECT count(*) FROM strategy_version_discard),
                (SELECT count(*) FROM assistant_conversation)
            """
        ).fetchone()
    assert counts == (0, 0, 0)
