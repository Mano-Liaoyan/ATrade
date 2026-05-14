"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import type { InstrumentIdentityInput } from "@/lib/instrumentIdentity";
import { attachTerminalWheelScrollOwnership } from "@/lib/terminalWheelScrollOwnership";
import { createTerminalModuleRoute, createTerminalSymbolRoute, isTerminalSymbolModuleId } from "@/lib/terminalRoutes";
import { useTerminalChartWorkspaceWorkflow } from "@/lib/terminalChartWorkspaceWorkflow";
import { CHART_RANGE_LABELS, type ChartRange } from "@/types/marketData";
import type {
  DisabledTerminalModuleId,
  EnabledTerminalModuleId,
  TerminalNavigationIntent,
} from "@/types/terminal";
import { TerminalDisabledModule } from "./TerminalDisabledModule";
import { TerminalHelpModule } from "./TerminalHelpModule";
import { TerminalModuleRail } from "./TerminalModuleRail";
import { TerminalPanel } from "./TerminalPanel";
import { TerminalStatusBadge } from "./TerminalStatusBadge";
import { TerminalStatusModule } from "./TerminalStatusModule";
import { TerminalWorkspaceLayout } from "./TerminalWorkspaceLayout";
import { TerminalAnalysisWorkspace } from "./TerminalAnalysisWorkspace";
import { TerminalBacktestWorkspace } from "./TerminalBacktestWorkspace";
import { TerminalChartLandingModule } from "./TerminalChartLandingModule";
import { TerminalChartWorkspace } from "./TerminalChartWorkspace";
import { TerminalHomeModule } from "./TerminalHomeModule";
import { TerminalSearchModule } from "./TerminalSearchModule";
import { TerminalWatchlistModule } from "./TerminalWatchlistModule";

type ATradeTerminalAppProps = {
  initialChartRange?: ChartRange;
  initialDisabledModuleId?: DisabledTerminalModuleId | null;
  initialIdentity?: InstrumentIdentityInput | null;
  initialModuleId?: EnabledTerminalModuleId;
  initialSymbol?: string | null;
};

export function ATradeTerminalApp({
  initialChartRange = "1D",
  initialDisabledModuleId = null,
  initialIdentity = null,
  initialModuleId = "HOME",
  initialSymbol = null,
}: ATradeTerminalAppProps) {
  const router = useRouter();
  const terminalFrameRef = useRef<HTMLElement | null>(null);
  const [activeModuleId, setActiveModuleId] = useState<EnabledTerminalModuleId>(initialModuleId);
  const [disabledModuleId, setDisabledModuleId] = useState<DisabledTerminalModuleId | null>(initialDisabledModuleId);
  const [navigationStatus, setNavigationStatus] = useState("Ready for module navigation.");
  const [pendingFocusRequest, setPendingFocusRequest] = useState<{ targetId: string } | null>(null);
  const [seededSearchQuery, setSeededSearchQuery] = useState("");
  const normalizedInitialSymbol = initialSymbol?.toUpperCase() ?? null;
  const [activeSymbol, setActiveSymbol] = useState<string | null>(normalizedInitialSymbol);
  const [activeIdentity, setActiveIdentity] = useState<InstrumentIdentityInput | null>(initialIdentity);
  const [activeChartRange, setActiveChartRange] = useState<ChartRange>(initialChartRange);

  useEffect(() => {
    const terminalFrame = terminalFrameRef.current;

    if (!terminalFrame) {
      return;
    }

    return attachTerminalWheelScrollOwnership(terminalFrame);
  }, []);

  useEffect(() => {
    setActiveModuleId(initialModuleId);
  }, [initialModuleId]);

  useEffect(() => {
    setDisabledModuleId(initialDisabledModuleId);
    if (initialDisabledModuleId) {
      setNavigationStatus(`${initialDisabledModuleId} is visible-disabled and unavailable in the paper workspace.`);
      setPendingFocusRequest({ targetId: `terminal-disabled-${initialDisabledModuleId.toLowerCase()}` });
      return;
    }

    setNavigationStatus(`Opened ${initialModuleId} from the URL route.`);
    setPendingFocusRequest({ targetId: getModuleFocusTargetId(initialModuleId) });
  }, [initialDisabledModuleId, initialModuleId]);

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

      if (isTerminalSymbolModuleId(intent.moduleId) && intent.symbol) {
        setActiveSymbol(intent.symbol.toUpperCase());
        setActiveIdentity(intent.identity ?? null);
        if (intent.chartRange) {
          setActiveChartRange(intent.chartRange);
        }
      }

      setActiveModuleId(intent.moduleId);

      const route = intent.route ?? (
        isTerminalSymbolModuleId(intent.moduleId) && intent.symbol
          ? createTerminalSymbolRoute(intent.moduleId, intent.identity ?? { symbol: intent.symbol }, { chartRange: intent.chartRange })
          : createTerminalModuleRoute(intent.moduleId)
      );
      pushTerminalRoute(route, router.push);
    },
    [router],
  );

  function handleModuleSelect(moduleId: EnabledTerminalModuleId) {
    openIntent(
      { moduleId, focusTargetId: getModuleFocusTargetId(moduleId), route: createTerminalModuleRoute(moduleId) },
      `Opened ${moduleId} from the module rail.`,
    );
  }

  function handleDisabledModule(moduleId: DisabledTerminalModuleId) {
    setDisabledModuleId(moduleId);
    setNavigationStatus(`${moduleId} is visible-disabled and unavailable in the paper workspace.`);
    setPendingFocusRequest({ targetId: `terminal-disabled-${moduleId.toLowerCase()}` });
    pushTerminalRoute(createTerminalModuleRoute(moduleId), router.push);
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
    <section ref={terminalFrameRef} className="atrade-terminal-app" data-testid="atrade-terminal-app" aria-label="ATrade paper workspace application frame">
      <p className="sr-only" aria-live="polite" role="status">
        {navigationStatus}
      </p>

      <div className="atrade-terminal-app__body">
        <TerminalModuleRail
          activeModuleId={activeModuleId}
          disabledModuleId={disabledModuleId}
          onDisabledModule={handleDisabledModule}
          onModuleSelect={handleModuleSelect}
        />
        <main className="atrade-terminal-app__workspace" data-testid="terminal-workspace" aria-label={`${activeModuleId} workspace`}>
          <TerminalWorkspaceLayout activeModuleId={activeModuleId}>
            {moduleContent}
          </TerminalWorkspaceLayout>
        </main>
      </div>
    </section>
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
      return symbol ? <TerminalChartModule identity={identity} initialChartRange={chartRange} symbol={symbol} /> : <TerminalChartLandingModule initialChartRange={chartRange} onOpenIntent={onOpenIntent} />;
    case "ANALYSIS":
      return <TerminalAnalysisModule chartRange={chartRange} identity={identity} symbol={symbol} />;
    case "BACKTEST":
      return <TerminalBacktestModule chartRange={chartRange} identity={identity} symbol={symbol} />;
    case "STATUS":
      return <TerminalStatusModule />;
    case "HELP":
      return <TerminalHelpModule />;
    default:
      return <TerminalHelpModule />;
  }
}

