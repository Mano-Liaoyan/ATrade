"""Runs one strategy version on live IB bars in a NautilusTrader LiveNode, until the stop request.

Only the forward test child process calls it: one process can run only one LiveNode (docs/architecture.md 4.1).
The facts of section 12 come from the NautilusTrader 2.0.0rc7 source. The ibkr_paper contract test checks them.
"""

import asyncio
import tempfile
from pathlib import Path

from nautilus_trader.adapters.interactive_brokers import (
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersDataClientFactory,
    InteractiveBrokersExecutionClientConfig,
    InteractiveBrokersExecutionClientFactory,
    InteractiveBrokersInstrumentProviderConfig,
)
from nautilus_trader.common import Environment
from nautilus_trader.config import StrategyConfig
from nautilus_trader.live import LiveExecutionEngineConfig, LiveNode
from nautilus_trader.model import BarType, InstrumentId, Symbol, TraderId, Venue

from atrade.forward_test.forward_test_child import LiveNodeInput
from atrade.strategy import load_strategy_classes

IB_CLIENT_NAME = "IB"
# The trader ID has the form NAME-TAG. NautilusTrader writes the tag into each ClientOrderId.
TRADER_ID_PREFIX = "ATRADE"


def create_instrument_id(live_node_input: LiveNodeInput) -> InstrumentId:
    # The IB instrument provider uses the simplified symbology: SYMBOL.PRIMARY_EXCHANGE, for example AAPL.NASDAQ.
    instrument = live_node_input.instrument
    return InstrumentId(Symbol(instrument.symbol), Venue(instrument.exchange))


def build_live_node(live_node_input: LiveNodeInput, instrument_id: InstrumentId) -> LiveNode:
    """IB data and execution clients with the client ID of the forward test, for this 1 instrument."""
    instrument_provider = InteractiveBrokersInstrumentProviderConfig(load_ids={instrument_id})
    data_client_config = InteractiveBrokersDataClientConfig(
        host=live_node_input.gateway_host,
        port=live_node_input.gateway_port,
        client_id=live_node_input.client_id,
        instrument_provider=instrument_provider,
    )
    execution_client_config = InteractiveBrokersExecutionClientConfig(
        host=live_node_input.gateway_host,
        port=live_node_input.gateway_port,
        client_id=live_node_input.client_id,
        account_id=live_node_input.account_id,
        instrument_provider=instrument_provider,
    )
    # The account position on the instrument belongs to this forward test (section 12.2).
    execution_engine_config = LiveExecutionEngineConfig(
        reconciliation=True, reconciliation_instrument_ids=[str(instrument_id)]
    )
    trader_id = TraderId(f"{TRADER_ID_PREFIX}-{live_node_input.forward_test_id:03d}")
    builder = LiveNode.builder(f"forward-test-{live_node_input.forward_test_id}", trader_id, Environment.LIVE)
    builder = builder.with_exec_engine_config(execution_engine_config)
    builder = builder.add_data_client(IB_CLIENT_NAME, InteractiveBrokersDataClientFactory(), data_client_config)
    builder = builder.add_exec_client(
        IB_CLIENT_NAME, InteractiveBrokersExecutionClientFactory(), execution_client_config
    )
    return builder.build()


def create_strategy_config(
    config_class: type[StrategyConfig], live_node_input: LiveNodeInput, instrument_id: InstrumentId
) -> StrategyConfig:
    bar_type = BarType.from_str(f"{instrument_id}-{live_node_input.bar_period.value}-LAST-EXTERNAL")
    # readability-exception: the user __init__ takes only its own fields (strategy.md section 9.2) and forwards the
    # other keywords to object.__init__, which refuses them. The NautilusTrader fields go to __new__ directly (E1).
    nautilus_fields: dict[str, object] = {
        "order_id_tag": live_node_input.order_id_tag,
        "external_order_instrument_ids": [instrument_id],
    }
    config: StrategyConfig = config_class.__new__(config_class, **nautilus_fields)
    config.__init__(instrument_id=instrument_id, bar_type=bar_type)  # pyright: ignore[reportCallIssue, reportUnknownMemberType]
    return config


async def wait_for_end_or_stop(live_node: LiveNode, stop_requested: asyncio.Event) -> None:
    run_task = asyncio.create_task(live_node.run_async())
    stop_task = asyncio.create_task(stop_requested.wait())
    await asyncio.wait({run_task, stop_task}, return_when=asyncio.FIRST_COMPLETED)
    if stop_requested.is_set():
        # LiveNode.stop does not cancel orders and does not close positions (section 12.6). No manage_stop.
        live_node.handle().stop()
    stop_task.cancel()
    await run_task


async def run_live_node(live_node_input: LiveNodeInput, stop_requested: asyncio.Event) -> None:
    """Runs until `stop_requested` is set, or until the LiveNode ends by itself."""
    instrument_id = create_instrument_id(live_node_input)
    with tempfile.TemporaryDirectory(prefix=f"atrade-forward-test-{live_node_input.forward_test_id}-") as directory:
        strategy_class, config_class = load_strategy_classes(live_node_input.strategy_code, Path(directory))
        live_node = build_live_node(live_node_input, instrument_id)
        live_node.add_strategy(strategy_class(create_strategy_config(config_class, live_node_input, instrument_id)))
        try:
            await wait_for_end_or_stop(live_node, stop_requested)
        finally:
            live_node.dispose()
