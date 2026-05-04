import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";
import { TerminalSectionHeader } from "./TerminalSectionHeader";

const terminalPanelVariants = cva(
  "grid gap-3 border text-terminal-text shadow-terminal-panel",
  {
    variants: {
      density: {
        compact: "p-3",
        default: "p-4",
        roomy: "p-5",
      },
      tone: {
        surface: "border-terminal-border bg-terminal-surface",
        elevated: "border-terminal-border-strong/70 bg-terminal-surface-elevated",
        inset: "border-terminal-border/75 bg-terminal-surface-inset",
      },
    },
    defaultVariants: {
      density: "default",
      tone: "surface",
    },
  },
);

export interface TerminalPanelProps
  extends Omit<React.HTMLAttributes<HTMLElement>, "title">,
    VariantProps<typeof terminalPanelVariants> {
  actions?: React.ReactNode;
  bodyClassName?: string;
  description?: React.ReactNode;
  eyebrow?: React.ReactNode;
  title?: React.ReactNode;
}

function TerminalPanel({
  actions,
  bodyClassName,
  children,
  className,
  density,
  description,
  eyebrow,
  title,
  tone,
  ...props
}: TerminalPanelProps) {
  return (
    <section
      className={cn("rounded-sm", terminalPanelVariants({ density, tone }), className)}
      data-terminal-panel
      {...props}
    >
      {title ? (
        <TerminalSectionHeader actions={actions} description={description} eyebrow={eyebrow} title={title} />
      ) : null}
      <div className={cn("min-w-0", bodyClassName)}>{children}</div>
    </section>
  );
}

export { TerminalPanel, terminalPanelVariants };
