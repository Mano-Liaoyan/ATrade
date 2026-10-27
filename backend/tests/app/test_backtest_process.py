"""The backtest child lowers its priority before it loads NautilusTrader and pyarrow (backtest.md section 10.1)."""

import subprocess
import sys

IMPORT_CHECK = (
    "import sys, atrade.app.backtest_process; "
    "print(sorted(name for name in ('nautilus_trader', 'pyarrow') if name in sys.modules))"
)


def test_importing_the_child_entry_does_not_load_nautilus_trader_or_pyarrow() -> None:
    result = subprocess.run([sys.executable, "-c", IMPORT_CHECK], capture_output=True, text=True, check=True)

    assert result.stdout.strip() == "[]"
