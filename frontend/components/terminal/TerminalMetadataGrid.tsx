import type { ReactNode } from 'react';

export type TerminalMetadataGridColumnCount = 1 | 2 | 3 | 4 | 'auto';

export type TerminalMetadataItem = {
  code?: boolean;
  detail?: ReactNode;
  detailTestId?: string;
  label: ReactNode;
  testId?: string;
  value: ReactNode;
};

export type TerminalMetadataGridProps = {
  ariaLabel: string;
  className?: string;
  columns?: TerminalMetadataGridColumnCount;
  items: TerminalMetadataItem[];
  testId?: string;
};

export function TerminalMetadataGrid({
  ariaLabel,
  className,
  columns = 'auto',
  items,
  testId,
}: TerminalMetadataGridProps) {
  return (
    <dl
      aria-label={ariaLabel}
      className={joinClassNames('terminal-metadata-grid', `terminal-metadata-grid--${columns}`, className)}
      data-testid={testId}
    >
      {items.map((item, index) => (
        <div className="terminal-metadata-grid__item" data-testid={item.testId} key={getItemKey(item.label, index)}>
          <dt className="terminal-metadata-grid__label">{item.label}</dt>
          <dd className="terminal-metadata-grid__value">
            {item.code ? <code>{item.value}</code> : item.value}
          </dd>
          {item.detail ? (
            <small className="terminal-metadata-grid__detail" data-testid={item.detailTestId}>{item.detail}</small>
          ) : null}
        </div>
      ))}
    </dl>
  );
}

function getItemKey(label: ReactNode, index: number): string {
  return typeof label === 'string' ? `${label}-${index}` : String(index);
}

function joinClassNames(...classNames: Array<string | false | null | undefined>): string {
  return classNames.filter(Boolean).join(' ');
}
