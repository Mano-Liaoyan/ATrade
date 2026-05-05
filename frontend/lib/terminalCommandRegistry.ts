import type {
  DisabledTerminalModuleId,
  EnabledTerminalModuleId,
  TerminalCommandParseFailure,
  TerminalCommandParseResult,
  TerminalCommandParseSuccess,
  TerminalNavigationIntent,
} from "@/types/terminal";
import {
  getTerminalDisabledModuleState,
  isDisabledTerminalModuleId,
} from "./terminalModuleRegistry";

export type TerminalCommandDefinition = {
  command: string;
  label: string;
  description: string;
  moduleId: EnabledTerminalModuleId;
  requiresArgument: boolean;
};

export const TERMINAL_COMMAND_HELP =
  "Supported commands: HOME, SEARCH <query>, CHART <symbol>, WATCH, WATCHLIST, ANALYSIS <symbol>, STATUS, HELP.";

export const TERMINAL_COMMAND_DEFINITIONS: TerminalCommandDefinition[] = [
  {
    command: "HOME",
    label: "HOME",
    description: "Open the ATrade Terminal home workspace.",
    moduleId: "HOME",
    requiresArgument: false,
  },
  {
    command: "SEARCH",
    label: "SEARCH <query>",
    description: "Open symbol search and seed the bounded stock query when provided.",
    moduleId: "SEARCH",
    requiresArgument: false,
  },
  {
    command: "CHART",
    label: "CHART <symbol>",
    description: "Open a chart workspace for the supplied symbol.",
    moduleId: "CHART",
    requiresArgument: true,
  },
  {
    command: "WATCH",
    label: "WATCH",
    description: "Open the backend-owned watchlist module.",
    moduleId: "WATCHLIST",
    requiresArgument: false,
  },
  {
    command: "WATCHLIST",
    label: "WATCHLIST",
    description: "Alias for WATCH; open the backend-owned watchlist module.",
    moduleId: "WATCHLIST",
    requiresArgument: false,
  },
  {
    command: "ANALYSIS",
    label: "ANALYSIS <symbol>",
    description: "Open provider-neutral analysis for a symbol or the analysis help state.",
    moduleId: "ANALYSIS",
    requiresArgument: false,
  },
  {
    command: "STATUS",
    label: "STATUS",
    description: "Open operational API, provider, cache, and paper-mode status.",
    moduleId: "STATUS",
    requiresArgument: false,
  },
  {
    command: "HELP",
    label: "HELP",
    description: "Open deterministic command help and safety notes.",
    moduleId: "HELP",
    requiresArgument: false,
  },
];

const COMMAND_BY_KEYWORD = new Map(
  TERMINAL_COMMAND_DEFINITIONS.map((definition) => [definition.command, definition]),
);

const COMMANDS_THAT_REJECT_ARGUMENTS = new Set(["HOME", "WATCH", "WATCHLIST", "STATUS", "HELP"]);

export function getTerminalCommandDefinitions(): TerminalCommandDefinition[] {
  return TERMINAL_COMMAND_DEFINITIONS;
}

