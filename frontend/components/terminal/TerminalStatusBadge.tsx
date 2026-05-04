import * as React from "react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type TerminalStatusTone = "neutral" | "info" | "success" | "warning" | "danger";

const statusVariantByTone: Record<TerminalStatusTone, BadgeProps["variant"]> = {
  danger: "danger",
  info: "info",
  neutral: "neutral",
  success: "success",
  warning: "warning",
};

export interface TerminalStatusBadgeProps extends Omit<BadgeProps, "variant"> {
  pulse?: boolean;
  tone?: TerminalStatusTone;
}

function TerminalStatusBadge({ className, children, pulse = false, tone = "neutral", ...props }: TerminalStatusBadgeProps) {
  return (
    <Badge
      className={cn("gap-1.5", className)}
      data-terminal-status-badge={tone}
      variant={statusVariantByTone[tone]}
      {...props}
    >
      <span
        aria-hidden="true"
        className={cn(
          "size-1.5 rounded-full",
          tone === "neutral" && "bg-status-neutral",
          tone === "info" && "bg-status-info",
          tone === "success" && "bg-status-success",
          tone === "warning" && "bg-status-warning",
          tone === "danger" && "bg-status-danger",
          pulse && "animate-pulse",
        )}
      />
      {children}
    </Badge>
  );
}

export { TerminalStatusBadge };
