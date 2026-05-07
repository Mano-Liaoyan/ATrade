import type { ReactNode } from "react";

import type { EnabledTerminalModuleId } from "@/types/terminal";

type TerminalWorkspaceLayoutProps = {
  activeModuleId: EnabledTerminalModuleId;
  children: ReactNode;
};

export function TerminalWorkspaceLayout({ activeModuleId, children }: TerminalWorkspaceLayoutProps) {
  return (
    <section className="terminal-workspace-layout" data-active-module={activeModuleId} data-testid="terminal-workspace-layout">
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
