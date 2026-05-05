import {
  DISABLED_TERMINAL_MODULE_IDS,
  ENABLED_TERMINAL_MODULE_IDS,
  type DisabledTerminalModuleDefinition,
  type DisabledTerminalModuleId,
  type EnabledTerminalModuleDefinition,
  type EnabledTerminalModuleId,
  type TerminalDisabledModuleState,
  type TerminalModuleDefinition,
  type TerminalModuleId,
} from "@/types/terminal";

export const TERMINAL_ENABLED_MODULES: EnabledTerminalModuleDefinition[] = [
  {
    id: "HOME",
    label: "Home",
    shortLabel: "HM",
    description: "Landing workspace with paper safety, provider state, shortcuts, and current market context.",
    availability: "enabled",
    placement: "primary",
    route: "/",
    tone: "positive",
  },
  {
    id: "SEARCH",
    label: "Search",
    shortLabel: "SR",
    description: "Bounded stock search through ATrade.Api with exact provider and market identity badges.",
    availability: "enabled",
    placement: "primary",
    route: "/#terminal-search",
  },
  {
    id: "WATCHLIST",
    label: "Watchlist",
    shortLabel: "WL",
    description: "Backend-owned exact provider/market pins from the workspace watchlist API.",
    availability: "enabled",
    placement: "primary",
    route: "/#terminal-watchlist",
  },
  {
    id: "CHART",
    label: "Chart",
    shortLabel: "CH",
    description: "Symbol chart workspace with source labels, range controls, indicators, and safe fallback states.",
    availability: "enabled",
    placement: "primary",
    route: "/symbols/[symbol]",
  },
  {
    id: "ANALYSIS",
    label: "Analysis",
    shortLabel: "AN",
    description: "Provider-neutral analysis workspace with explicit no-engine and runtime-unavailable states.",
    availability: "enabled",
    placement: "primary",
    route: "/#terminal-analysis",
  },
  {
    id: "STATUS",
    label: "Status",
    shortLabel: "ST",
    description: "Operational status for API health, broker readiness, provider/cache/source metadata, and paper mode.",
    availability: "enabled",
    placement: "primary",
    route: "/#terminal-status",
  },
  {
    id: "HELP",
    label: "Help",
    shortLabel: "?",
    description: "Module reference with provider-state explanations and paper-only safety reminders.",
    availability: "enabled",
    placement: "primary",
    route: "/#terminal-help",
  },
];

export const TERMINAL_DISABLED_MODULES: DisabledTerminalModuleDefinition[] = [
  {
    id: "NEWS",
    label: "News",
    shortLabel: "NW",
    description: "Future news workflow placeholder.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "News is not available in this release",
    disabledMessage: "No committed news provider or news API exists in ATrade yet.",
    disabledDetails: [
      "The workspace does not show scraped headlines, stale fixture stories, or invented market narratives.",
      "Use provider-backed market data modules instead of mock news content.",
    ],
  },
  {
    id: "PORTFOLIO",
    label: "Portfolio",
    shortLabel: "PF",
    description: "Future durable positions and P/L workspace placeholder.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "Portfolio is not available in this release",
    disabledMessage: "No durable positions or portfolio P/L workspace exists beyond current paper account status contracts.",
    disabledDetails: [
      "The workspace does not synthesize holdings, balances, or account identifiers.",
      "Paper account status remains visible through STATUS without exposing order-entry controls.",
    ],
  },
  {
    id: "RESEARCH",
    label: "Research",
    shortLabel: "RS",
    description: "Future research-document and fundamentals workflow placeholder.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "Research is not available in this release",
    disabledMessage: "No research-document ingestion, fundamentals provider, or analyst-rating API is configured for browser use.",
    disabledDetails: [
      "The workspace does not ship placeholder analyst opinions or fixture research notes.",
      "Provider-neutral analysis remains separate under the ANALYSIS module.",
    ],
  },
  {
    id: "SCREENER",
    label: "Screener",
    shortLabel: "SC",
    description: "Future arbitrary multi-factor screen builder placeholder.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "Screener is not available in this release",
    disabledMessage: "The current backend supports scanner/trending and bounded symbol search only.",
    disabledDetails: [
      "No arbitrary multi-factor screen-building API exists yet.",
      "The workspace does not display fake factor tables or prebuilt demo screens.",
    ],
  },
  {
    id: "ECON",
    label: "Econ",
    shortLabel: "EC",
    description: "Future macro calendar and economic-series placeholder.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "Economic calendar is not available in this release",
    disabledMessage: "No economic calendar, macro series, or central-bank feed is integrated with ATrade yet.",
    disabledDetails: [
      "The workspace does not invent macro events, central-bank notes, or economic time series.",
      "Provider-unavailable states remain explicit rather than hidden behind sample data.",
    ],
  },
  {
    id: "AI",
    label: "AI",
    shortLabel: "AI",
    description: "Future assistant/runtime placeholder.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "AI assistant is not available in this release",
    disabledMessage: "No committed AI assistant, model runtime, tool-use backend, or retrieval contract exists for browser use.",
    disabledDetails: [
      "Module navigation is local; no raw user navigation text is sent to an LLM.",
      "The workspace does not display demo assistant output or generated market commentary.",
    ],
  },
  {
    id: "NODE",
    label: "Node",
    shortLabel: "ND",
    description: "Future node-graph strategy workflow placeholder.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "Node graph is not available in this release",
    disabledMessage: "No node-graph workflow or visual strategy graph runtime exists in the current frontend scope.",
    disabledDetails: [
      "The workspace does not render fake graph nodes, strategy wires, or simulated execution canvases.",
      "Analysis workflows remain provider-neutral and non-order-routing.",
    ],
  },
  {
    id: "ORDERS",
    label: "Orders",
    shortLabel: "OR",
    description: "Explicitly disabled order workflow surface.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "Orders are disabled",
    disabledMessage: "Orders are disabled by the paper-only safety contract.",
    disabledDetails: [
      "This workspace does not provide order tickets, buy/sell buttons, staged submissions, previews, or confirmations.",
      "The browser remains behind ATrade.Api and no live-trading behavior is added in this reconstruction batch.",
    ],
    tone: "warning",
  },
];

