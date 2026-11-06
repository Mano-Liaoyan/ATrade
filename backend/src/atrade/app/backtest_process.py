"""Backtest child process entry point: runs one backtest. The Web process starts it with only a backtest ID.

Run with `python -m atrade.app.backtest_process <backtest ID>`. The environment has only PATH, HOME, TZ, and
DATABASE_URL (docs/architecture/backtest.md section 10.1).
"""

import logging
import os
import signal
import sys
import threading
from pathlib import Path

from atrade.foundation.clock import SystemClock

BACKTEST_PROCESS_COMMAND = [sys.executable, "-m", "atrade.app.backtest_process"]
# The highest value: when memory is low, the kernel stops the backtest before the Web process. No RLIMIT_AS:
# the memory limit of the web container applies (section 10.1).
OOM_SCORE_ADJ = 1000
OOM_SCORE_ADJ_FILE = Path("/proc/self/oom_score_adj")
# Lower CPU priority than the Web process, like `nice -n 10`.
NICENESS_INCREMENT = 10


def lower_own_priority() -> None:
    """Any process can raise its own oom_score_adj and niceness. Only Linux has the oom_score_adj file."""
    if OOM_SCORE_ADJ_FILE.exists():
        OOM_SCORE_ADJ_FILE.write_text(str(OOM_SCORE_ADJ))
    os.nice(NICENESS_INCREMENT)


def stop_after_web_process() -> None:
    """Only the Web process holds the write end of the standard input, so the read returns when the Web process ends
    in any way. The runner starts the child in its own process group: the signal of a terminal or of a container stop
    does not reach it, and a child without this thread could outlive the Web process with its workers (section 10.1).
    """
    os.read(sys.stdin.fileno(), 1)
    os.killpg(os.getpid(), signal.SIGKILL)


def main() -> None:
    threading.Thread(target=stop_after_web_process, daemon=True).start()
    # Standard output: the parent reads the standard error only for a failure text (section 10.3), so only standard
    # output reaches the log of the web container.
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    lower_own_priority()
    # NautilusTrader and pyarrow load after the priority change, so their import also runs with the lower priority.
    from atrade.backtest import run_backtest

    backtest_id = int(sys.argv[1])
    run_backtest(database_url=os.environ["DATABASE_URL"], backtest_id=backtest_id, clock=SystemClock())


if __name__ == "__main__":
    main()
