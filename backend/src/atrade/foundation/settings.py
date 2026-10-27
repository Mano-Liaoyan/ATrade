"""Settings that ATrade reads from environment variables (docs/architecture.md section 15).

Docker Compose loads the variables from `.env`. `.env.example` lists every variable.
"""

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_FRONTEND_BUILD_DIR = Path("/app/frontend-build")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ATRADE_", frozen=True)

    # The backtest child process gets DATABASE_URL by this exact name (section 10), so it has no prefix.
    database_url: str = Field(validation_alias=AliasChoices("DATABASE_URL", "database_url"))
    trading_mode: Literal["paper", "live"] = "paper"
    frontend_build_dir: Path = DEFAULT_FRONTEND_BUILD_DIR

    @field_validator("trading_mode")
    @classmethod
    def refuse_live_trading_mode(cls, trading_mode: str) -> str:
        if trading_mode == "live":
            message = "trading_mode 'live' is not allowed in this stage. Set ATRADE_TRADING_MODE=paper."
            raise ValueError(message)
        return trading_mode
