import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 font-[family-name:var(--font-mono)] text-xs",
  {
    variants: {
      variant: {
        default: "bg-rule text-sepia",
        info: "bg-indigo/10 text-indigo",
        success: "bg-moss/10 text-moss",
        destructive: "bg-oxide/10 text-oxide",
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
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />;
}

export { Badge, badgeVariants };
