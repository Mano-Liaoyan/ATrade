import * as React from "react";

import { cn } from "@/lib/utils";

export interface TerminalSectionHeaderProps extends Omit<React.HTMLAttributes<HTMLElement>, "title"> {
  actions?: React.ReactNode;
  description?: React.ReactNode;
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
}

function TerminalSectionHeader({
  actions,
  className,
  description,
  eyebrow,
  title,
  ...props
}: TerminalSectionHeaderProps) {
  return (
    <header
      className={cn(
        "flex flex-col gap-2 border-b border-terminal-border/70 pb-2 terminal:flex-row terminal:items-start terminal:justify-between",
        className,
      )}
      data-terminal-section-header
      {...props}
    >
      <div className="min-w-0 space-y-1">
        {eyebrow ? (
          <p className="m-0 font-mono text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-terminal-amber">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="m-0 truncate font-mono text-sm font-semibold uppercase tracking-[0.14em] text-terminal-text">
          {title}
        </h2>
        {description ? <p className="m-0 max-w-3xl text-[0.82rem] leading-5 text-terminal-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

export { TerminalSectionHeader };
