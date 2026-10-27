"""Runs one strategy version on live IB bars in a NautilusTrader LiveNode, until the stop request.

Only the forward test child process calls it: one process can run only one LiveNode (docs/architecture.md 4.1).
The facts of section 12 come from the NautilusTrader 2.0.0rc7 source. The ibkr_paper contract test checks them.
"""

import asyncio
import tempfile
from dataclasses import dataclass
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
from nautilus_trader.live import LiveExecutionEngineConfig, LiveNode, LiveNodeBuilder, LiveNodeConfig
from nautilus_trader.model import BarType, InstrumentId, Symbol, TraderId, Venue
from nautilus_trader.persistence import DataCatalogConfig

from atrade.backtest import write_look_back_catalog
from atrade.forward_test.forward_test_child import LiveNodeEnd, LiveNodeInput
from atrade.forward_test.forward_test_recorder import ForwardTestRecorder, RecorderInput
from atrade.strategy import load_strategy_classes

IB_CLIENT_NAME = "IB"
# The trader ID has the form NAME-TAG. NautilusTrader writes the tag into each ClientOrderId.
TRADER_ID_PREFIX = "ATRADE"
GATEWAY_PROBE_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class GatewayWatch:
    """When IB Gateway is not reachable for `lost_after_seconds` in a row, the LiveNode stops (section 12.7).

    The NautilusTrader 2.0.0rc7 LiveNode does not show the connection state of its IB execution client to Python.
    So the child opens a TCP connection to the Gateway port every `check_interval_seconds`. A Gateway that does not
    accept connections cannot keep the execution client connected.
    """

    check_interval_seconds: float = 30.0
    lost_after_seconds: float = 300.0


async def can_reach_gateway(host: str, port: int) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), GATEWAY_PROBE_TIMEOUT_SECONDS)
    except OSError, TimeoutError:
        return False
    writer.close()
    return True


async def wait_for_gateway_loss(live_node_input: LiveNodeInput, gateway_watch: GatewayWatch) -> None:
    """Returns when IB Gateway was not reachable for `gateway_watch.lost_after_seconds` in a row."""
    loop = asyncio.get_running_loop()
    unreachable_since: float | None = None
    while True:
        if await can_reach_gateway(live_node_input.gateway_host, live_node_input.gateway_port):
            unreachable_since = None
        else:
            now = loop.time()
            unreachable_since = now if unreachable_since is None else unreachable_since
            if now - unreachable_since >= gateway_watch.lost_after_seconds:
                return
        await asyncio.sleep(gateway_watch.check_interval_seconds)


def create_instrument_id(live_node_input: LiveNodeInput) -> InstrumentId:
    # The IB instrument provider uses the simplified symbology: SYMBOL.PRIMARY_EXCHANGE, for example AAPL.NASDAQ.
    instrument = live_node_input.instrument
    return InstrumentId(Symbol(instrument.symbol), Venue(instrument.exchange))


def create_live_node_builder(
    live_node_input: LiveNodeInput, instrument_id: InstrumentId, warm_up_catalog: DataCatalogConfig
) -> LiveNodeBuilder:
    """The node without clients. The catalog holds the warm-up bars and says that it holds all times, so the data
    engine answers each `request_bars` from the catalog and never asks IBKR (section 12.15).

    The reason: the IB data client of NautilusTrader 2.0.0rc7 splits a long request into a part in days and a rest
    in seconds. IBKR refuses a rest shorter than the bar (error 321), so a 7-day request of 1-minute bars fails.
    """
    # The account position on the instrument belongs to this forward test (section 12.2).
    execution_engine_config = LiveExecutionEngineConfig(
        reconciliation=True, reconciliation_instrument_ids=[str(instrument_id)]
    )
    config = LiveNodeConfig(
        environment=Environment.LIVE,
        trader_id=TraderId(f"{TRADER_ID_PREFIX}-{live_node_input.forward_test_id:03d}"),
        exec_engine=execution_engine_config,
        catalogs=[warm_up_catalog],
    )
    # The stub types the unused factory dicts without key and value types.
    return LiveNodeBuilder.from_config(f"forward-test-{live_node_input.forward_test_id}", config)  # pyright: ignore[reportUnknownMemberType]


