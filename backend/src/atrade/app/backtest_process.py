"""Backtest child process entry point: runs one backtest. The Web process starts it with only a backtest ID.

Run with `python -m atrade.app.backtest_process <backtest ID>`. The environment has only PATH, HOME, TZ, and
DATABASE_URL (docs/architecture.md section 10).
"""

import os
import sys

from atrade.backtest import run_backtest
from atrade.foundation.clock import SystemClock

BACKTEST_PROCESS_COMMAND = [sys.executable, "-m", "atrade.app.backtest_process"]


def main() -> None:
    backtest_id = int(sys.argv[1])
    run_backtest(database_url=os.environ["DATABASE_URL"], backtest_id=backtest_id, clock=SystemClock())


if __name__ == "__main__":
    main()
