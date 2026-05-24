import type { ReactNode } from "react";

export type BadgeVariant = "default" | "success" | "error" | "warning" | "info" | "accent";
export type BadgeSize = "sm" | "md";

type BadgeProps = {
  variant?: BadgeVariant;
  size?: BadgeSize;
  children: ReactNode;
  className?: string;
};

const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-surface-sunken text-text-secondary border-border-light",
  success: "bg-success-subtle text-success border-success-subtle",
  error: "bg-error-subtle text-error border-error-subtle",
  warning: "bg-warning-subtle text-warning border-warning-subtle",
  info: "bg-info-subtle text-info border-info-subtle",
  accent: "bg-accent-subtle text-accent border-accent-subtle",
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-xs",
};

export function Badge({
  variant = "default",
  size = "sm",
  children,
  className = "",
}: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 font-semibold rounded-full border",
        variantClasses[variant],
        sizeClasses[size],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </span>
  );
}