def build_live_node(
    live_node_input: LiveNodeInput, instrument_id: InstrumentId, warm_up_catalog: DataCatalogConfig
) -> LiveNode:
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
    builder = create_live_node_builder(live_node_input, instrument_id, warm_up_catalog)
    builder = builder.add_data_client(IB_CLIENT_NAME, InteractiveBrokersDataClientFactory(), data_client_config)
    builder = builder.add_exec_client(
        IB_CLIENT_NAME, InteractiveBrokersExecutionClientFactory(), execution_client_config
    )
    return builder.build()


def create_bar_type(live_node_input: LiveNodeInput, instrument_id: InstrumentId) -> BarType:
    return BarType.from_str(f"{instrument_id}-{live_node_input.bar_period.value}-LAST-EXTERNAL")


def create_recorder(live_node_input: LiveNodeInput, instrument_id: InstrumentId) -> ForwardTestRecorder:
    """The platform DataActor on the same bar type as the strategy (section 12.8)."""
    return ForwardTestRecorder(
        RecorderInput(
            database_url=live_node_input.database_url,
            forward_test_id=live_node_input.forward_test_id,
            instrument_id=instrument_id,
            bar_type=create_bar_type(live_node_input, instrument_id),
            bar_period=live_node_input.bar_period,
            start_balance_usd=live_node_input.start_balance_usd,
        )
    )


def create_strategy_config(
    config_class: type[StrategyConfig], live_node_input: LiveNodeInput, instrument_id: InstrumentId
) -> StrategyConfig:
    bar_type = create_bar_type(live_node_input, instrument_id)
    # readability-exception: the user __init__ takes only its own fields (strategy.md section 9.2) and forwards the
    # other keywords to object.__init__, which refuses them. The NautilusTrader fields go to __new__ directly (E1).
    nautilus_fields: dict[str, object] = {
        "order_id_tag": live_node_input.order_id_tag,
        "external_order_instrument_ids": [instrument_id],
    }
    config: StrategyConfig = config_class.__new__(config_class, **nautilus_fields)
    config.__init__(instrument_id=instrument_id, bar_type=bar_type)  # pyright: ignore[reportCallIssue, reportUnknownMemberType]
    return config


async def wait_for_end_or_stop(
    live_node: LiveNode, live_node_input: LiveNodeInput, stop_requested: asyncio.Event, gateway_watch: GatewayWatch
) -> LiveNodeEnd:
    run_task = asyncio.create_task(live_node.run_async())
    stop_task = asyncio.create_task(stop_requested.wait())
    gateway_loss_task = asyncio.create_task(wait_for_gateway_loss(live_node_input, gateway_watch))
    await asyncio.wait({run_task, stop_task, gateway_loss_task}, return_when=asyncio.FIRST_COMPLETED)
    is_gateway_lost = gateway_loss_task.done() and not stop_requested.is_set()
    if stop_requested.is_set() or is_gateway_lost:
        # LiveNode.stop does not cancel orders and does not close positions (section 12.6). No manage_stop.
        live_node.handle().stop()
    stop_task.cancel()
    gateway_loss_task.cancel()
    await run_task
    return "gateway_lost" if is_gateway_lost else "ended"


async def run_live_node(
    live_node_input: LiveNodeInput, stop_requested: asyncio.Event, *, gateway_watch: GatewayWatch | None = None
) -> LiveNodeEnd:
    """Runs until `stop_requested` is set, until IB Gateway is lost, or until the LiveNode ends by itself."""
    instrument_id = create_instrument_id(live_node_input)
    with tempfile.TemporaryDirectory(prefix=f"atrade-forward-test-{live_node_input.forward_test_id}-") as directory:
        strategy_class, config_class = load_strategy_classes(live_node_input.strategy_code, Path(directory))
        warm_up_catalog = write_look_back_catalog(
            list(live_node_input.warm_up_bars), live_node_input.instrument, live_node_input.bar_period, Path(directory)
        )
        live_node = build_live_node(live_node_input, instrument_id, warm_up_catalog)
        live_node.add_strategy(strategy_class(create_strategy_config(config_class, live_node_input, instrument_id)))
        live_node.add_actor(create_recorder(live_node_input, instrument_id))
        try:
            return await wait_for_end_or_stop(
                live_node, live_node_input, stop_requested, gateway_watch or GatewayWatch()
            )
        finally:
            live_node.dispose()
