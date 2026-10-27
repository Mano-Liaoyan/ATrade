"""Account data that the Web process reads from IB Gateway: account values and portfolio positions.

ib_async keeps both up to date after the connection, because it subscribes to the account updates
of the only managed account. The `ibkr` module converts them to these types and adds no business rules.
"""

from dataclasses import dataclass
from decimal import Decimal

from ib_async import AccountValue as IbAccountValue
from ib_async import PortfolioItem


@dataclass(frozen=True)
class AccountValue:
    """One account value, for example tag "NetLiquidation" in currency "USD". IBKR sends the value as text."""

    account: str
    tag: str
    value: str
    currency: str


@dataclass(frozen=True)
class PortfolioPosition:
    account: str
    symbol: str
    security_type: str
    exchange: str
    currency: str
    quantity: Decimal
    average_cost: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal


def convert_account_value(ib_account_value: IbAccountValue) -> AccountValue:
    return AccountValue(
        account=ib_account_value.account,
        tag=ib_account_value.tag,
        value=ib_account_value.value,
        currency=ib_account_value.currency,
    )


def convert_portfolio_item(portfolio_item: PortfolioItem) -> PortfolioPosition:
    contract = portfolio_item.contract
    # str() first, so that the Decimal has the short form of the float, for example 200.1 and not 200.09999...
    return PortfolioPosition(
        account=portfolio_item.account,
        symbol=contract.localSymbol or contract.symbol,
        security_type=contract.secType,
        exchange=contract.primaryExchange or contract.exchange,
        currency=contract.currency,
        quantity=Decimal(str(portfolio_item.position)),
        average_cost=Decimal(str(portfolio_item.averageCost)),
        market_price=Decimal(str(portfolio_item.marketPrice)),
        market_value=Decimal(str(portfolio_item.marketValue)),
        unrealized_pnl=Decimal(str(portfolio_item.unrealizedPNL)),
    )
