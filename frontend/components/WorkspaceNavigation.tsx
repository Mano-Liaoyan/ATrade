export type WorkspaceNavigationItem = {
  id: string;
  label: string;
  href: string;
  description?: string;
  badge?: string;
};

type WorkspaceNavigationProps = {
  label: string;
  items: WorkspaceNavigationItem[];
};

export function WorkspaceNavigation({ label, items }: WorkspaceNavigationProps) {
  return (
    <nav className="terminal-navigation" aria-label={label} data-testid="workspace-navigation">
      <p className="terminal-navigation__label">Navigate</p>
      <ul>
        {items.map((item) => (
          <li key={item.id}>
            <a className="terminal-navigation__link" href={item.href}>
              <span>{item.label}</span>
              {item.badge ? <strong>{item.badge}</strong> : null}
              {item.description ? <small>{item.description}</small> : null}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
