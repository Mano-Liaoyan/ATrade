import type { ReactNode } from 'react';

export type WorkspaceCommandBarItem = {
  label: string;
  href?: string;
  description?: string;
  tone?: 'default' | 'positive' | 'warning' | 'muted';
};

export type WorkspaceCommandBarStatus = {
  label: string;
  value: string;
  tone?: 'default' | 'positive' | 'warning' | 'muted';
};

type WorkspaceCommandBarProps = {
  eyebrow: string;
  title: string;
  subtitle: string;
  description?: string;
  titleId: string;
  commands?: WorkspaceCommandBarItem[];
  statusItems?: WorkspaceCommandBarStatus[];
  children?: ReactNode;
};

export function WorkspaceCommandBar({
  eyebrow,
  title,
  subtitle,
  description,
  titleId,
  commands = [],
  statusItems = [],
  children,
}: WorkspaceCommandBarProps) {
  return (
    <header className="terminal-command-bar" data-testid="workspace-command-bar">
      <div className="terminal-command-bar__copy">
        <p className="eyebrow terminal-command-bar__eyebrow">{eyebrow}</p>
        <h1 id={titleId}>{title}</h1>
        <p className="terminal-command-bar__subtitle">{subtitle}</p>
        {description ? <p className="terminal-command-bar__description">{description}</p> : null}
      </div>

      <div className="terminal-command-bar__controls" aria-label="Workspace command controls">
        {statusItems.length > 0 ? (
          <dl className="terminal-command-bar__status" aria-label="Workspace state summary">
            {statusItems.map((item) => (
              <div className={`terminal-status terminal-status--${item.tone ?? 'default'}`} key={`${item.label}-${item.value}`}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>
        ) : null}

        {commands.length > 0 ? (
          <div className="terminal-command-bar__actions" aria-label="Workspace commands">
            {commands.map((command) =>
              command.href ? (
                <a
                  className={`terminal-command terminal-command--${command.tone ?? 'default'}`}
                  href={command.href}
                  key={`${command.label}-${command.href}`}
                  title={command.description}
                >
                  {command.label}
                </a>
              ) : (
                <span
                  className={`terminal-command terminal-command--${command.tone ?? 'muted'}`}
                  key={command.label}
                  title={command.description}
                >
                  {command.label}
                </span>
              ),
            )}
          </div>
        ) : null}

        {children ? <div className="terminal-command-bar__custom-controls">{children}</div> : null}
      </div>
    </header>
  );
}
