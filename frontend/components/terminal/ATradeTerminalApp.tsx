"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AnalysisPanel } from "@/components/AnalysisPanel";
import { BrokerPaperStatus } from "@/components/BrokerPaperStatus";
import { CandlestickChart } from "@/components/CandlestickChart";
import { IndicatorPanel } from "@/components/IndicatorPanel";
import { SymbolSearch } from "@/components/SymbolSearch";
import { TimeframeSelector } from "@/components/TimeframeSelector";
import { TrendingList } from "@/components/TrendingList";
import { Watchlist } from "@/components/Watchlist";
import type { InstrumentIdentityInput } from "@/lib/instrumentIdentity";
import { getTrendingSymbols } from "@/lib/marketDataClient";
import { formatMarketDataSourceLabel, useSymbolChartWorkflow } from "@/lib/symbolChartWorkflow";
import { useWatchlistWorkflow } from "@/lib/watchlistWorkflow";
import type { TrendingSymbol } from "@/types/marketData";
import { CHART_RANGE_LABELS, type ChartRange } from "@/types/marketData";
import type {
  DisabledTerminalModuleId,
  EnabledTerminalModuleId,
  TerminalCommandParseResult,
  TerminalNavigationIntent,
} from "@/types/terminal";
import { getTerminalDisabledModuleState } from "@/lib/terminalModuleRegistry";
import { TerminalCommandInput } from "./TerminalCommandInput";
import { TerminalDisabledModule } from "./TerminalDisabledModule";
import { TerminalHelpModule } from "./TerminalHelpModule";
import { TerminalModuleRail } from "./TerminalModuleRail";
import { TerminalPanel } from "./TerminalPanel";
import { TerminalStatusBadge } from "./TerminalStatusBadge";
import { TerminalStatusModule } from "./TerminalStatusModule";
import { TerminalStatusStrip } from "./TerminalStatusStrip";

type ATradeTerminalAppProps = {
  initialIdentity?: InstrumentIdentityInput | null;
  initialModuleId?: EnabledTerminalModuleId;
  initialSymbol?: string | null;
};