export function parseTerminalCommand(rawInput: string): TerminalCommandParseResult {
  const input = rawInput;
  const compactInput = rawInput.trim().replace(/\s+/g, " ");

  if (!compactInput) {
    return invalidCommand(input, "", null, "Enter an ATrade Terminal command. HELP lists the deterministic command grammar.");
  }

  const [firstToken = "", ...restTokens] = compactInput.split(" ");
  const command = firstToken.toUpperCase();
  const argument = restTokens.join(" ").trim();
  const normalizedInput = argument ? `${command} ${argument}` : command;

  if (isDisabledTerminalModuleId(command)) {
    return disabledModuleCommand(input, normalizedInput, command);
  }

  if (!COMMAND_BY_KEYWORD.has(command)) {
    return invalidCommand(input, normalizedInput, command, `Unknown command "${command}". Type HELP for supported commands.`);
  }

  if (COMMANDS_THAT_REJECT_ARGUMENTS.has(command) && argument) {
    return invalidCommand(input, normalizedInput, command, `${command} does not accept arguments. ${TERMINAL_COMMAND_HELP}`);
  }

  switch (command) {
    case "HOME":
      return openModuleCommand(input, normalizedInput, command, {
        moduleId: "HOME",
        route: "/",
        focusTargetId: "terminal-module-home",
      });
    case "SEARCH":
      return openModuleCommand(input, normalizedInput, command, {
        moduleId: "SEARCH",
        route: "/",
        focusTargetId: "terminal-search",
        searchQuery: argument || undefined,
      });
    case "CHART": {
      const symbol = normalizeSymbolArgument(argument);
      if (!symbol) {
        return invalidCommand(input, normalizedInput, command, "CHART requires a symbol, for example CHART AAPL.");
      }

      return openModuleCommand(input, `CHART ${symbol}`, command, {
        moduleId: "CHART",
        route: `/symbols/${encodeURIComponent(symbol)}`,
        focusTargetId: "terminal-chart",
        symbol,
        chartRange: "1D",
      });
    }
    case "WATCH":
    case "WATCHLIST":
      return openModuleCommand(input, normalizedInput, command, {
        moduleId: "WATCHLIST",
        route: "/",
        focusTargetId: "terminal-watchlist",
      });
    case "ANALYSIS": {
      const symbol = normalizeSymbolArgument(argument);
      return openModuleCommand(input, symbol ? `ANALYSIS ${symbol}` : "ANALYSIS", command, {
        moduleId: "ANALYSIS",
        route: symbol ? `/symbols/${encodeURIComponent(symbol)}?module=ANALYSIS&range=1D` : "/",
        focusTargetId: "terminal-analysis",
        symbol: symbol || undefined,
        chartRange: symbol ? "1D" : undefined,
      });
    }
    case "STATUS":
      return openModuleCommand(input, normalizedInput, command, {
        moduleId: "STATUS",
        route: "/",
        focusTargetId: "terminal-status",
      });
    case "HELP":
      return openModuleCommand(input, normalizedInput, command, {
        moduleId: "HELP",
        route: "/",
        focusTargetId: "terminal-help",
      });
    default:
      return invalidCommand(input, normalizedInput, command, `Unknown command "${command}". Type HELP for supported commands.`);
  }
}

function openModuleCommand(
  input: string,
  normalizedInput: string,
  command: string,
  intent: TerminalNavigationIntent,
): TerminalCommandParseSuccess {
  return {
    ok: true,
    input,
    normalizedInput,
    command,
    action: {
      kind: "open-module",
      intent,
    },
    feedback: buildFeedback(intent),
  };
}

function disabledModuleCommand(
  input: string,
  normalizedInput: string,
  moduleId: DisabledTerminalModuleId,
): TerminalCommandParseSuccess {
  const unavailable = getTerminalDisabledModuleState(moduleId);

  return {
    ok: true,
    input,
    normalizedInput,
    command: moduleId,
    action: {
      kind: "open-disabled-module",
      moduleId,
      unavailable,
    },
    feedback: `${unavailable.title}: ${unavailable.message}`,
  };
}

function invalidCommand(
  input: string,
  normalizedInput: string,
  command: string | null,
  message: string,
): TerminalCommandParseFailure {
  return {
    ok: false,
    input,
    normalizedInput,
    command,
    message,
    help: TERMINAL_COMMAND_HELP,
  };
}

function normalizeSymbolArgument(argument: string): string | null {
  const symbol = argument.trim().replace(/^\$+/, "").toUpperCase();

  if (!symbol || !/^[A-Z0-9][A-Z0-9._-]{0,23}$/.test(symbol)) {
    return null;
  }

  return symbol;
}

function buildFeedback(intent: TerminalNavigationIntent): string {
  switch (intent.moduleId) {
    case "HOME":
      return "Opening HOME.";
    case "SEARCH":
      return intent.searchQuery ? `Opening SEARCH for ${intent.searchQuery}.` : "Opening SEARCH.";
    case "WATCHLIST":
      return "Opening WATCHLIST.";
    case "CHART":
      return intent.symbol ? `Opening CHART for ${intent.symbol}.` : "Opening CHART.";
    case "ANALYSIS":
      return intent.symbol ? `Opening ANALYSIS for ${intent.symbol}.` : "Opening ANALYSIS.";
    case "STATUS":
      return "Opening STATUS.";
    case "HELP":
      return "Opening HELP.";
    default:
      return "Opening module.";
  }
}
