"""The backtests of the AI assistant and of the user use one queue and the same backtest limits.

docs/architecture/assistant.md 25.4.2. The user starts a backtest on port 8000 and the AI assistant starts one on
port 8001. One real runner with concurrency 1 runs both.
"""

from pathlib import Path

import httpx
import pytest

from atrade.app.assistant_port import CONVERSATION_HEADER
from tests.app.test_assistant_port import backtest_body, open_both_clients
from tests.assistant.assistant_app import create_conversation
from tests.backtest.real_runner import (
    TEST_STRATEGY_FILE,
    run_backtest_runner,
    save_test_bars,
    start_backtest,
    wait_for_final_status,
    wait_for_status,
)
from tests.backtest.test_backtest_isolation import make_process_facts_code
from tests.fakes.clock import FixedClock


@pytest.mark.anyio
async def test_the_backtest_of_the_ai_assistant_waits_in_the_queue_of_the_user_and_has_the_same_limits(
    database_url: str, clock: FixedClock, frontend_build_dir: Path, tmp_path: Path
) -> None:
    save_test_bars(database_url)
    async with open_both_clients(database_url, clock, frontend_build_dir) as (browser, assistant):
        endless_code = make_process_facts_code(tmp_path / "process_facts.json", loop_forever_in_on_bar=True)
        user_backtest_id = await start_backtest(browser, endless_code)
        strategy_id = (await browser.post("/api/strategies", json={"name": "AI strategy"})).json()["id"]
        headers = {CONVERSATION_HEADER: str(await create_conversation(browser, strategy_id))}
        saved = await assistant.post(
            f"/api/strategies/{strategy_id}/versions", json={"code": TEST_STRATEGY_FILE.read_text()}, headers=headers
        )
        started = await assistant.post("/api/backtests", json=backtest_body(saved.json()["id"]), headers=headers)
        assert started.status_code == httpx.codes.CREATED, started.text
        ai_backtest_id = started.json()["id"]

        async with run_backtest_runner(browser, database_url, clock, timeout_seconds=3, concurrency=1):
            await wait_for_status(browser, user_backtest_id, "running")
            ai_backtest_while_user_backtest_runs = (await assistant.get(f"/api/backtests/{ai_backtest_id}")).json()
            user_backtest = await wait_for_final_status(browser, user_backtest_id)
            ai_backtest = await wait_for_final_status(assistant, ai_backtest_id)

    assert ai_backtest_while_user_backtest_runs["status"] == "queued"
    assert user_backtest["status"] == "timed_out"
    assert ai_backtest["status"] == "finished", ai_backtest["error_message"]
