"use client";

import type { ReactNode } from "react";

type AlertProps = {
  variant: "success" | "error" | "warning" | "info";
  children: ReactNode;
  dismissible?: boolean;
  onDismiss?: () => void;
};

const variantClasses: Record<AlertProps["variant"], string> = {
  error: "bg-error-subtle border border-error/20 text-error",
  success: "bg-success-subtle border border-success/20 text-success",
  warning: "bg-warning-subtle border border-warning/20 text-warning",
  info: "bg-info-subtle border border-info/20 text-info",
};

export function Alert({ variant, children, dismissible, onDismiss }: AlertProps) {
  return (
    <div
      className={`flex items-start gap-3 rounded-md p-3.5 ${variantClasses[variant]}`}
      role="alert"
    >
      <div className="flex-1 text-sm">{children}</div>
      {dismissible && onDismiss && (
        <button
          className="ml-auto text-current opacity-60 hover:opacity-100 transition-opacity flex-shrink-0 text-lg leading-none"
          onClick={onDismiss}
          aria-label="Dismiss"
          type="button"
        >
          &times;
        </button>
      )}
    </div>
  );
}
