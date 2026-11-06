"""A small Web process for a test: it runs only the backtest runner, so the test can kill it with SIGKILL.

Run with `python -m tests.backtest.backtest_runner_program <database URL>`.
"""

import asyncio
import sys

from atrade.app.backtest_process import BACKTEST_PROCESS_COMMAND
from atrade.backtest import BacktestRunner
from atrade.foundation.clock import SystemClock


def main() -> None:
    runner = BacktestRunner(database_url=sys.argv[1], clock=SystemClock(), process_command=BACKTEST_PROCESS_COMMAND)
    asyncio.run(runner.keep_running())


if __name__ == "__main__":
    main()
