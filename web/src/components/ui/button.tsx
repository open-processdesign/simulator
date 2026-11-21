import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// shadcn/ui Button, themed with OPD tokens (docs/DESIGN_SYSTEM.md):
// primary = accent, secondary = outline, ghost.
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-accent text-on-accent hover:bg-accent-hover",
        secondary: "border border-border-strong bg-surface text-text hover:bg-surface-muted",
        ghost: "text-muted hover:bg-surface-muted hover:text-text",
      },
      size: {
        sm: "h-7 px-2.5 text-xs",
        md: "h-8 px-3 text-sm",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : "button";
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

export { buttonVariants };
