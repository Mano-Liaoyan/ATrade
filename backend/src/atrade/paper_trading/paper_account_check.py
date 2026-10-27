"""The paper account check: 4 conditions that must all be true before ATrade sends an order (section 11.2).

The check fails closed. Each condition that ATrade cannot confirm is a failure.
"""

from dataclasses import dataclass
from typing import Literal

from atrade.foundation.settings import Settings
from atrade.ibkr import GatewayConnection

# IBKR paper account numbers start with DU. This protects against a live account number in .env.
PAPER_ACCOUNT_PREFIX = "DU"


@dataclass(frozen=True)
class PaperAccountCheck:
    status: Literal["disconnected", "passed", "failed"]
    # Why the check failed. None when it passed or when ATrade is not connected.
    message: str | None
    actual_accounts: tuple[str, ...]
    expected_account: str | None


class PaperAccountCheckError(PermissionError):
    """ATrade refuses the order or the forward test start, because the paper account check did not pass."""

    def __init__(self, check: PaperAccountCheck) -> None:
        super().__init__(check.message)
        self.check = check


def check_paper_account(*, settings: Settings, gateway_connection: GatewayConnection) -> PaperAccountCheck:
    actual_accounts = tuple(gateway_connection.read_managed_accounts())
    expected_account = settings.ibkr_account_id
    if not gateway_connection.is_connected():
        return PaperAccountCheck(
            status="disconnected", message=None, actual_accounts=(), expected_account=expected_account
        )
    failure_message = find_failed_condition(settings=settings, gateway_connection=gateway_connection)
    if failure_message is None:
        return PaperAccountCheck(
            status="passed", message=None, actual_accounts=actual_accounts, expected_account=expected_account
        )
    return PaperAccountCheck(
        status="failed", message=failure_message, actual_accounts=actual_accounts, expected_account=expected_account
    )


def find_failed_condition(*, settings: Settings, gateway_connection: GatewayConnection) -> str | None:
    """Returns the reason of the first failed condition, or None when all 4 conditions are true."""
    if settings.trading_mode != "paper":
        return f"trading_mode is '{settings.trading_mode}'. ATrade sends orders only when it is 'paper'."
    connected_port = gateway_connection.read_port()
    if connected_port != settings.ibkr_paper_port:
        return f"ATrade is connected to port {connected_port}, not to the paper port {settings.ibkr_paper_port}."
    expected_account = settings.ibkr_account_id
    if expected_account is None:
        return "ATRADE_IBKR_ACCOUNT_ID is not set, so ATrade cannot compare the account."
    actual_accounts = gateway_connection.read_managed_accounts()
    if len(actual_accounts) != 1:
        return f"IB Gateway returned {len(actual_accounts)} accounts. Exactly 1 paper account is necessary."
    actual_account = actual_accounts[0]
    if actual_account != expected_account:
        return f"The account {actual_account} from IB Gateway is not the expected account {expected_account}."
    if not actual_account.startswith(PAPER_ACCOUNT_PREFIX):
        return f"The account {actual_account} does not start with {PAPER_ACCOUNT_PREFIX}. It is not a paper account."
    return None


def require_paper_account(*, settings: Settings, gateway_connection: GatewayConnection) -> str:
    """Returns the checked paper account number. Raises PaperAccountCheckError when a condition fails."""
    check = check_paper_account(settings=settings, gateway_connection=gateway_connection)
    if check.status != "passed":
        raise PaperAccountCheckError(check)
    return check.actual_accounts[0]
