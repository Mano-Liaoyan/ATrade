"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import type { InstrumentIdentityInput } from "@/lib/instrumentIdentity";
import { useTerminalChartWorkspaceWorkflow } from "@/lib/terminalChartWorkspaceWorkflow";
import { CHART_RANGE_LABELS, type ChartRange } from "@/types/marketData";
import type {
  DisabledTerminalModuleId,
  EnabledTerminalModuleId,
  TerminalNavigationIntent,
} from "@/types/terminal";
import { getTerminalDisabledModuleState } from "@/lib/terminalModuleRegistry";
import { TerminalDisabledModule } from "./TerminalDisabledModule";
import { TerminalHelpModule } from "./TerminalHelpModule";
import { TerminalModuleRail } from "./TerminalModuleRail";
import { TerminalPanel } from "./TerminalPanel";
import { TerminalStatusBadge } from "./TerminalStatusBadge";
import { TerminalStatusModule } from "./TerminalStatusModule";
import { TerminalStatusStrip } from "./TerminalStatusStrip";
import { TerminalMarketMonitor } from "./TerminalMarketMonitor";
import { TerminalWorkspaceLayout } from "./TerminalWorkspaceLayout";
import { TerminalAnalysisWorkspace } from "./TerminalAnalysisWorkspace";
import { TerminalChartWorkspace } from "./TerminalChartWorkspace";

type ATradeTerminalAppProps = {
  initialChartRange?: ChartRange;
  initialIdentity?: InstrumentIdentityInput | null;
  initialModuleId?: EnabledTerminalModuleId;
  initialSymbol?: string | null;
};

