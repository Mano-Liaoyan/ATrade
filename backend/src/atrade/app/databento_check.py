"""User check of the Databento import (docs/architecture.md section 6.4, market_data.md sections 8.8.3 and 8.8.4).

    python -m atrade.app.databento_check
    python -m atrade.app.databento_check --accept [--reject-split <ID> ...]

Without options, the program lists the detected stock splits that wait for the check and the symbol links that are
not checked. With `--accept`, it confirms all listed stock splits except the rejected IDs, changes the stored bars
before their ex-dates, and records the check of all listed links.
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from pydantic import ValidationError

from atrade.foundation.settings import Settings
from atrade.market_data import (
    ImportCheckError,
    ImportDetections,
    check_import_detections,
    read_unchecked_import_detections,
)

logger = logging.getLogger(__name__)


def read_arguments(arguments: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lists or checks the stock splits and symbol links of the import.")
    parser.add_argument("--accept", action="store_true", help="Confirm all listed detections except the rejected.")
    parser.add_argument(
        "--reject-split", action="append", type=int, default=[], dest="rejected_split_ids", help="A wrong stock split."
    )
    return parser.parse_args(arguments)


def log_detections(detections: ImportDetections) -> None:
    logger.info("%d detected stock splits wait for the check:", len(detections.stock_splits))
    for split in detections.stock_splits:
        instrument = split.instrument
        logger.info(
            "  ID %d: %s %s %s, ex-date %s, split ratio %s",
            split.id,
            instrument.symbol,
            instrument.exchange,
            instrument.currency,
            split.ex_date_utc.date().isoformat(),
            split.split_ratio,
        )
    logger.info("%d symbol links are not checked:", len(detections.symbol_links))
    for link in detections.symbol_links:
        logger.info(
            "  %s to %s on %s, from %s", link.old_symbol, link.new_symbol, link.exchange, link.change_day.isoformat()
        )


def main(arguments: Sequence[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO)
    options = read_arguments(arguments)
    rejected_split_ids: list[int] = options.rejected_split_ids
    if rejected_split_ids and not options.accept:
        logger.error("--reject-split needs --accept. The check changed nothing.")
        sys.exit(1)
    try:
        settings = Settings()  # pyright: ignore[reportCallIssue] readability-exception: pydantic-settings fills required fields from the environment.
    except ValidationError as error:
        logger.error("The import check does not start. The settings are not valid:\n%s", error)
        sys.exit(1)
    if not options.accept:
        log_detections(read_unchecked_import_detections(database_url=settings.database_url))
        return
    try:
        detections = check_import_detections(
            database_url=settings.database_url,
            rejected_split_ids=set(rejected_split_ids),
            checked_at_utc=datetime.now(UTC),
        )
    except ImportCheckError as error:
        logger.error("The check changed nothing. %s", error)
        sys.exit(1)
    rejected_count = len(set(rejected_split_ids))
    logger.info(
        "Confirmed %d stock splits, rejected %d, and checked %d symbol links.",
        len(detections.stock_splits) - rejected_count,
        rejected_count,
        len(detections.symbol_links),
    )


if __name__ == "__main__":
    main()
