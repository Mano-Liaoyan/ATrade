"""Adds the ATrade execution and data clients to a LiveNode (docs/architecture/forward_test.md section 12.19).

The child process still uses the IB clients (`live_node_run.py`) until #215.
"""

from nautilus_trader.config import DataClientConfig, ExecutionClientConfig
from nautilus_trader.live import LiveNodeBuilder, RoutingConfig

from atrade.forward_test.bar_store_data_client import BAR_STORE_DATA_CLIENT_NAME, BarStoreDataClientFactory
from atrade.forward_test.owner_ledger_execution_client import (
    OWNER_LEDGER_EXECUTION_CLIENT_NAME,
    OwnerLedgerExecutionClientFactory,
)


def add_atrade_clients(
    builder: LiveNodeBuilder,
    data_client_factory: BarStoreDataClientFactory | None,
    execution_client_factory: OwnerLedgerExecutionClientFactory,
) -> LiveNodeBuilder:
    """The clients are the default route for all venues: the instrument IDs use the primary exchanges as venues.

    Without a data client factory, the node keeps its other data clients (for example the IB data client).
    """
    if data_client_factory is not None:
        builder = builder.add_data_client(
            BAR_STORE_DATA_CLIENT_NAME, data_client_factory, DataClientConfig(), RoutingConfig(default=True)
        )
    return builder.add_exec_client(
        OWNER_LEDGER_EXECUTION_CLIENT_NAME,
        execution_client_factory,
        ExecutionClientConfig(),
        RoutingConfig(default=True),
    )
