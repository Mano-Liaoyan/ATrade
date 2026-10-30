"""The forward-test worker: it compares the desired state with the actual state, starts and stops child processes,
and writes the actual state (docs/architecture.md sections 12.3, 12.4, 12.6, 12.7).

Real PostgreSQL. The function that starts a child process is a fake (section 17.4).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import psycopg
import pytest

from atrade.forward_test import GATEWAY_UNREACHABLE_EXIT_CODE, PAPER_CHECK_FAILED_EXIT_CODE, ForwardTestWorker
from tests.fakes.clock import FixedClock
from tests.fakes.forward_test_child import FakeChildStarter
from tests.forward_test.test_forward_test_routes import (
    FORWARD_TESTS_PATH,
    make_start_request,
    save_test_strategy_version,
)

type JsonObject = dict[str, Any]


async def start_forward_test(web_client: httpx.AsyncClient, *, symbol: str = "AAPL") -> JsonObject:
    strategy_version_id = await save_test_strategy_version(web_client)
    response = await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol=symbol))
    return response.json()


async def read_forward_test(web_client: httpx.AsyncClient, forward_test_id: int) -> JsonObject:
    forward_tests = (await web_client.get(FORWARD_TESTS_PATH)).json()
    [forward_test] = [item for item in forward_tests if item["id"] == forward_test_id]
    return forward_test


def make_worker(database_url: str, clock: FixedClock, child_starter: FakeChildStarter) -> ForwardTestWorker:
    return ForwardTestWorker(database_url=database_url, clock=clock, start_child=child_starter.start_child)


@pytest.mark.anyio
async def test_starts_one_child_for_a_new_forward_test(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    child_starter = FakeChildStarter()
    worker = make_worker(database_url, clock, child_starter)

    await worker.compare_states()
    await worker.compare_states()

    assert child_starter.read_started() == [(forward_test["id"], "run")]
    assert (await read_forward_test(web_client, forward_test["id"]))["status"] == "running"


@pytest.mark.anyio
async def test_stop_asks_the_child_to_stop_and_frees_the_client_id_after_it_ends(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    child_starter = FakeChildStarter()
    worker = make_worker(database_url, clock, child_starter)
    await worker.compare_states()
    [child] = child_starter.children

    await web_client.post(f"{FORWARD_TESTS_PATH}/{forward_test['id']}/stop")
    await worker.compare_states()

    assert child.is_stop_requested
    stopping = await read_forward_test(web_client, forward_test["id"])
    assert (stopping["status"], stopping["client_id"]) == ("stopping", 10)

    # The child stopped the LiveNode and cancelled its orders.
    child.exit_code = 0
    await worker.compare_states()

    stopped = await read_forward_test(web_client, forward_test["id"])
    assert (stopped["status"], stopped["client_id"]) == ("stopped", None)
    assert stopped["stopped_at_utc"] == "2026-01-02T03:04:05Z"


@pytest.mark.anyio
async def test_a_free_client_id_goes_to_the_next_start(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    for symbol in ["AAPL", "MSFT"]:
        await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol=symbol))
    [second, first] = (await web_client.get(FORWARD_TESTS_PATH)).json()
    child_starter = FakeChildStarter(is_ending_children_at_once=True)
    worker = make_worker(database_url, clock, child_starter)
    await worker.compare_states()
    await web_client.post(f"{FORWARD_TESTS_PATH}/{first['id']}/stop")
    await worker.compare_states()
    await worker.compare_states()

    response = await web_client.post(FORWARD_TESTS_PATH, json=make_start_request(strategy_version_id, symbol="AMZN"))

    assert (first["client_id"], second["client_id"], response.json()["client_id"]) == (10, 11, 10)


@pytest.mark.anyio
async def test_a_failed_paper_account_check_fails_the_forward_test_without_retry(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    child_starter = FakeChildStarter()
    worker = make_worker(database_url, clock, child_starter)
    await worker.compare_states()

    child_starter.children[0].exit_code = PAPER_CHECK_FAILED_EXIT_CODE
    await worker.compare_states()
    await worker.compare_states()

    failed = await read_forward_test(web_client, forward_test["id"])
    # The child sent no order, so the client ID is free at once.
    assert (failed["status"], failed["client_id"]) == ("failed", None)
    assert failed["error_message"] == "The paper account check failed."
    assert len(child_starter.children) == 1


@pytest.mark.anyio
async def test_a_crash_restarts_the_forward_test_with_the_same_client_id(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    child_starter = FakeChildStarter()
    worker = make_worker(database_url, clock, child_starter)
    await worker.compare_states()

    child_starter.children[0].exit_code = 1
    await worker.compare_states()

    crashed = await read_forward_test(web_client, forward_test["id"])
    assert (crashed["status"], crashed["client_id"], crashed["crash_count"]) == ("starting", 10, 1)
    assert crashed["interruptions"] == [
        {"reason": "crash", "started_at_utc": "2026-01-02T03:04:05Z", "ended_at_utc": None}
    ]

    await worker.compare_states()

    assert child_starter.read_started() == [(forward_test["id"], "run"), (forward_test["id"], "run")]
    restarted = await read_forward_test(web_client, forward_test["id"])
    assert (restarted["status"], restarted["client_id"]) == ("running", 10)


@pytest.mark.anyio
async def test_three_crashes_in_a_row_fail_the_forward_test_and_keep_the_client_id(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    child_starter = FakeChildStarter()
    worker = make_worker(database_url, clock, child_starter)

    for _ in range(3):
        await worker.compare_states()
        child_starter.children[-1].exit_code = 1
        await worker.compare_states()
    await worker.compare_states()

    failed = await read_forward_test(web_client, forward_test["id"])
    assert (failed["status"], failed["client_id"], failed["crash_count"]) == ("failed", 10, 3)
    assert (
        failed["error_message"]
        == "The forward test process ended with exit code 1. The forward-test log has the reason."
    )
    assert len(child_starter.children) == 3

    # The stop cancels the orders of the client ID and frees it.
    await web_client.post(f"{FORWARD_TESTS_PATH}/{forward_test['id']}/stop")
    await worker.compare_states()
    assert child_starter.read_started()[-1] == (forward_test["id"], "cancel_orders")
    child_starter.children[-1].exit_code = 0
    await worker.compare_states()

    stopped = await read_forward_test(web_client, forward_test["id"])
    assert (stopped["status"], stopped["client_id"]) == ("stopped", None)
    # The crash message is not the current state of a stopped forward test. The crash interruptions keep the history.
    assert stopped["error_message"] is None
    assert [interruption["reason"] for interruption in stopped["interruptions"]] == ["crash"]
    assert stopped["interruptions"][0]["ended_at_utc"] == "2026-01-02T03:04:05Z"


@pytest.mark.anyio
async def test_a_crash_after_a_long_run_starts_a_new_count(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    child_starter = FakeChildStarter()
    worker = make_worker(database_url, clock, child_starter)
    for _ in range(2):
        await worker.compare_states()
        child_starter.children[-1].exit_code = 1
        await worker.compare_states()

    await worker.compare_states()
    clock.now_utc += timedelta(hours=1)
    child_starter.children[-1].exit_code = 1
    await worker.compare_states()

    restarting = await read_forward_test(web_client, forward_test["id"])
    assert (restarting["status"], restarting["crash_count"]) == ("starting", 1)


@pytest.mark.anyio
async def test_a_lost_gateway_waits_for_it_without_a_crash_count(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    child_starter = FakeChildStarter()
    worker = make_worker(database_url, clock, child_starter)
    await worker.compare_states()

    child_starter.children[0].exit_code = GATEWAY_UNREACHABLE_EXIT_CODE
    await worker.compare_states()
    await worker.compare_states()

    # The new child waits for IB Gateway. It writes "running" when its LiveNode starts.
    waiting = await read_forward_test(web_client, forward_test["id"])
    assert (waiting["status"], waiting["client_id"], waiting["crash_count"]) == ("waiting_for_gateway", 10, 0)
    assert child_starter.read_started() == [(forward_test["id"], "run"), (forward_test["id"], "run")]
    assert [item["reason"] for item in waiting["interruptions"]] == ["gateway"]


@pytest.mark.anyio
async def test_the_end_time_stops_the_forward_test(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    request = make_start_request(strategy_version_id) | {"end_time_utc": "2026-01-02T05:00:00Z"}
    forward_test = (await web_client.post(FORWARD_TESTS_PATH, json=request)).json()
    child_starter = FakeChildStarter()
    worker = make_worker(database_url, clock, child_starter)
    await worker.compare_states()
    [child] = child_starter.children

    clock.now_utc = datetime(2026, 1, 2, 4, 59, 59, tzinfo=UTC)
    await worker.compare_states()
    assert not child.is_stop_requested

    clock.now_utc = datetime(2026, 1, 2, 5, 0, 0, tzinfo=UTC)
    await worker.compare_states()
    assert child.is_stop_requested
    child.exit_code = 0
    await worker.compare_states()

    stopped = await read_forward_test(web_client, forward_test["id"])
    assert (stopped["status"], stopped["client_id"]) == ("stopped", None)
    assert stopped["end_time_utc"] == "2026-01-02T05:00:00Z"
    assert stopped["stopped_at_utc"] == "2026-01-02T05:00:00Z"


@pytest.mark.anyio
async def test_a_passed_end_time_without_a_child_cancels_the_orders(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    strategy_version_id = await save_test_strategy_version(web_client)
    request = make_start_request(strategy_version_id) | {"end_time_utc": "2026-01-02T05:00:00Z"}
    forward_test = (await web_client.post(FORWARD_TESTS_PATH, json=request)).json()
    await make_worker(database_url, clock, FakeChildStarter()).compare_states()

    # The forward-test service was down at the end time.
    clock.now_utc = datetime(2026, 1, 2, 6, 0, 0, tzinfo=UTC)
    child_starter = FakeChildStarter()
    await make_worker(database_url, clock, child_starter).compare_states()

    assert child_starter.read_started() == [(forward_test["id"], "cancel_orders")]


@pytest.mark.anyio
async def test_a_failed_cancel_is_stop_failed_and_keeps_the_client_id(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    child_starter = FakeChildStarter()
    worker = make_worker(database_url, clock, child_starter)
    await worker.compare_states()
    await web_client.post(f"{FORWARD_TESTS_PATH}/{forward_test['id']}/stop")
    await worker.compare_states()

    child_starter.children[0].exit_code = 1
    await worker.compare_states()

    stop_failed = await read_forward_test(web_client, forward_test["id"])
    assert (stop_failed["status"], stop_failed["client_id"]) == ("stop_failed", 10)

    # The next comparison retries the cancel with the same client ID.
    await worker.compare_states()
    assert child_starter.read_started()[-1] == (forward_test["id"], "cancel_orders")


@pytest.mark.anyio
async def test_a_new_worker_starts_the_running_forward_tests_again(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    await make_worker(database_url, clock, FakeChildStarter()).compare_states()

    # The forward-test service restarted. Its children ended with it.
    child_starter = FakeChildStarter()
    await make_worker(database_url, clock, child_starter).compare_states()

    assert child_starter.read_started() == [(forward_test["id"], "run")]
    restarted = await read_forward_test(web_client, forward_test["id"])
    assert (restarted["status"], restarted["client_id"], restarted["crash_count"]) == ("running", 10, 0)
    assert restarted["interruptions"] == [
        {"reason": "worker_restart", "started_at_utc": "2026-01-02T03:04:05Z", "ended_at_utc": None}
    ]


def read_owner_sums(database_url: str) -> list[tuple[object, ...]]:
    """(owner kind, symbol, quantity, cash) for each owner and instrument of the owner ledger."""
    with psycopg.connect(database_url) as connection:
        return connection.execute(
            """
            SELECT owner_kind, symbol, sum(quantity_change), sum(cash_change) FROM owner_ledger_entry
            GROUP BY owner_kind, symbol ORDER BY owner_kind, symbol NULLS FIRST
            """
        ).fetchall()


@pytest.mark.anyio
async def test_a_stop_transfers_the_positions_and_the_cash_to_by_hand_and_keeps_the_fills(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    # The ATrade execution client wrote a buy of 10 AAPL at 100 with 1 USD commission.
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            INSERT INTO owner_ledger_entry (owner_kind, forward_test_id, entry_kind, time_utc, account, symbol,
                exchange, currency, quantity_change, price, commission, cash_change, ibkr_execution_id, ibkr_order_id)
            VALUES ('forward_test', %(id)s, 'fill', %(time_utc)s, 'DU1234567', 'AAPL', 'NASDAQ', 'USD', 10, 100, 1,
                -1001, 'E-1', 1)
            """,
            {"id": forward_test["id"], "time_utc": datetime(2026, 1, 2, 3, 5, tzinfo=UTC)},
        )
    child_starter = FakeChildStarter()
    worker = make_worker(database_url, clock, child_starter)
    await worker.compare_states()
    [child] = child_starter.children
    await web_client.post(f"{FORWARD_TESTS_PATH}/{forward_test['id']}/stop")
    await worker.compare_states()
    # The ledger start of "By hand" is 100000 USD cash. The forward test got 10000 of it at the start.
    assert read_owner_sums(database_url) == [
        ("by_hand", None, Decimal(0), Decimal(90000)),
        ("forward_test", None, Decimal(0), Decimal(10000)),
        ("forward_test", "AAPL", Decimal(10), Decimal(-1001)),
    ]

    child.exit_code = 0
    await worker.compare_states()
    await worker.compare_states()

    assert read_owner_sums(database_url) == [
        ("by_hand", None, Decimal(0), Decimal(98999)),
        ("by_hand", "AAPL", Decimal(10), Decimal(0)),
        ("forward_test", None, Decimal(0), Decimal(1001)),
        ("forward_test", "AAPL", Decimal(0), Decimal(-1001)),
    ]
    detail = (await web_client.get(f"{FORWARD_TESTS_PATH}/{forward_test['id']}")).json()
    assert [(fill["symbol"], fill["side"], fill["quantity_shares"]) for fill in detail["fills"]] == [
        ("AAPL", "BUY", "10")
    ]
