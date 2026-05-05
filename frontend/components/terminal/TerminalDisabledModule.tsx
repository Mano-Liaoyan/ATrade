import type { DisabledTerminalModuleDefinition, DisabledTerminalModuleId } from "@/types/terminal";
import { cn } from "@/lib/utils";
import { getTerminalDisabledModuleState } from "@/lib/terminalModuleRegistry";
import { TerminalPanel } from "./TerminalPanel";
import { TerminalStatusBadge } from "./TerminalStatusBadge";

type TerminalDisabledModuleProps = {
  moduleId?: DisabledTerminalModuleId;
  module?: DisabledTerminalModuleDefinition;
  className?: string;
};

export function TerminalDisabledModule({ className, module, moduleId }: TerminalDisabledModuleProps) {
  const unavailable = module
    ? {
        module,
        title: module.disabledTitle,
        message: module.disabledMessage,
        details: module.disabledDetails,
        actionLabel: "HELP" as const,
      }
    : moduleId
      ? getTerminalDisabledModuleState(moduleId)
      : null;

  if (!unavailable) {
    return null;
  }

  return (
    <TerminalPanel
      className={cn("terminal-disabled-module", className)}
      data-testid={`terminal-disabled-module-${unavailable.module.id.toLowerCase()}`}
      description={unavailable.message}
      eyebrow="Visible-disabled module"
      title={`${unavailable.module.label} unavailable`}
      tone="inset"
      actions={<TerminalStatusBadge tone="warning">Not available</TerminalStatusBadge>}
    >
      <div className="terminal-disabled-module__body" aria-live="polite">
        <p className="terminal-disabled-module__title">{unavailable.title}</p>
        <p>{unavailable.message}</p>
        <ul aria-label={`${unavailable.module.label} unavailable details`}>
          {unavailable.details.map((detail) => (
            <li key={detail}>{detail}</li>
          ))}
        </ul>
        <p className="terminal-disabled-module__footer">
          This surface is intentionally empty: no fake data, no demo provider responses, and no order-entry controls are rendered here. Type HELP for enabled commands.
        </p>
      </div>
    </TerminalPanel>
  );
}
