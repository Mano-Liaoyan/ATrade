"""Stops other processes of the same user from reading this process (docs/architecture/backtest.md section 10.1)."""

import ctypes
import sys
from typing import Final

PR_SET_DUMPABLE: Final = 4
NOT_DUMPABLE: Final = 0


def block_process_reads() -> None:
    """Makes `/proc/<this process>/environ` and `mem` unreadable for strategy child processes. No effect outside Linux.

    The flag applies to all threads. It ends at exec, so a child process keeps its own `/proc/self` files.
    """
    if sys.platform != "linux":
        return
    if ctypes.CDLL(None, use_errno=True).prctl(PR_SET_DUMPABLE, NOT_DUMPABLE) != 0:
        raise OSError(ctypes.get_errno(), "prctl(PR_SET_DUMPABLE) failed.")
