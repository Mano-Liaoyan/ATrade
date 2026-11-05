"""IBKR stock split check program. The user runs it after the Databento import (docs/architecture.md section 6.4).

    python -m atrade.app.ibkr_split_check read [--ibkr-client-id <ID>]
    python -m atrade.app.ibkr_split_check report
    python -m atrade.app.ibkr_split_check apply

The check of the instruments that still trade has 3 steps (market_data.md section 8.8.3.1):

- read: reads the IBKR daily closes, one instrument at a time, and stores them. It needs IB Gateway and connects
  with its own client ID, default 30. It waits after an IBKR pacing violation or a lost connection and then
  continues. It stops when no instrument waits. A new run after a stop reads only the instruments that still wait.
- report: finds the stock splits in the stored closes and compares them with the confirmed stock splits of the
  import check. It changes nothing.
- apply: adjusts the stored Databento bars for each stock split that it finds in the stored closes.
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
from atrade.market_data import (
    IbkrCloseReadReport,
    ReportedSplit,
    SplitRuleReport,
    apply_ibkr_split_check,
    report_ibkr_split_check,
    run_ibkr_close_read,
)

logger = logging.getLogger(__name__)
DEFAULT_IBKR_CLIENT_ID = 30
# The report shows at most this count of lines of each list.
REPORT_LINE_COUNT = 40


def read_arguments(arguments: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finds the stock splits of the Databento instruments with IBKR.")
    parser.add_argument("step", choices=["read", "report", "apply"], help="The step of the check.")
    parser.add_argument(
        "--ibkr-client-id", type=int, default=DEFAULT_IBKR_CLIENT_ID, help="The IB Gateway client ID of the check."
    )
    return parser.parse_args(arguments)


async def read_with_gateway(*, settings: Settings, client_id: int) -> IbkrCloseReadReport:
    gateway = IbAsyncGatewayConnection(host=settings.ibkr_host, port=settings.ibkr_paper_port, client_id=client_id)
    try:
        await gateway.connect()
    except GatewayRequestError as error:
        # The check waits for IB Gateway and connects again (run_ibkr_split_check).
        logger.warning("IB Gateway is not reachable at the start: %s", error)
    try:
        return await run_ibkr_close_read(database_url=settings.database_url, gateway=gateway)
    finally:
        gateway.disconnect()


def format_split(split: ReportedSplit) -> str:
    return f"{split.instrument.symbol} {split.instrument.exchange} {split.ex_date} {split.split_ratio:f}"


def log_report(report: SplitRuleReport) -> None:
    logger.info(
        "Read instruments: %d. Without IBKR closes: %d (the apply step uses the detection rule).",
        report.read_instrument_count,
        report.without_closes_count,
    )
    with_gap = report.select_other_splits(has_price_gap=True)
    without_gap = report.select_other_splits(has_price_gap=False)
    logger.info(
        "Known stock splits: %d. Found: %d. Missed: %d. Other found stock splits: %d.",
        report.known_split_count,
        report.found_known_count,
        len(report.missed_splits),
        len(report.other_splits),
    )
    logger.info(
        "Other stock splits with the Databento price gap (apply adjusts the bars): %d. Without the gap (they wait for"
        " the user check): %d.",
        len(with_gap),
        len(without_gap),
    )
    logger.info("Missed known stock splits (first %d):", REPORT_LINE_COUNT)
    for split in report.missed_splits[:REPORT_LINE_COUNT]:
        logger.info("  %s", format_split(split))
    for has_gap, name in ((True, "with the price gap"), (False, "without the price gap")):
        logger.info("Other stock splits %s, by split ratio:", name)
        for ratio, count in report.count_other_ratios(has_price_gap=has_gap)[:REPORT_LINE_COUNT]:
            logger.info("  %s: %d", f"{ratio:f}", count)
        logger.info("Other stock splits %s, by symbol:", name)
        for symbol, count in report.count_other_symbols(has_price_gap=has_gap)[:REPORT_LINE_COUNT]:
            logger.info("  %s: %d", symbol, count)
    logger.info("All other stock splits without the price gap:")
    for split in without_gap:
        logger.info("  %s", format_split(split))
    logger.info("All other stock splits with the price gap:")
    for split in with_gap:
        logger.info("  %s", format_split(split))


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
    if options.step == "read":
        read_report = asyncio.run(read_with_gateway(settings=settings, client_id=client_id))
        logger.info(
            "Read %d instruments. %d of them have no IBKR closes. Next: python -m atrade.app.ibkr_split_check report",
            read_report.read_instrument_count,
            read_report.without_closes_count,
        )
    elif options.step == "report":
        log_report(asyncio.run(report_ibkr_split_check(database_url=settings.database_url)))
    else:
        report = asyncio.run(apply_ibkr_split_check(database_url=settings.database_url, clock=SystemClock()))
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