export function ATradeTerminalApp({
  initialIdentity = null,
  initialModuleId = "HOME",
  initialSymbol = null,
}: ATradeTerminalAppProps) {
  const router = useRouter();
  const [activeModuleId, setActiveModuleId] = useState<EnabledTerminalModuleId>(initialModuleId);
  const [disabledModuleId, setDisabledModuleId] = useState<DisabledTerminalModuleId | null>(null);
  const [commandFeedback, setCommandFeedback] = useState("Ready for deterministic terminal commands.");
  const [pendingFocusTargetId, setPendingFocusTargetId] = useState<string | null>(null);
  const [seededSearchQuery, setSeededSearchQuery] = useState("");
  const [trendingSymbols, setTrendingSymbols] = useState<TrendingSymbol[]>([]);
  const [marketDataLoading, setMarketDataLoading] = useState(true);
  const [marketDataError, setMarketDataError] = useState<string | null>(null);
  const [marketDataSource, setMarketDataSource] = useState<string | null>(null);
  const watchlist = useWatchlistWorkflow();
  const normalizedInitialSymbol = initialSymbol?.toUpperCase() ?? null;

  const loadTrendingSymbols = useCallback(async () => {
    setMarketDataLoading(true);
    setMarketDataError(null);

    try {
      const response = await getTrendingSymbols();
      setTrendingSymbols(response.symbols);
      setMarketDataSource(response.source);
    } catch (caughtError) {
      setMarketDataError(caughtError instanceof Error ? caughtError.message : "IBKR market data is unavailable.");
      setMarketDataSource(null);
      setTrendingSymbols([]);
    } finally {
      setMarketDataLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTrendingSymbols();
  }, [loadTrendingSymbols]);

  useEffect(() => {
    setActiveModuleId(initialModuleId);
  }, [initialModuleId]);

  useEffect(() => {
    if (!pendingFocusTargetId) {
      return;
    }

    const animationFrame = window.requestAnimationFrame(() => {
      const target = document.getElementById(pendingFocusTargetId);
      target?.focus({ preventScroll: true });
      target?.scrollIntoView({ block: "start", behavior: "smooth" });
    });

    return () => window.cancelAnimationFrame(animationFrame);
  }, [activeModuleId, disabledModuleId, pendingFocusTargetId]);

  const sortedTrendingSymbols = useMemo(
    () => [...trendingSymbols].sort((left, right) => right.score - left.score),
    [trendingSymbols],
  );

  const marketDataStatus = marketDataLoading
    ? "Loading IBKR/iBeam"
    : marketDataError
      ? "Provider unavailable"
      : `${sortedTrendingSymbols.length} provider symbols`;
  const watchlistStatus = watchlist.loading
    ? "Loading pins"
    : watchlist.error
      ? "Backend unavailable"
      : `${watchlist.symbols.length} saved pins`;

  const openIntent = useCallback(
    (intent: TerminalNavigationIntent, feedback: string) => {
      setDisabledModuleId(null);
      setCommandFeedback(feedback);
      setPendingFocusTargetId(intent.focusTargetId ?? `terminal-module-${intent.moduleId.toLowerCase()}`);

      if (intent.moduleId === "SEARCH" && intent.searchQuery) {
        setSeededSearchQuery(intent.searchQuery);
      }

      if (intent.moduleId === "HOME") {
        setActiveModuleId("HOME");
        if (window.location.pathname !== "/") {
          router.push("/");
        }
        return;
      }

      if (intent.moduleId === "CHART" && intent.symbol) {
        setActiveModuleId("CHART");
        if (normalizedInitialSymbol !== intent.symbol) {
          router.push(intent.route ?? `/symbols/${encodeURIComponent(intent.symbol)}`);
        }
        return;
      }

      if (intent.moduleId === "ANALYSIS" && intent.symbol && normalizedInitialSymbol !== intent.symbol) {
        setActiveModuleId("ANALYSIS");
        router.push(intent.route ?? `/symbols/${encodeURIComponent(intent.symbol)}?module=ANALYSIS`);
        return;
      }

      setActiveModuleId(intent.moduleId);
    },
    [normalizedInitialSymbol, router],
  );

  function handleCommand(result: TerminalCommandParseResult) {
    if (!result.ok) {
      setDisabledModuleId(null);
      setCommandFeedback(`${result.message} ${result.help}`);
      return;
    }

    if (result.action.kind === "open-disabled-module") {
      setDisabledModuleId(result.action.moduleId);
      setCommandFeedback(result.feedback);
      setPendingFocusTargetId(`terminal-disabled-${result.action.moduleId.toLowerCase()}`);
      return;
    }

    openIntent(result.action.intent, result.feedback);
  }

  function handleModuleSelect(moduleId: EnabledTerminalModuleId) {
    openIntent(
      { moduleId, focusTargetId: getModuleFocusTargetId(moduleId), route: moduleId === "HOME" ? "/" : undefined },
      `Opened ${moduleId} from the module rail.`,
    );
  }

  function handleDisabledModule(moduleId: DisabledTerminalModuleId) {
    const unavailable = getTerminalDisabledModuleState(moduleId);
    setDisabledModuleId(moduleId);
    setCommandFeedback(`${unavailable.title}: ${unavailable.message}`);
    setPendingFocusTargetId(`terminal-disabled-${moduleId.toLowerCase()}`);
  }

  const moduleContent = disabledModuleId ? (
    <div id={`terminal-disabled-${disabledModuleId.toLowerCase()}`} tabIndex={-1}>
      <TerminalDisabledModule moduleId={disabledModuleId} />
    </div>
  ) : (
    <TerminalModuleContent
      activeModuleId={activeModuleId}
      identity={initialIdentity}
      marketDataError={marketDataError}
      marketDataLoading={marketDataLoading}
      marketDataSource={marketDataSource}
      onReloadTrending={loadTrendingSymbols}
      searchQuery={seededSearchQuery}
      sortedTrendingSymbols={sortedTrendingSymbols}
      symbol={normalizedInitialSymbol}
      watchlist={watchlist}
    />
  );

  return (
    <section className="atrade-terminal-app" data-testid="atrade-terminal-app" aria-label="ATrade Terminal application frame">
      <header className="atrade-terminal-app__header">
        <div className="atrade-terminal-app__brand">
          <p className="eyebrow">ATrade Terminal</p>
          <h1>ATrade Terminal Shell</h1>
          <p>Command-first paper workspace · ATrade.Api boundary · provider-truthful states</p>
        </div>
        <TerminalCommandInput feedback={commandFeedback} onCommand={handleCommand} />
      </header>

      <div className="terminal-safety-strip" data-testid="terminal-safety-strip" aria-label="Paper trading safety and provider identity notes">
        <span>Paper-only workspace: ATrade Terminal exposes search, watchlist, charts, status, help, and analysis entry points only.</span>
        <span>Provider state and exact instrument identity stay visible; unavailable states are not replaced with fake market data.</span>
        <span>Orders are disabled by the paper-only safety contract.</span>
      </div>

      <div className="atrade-terminal-app__body">
        <TerminalModuleRail
          activeModuleId={activeModuleId}
          disabledModuleId={disabledModuleId}
          onDisabledModule={handleDisabledModule}
          onModuleSelect={handleModuleSelect}
        />
        <main className="atrade-terminal-app__workspace" data-testid="terminal-workspace" aria-label={`${activeModuleId} workspace`}>
          {moduleContent}
        </main>
      </div>

      <TerminalStatusStrip
        activeModuleId={activeModuleId}
        commandFeedback={commandFeedback}
        marketDataStatus={marketDataStatus}
        symbol={normalizedInitialSymbol}
        watchlistStatus={watchlistStatus}
      />
    </section>
  );
}

type TerminalModuleContentProps = {
  activeModuleId: EnabledTerminalModuleId;
  identity: InstrumentIdentityInput | null;
  marketDataError: string | null;
  marketDataLoading: boolean;
  marketDataSource: string | null;
  onReloadTrending: () => void;
  searchQuery: string;
  sortedTrendingSymbols: TrendingSymbol[];
  symbol: string | null;
  watchlist: ReturnType<typeof useWatchlistWorkflow>;
};

function TerminalModuleContent({
  activeModuleId,
  identity,
  marketDataError,
  marketDataLoading,
  marketDataSource,
  onReloadTrending,
  searchQuery,
  sortedTrendingSymbols,
  symbol,
  watchlist,
}: TerminalModuleContentProps) {
  switch (activeModuleId) {
    case "HOME":
      return (
        <TerminalHomeModule
          marketDataError={marketDataError}
          marketDataLoading={marketDataLoading}
          marketDataSource={marketDataSource}
          onReloadTrending={onReloadTrending}
          sortedTrendingSymbols={sortedTrendingSymbols}
          watchlist={watchlist}
        />
      );
    case "SEARCH":
      return <TerminalSearchModule searchQuery={searchQuery} watchlist={watchlist} />;
    case "WATCHLIST":
      return <TerminalWatchlistModule sortedTrendingSymbols={sortedTrendingSymbols} watchlist={watchlist} />;
    case "CHART":
      return symbol ? <TerminalChartModule identity={identity} symbol={symbol} /> : <TerminalChartPlaceholder />;
    case "ANALYSIS":
      return <TerminalAnalysisModule symbol={symbol} />;
    case "STATUS":
      return <TerminalStatusModule />;
    case "HELP":
      return <TerminalHelpModule />;
    default:
      return <TerminalHelpModule />;
  }
}

type TerminalHomeModuleProps = {
  marketDataError: string | null;
  marketDataLoading: boolean;
  marketDataSource: string | null;
  onReloadTrending: () => void;
  sortedTrendingSymbols: TrendingSymbol[];
  watchlist: ReturnType<typeof useWatchlistWorkflow>;
};

function TerminalHomeModule({
  marketDataError,
  marketDataLoading,
  marketDataSource,
  onReloadTrending,
  sortedTrendingSymbols,
  watchlist,
}: TerminalHomeModuleProps) {
  return (
    <section className="terminal-module terminal-module--home workspace-stack" data-testid="terminal-home-module" id="terminal-module-home" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Home"
        title="ATrade Terminal home"
        description="Paper-only command workspace with provider state, search, watchlist, chart, analysis, status, and help entry points."
        actions={<TerminalStatusBadge tone="success">Paper only</TerminalStatusBadge>}
      >
        <div className="terminal-home-summary">
          <div>
            <span>Market data</span>
            <strong>{marketDataLoading ? "Loading" : marketDataError ? "Unavailable" : `${sortedTrendingSymbols.length} symbols`}</strong>
            <small>{formatMarketDataSource(marketDataSource)}</small>
          </div>
          <div>
            <span>Watchlist</span>
            <strong>{watchlist.loading ? "Loading" : watchlist.error ? "Backend unavailable" : `${watchlist.symbols.length} pins`}</strong>
            <small>Postgres-backed through ATrade.Api</small>
          </div>
          <div>
            <span>Safety</span>
            <strong>No live orders</strong>
            <small>Orders are disabled by the paper-only safety contract.</small>
          </div>
        </div>
      </TerminalPanel>

      <section id="terminal-search" tabIndex={-1}>
        <SymbolSearch
          getPinState={watchlist.getSearchResultPinState}
          onTogglePin={(result) => void watchlist.toggleSearchPin(result)}
        />
      </section>

      <section id="terminal-watchlist" tabIndex={-1}>
        <Watchlist
          symbols={watchlist.symbols}
          trendingSymbols={sortedTrendingSymbols}
          loading={watchlist.loading}
          error={watchlist.error}
          source={watchlist.source}
          getPinState={watchlist.getWatchlistSymbolPinState}
          onRetry={watchlist.retry}
          onRemove={(itemSymbol) => void watchlist.removePin(itemSymbol)}
        />
      </section>

      <TerminalTrendingSection
        marketDataError={marketDataError}
        marketDataLoading={marketDataLoading}
        marketDataSource={marketDataSource}
        onReloadTrending={onReloadTrending}
        sortedTrendingSymbols={sortedTrendingSymbols}
        watchlist={watchlist}
      />
    </section>
  );
}

function TerminalSearchModule({ searchQuery, watchlist }: { searchQuery: string; watchlist: ReturnType<typeof useWatchlistWorkflow> }) {
  return (
    <section className="terminal-module terminal-module--search" data-testid="terminal-search-module" id="terminal-search" tabIndex={-1}>
      <SymbolSearch
        initialQuery={searchQuery}
        getPinState={watchlist.getSearchResultPinState}
        onTogglePin={(result) => void watchlist.toggleSearchPin(result)}
      />
    </section>
  );
}

function TerminalWatchlistModule({
  sortedTrendingSymbols,
  watchlist,
}: {
  sortedTrendingSymbols: TrendingSymbol[];
  watchlist: ReturnType<typeof useWatchlistWorkflow>;
}) {
  return (
    <section className="terminal-module terminal-module--watchlist" data-testid="terminal-watchlist-module" id="terminal-watchlist" tabIndex={-1}>
      <Watchlist
        symbols={watchlist.symbols}
        trendingSymbols={sortedTrendingSymbols}
        loading={watchlist.loading}
        error={watchlist.error}
        source={watchlist.source}
        getPinState={watchlist.getWatchlistSymbolPinState}
        onRetry={watchlist.retry}
        onRemove={(itemSymbol) => void watchlist.removePin(itemSymbol)}
      />
    </section>
  );
}

function TerminalTrendingSection({
  marketDataError,
  marketDataLoading,
  marketDataSource,
  onReloadTrending,
  sortedTrendingSymbols,
  watchlist,
}: {
  marketDataError: string | null;
  marketDataLoading: boolean;
  marketDataSource: string | null;
  onReloadTrending: () => void;
  sortedTrendingSymbols: TrendingSymbol[];
  watchlist: ReturnType<typeof useWatchlistWorkflow>;
}) {
  return (
    <section id="terminal-monitor" className="terminal-module__monitor workspace-stack" aria-label="Trending provider-backed symbols">
      {marketDataLoading ? (
        <div className="workspace-panel loading-state" role="status">
          Loading IBKR/iBeam trending stocks and ETFs…
        </div>
      ) : null}

      {!marketDataLoading && marketDataError ? (
        <div className="workspace-panel error-state" role="alert">
          <strong>IBKR market data unavailable.</strong>
          <p>{marketDataError}</p>
          <button className="primary-button" type="button" onClick={() => void onReloadTrending()}>
            Retry IBKR market data
          </button>
        </div>
      ) : null}

      {!marketDataLoading && !marketDataError && sortedTrendingSymbols.length === 0 ? (
        <div className="workspace-panel empty-state">
          <strong>No trending symbols returned.</strong>
          <p>The IBKR/iBeam provider responded, but no stocks or ETFs were available for the workspace.</p>
        </div>
      ) : null}

      {!marketDataLoading && !marketDataError && sortedTrendingSymbols.length > 0 ? (
        <TrendingList
          symbols={sortedTrendingSymbols}
          getPinState={watchlist.getTrendingPinState}
          source={marketDataSource}
          onTogglePin={(itemSymbol) => void watchlist.toggleTrendingPin(itemSymbol)}
        />
      ) : null}
    </section>
  );
}

function TerminalChartPlaceholder() {
  return (
    <section className="terminal-module terminal-module--chart" data-testid="terminal-chart-placeholder" id="terminal-chart" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Chart"
        title="Open a symbol chart"
        description="Use CHART <symbol> or open a result from SEARCH/WATCHLIST so exact provider identity can flow through the route when available."
        actions={<TerminalStatusBadge tone="info">CHART</TerminalStatusBadge>}
      >
        <p>Example deterministic command: CHART AAPL. Missing provider/runtime states remain visible through the chart workflow.</p>
      </TerminalPanel>
    </section>
  );
}

function TerminalChartModule({ identity, symbol }: { identity: InstrumentIdentityInput | null; symbol: string }) {
  const chart = useSymbolChartWorkflow({ symbol, identity });
  const sourceLabel = formatMarketDataSourceLabel(chart.candles?.source);
  const streamTone = chart.streamState === "connected" ? "success" : chart.streamState === "connecting" ? "info" : "warning";

  return (
    <section className="terminal-module terminal-module--chart workspace-stack" data-testid="terminal-chart-module" id="terminal-chart" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Chart"
        title={`${chart.normalizedSymbol} chart workspace`}
        description="Chart range controls use lookback windows from now while provider/source metadata, SignalR state, and HTTP fallback notes stay visible."
        actions={<TerminalStatusBadge tone={streamTone}>SignalR {chart.streamState}</TerminalStatusBadge>}
      >
        <div id="terminal-chart-range" className="chart-command-range" aria-label="Chart range lookback controls">
          <span className="indicator-label">Chart range lookback controls</span>
          <TimeframeSelector value={chart.chartRange} onChange={chart.setChartRange} />
        </div>
      </TerminalPanel>

      <section className="workspace-panel terminal-data-panel chart-view" data-testid="chart-workspace">
        <div className="panel-heading chart-heading terminal-panel-heading">
          <div>
            <p className="eyebrow">Lookback candlestick chart</p>
            <h2>{chart.normalizedSymbol} candles and indicators</h2>
            <p>Current source: {sourceLabel}. Chart controls request the selected lookback range from now.</p>
          </div>
          <div className="chart-actions">
            <span className={chart.streamState === "connected" ? "stream-pill stream-pill--connected" : "stream-pill"} data-testid="stream-state">
              SignalR {chart.streamState}
            </span>
            <span className="pill">{CHART_RANGE_LABELS[chart.chartRange]} lookback</span>
          </div>
        </div>

        {chart.loading ? <div className="loading-state" role="status">Loading OHLC candlestick chart data…</div> : null}
        {!chart.loading && chart.error ? (
          <div className="error-state" role="alert">
            <strong>IBKR chart data unavailable.</strong>
            <p>{chart.error}</p>
            <button className="primary-button" type="button" onClick={() => void chart.refreshChartData(true)}>
              Retry chart data
            </button>
          </div>
        ) : null}
        {!chart.loading && !chart.error && chart.candles ? <CandlestickChart candles={chart.candles} indicators={chart.indicators} /> : null}

        <IndicatorPanel indicators={chart.indicators} />
        <ChartFooter chart={chart} sourceLabel={sourceLabel} />
      </section>

      <section id="terminal-analysis" tabIndex={-1} aria-label="Provider-neutral analysis entry point">
        <AnalysisPanel symbol={chart.normalizedSymbol} chartRange={chart.chartRange} candleSource={chart.candles?.source} />
      </section>
    </section>
  );
}

function TerminalAnalysisModule({ symbol }: { symbol: string | null }) {
  return (
    <section className="terminal-module terminal-module--analysis workspace-stack" data-testid="terminal-analysis-module" id="terminal-analysis" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Analysis"
        title={symbol ? `${symbol} analysis workspace` : "Open analysis for a symbol"}
        description="Provider-neutral analysis lists configured engines and surfaces no-engine or runtime-unavailable states without fake signals."
        actions={<TerminalStatusBadge tone="info">ANALYSIS</TerminalStatusBadge>}
      >
        {symbol ? <p>Running over the default {CHART_RANGE_LABELS["1D"]} chart range until a chart workspace selects another lookback.</p> : <p>Use ANALYSIS &lt;symbol&gt; from the command input or open a chart before selecting ANALYSIS.</p>}
      </TerminalPanel>
      {symbol ? <AnalysisPanel symbol={symbol} chartRange={"1D" as ChartRange} /> : null}
    </section>
  );
}

function ChartFooter({ chart, sourceLabel }: { chart: ReturnType<typeof useSymbolChartWorkflow>; sourceLabel: string }) {
  return (
    <div className="chart-footer-note">
      <p>
        HTTP candles/indicators are refreshed for the selected lookback range from now. SignalR applies IBKR snapshot updates when `/hubs/market-data` is reachable;
        if streaming is unavailable this view falls back to HTTP polling without synthetic fallback data.
      </p>
      {chart.candles ? <p>Current candle source: {sourceLabel}.</p> : null}
      {chart.streamState === "unavailable" ? (
        <p>Streaming snapshots are unavailable; polling continues against the IBKR/iBeam HTTP provider.</p>
      ) : null}
      {chart.latestUpdate ? (
        <p>
          Last market-data stream update: {chart.latestUpdate.symbol} {chart.latestUpdate.timeframe} range close {chart.latestUpdate.close.toFixed(2)} from {formatMarketDataSourceLabel(chart.latestUpdate.source)}.
        </p>
      ) : null}
      <p>{formatChartIdentity(chart)}</p>
    </div>
  );
}

function formatChartIdentity(chart: ReturnType<typeof useSymbolChartWorkflow>): string {
  if (!chart.chartIdentity) {
    return `${chart.normalizedSymbol} uses the default manual symbol identity until provider metadata is supplied by search, trending, or cache payloads.`;
  }

  const provider = chart.chartIdentity.provider.toUpperCase();
  const providerId = chart.chartIdentity.providerSymbolId ? ` · provider id ${chart.chartIdentity.providerSymbolId}` : "";
  const exchange = chart.chartIdentity.exchange ? ` · market ${chart.chartIdentity.exchange}` : "";

  return `${chart.chartIdentity.symbol} exact instrument identity: provider ${provider}${providerId}${exchange} · ${chart.chartIdentity.currency} · ${chart.chartIdentity.assetClass}.`;
}

function getModuleFocusTargetId(moduleId: EnabledTerminalModuleId): string {
  switch (moduleId) {
    case "HOME":
      return "terminal-module-home";
    case "SEARCH":
      return "terminal-search";
    case "WATCHLIST":
      return "terminal-watchlist";
    case "CHART":
      return "terminal-chart";
    case "ANALYSIS":
      return "terminal-analysis";
    case "STATUS":
      return "terminal-status";
    case "HELP":
      return "terminal-help";
    default:
      return "terminal-workspace";
  }
}

function formatMarketDataSource(source: string | null): string {
  if (!source) {
    return "IBKR/iBeam";
  }

  if (source.includes("scanner")) {
    return "IBKR scanner";
  }

  return source.includes("ibkr") ? "IBKR/iBeam" : source;
}
