"""Keeps the secrets of this process from its child processes and from other processes of the same user
(docs/architecture/backtest.md section 10.1)."""

import ctypes
import os
import sys
from typing import Final

PR_SET_DUMPABLE: Final = 4
NOT_DUMPABLE: Final = 0
# Each child process gets only these variables and the variables that it names. Secrets stay in the parent.
CHILD_ENVIRONMENT_ALLOW_LIST: Final = ("PATH", "HOME", "TZ")


def create_child_environment(*variable_names: str) -> dict[str, str]:
    names = (*CHILD_ENVIRONMENT_ALLOW_LIST, *variable_names)
    return {name: os.environ[name] for name in names if name in os.environ}


def block_process_reads() -> None:
    """Makes `/proc/<this process>/environ` and `mem` unreadable for strategy child processes. No effect outside Linux.

    The flag applies to all threads. It ends at exec, so a child process keeps its own `/proc/self` files.
    """
    if sys.platform != "linux":
        return
    if ctypes.CDLL(None, use_errno=True).prctl(PR_SET_DUMPABLE, NOT_DUMPABLE) != 0:
        raise OSError(ctypes.get_errno(), "prctl(PR_SET_DUMPABLE) failed.")
