import * as React from "react";

import { cn } from "@/lib/utils";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

const Input = React.forwardRef<HTMLInputElement, InputProps>(({ className, type, ...props }, ref) => (
  <input
    className={cn(
      "flex h-9 w-full rounded-sm border border-terminal-border bg-terminal-surface-inset px-3 py-2 font-mono text-sm text-terminal-text shadow-inner outline-none placeholder:text-terminal-subtle focus:border-terminal-amber focus:ring-2 focus:ring-terminal-amber/30 disabled:cursor-not-allowed disabled:opacity-50",
      className,
    )}
    ref={ref}
    type={type}
    {...props}
  />
));
Input.displayName = "Input";

export { Input };