export function ATradeTerminalApp({
  initialChartRange = "1D",
  initialIdentity = null,
  initialModuleId = "HOME",
  initialSymbol = null,
}: ATradeTerminalAppProps) {
  const router = useRouter();
  const [activeModuleId, setActiveModuleId] = useState<EnabledTerminalModuleId>(initialModuleId);
  const [disabledModuleId, setDisabledModuleId] = useState<DisabledTerminalModuleId | null>(null);
  const [navigationStatus, setNavigationStatus] = useState("Ready for module navigation.");
  const [pendingFocusRequest, setPendingFocusRequest] = useState<{ targetId: string } | null>(null);
  const [seededSearchQuery, setSeededSearchQuery] = useState("");
  const normalizedInitialSymbol = initialSymbol?.toUpperCase() ?? null;
  const [activeSymbol, setActiveSymbol] = useState<string | null>(normalizedInitialSymbol);
  const [activeIdentity, setActiveIdentity] = useState<InstrumentIdentityInput | null>(initialIdentity);
  const [activeChartRange, setActiveChartRange] = useState<ChartRange>(initialChartRange);
  const marketDataStatus = "Market monitor owns provider state";
  const watchlistStatus = "Backend-owned pins in monitor";

  useEffect(() => {
    setActiveModuleId(initialModuleId);
  }, [initialModuleId]);

  useEffect(() => {
    setActiveSymbol(normalizedInitialSymbol);
    setActiveIdentity(initialIdentity);
  }, [initialIdentity, normalizedInitialSymbol]);

  useEffect(() => {
    setActiveChartRange(initialChartRange);
  }, [initialChartRange]);

  useEffect(() => {
    if (!pendingFocusRequest) {
      return;
    }

    const { targetId } = pendingFocusRequest;
    const animationFrame = window.requestAnimationFrame(() => {
      const target = document.getElementById(targetId);
      target?.focus({ preventScroll: true });
      target?.scrollIntoView({ block: "start", behavior: "smooth" });
    });

    return () => window.cancelAnimationFrame(animationFrame);
  }, [activeModuleId, disabledModuleId, pendingFocusRequest]);

  const openIntent = useCallback(
    (intent: TerminalNavigationIntent, statusMessage: string) => {
      setDisabledModuleId(null);
      setNavigationStatus(statusMessage);
      setPendingFocusRequest({ targetId: intent.focusTargetId ?? getModuleFocusTargetId(intent.moduleId) });

      if (intent.moduleId === "SEARCH") {
        setSeededSearchQuery(intent.searchQuery ?? "");
      } else if (intent.moduleId === "HOME" || intent.moduleId === "WATCHLIST") {
        setSeededSearchQuery("");
      }

      if ((intent.moduleId === "CHART" || intent.moduleId === "ANALYSIS") && intent.symbol) {
        setActiveSymbol(intent.symbol.toUpperCase());
        setActiveIdentity(intent.identity ?? null);
        if (intent.chartRange) {
          setActiveChartRange(intent.chartRange);
        }
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
        const route = intent.route ?? `/symbols/${encodeURIComponent(intent.symbol)}`;
        if (normalizedInitialSymbol !== intent.symbol || intent.route) {
          router.push(route);
        }
        return;
      }

      if (intent.moduleId === "ANALYSIS" && intent.symbol) {
        setActiveModuleId("ANALYSIS");
        const route = intent.route ?? `/symbols/${encodeURIComponent(intent.symbol)}?module=ANALYSIS`;
        if (normalizedInitialSymbol !== intent.symbol || intent.route) {
          router.push(route);
        }
        return;
      }

      setActiveModuleId(intent.moduleId);
    },
    [normalizedInitialSymbol, router],
  );

  function handleModuleSelect(moduleId: EnabledTerminalModuleId) {
    openIntent(
      { moduleId, focusTargetId: getModuleFocusTargetId(moduleId), route: moduleId === "HOME" ? "/" : undefined },
      `Opened ${moduleId} from the module rail.`,
    );
  }

  function handleDisabledModule(moduleId: DisabledTerminalModuleId) {
    const unavailable = getTerminalDisabledModuleState(moduleId);
    setDisabledModuleId(moduleId);
    setNavigationStatus(`${unavailable.title}: ${unavailable.message}`);
    setPendingFocusRequest({ targetId: `terminal-disabled-${moduleId.toLowerCase()}` });
  }

  const moduleContent = disabledModuleId ? (
    <div id={`terminal-disabled-${disabledModuleId.toLowerCase()}`} tabIndex={-1}>
      <TerminalDisabledModule moduleId={disabledModuleId} />
    </div>
  ) : (
    <TerminalModuleContent
      activeModuleId={activeModuleId}
      chartRange={activeChartRange}
      identity={activeIdentity}
      onOpenIntent={openIntent}
      searchQuery={seededSearchQuery}
      symbol={activeSymbol}
    />
  );

  return (
    <section className="atrade-terminal-app" data-testid="atrade-terminal-app" aria-label="ATrade paper workspace application frame">
      <header className="atrade-terminal-app__header">
        <div className="atrade-terminal-app__brand">
          <p className="eyebrow">ATrade Workspace</p>
          <h1>Paper Trading Workspace</h1>
          <p>Module-driven paper workspace · ATrade.Api boundary · provider-truthful states</p>
        </div>
      </header>

      <div className="terminal-safety-strip" data-testid="terminal-safety-strip" aria-label="Paper trading safety and provider identity notes">
        <span>Paper-only workspace: search, watchlist, charts, status, help, and analysis entry points are exposed without order controls.</span>
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
          <TerminalWorkspaceLayout
            activeModuleId={activeModuleId}
            context={(
              <TerminalContextSummary
                activeModuleId={activeModuleId}
                marketDataStatus={marketDataStatus}
                symbol={activeSymbol}
                watchlistStatus={watchlistStatus}
              />
            )}
            monitor={<TerminalMonitorPanel />}
          >
            {moduleContent}
          </TerminalWorkspaceLayout>
        </main>
      </div>

      <TerminalStatusStrip
        activeModuleId={activeModuleId}
        marketDataStatus={marketDataStatus}
        statusMessage={navigationStatus}
        symbol={activeSymbol}
        watchlistStatus={watchlistStatus}
      />
    </section>
  );
}

