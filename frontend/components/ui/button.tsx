import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-sm border text-xs font-semibold uppercase tracking-[0.12em] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-terminal-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-canvas disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "border-terminal-cyan/45 bg-terminal-cyan/14 text-terminal-cyan shadow-terminal-glow hover:bg-terminal-cyan/22",
        terminal:
          "border-terminal-border bg-terminal-surface-elevated text-terminal-text hover:border-terminal-cyan/55 hover:bg-terminal-cyan/10",
        amber:
          "border-terminal-amber/45 bg-terminal-amber/14 text-terminal-amber hover:bg-terminal-amber/22",
        destructive:
          "border-terminal-red/45 bg-terminal-red/14 text-terminal-red hover:bg-terminal-red/22",
        outline:
          "border-terminal-border bg-transparent text-terminal-text hover:border-terminal-cyan/50 hover:bg-terminal-surface-elevated",
        ghost:
          "border-transparent bg-transparent text-terminal-muted hover:bg-terminal-surface-elevated hover:text-terminal-text",
      },
      size: {
        default: "h-9 px-3 py-2",
        sm: "h-8 px-2.5",
        xs: "h-7 px-2 text-[0.68rem]",
        lg: "h-10 px-4",
        icon: "size-9 p-0",
      },
    },
    defaultVariants: {
      variant: "terminal",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";

    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
