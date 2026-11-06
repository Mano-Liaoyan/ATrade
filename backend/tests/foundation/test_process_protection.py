"""The block of process reads has no effect outside Linux, so `web` and the worker start on each supported Unix."""

import ctypes
import sys

import pytest

from atrade.foundation.process_protection import block_process_reads


def fail_if_called(*_: object, **__: object) -> None:
    raise AssertionError


def test_does_not_call_prctl_outside_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(ctypes, "CDLL", fail_if_called)

    block_process_reads()
