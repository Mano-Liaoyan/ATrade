"""The restart of a forward test after a stock split (docs/architecture/forward_test.md sections 12.7 and 12.22).

Real PostgreSQL. The function that starts a child process is a fake (section 17.4).
"""

import httpx
import pytest

from tests.fakes.clock import FixedClock
from tests.fakes.forward_test_child import FakeChildStarter
from tests.forward_test.test_forward_test_worker import make_worker, read_forward_test, start_forward_test


@pytest.mark.anyio
async def test_a_stock_split_restart_does_not_count_toward_the_crash_limit(
    web_client: httpx.AsyncClient, database_url: str, clock: FixedClock
) -> None:
    forward_test = await start_forward_test(web_client)
    child_starter = FakeChildStarter()
    worker = make_worker(database_url, clock, child_starter)
    await worker.compare_states()
    # 2 crashes in a row: a third crash would fail the forward test.
    for _ in range(2):
        child_starter.children[-1].exit_code = 1
        await worker.compare_states()
        await worker.compare_states()

    for _ in range(3):
        worker.request_restart([forward_test["id"]])
        assert child_starter.children[-1].is_stop_requested
        child_starter.children[-1].exit_code = 0
        await worker.compare_states()
        await worker.compare_states()

    restarted = await read_forward_test(web_client, forward_test["id"])
    assert (restarted["status"], restarted["crash_count"]) == ("running", 2)
    assert [child.mode for child in child_starter.children] == ["run"] * 6
    # The restart before the open misses no bar, so it opens no interruption (section 12.24).
    assert [interruption["reason"] for interruption in restarted["interruptions"]] == ["crash"]
