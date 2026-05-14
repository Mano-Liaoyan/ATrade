import type { ReactNode } from "react";

import type { EnabledTerminalModuleId } from "@/types/terminal";
import { TerminalWorkspaceStatusIndicator } from "./TerminalWorkspaceStatusIndicator";

type TerminalWorkspaceLayoutProps = {
  activeModuleId: EnabledTerminalModuleId;
  children: ReactNode;
};

export function TerminalWorkspaceLayout({ activeModuleId, children }: TerminalWorkspaceLayoutProps) {
  return (
    <section className="terminal-workspace-layout" data-active-module={activeModuleId} data-testid="terminal-workspace-layout">
      <header className="terminal-workspace-layout__status" aria-label="Global workspace status">
        <TerminalWorkspaceStatusIndicator />
      </header>
      <div
        className="terminal-workspace-layout__primary terminal-scroll-owned terminal-workspace-scroll-owned"
        data-layout-region="primary"
        data-scroll-owner="primary-workspace"
      >
        {children}
      </div>
    </section>
  );
}
