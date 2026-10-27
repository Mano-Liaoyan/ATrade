"""Fake of the function that starts a forward test child process (docs/architecture.md section 17.4).

The worker tests and the e2e server pass `FakeChildStarter.start_child` to the worker. No process starts. A test
ends a fake child when it sets `exit_code`.
"""

from dataclasses import dataclass, field

from atrade.forward_test import ChildMode


@dataclass
class FakeForwardTestChild:
    forward_test_id: int
    mode: ChildMode
    exit_code: int | None = None
    is_stop_requested: bool = False
    # When it is True, the child ends with exit code 0 at the stop request, like a stop that cancelled all orders.
    is_ending_at_stop_request: bool = False

    def read_exit_code(self) -> int | None:
        return self.exit_code

    def request_stop(self) -> None:
        self.is_stop_requested = True
        if self.is_ending_at_stop_request:
            self.exit_code = 0


@dataclass
class FakeChildStarter:
    # The e2e server sets it to True: each child stops at once, and each cancel child ends at once with exit code 0.
    is_ending_children_at_once: bool = False
    children: list[FakeForwardTestChild] = field(default_factory=list[FakeForwardTestChild])

    async def start_child(self, forward_test_id: int, mode: ChildMode) -> FakeForwardTestChild:
        child = FakeForwardTestChild(
            forward_test_id=forward_test_id, mode=mode, is_ending_at_stop_request=self.is_ending_children_at_once
        )
        if self.is_ending_children_at_once and mode == "cancel_orders":
            child.exit_code = 0
        self.children.append(child)
        return child

    def read_started(self) -> list[tuple[int, ChildMode]]:
        return [(child.forward_test_id, child.mode) for child in self.children]
