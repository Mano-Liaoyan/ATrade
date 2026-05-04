import type { ReactNode } from 'react';

export type WorkspaceContextMetric = {
  label: string;
  value: string;
  tone?: 'default' | 'positive' | 'warning' | 'muted';
};

export type WorkspaceContextCard = {
  label: string;
  title: string;
  description: string;
  tone?: 'default' | 'positive' | 'warning' | 'muted';
};

type WorkspaceContextPanelProps = {
  eyebrow: string;
  title: string;
  description?: string;
  metrics?: WorkspaceContextMetric[];
  cards?: WorkspaceContextCard[];
  children?: ReactNode;
};

export function WorkspaceContextPanel({
  eyebrow,
  title,
  description,
  metrics = [],
  cards = [],
  children,
}: WorkspaceContextPanelProps) {
  return (
    <section className="terminal-context-panel" data-testid="workspace-context-panel" aria-labelledby="workspace-context-panel-title">
      <div className="panel-heading terminal-context-panel__heading">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2 id="workspace-context-panel-title">{title}</h2>
        </div>
      </div>

      {description ? <p className="terminal-context-panel__description">{description}</p> : null}

      {metrics.length > 0 ? (
        <dl className="terminal-context-panel__metrics" aria-label="Workspace context metrics">
          {metrics.map((metric) => (
            <div className={`terminal-context-metric terminal-context-metric--${metric.tone ?? 'default'}`} key={`${metric.label}-${metric.value}`}>
              <dt>{metric.label}</dt>
              <dd>{metric.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {cards.length > 0 ? (
        <div className="terminal-context-panel__cards" aria-label="Workspace context cards">
          {cards.map((card) => (
            <article className={`terminal-context-card terminal-context-card--${card.tone ?? 'default'}`} key={`${card.label}-${card.title}`}>
              <span>{card.label}</span>
              <strong>{card.title}</strong>
              <p>{card.description}</p>
            </article>
          ))}
        </div>
      ) : null}

      {children ? <div className="terminal-context-panel__content">{children}</div> : null}
    </section>
  );
}
