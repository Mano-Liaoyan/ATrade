"""Databento client: downloads the files of a batch job that the user bought (docs/architecture.md section 6.2).

`market_data` holds the Databento client. `ibkr` stays IBKR only. Tests use `tests/fakes/databento.py`.
"""

from pathlib import Path
from typing import Protocol

import databento


class DatabentoClient(Protocol):
    def download_batch_job(self, job_id: str, output_dir: Path) -> list[Path]:
        """Downloads all files of a done batch job to `<output_dir>/<job_id>/` and returns their paths."""
        ...


class DatabentoHistoricalClient:
    """The real client. A download of a done batch job does not cost again for 30 days (section 8.8.1)."""

    def __init__(self, api_key: str) -> None:
        self.historical = databento.Historical(key=api_key)

    def download_batch_job(self, job_id: str, output_dir: Path) -> list[Path]:
        return self.historical.batch.download(job_id=job_id, output_dir=output_dir)
