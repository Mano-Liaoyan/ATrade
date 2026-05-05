"use client";

import { useId, useState } from "react";

import type { DisabledTerminalModuleId, EnabledTerminalModuleId, TerminalModuleIconId } from "@/types/terminal";
import {
  getDisabledTerminalModules,
  getEnabledTerminalModules,
  getTerminalDisabledModuleState,
} from "@/lib/terminalModuleRegistry";
import { cn } from "@/lib/utils";
import {
  Activity,
  Ban,
  Bookmark,
  Bot,
  BriefcaseBusiness,
  ChartCandlestick,
  CircleQuestionMark,
  FileSearch,
  FlaskConical,
  Home,
  Landmark,
  Newspaper,
  PanelLeftClose,
  PanelLeftOpen,
  Search,
  SlidersHorizontal,
  Workflow,
  type LucideIcon,
} from "lucide-react";

const TERMINAL_MODULE_ICON_COMPONENTS: Record<TerminalModuleIconId, LucideIcon> = {
  "activity": Activity,
  "ban": Ban,
  "bookmark": Bookmark,
  "bot": Bot,
  "briefcase-business": BriefcaseBusiness,
  "chart-candlestick": ChartCandlestick,
  "circle-question": CircleQuestionMark,
  "file-search": FileSearch,
  "flask-conical": FlaskConical,
  "home": Home,
  "landmark": Landmark,
  "newspaper": Newspaper,
  "search": Search,
  "sliders-horizontal": SlidersHorizontal,
  "workflow": Workflow,
};

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
  const moduleGroupsId = useId();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const ToggleIcon = isCollapsed ? PanelLeftOpen : PanelLeftClose;

  return (
    <nav
      className={cn("terminal-module-rail", isCollapsed && "terminal-module-rail--collapsed")}
      data-collapsed={isCollapsed ? "true" : "false"}
      data-rail-state={isCollapsed ? "collapsed" : "expanded"}
      data-testid="terminal-module-rail"
      aria-label="Workspace modules"
    >
      <button
        className="terminal-module-rail__toggle"
        type="button"
        aria-controls={moduleGroupsId}
        aria-expanded={!isCollapsed}
        aria-label={isCollapsed ? "Expand module rail" : "Collapse module rail"}
        title={isCollapsed ? "Expand module rail" : "Collapse module rail"}
        onClick={() => setIsCollapsed((current) => !current)}
      >
        <ToggleIcon aria-hidden="true" focusable="false" size={18} strokeWidth={2.2} />
        <span className="terminal-module-rail__toggle-label">{isCollapsed ? "Expand" : "Collapse"}</span>
      </button>

      <div className="terminal-module-rail__navigation" id={moduleGroupsId}>
        <div className="terminal-module-rail__group" aria-label="Enabled modules">
        {enabledModules.map((module) => {
          const Icon = TERMINAL_MODULE_ICON_COMPONENTS[module.icon];

          return (
            <button
              className={cn(
                "terminal-module-rail__item",
                activeModuleId === module.id && !disabledModuleId && "terminal-module-rail__item--active",
              )}
              data-module-icon={module.icon}
              data-module-id={module.id}
              data-module-short-label={module.shortLabel}
              key={module.id}
              title={isCollapsed ? module.label : undefined}
              type="button"
              aria-current={activeModuleId === module.id && !disabledModuleId ? "page" : undefined}
              onClick={() => onModuleSelect(module.id)}
            >
              <span className="terminal-module-rail__short terminal-module-rail__icon" aria-hidden="true">
                <Icon aria-hidden="true" focusable="false" size={18} strokeWidth={2.2} />
              </span>
              <span className="terminal-module-rail__label">{module.label}</span>
            </button>
          );
        })}
      </div>

      <div className="terminal-module-rail__separator" aria-hidden="true" />

      <div className="terminal-module-rail__group terminal-module-rail__group--disabled" aria-label="Future disabled modules">
        {disabledModules.map((module) => {
          const unavailable = getTerminalDisabledModuleState(module.id);
          const isSelected = disabledModuleId === module.id;
          const Icon = TERMINAL_MODULE_ICON_COMPONENTS[module.icon];

          return (
            <button
              aria-disabled="true"
              className={cn("terminal-module-rail__item terminal-module-rail__item--disabled", isSelected && "terminal-module-rail__item--selected-disabled")}
              data-module-icon={module.icon}
              data-module-id={module.id}
              data-module-short-label={module.shortLabel}
              key={module.id}
              tabIndex={-1}
              title={`${unavailable.title}: ${unavailable.message}`}
              type="button"
              onClick={() => onDisabledModule?.(module.id)}
            >
              <span className="terminal-module-rail__short terminal-module-rail__icon" aria-hidden="true">
                <Icon aria-hidden="true" focusable="false" size={18} strokeWidth={2.2} />
              </span>
              <span className="terminal-module-rail__label">{module.label}</span>
            </button>
          );
        })}
      </div>
      </div>
    </nav>
  );
}
