import {
  TERMINAL_DISABLED_MODULE_ROUTES,
  TERMINAL_ENABLED_MODULE_ROUTES,
} from "@/lib/terminalRoutes";
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
    icon: "home",
    description: "Landing workspace with paper safety, provider state, shortcuts, and current market context.",
    availability: "enabled",
    placement: "primary",
    route: TERMINAL_ENABLED_MODULE_ROUTES.HOME,
    tone: "positive",
  },
  {
    id: "SEARCH",
    label: "Search",
    shortLabel: "SR",
    icon: "search",
    description: "Bounded stock search through ATrade.Api with exact provider and market identity badges.",
    availability: "enabled",
    placement: "primary",
    route: TERMINAL_ENABLED_MODULE_ROUTES.SEARCH,
  },
  {
    id: "WATCHLIST",
    label: "Watchlist",
    shortLabel: "WL",
    icon: "bookmark",
    description: "Backend-owned exact provider/market pins from the workspace watchlist API.",
    availability: "enabled",
    placement: "primary",
    route: TERMINAL_ENABLED_MODULE_ROUTES.WATCHLIST,
  },
  {
    id: "CHART",
    label: "Chart",
    shortLabel: "CH",
    icon: "chart-candlestick",
    description: "Chart with source, range, indicators, and fallback status.",
    availability: "enabled",
    placement: "primary",
    route: TERMINAL_ENABLED_MODULE_ROUTES.CHART,
  },
  {
    id: "ANALYSIS",
    label: "Analysis",
    shortLabel: "AN",
    icon: "flask-conical",
    description: "Analysis with engine status and unavailable labels.",
    availability: "enabled",
    placement: "primary",
    route: TERMINAL_ENABLED_MODULE_ROUTES.ANALYSIS,
  },
  {
    id: "BACKTEST",
    label: "Backtest",
    shortLabel: "BT",
    icon: "activity",
    description: "Saved single-symbol backtest runs, paper capital, live status, history, cancel, and retry through ATrade.Api.",
    availability: "enabled",
    placement: "primary",
    route: TERMINAL_ENABLED_MODULE_ROUTES.BACKTEST,
  },
  {
    id: "STATUS",
    label: "Status",
    shortLabel: "ST",
    icon: "activity",
    description: "Operational provider, cache, analysis, and fallback status.",
    availability: "enabled",
    placement: "primary",
    route: TERMINAL_ENABLED_MODULE_ROUTES.STATUS,
  },
  {
    id: "HELP",
    label: "Help",
    shortLabel: "?",
    icon: "circle-question",
    description: "Module and unavailable-state reference.",
    availability: "enabled",
    placement: "primary",
    route: TERMINAL_ENABLED_MODULE_ROUTES.HELP,
  },
];

export const TERMINAL_DISABLED_MODULES: DisabledTerminalModuleDefinition[] = [
  {
    id: "NEWS",
    label: "News",
    shortLabel: "NW",
    icon: "newspaper",
    description: "News module unavailable.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "News is not available",
    disabledMessage: "News provider not configured.",
    disabledDetails: [
      "Not available in this release.",
    ],
    route: TERMINAL_DISABLED_MODULE_ROUTES.NEWS,
  },
  {
    id: "PORTFOLIO",
    label: "Portfolio",
    shortLabel: "PF",
    icon: "briefcase-business",
    description: "Portfolio module unavailable.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "Portfolio is not available",
    disabledMessage: "Portfolio workspace not available.",
    disabledDetails: [
      "Positions and P/L storage are not configured.",
    ],
    route: TERMINAL_DISABLED_MODULE_ROUTES.PORTFOLIO,
  },
  {
    id: "RESEARCH",
    label: "Research",
    shortLabel: "RS",
    icon: "file-search",
    description: "Research module unavailable.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "Research is not available",
    disabledMessage: "Research provider not configured.",
    disabledDetails: [
      "Not available in this release.",
    ],
    route: TERMINAL_DISABLED_MODULE_ROUTES.RESEARCH,
  },
  {
    id: "SCREENER",
    label: "Screener",
    shortLabel: "SC",
    icon: "sliders-horizontal",
    description: "Screener module unavailable.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "Screener is not available",
    disabledMessage: "Screener builder not available.",
    disabledDetails: [
      "Use Search for supported stock discovery.",
    ],
    route: TERMINAL_DISABLED_MODULE_ROUTES.SCREENER,
  },
  {
    id: "ECON",
    label: "Econ",
    shortLabel: "EC",
    icon: "landmark",
    description: "Economic calendar module unavailable.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "Economic calendar is not available",
    disabledMessage: "Economic calendar provider not configured.",
    disabledDetails: [
      "Not available in this release.",
    ],
    route: TERMINAL_DISABLED_MODULE_ROUTES.ECON,
  },
  {
    id: "AI",
    label: "AI",
    shortLabel: "AI",
    icon: "bot",
    description: "AI assistant module unavailable.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "AI assistant is not available",
    disabledMessage: "AI assistant not configured.",
    disabledDetails: [
      "Not available in this release.",
    ],
    route: TERMINAL_DISABLED_MODULE_ROUTES.AI,
  },
  {
    id: "NODE",
    label: "Node",
    shortLabel: "ND",
    icon: "workflow",
    description: "Node graph module unavailable.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "Node graph is not available",
    disabledMessage: "Node graph not available.",
    disabledDetails: [
      "Not available in this release.",
    ],
    route: TERMINAL_DISABLED_MODULE_ROUTES.NODE,
  },
  {
    id: "ORDERS",
    label: "Orders",
    shortLabel: "OR",
    icon: "ban",
    description: "Orders disabled.",
    availability: "disabled",
    placement: "future",
    disabledTitle: "Orders are disabled",
    disabledMessage: "Orders disabled in this paper workspace.",
    disabledDetails: [
      "No order tickets or submit actions.",
    ],
    route: TERMINAL_DISABLED_MODULE_ROUTES.ORDERS,
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
