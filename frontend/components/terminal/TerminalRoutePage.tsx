import { createTerminalRouteAppState, type TerminalRouteSearchParams } from "@/lib/terminalRoutes";
import type { DisabledTerminalModuleId, EnabledTerminalModuleId } from "@/types/terminal";
import { ATradeTerminalApp } from "./ATradeTerminalApp";

type TerminalRoutePageProps = {
  disabledModuleId?: DisabledTerminalModuleId | null;
  moduleId?: EnabledTerminalModuleId;
  searchParams?: TerminalRouteSearchParams;
  symbol?: string | null;
};

export function TerminalRoutePage({
  disabledModuleId = null,
  moduleId = "HOME",
  searchParams = {},
  symbol = null,
}: TerminalRoutePageProps) {
  const routeState = createTerminalRouteAppState({
    disabledModuleId,
    moduleId,
    searchParams,
    symbol,
  });

  return <ATradeTerminalApp {...routeState} />;
}
