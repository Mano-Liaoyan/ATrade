import type { ChartRange, MarketDataSymbolIdentity } from "./marketData";

export const ENABLED_TERMINAL_MODULE_IDS = [
  "HOME",
  "SEARCH",
  "WATCHLIST",
  "CHART",
  "ANALYSIS",
  "STATUS",
  "HELP",
] as const;

export const DISABLED_TERMINAL_MODULE_IDS = [
  "NEWS",
  "PORTFOLIO",
  "RESEARCH",
  "SCREENER",
  "ECON",
  "AI",
  "NODE",
  "ORDERS",
] as const;

export const TERMINAL_MODULE_IDS = [
  ...ENABLED_TERMINAL_MODULE_IDS,
  ...DISABLED_TERMINAL_MODULE_IDS,
] as const;

export type EnabledTerminalModuleId = (typeof ENABLED_TERMINAL_MODULE_IDS)[number];
export type DisabledTerminalModuleId = (typeof DISABLED_TERMINAL_MODULE_IDS)[number];
export type TerminalModuleId = (typeof TERMINAL_MODULE_IDS)[number];

export type TerminalModuleAvailability = "enabled" | "disabled";
export type TerminalModulePlacement = "primary" | "future";
export type TerminalModuleTone = "default" | "positive" | "warning" | "muted";
export type TerminalModuleIconId =
  | "home"
  | "search"
  | "bookmark"
  | "chart-candlestick"
  | "flask-conical"
  | "activity"
  | "circle-question"
  | "newspaper"
  | "briefcase-business"
  | "file-search"
  | "sliders-horizontal"
  | "landmark"
  | "bot"
  | "workflow"
  | "ban";

export type TerminalModuleDefinition = {
  id: TerminalModuleId;
  label: string;
  shortLabel: string;
  icon: TerminalModuleIconId;
  description: string;
  availability: TerminalModuleAvailability;
  placement: TerminalModulePlacement;
  route?: string;
  disabledTitle?: string;
  disabledMessage?: string;
  disabledDetails?: string[];
  tone?: TerminalModuleTone;
};

export type EnabledTerminalModuleDefinition = TerminalModuleDefinition & {
  id: EnabledTerminalModuleId;
  availability: "enabled";
  placement: "primary";
};

export type DisabledTerminalModuleDefinition = TerminalModuleDefinition & {
  id: DisabledTerminalModuleId;
  availability: "disabled";
  placement: "future";
  disabledTitle: string;
  disabledMessage: string;
  disabledDetails: string[];
};

export type TerminalDisabledModuleState = {
  module: DisabledTerminalModuleDefinition;
  title: string;
  message: string;
  details: string[];
};

export type TerminalNavigationIntent = {
  moduleId: EnabledTerminalModuleId;
  route?: string;
  focusTargetId?: string;
  searchQuery?: string;
  symbol?: string;
  identity?: MarketDataSymbolIdentity | null;
  chartRange?: ChartRange;
};