export const TERMINAL_MODULES: TerminalModuleDefinition[] = [
  ...TERMINAL_ENABLED_MODULES,
  ...TERMINAL_DISABLED_MODULES,
];

const MODULE_BY_ID = new Map<TerminalModuleId, TerminalModuleDefinition>(
  TERMINAL_MODULES.map((module) => [module.id, module]),
);

export function isEnabledTerminalModuleId(value: string): value is EnabledTerminalModuleId {
  return (ENABLED_TERMINAL_MODULE_IDS as readonly string[]).includes(value);
}

export function isDisabledTerminalModuleId(value: string): value is DisabledTerminalModuleId {
  return (DISABLED_TERMINAL_MODULE_IDS as readonly string[]).includes(value);
}

export function isTerminalModuleId(value: string): value is TerminalModuleId {
  return isEnabledTerminalModuleId(value) || isDisabledTerminalModuleId(value);
}

export function getTerminalModule(moduleId: TerminalModuleId): TerminalModuleDefinition {
  const module = MODULE_BY_ID.get(moduleId);

  if (!module) {
    throw new Error(`Unknown workspace module: ${moduleId}`);
  }

  return module;
}

export function getEnabledTerminalModules(): EnabledTerminalModuleDefinition[] {
  return TERMINAL_ENABLED_MODULES;
}

export function getDisabledTerminalModules(): DisabledTerminalModuleDefinition[] {
  return TERMINAL_DISABLED_MODULES;
}

export function getTerminalDisabledModuleState(moduleId: DisabledTerminalModuleId): TerminalDisabledModuleState {
  const module = getTerminalModule(moduleId) as DisabledTerminalModuleDefinition;

  return {
    module,
    title: module.disabledTitle,
    message: module.disabledMessage,
    details: module.disabledDetails,
  };
}

export function resolveTerminalModuleAvailability(moduleId: TerminalModuleId):
  | { available: true; module: EnabledTerminalModuleDefinition }
  | { available: false; module: DisabledTerminalModuleDefinition; unavailable: TerminalDisabledModuleState } {
  const module = getTerminalModule(moduleId);

  if (module.availability === "enabled") {
    return { available: true, module: module as EnabledTerminalModuleDefinition };
  }

  const disabledModule = module as DisabledTerminalModuleDefinition;
  return {
    available: false,
    module: disabledModule,
    unavailable: getTerminalDisabledModuleState(disabledModule.id),
  };
}
