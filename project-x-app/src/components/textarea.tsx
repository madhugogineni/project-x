"use client";

import type { TextareaHTMLAttributes } from "react";

type TextareaProps = Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "onChange"> & {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  helperText?: string;
};

export function Textarea({
  label,
  name,
  value,
  onChange,
  error,
  helperText,
  required,
  disabled,
  placeholder,
  rows = 3,
  ...props
}: TextareaProps) {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      <div className="flex items-center gap-1.5">
        <label className="text-sm font-semibold text-text-secondary" htmlFor={name}>
          {label}
          {required && <span className="text-error ml-0.5">*</span>}
        </label>
        {helperText && !error && (
          <span className="relative inline-flex items-center group">
            <span
              tabIndex={0}
              role="img"
              aria-label={helperText}
              className="inline-flex h-4 w-4 items-center justify-center rounded-full text-text-tertiary hover:text-accent focus:text-accent focus:outline-none focus:ring-2 focus:ring-accent-subtle"
            >
              <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
            </span>
            <span
              role="tooltip"
              className="pointer-events-none absolute left-1/2 top-full z-[400] mt-2 hidden w-max max-w-[220px] -translate-x-1/2 rounded-md border border-border-light bg-surface-strong px-2.5 py-1.5 text-xs font-medium text-text-secondary shadow-md group-hover:block group-focus-within:block"
            >
              {helperText}
            </span>
          </span>
        )}
      </div>
      <textarea
        id={name}
        name={name}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        required={required}
        rows={rows}
        className={[
          "w-full px-3.5 py-2.5 border-[1.5px] rounded-md bg-surface-base text-text-primary text-sm placeholder:text-text-tertiary transition-all duration-[180ms] resize-y leading-relaxed",
          "focus:outline-none focus:bg-surface-strong focus:shadow-[0_0_0_3px_var(--accent-primary-subtle)]",
          "hover:border-border-strong",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          error
            ? "border-error focus:border-error focus:shadow-[0_0_0_3px_var(--error-subtle)]"
            : "border-border-default focus:border-accent",
        ]
          .filter(Boolean)
          .join(" ")}
        aria-invalid={!!error}
        aria-describedby={error ? `${name}-error` : undefined}
        {...props}
      />
      {error && (
        <p id={`${name}-error`} className="text-xs text-error mt-1" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
