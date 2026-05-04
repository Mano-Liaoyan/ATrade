import type { ReactNode } from 'react';
import { WorkspaceCommandBar, type WorkspaceCommandBarItem, type WorkspaceCommandBarStatus } from './WorkspaceCommandBar';
import { WorkspaceContextPanel, type WorkspaceContextCard, type WorkspaceContextMetric } from './WorkspaceContextPanel';
import { WorkspaceNavigation, type WorkspaceNavigationItem } from './WorkspaceNavigation';

const DEFAULT_WORKSPACE_SAFETY_DISCLOSURES = [
  'Paper-only workspace: this shell exposes charting, search, watchlist, provider status, and analysis entry points only.',
  'Provider state and exact instrument identity stay visible; no fake market data or local symbol catalog is introduced here.',
  'No live broker orders are available from this shell.',
];

type WorkspaceShellContext = {
  eyebrow: string;
  title: string;
  description?: string;
  metrics?: WorkspaceContextMetric[];
  cards?: WorkspaceContextCard[];
  children?: ReactNode;
};

type TerminalWorkspaceShellProps = {
  workspaceId: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  description?: string;
  navigationLabel: string;
  navigationItems: WorkspaceNavigationItem[];
  commandItems?: WorkspaceCommandBarItem[];
  statusItems?: WorkspaceCommandBarStatus[];
  commandControls?: ReactNode;
  safetyDisclosures?: string[];
  context: WorkspaceShellContext;
  children: ReactNode;
};

export function TerminalWorkspaceShell({
  workspaceId,
  eyebrow,
  title,
  subtitle,
  description,
  navigationLabel,
  navigationItems,
  commandItems = [],
  statusItems = [],
  commandControls,
  safetyDisclosures = DEFAULT_WORKSPACE_SAFETY_DISCLOSURES,
  context,
  children,
}: TerminalWorkspaceShellProps) {
  const titleId = `${workspaceId}-title`;

  return (
    <section className="terminal-workspace-shell" data-testid="terminal-workspace-shell" aria-labelledby={titleId}>
      <WorkspaceCommandBar
        eyebrow={eyebrow}
        title={title}
        subtitle={subtitle}
        description={description}
        titleId={titleId}
        commands={commandItems}
        statusItems={statusItems}
      >
        {commandControls}
      </WorkspaceCommandBar>

      {safetyDisclosures.length > 0 ? (
        <div className="terminal-safety-strip" data-testid="terminal-safety-strip" aria-label="Paper trading safety and provider identity notes">
          {safetyDisclosures.map((disclosure) => (
            <span key={disclosure}>{disclosure}</span>
          ))}
        </div>
      ) : null}

      <div className="terminal-workspace-shell__grid">
        <WorkspaceNavigation label={navigationLabel} items={navigationItems} />

        <main className="terminal-workspace-shell__main" data-testid="terminal-workspace-main" aria-label={`${title} primary workspace`}>
          {children}
        </main>

        <aside className="terminal-workspace-shell__context" data-testid="terminal-workspace-context" aria-label={`${title} context`}>
          <WorkspaceContextPanel
            eyebrow={context.eyebrow}
            title={context.title}
            description={context.description}
            metrics={context.metrics}
            cards={context.cards}
          >
            {context.children}
          </WorkspaceContextPanel>
        </aside>
      </div>
    </section>
  );
}