function TerminalContextSummary({
  activeModuleId,
  marketDataStatus,
  symbol,
  watchlistStatus,
}: {
  activeModuleId: EnabledTerminalModuleId;
  marketDataStatus: string;
  symbol: string | null;
  watchlistStatus: string;
}) {
  return (
    <div className="terminal-context-summary" data-testid="terminal-context-summary">
      <TerminalPanel
        eyebrow="Context"
        title="Provider and safety map"
        description="Context stays visible while modules change, so provider state and paper-only constraints are never hidden by navigation."
        tone="inset"
      >
        <dl className="terminal-context-summary__grid">
          <div>
            <dt>Active module</dt>
            <dd>{activeModuleId}</dd>
          </div>
          <div>
            <dt>Market data</dt>
            <dd>{marketDataStatus}</dd>
          </div>
          <div>
            <dt>Watchlist</dt>
            <dd>{watchlistStatus}</dd>
          </div>
          <div>
            <dt>Symbol</dt>
            <dd>{symbol ?? "No symbol selected"}</dd>
          </div>
        </dl>
      </TerminalPanel>
      <TerminalPanel eyebrow="Safety" title="Paper-only status" tone="inset" actions={<TerminalStatusBadge tone="warning">No orders</TerminalStatusBadge>}>
        <p>Orders are disabled by the paper-only safety contract. Browser-visible data flows through ATrade.Api.</p>
      </TerminalPanel>
    </div>
  );
}

function TerminalMonitorPanel() {
  return (
    <div className="terminal-monitor-panel" data-testid="terminal-monitor-panel">
      <span className="terminal-monitor-panel__label">Monitor</span>
      <span>SEARCH, WATCHLIST, and HOME render the dense market monitor.</span>
      <ul>
        <li>
          <strong>Search</strong>
          <span>Capped ranked IBKR stock results</span>
        </li>
        <li>
          <strong>Watch</strong>
          <span>Backend-owned exact pins</span>
        </li>
        <li>
          <strong>Actions</strong>
          <span>Chart/analysis preserve identity</span>
        </li>
      </ul>
    </div>
  );
}

type TerminalModuleContentProps = {
  activeModuleId: EnabledTerminalModuleId;
  chartRange: ChartRange;
  identity: InstrumentIdentityInput | null;
  onOpenIntent: (intent: TerminalNavigationIntent, statusMessage: string) => void;
  searchQuery: string;
  symbol: string | null;
};

function TerminalModuleContent({
  activeModuleId,
  chartRange,
  identity,
  onOpenIntent,
  searchQuery,
  symbol,
}: TerminalModuleContentProps) {
  switch (activeModuleId) {
    case "HOME":
      return <TerminalHomeModule onOpenIntent={onOpenIntent} searchQuery={searchQuery} />;
    case "SEARCH":
      return <TerminalSearchModule onOpenIntent={onOpenIntent} searchQuery={searchQuery} />;
    case "WATCHLIST":
      return <TerminalWatchlistModule onOpenIntent={onOpenIntent} />;
    case "CHART":
      return symbol ? <TerminalChartModule identity={identity} initialChartRange={chartRange} symbol={symbol} /> : <TerminalChartPlaceholder />;
    case "ANALYSIS":
      return <TerminalAnalysisModule chartRange={chartRange} identity={identity} symbol={symbol} />;
    case "STATUS":
      return <TerminalStatusModule />;
    case "HELP":
      return <TerminalHelpModule />;
    default:
      return <TerminalHelpModule />;
  }
}

type TerminalMarketMonitorModuleProps = {
  onOpenIntent: (intent: TerminalNavigationIntent, statusMessage: string) => void;
  searchQuery?: string;
};

