"""Program entry points. They create all dependencies by hand and connect the capabilities.

This file imports nothing. `python -m atrade.app.<entry>` imports this package first, and each entry loads only
what it needs. The backtest child must lower its priority before it loads NautilusTrader (backtest_process.py).
Import from the entry modules, for example `atrade.app.web` and `atrade.app.database_migrations`.
"""
