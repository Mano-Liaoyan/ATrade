import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const terminalSurfaceVariants = cva("border text-terminal-text", {
  variants: {
    tone: {
      canvas: "border-terminal-border/50 bg-terminal-canvas",
      surface: "border-terminal-border bg-terminal-surface shadow-terminal-panel",
      elevated: "border-terminal-border-strong/70 bg-terminal-surface-elevated shadow-terminal-panel",
      inset: "border-terminal-border/75 bg-terminal-surface-inset",
    },
    padding: {
      none: "p-0",
      compact: "p-3",
      default: "p-4",
      roomy: "p-5",
    },
    radius: {
      none: "rounded-none",
      sm: "rounded-sm",
      md: "rounded-md",
    },
  },
  defaultVariants: {
    tone: "surface",
    padding: "default",
    radius: "sm",
  },
});

export interface TerminalSurfaceProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof terminalSurfaceVariants> {}

function TerminalSurface({ className, tone, padding, radius, ...props }: TerminalSurfaceProps) {
  return (
    <div
      className={cn(terminalSurfaceVariants({ tone, padding, radius }), className)}
      data-terminal-surface
      {...props}
    />
  );
}

export { TerminalSurface, terminalSurfaceVariants };
