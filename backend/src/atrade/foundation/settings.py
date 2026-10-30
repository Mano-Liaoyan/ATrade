"""Settings that ATrade reads from environment variables (docs/architecture.md section 15).

Docker Compose loads the variables from `.env`. `.env.example` lists every variable.
"""

from decimal import Decimal
from pathlib import Path
from typing import Literal, Self

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_FRONTEND_BUILD_DIR = Path("/app/frontend-build")
# NautilusTrader refuses an IB client ID that is a multiple of 1000 (section 4.1). This includes 0.
CLIENT_ID_STEP_REFUSED_BY_NAUTILUS = 1000


def require_usable_client_id(client_id: int) -> None:
    if client_id == 0:
        message = "IBKR client ID 0 is not allowed. Client ID 0 binds the manual orders of the Gateway."
        raise ValueError(message)
    if client_id % CLIENT_ID_STEP_REFUSED_BY_NAUTILUS == 0:
        message = f"IBKR client ID {client_id} is a multiple of 1000. NautilusTrader refuses it."
        raise ValueError(message)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ATRADE_", frozen=True)

    # The backtest child process gets DATABASE_URL by this exact name (section 10), so it has no prefix.
    database_url: str = Field(validation_alias=AliasChoices("DATABASE_URL", "database_url"))
    trading_mode: Literal["paper", "live"] = "paper"
    frontend_build_dir: Path = DEFAULT_FRONTEND_BUILD_DIR
    # The expected IBKR paper account number, for example DU1234567. None when it is not configured.
    ibkr_account_id: str | None = None
    # Inside the Compose network, socat in the Gateway image serves the paper API on ib-gateway:4004.
    ibkr_host: str = "ib-gateway"
    ibkr_paper_port: int = Field(default=4004, gt=0)
    ibkr_web_client_id: int = Field(default=1, ge=0)
    forward_test_client_id_first: int = Field(default=10, ge=0)
    forward_test_client_id_last: int = Field(default=13, ge=0)
    # Paper capital when no paper account balance is available.
    local_paper_capital_usd: Decimal = Field(default=Decimal(100000), gt=0)
    # Secret. Decision #146 names it without the ATRADE_ prefix. None when it is not configured.
    databento_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("DATABENTO_API_KEY", "databento_api_key")
    )

    @field_validator("trading_mode")
    @classmethod
    def refuse_live_trading_mode(cls, trading_mode: str) -> str:
        if trading_mode == "live":
            message = "trading_mode 'live' is not allowed in this stage. Set ATRADE_TRADING_MODE=paper."
            raise ValueError(message)
        return trading_mode

    @field_validator("ibkr_account_id", "databento_api_key", mode="before")
    @classmethod
    def treat_empty_value_as_none(cls, value: object) -> object:
        # Compose passes an empty value when .env does not set the variable.
        if value == "":
            return None
        return value

    @field_validator("ibkr_web_client_id", "forward_test_client_id_first", "forward_test_client_id_last")
    @classmethod
    def refuse_unusable_client_id(cls, client_id: int) -> int:
        require_usable_client_id(client_id)
        return client_id

    @model_validator(mode="after")
    def refuse_overlapping_client_ids(self) -> Self:
        first = self.forward_test_client_id_first
        last = self.forward_test_client_id_last
        if last < first:
            message = f"The forward test client ID range {first}-{last} ends before it starts."
            raise ValueError(message)
        # A multiple of 1000 inside the range is refused, because forward tests take every ID in the range.
        for client_id in range(first, last + 1):
            require_usable_client_id(client_id)
        if first <= self.ibkr_web_client_id <= last:
            message = (
                f"The Web client ID {self.ibkr_web_client_id} is inside the forward test client ID range"
                f" {first}-{last}. Each process must use a different client ID."
            )
            raise ValueError(message)
        return self
