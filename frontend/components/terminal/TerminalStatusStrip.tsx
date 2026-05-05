import type { EnabledTerminalModuleId } from "@/types/terminal";
import { getTerminalModule } from "@/lib/terminalModuleRegistry";

type TerminalStatusStripProps = {
  activeModuleId: EnabledTerminalModuleId;
  marketDataStatus?: string;
  statusMessage?: string;
  symbol?: string | null;
  watchlistStatus?: string;
};

export function TerminalStatusStrip({
  activeModuleId,
  marketDataStatus = "Provider state visible",
  statusMessage,
  symbol,
  watchlistStatus = "Backend watchlist",
}: TerminalStatusStripProps) {
  const activeModule = getTerminalModule(activeModuleId);

  return (
    <footer className="terminal-status-strip" data-testid="terminal-status-strip" aria-label="Workspace status strip">
      <span>
        Module <strong>{activeModule.id}</strong> · {activeModule.description}
      </span>
      {symbol ? (
        <span>
          Symbol <strong>{symbol}</strong>
        </span>
      ) : null}
      <span>{marketDataStatus}</span>
      <span>{watchlistStatus}</span>
      <span>Paper only · Browser data through ATrade.Api · No live orders</span>
      <span aria-live="polite" role="status">
        {statusMessage ?? "Ready"}
      </span>
    </footer>
  );
}
