"""IBKR stock split check program. The user runs it after the Databento import (docs/architecture.md section 6.4).

    python -m atrade.app.ibkr_split_check [--ibkr-client-id <ID>]

The program compares the stored Databento daily closes of the instruments that still trade with the IBKR daily
closes, one instrument at a time, and adjusts the stored Databento bars for each stock split that it finds
(market_data.md section 8.8.3). It needs IB Gateway and connects with its own client ID, default 30. It waits after an
IBKR pacing violation or a lost connection and then continues. It stops when no instrument waits. A new run after a
stop checks only the instruments that still wait.
"""

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from atrade.foundation.clock import SystemClock
from atrade.foundation.settings import Settings, require_usable_client_id
from atrade.ibkr import GatewayRequestError, IbAsyncGatewayConnection
from atrade.market_data import IbkrSplitCheckReport, run_ibkr_split_check

logger = logging.getLogger(__name__)
DEFAULT_IBKR_CLIENT_ID = 30


def read_arguments(arguments: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finds the stock splits of the Databento instruments with IBKR.")
    parser.add_argument(
        "--ibkr-client-id", type=int, default=DEFAULT_IBKR_CLIENT_ID, help="The IB Gateway client ID of the check."
    )
    return parser.parse_args(arguments)


async def check_with_gateway(*, settings: Settings, client_id: int) -> IbkrSplitCheckReport:
    gateway = IbAsyncGatewayConnection(host=settings.ibkr_host, port=settings.ibkr_paper_port, client_id=client_id)
    try:
        await gateway.connect()
    except GatewayRequestError as error:
        # The check waits for IB Gateway and connects again (run_ibkr_split_check).
        logger.warning("IB Gateway is not reachable at the start: %s", error)
    try:
        return await run_ibkr_split_check(database_url=settings.database_url, gateway=gateway, clock=SystemClock())
    finally:
        gateway.disconnect()


def main(arguments: Sequence[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    options = read_arguments(arguments)
    client_id: int = options.ibkr_client_id
    try:
        require_usable_client_id(client_id)
        settings = Settings()  # pyright: ignore[reportCallIssue] readability-exception: pydantic-settings fills required fields from the environment.
    except (ValidationError, ValueError) as error:
        logger.error("The IBKR stock split check does not start. %s", error)
        sys.exit(1)
    report = asyncio.run(check_with_gateway(settings=settings, client_id=client_id))
    logger.info(
        "Checked %d instruments. Applied %d stock splits. %d stock splits wait for the check.",
        report.checked_instrument_count,
        report.applied_split_count,
        report.waiting_split_count,
    )
    if report.waiting_split_count > 0:
        logger.info("Check them with: python -m atrade.app.databento_check")


if __name__ == "__main__":
    main()
