import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-sm border px-2 py-0.5 font-mono text-[0.68rem] font-semibold uppercase tracking-[0.12em]",
  {
    variants: {
      variant: {
        default: "border-terminal-border bg-terminal-surface-elevated text-terminal-text",
        neutral: "border-status-neutral/35 bg-status-neutral/10 text-status-neutral",
        info: "border-status-info/45 bg-status-info/12 text-status-info",
        success: "border-status-success/45 bg-status-success/12 text-status-success",
        warning: "border-status-warning/45 bg-status-warning/12 text-status-warning",
        danger: "border-status-danger/45 bg-status-danger/12 text-status-danger",
        outline: "border-terminal-border bg-transparent text-terminal-muted",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, className }))} data-slot="badge" {...props} />;
}

export { Badge, badgeVariants };
