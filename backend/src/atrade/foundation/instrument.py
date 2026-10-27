"""Instrument: a symbol, an exchange, and a currency identify a security that the user can trade (GLOSSARY.md)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    symbol: str
    exchange: str
    currency: str