function TerminalChartModule({ identity, initialChartRange, symbol }: { identity: InstrumentIdentityInput | null; initialChartRange: ChartRange; symbol: string }) {
  const chart = useTerminalChartWorkspaceWorkflow({ symbol, identity, initialChartRange });

  return (
    <section className="terminal-module terminal-module--chart" data-testid="terminal-chart-module" id="terminal-chart" tabIndex={-1}>
      <TerminalChartWorkspace chart={chart} identity={identity} />
    </section>
  );
}

function TerminalBacktestModule({ chartRange, identity, symbol }: { chartRange: ChartRange; identity: InstrumentIdentityInput | null; symbol: string | null }) {
  return (
    <section className="terminal-module terminal-module--backtest workspace-stack" data-testid="terminal-backtest-module" id="terminal-backtest" tabIndex={-1}>
      <TerminalBacktestWorkspace chartRange={chartRange} identity={identity} symbol={symbol} />
    </section>
  );
}

function TerminalAnalysisModule({ chartRange, identity, symbol }: { chartRange: ChartRange; identity: InstrumentIdentityInput | null; symbol: string | null }) {
  return (
    <section className="terminal-module terminal-module--analysis workspace-stack" data-testid="terminal-analysis-module" id="terminal-analysis" tabIndex={-1}>
      <TerminalPanel
        eyebrow="Analysis"
        title={symbol ? `${symbol} analysis workspace` : "Open analysis for a symbol"}
        description="Provider-neutral analysis with engine status."
        actions={<TerminalStatusBadge tone="info">ANALYSIS</TerminalStatusBadge>}
      >
        {symbol ? <p>Range: {CHART_RANGE_LABELS[chartRange]}.</p> : <p>Open a chart or market row first.</p>}
      </TerminalPanel>
      <TerminalAnalysisWorkspace chartRange={chartRange} identity={identity} symbol={symbol} />
    </section>
  );
}

function pushTerminalRoute(route: string, push: (href: string) => void) {
  const currentRoute = `${window.location.pathname}${window.location.search}`;

  if (currentRoute !== route) {
    push(route);
  }
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
    case "BACKTEST":
      return "terminal-backtest";
    case "STATUS":
      return "terminal-status";
    case "HELP":
      return "terminal-help";
    default:
      return "terminal-workspace";
  }
}