function TerminalHomeModule({ onOpenIntent, searchQuery = "" }: TerminalMarketMonitorModuleProps) {
  return (
    <section className="terminal-module terminal-module--home workspace-stack" data-testid="terminal-home-module" id="terminal-module-home" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Home"
        title="Paper workspace home"
        description="Paper-only module workspace with provider state, search, watchlist, chart, analysis, status, help, and the dense market monitor."
        actions={<TerminalStatusBadge tone="success">Paper only</TerminalStatusBadge>}
      >
        <div className="terminal-home-summary">
          <div>
            <span>Market monitor</span>
            <strong>Search · watch · trend</strong>
            <small>Unified bounded search, provider trending, and backend-owned exact pins.</small>
          </div>
          <div>
            <span>Identity</span>
            <strong>Exact handoff</strong>
            <small>Provider, provider ID, market, currency, and asset class stay on chart/analysis routes.</small>
          </div>
          <div>
            <span>Safety</span>
            <strong>No live orders</strong>
            <small>Orders are disabled by the paper-only safety contract.</small>
          </div>
        </div>
      </TerminalPanel>

      <TerminalMarketMonitor initialSearchQuery={searchQuery} onOpenIntent={onOpenIntent} title="Home market monitor" />
    </section>
  );
}

function TerminalSearchModule({ onOpenIntent, searchQuery = "" }: TerminalMarketMonitorModuleProps) {
  return (
    <section className="terminal-module terminal-module--search" data-testid="terminal-search-module" id="terminal-search" tabIndex={-1}>
      <TerminalMarketMonitor initialSearchQuery={searchQuery} onOpenIntent={onOpenIntent} title={searchQuery ? `Search monitor · ${searchQuery}` : "Search market monitor"} />
    </section>
  );
}

function TerminalWatchlistModule({ onOpenIntent }: TerminalMarketMonitorModuleProps) {
  return (
    <section className="terminal-module terminal-module--watchlist" data-testid="terminal-watchlist-module" id="terminal-watchlist" tabIndex={-1}>
      <TerminalMarketMonitor onOpenIntent={onOpenIntent} title="Watchlist market monitor" />
    </section>
  );
}

function TerminalChartPlaceholder() {
  return (
    <section className="terminal-module terminal-module--chart" data-testid="terminal-chart-placeholder" id="terminal-chart" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Chart"
        title="Open a symbol chart"
        description="Open a result from SEARCH or WATCHLIST so exact provider identity can flow through the route when available."
        actions={<TerminalStatusBadge tone="info">CHART</TerminalStatusBadge>}
      >
        <p>Select Chart on a market monitor row to keep provider/runtime states visible through the chart workflow.</p>
      </TerminalPanel>
    </section>
  );
}

function TerminalChartModule({ identity, initialChartRange, symbol }: { identity: InstrumentIdentityInput | null; initialChartRange: ChartRange; symbol: string }) {
  const chart = useTerminalChartWorkspaceWorkflow({ symbol, identity, initialChartRange });

  return (
    <section className="terminal-module terminal-module--chart" data-testid="terminal-chart-module" id="terminal-chart" tabIndex={-1}>
      <TerminalChartWorkspace chart={chart} identity={identity} />
    </section>
  );
}

function TerminalAnalysisModule({ chartRange, identity, symbol }: { chartRange: ChartRange; identity: InstrumentIdentityInput | null; symbol: string | null }) {
  return (
    <section className="terminal-module terminal-module--analysis workspace-stack" data-testid="terminal-analysis-module" id="terminal-analysis" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Analysis"
        title={symbol ? `${symbol} analysis workspace` : "Open analysis for a symbol"}
        description="Provider-neutral analysis lists configured engines and surfaces no-engine or runtime-unavailable states without fake signals."
        actions={<TerminalStatusBadge tone="info">ANALYSIS</TerminalStatusBadge>}
      >
        {symbol ? <p>Running over the selected {CHART_RANGE_LABELS[chartRange]} chart range from the route or chart workspace context.</p> : <p>Open a chart or select Analyze from a market monitor row before viewing symbol analysis.</p>}
      </TerminalPanel>
      <TerminalAnalysisWorkspace chartRange={chartRange} identity={identity} symbol={symbol} />
    </section>
  );
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
