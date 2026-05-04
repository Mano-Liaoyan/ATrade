"use client";

import type { DisabledTerminalModuleId, EnabledTerminalModuleId } from "@/types/terminal";
import {
  getDisabledTerminalModules,
  getEnabledTerminalModules,
  getTerminalDisabledModuleState,
} from "@/lib/terminalModuleRegistry";
import { cn } from "@/lib/utils";

type TerminalModuleRailProps = {
  activeModuleId: EnabledTerminalModuleId;
  disabledModuleId?: DisabledTerminalModuleId | null;
  onDisabledModule?: (moduleId: DisabledTerminalModuleId) => void;
  onModuleSelect: (moduleId: EnabledTerminalModuleId) => void;
};

export function TerminalModuleRail({
  activeModuleId,
  disabledModuleId = null,
  onDisabledModule,
  onModuleSelect,
}: TerminalModuleRailProps) {
  const enabledModules = getEnabledTerminalModules();
  const disabledModules = getDisabledTerminalModules();

  return (
    <nav className="terminal-module-rail" data-testid="terminal-module-rail" aria-label="ATrade Terminal modules">
      <div className="terminal-module-rail__group" aria-label="Enabled modules">
        {enabledModules.map((module) => (
          <button
            className={cn(
              "terminal-module-rail__item",
              activeModuleId === module.id && !disabledModuleId && "terminal-module-rail__item--active",
            )}
            data-module-id={module.id}
            key={module.id}
            type="button"
            aria-current={activeModuleId === module.id && !disabledModuleId ? "page" : undefined}
            onClick={() => onModuleSelect(module.id)}
          >
            <span className="terminal-module-rail__short">{module.shortLabel}</span>
            <span className="terminal-module-rail__label">{module.label}</span>
          </button>
        ))}
      </div>

      <div className="terminal-module-rail__separator" aria-hidden="true" />

      <div className="terminal-module-rail__group terminal-module-rail__group--disabled" aria-label="Future disabled modules">
        {disabledModules.map((module) => {
          const unavailable = getTerminalDisabledModuleState(module.id);
          const isSelected = disabledModuleId === module.id;

          return (
            <button
              aria-disabled="true"
              className={cn("terminal-module-rail__item terminal-module-rail__item--disabled", isSelected && "terminal-module-rail__item--selected-disabled")}
              data-module-id={module.id}
              key={module.id}
              tabIndex={-1}
              title={`${unavailable.title}: ${unavailable.message}`}
              type="button"
              onClick={() => onDisabledModule?.(module.id)}
            >
              <span className="terminal-module-rail__short">{module.shortLabel}</span>
              <span className="terminal-module-rail__label">{module.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
