"""The forward test child entry accepts only the child modes "run" and "cancel_orders"."""

import pytest
from pydantic import ValidationError

from atrade.app.forward_test_process import read_child_mode


def test_reads_each_child_mode() -> None:
    assert read_child_mode("run") == "run"
    assert read_child_mode("cancel_orders") == "cancel_orders"


def test_refuses_an_unknown_child_mode() -> None:
    with pytest.raises(ValidationError):
        read_child_mode("delete_everything")
