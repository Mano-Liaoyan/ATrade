"""Instrument: a symbol, an exchange, and a currency identify a security that the user can trade (GLOSSARY.md)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    symbol: str
    exchange: str
    currency: str

    def has_same_symbol_and_currency(self, other: Instrument) -> bool:
        """The compare for an open order. ib_async decodes no primary exchange for an order of an earlier session, so
        that order has the exchange SMART."""
        return self.symbol == other.symbol and self.currency == other.currency
