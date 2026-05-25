"use client";

import React from "react";
import ReactSelect, { type StylesConfig, type GroupBase } from "react-select";

type SelectOption = {
  value: string;
  label: string;
};

type SelectProps = {
  label: string;
  name: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  error?: string;
  disabled?: boolean;
  required?: boolean;
  searchable?: boolean;
  formatOptionLabel?: (option: SelectOption) => React.ReactNode;
};

// Build react-select styles from CSS variables at render time so they
// automatically pick up the active light / dark theme.
function buildStyles(hasError: boolean): StylesConfig<SelectOption, false, GroupBase<SelectOption>> {
  const css = (prop: string) =>
    typeof document !== "undefined"
      ? getComputedStyle(document.documentElement).getPropertyValue(prop).trim()
      : "";

  return {
    control: (base, state) => ({
      ...base,
      minHeight: "2.75rem",
      height: "2.75rem",
      alignItems: "center",
      borderWidth: "1.5px",
      borderStyle: "solid",
      borderColor: hasError
        ? css("--error") || "#ef4444"
        : state.isFocused
          ? css("--accent-primary") || "#3b82f6"
          : css("--border-default") || "#d1d5db",
      borderRadius: css("--radius-md") || "0.5rem",
      backgroundColor: state.isFocused
        ? css("--surface-strong") || "#fff"
        : css("--surface-base") || "#f9fafb",
      boxShadow: hasError
        ? `0 0 0 3px ${css("--error-subtle") || "rgba(239,68,68,.15)"}`
        : state.isFocused
          ? `0 0 0 3px ${css("--accent-primary-subtle") || "rgba(59,130,246,.15)"}`
          : "none",
      cursor: "pointer",
      transition: "border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease",
      "&:hover": {
        borderColor: state.isFocused
          ? css("--accent-primary") || "#3b82f6"
          : css("--border-strong") || "#9ca3af",
      },
    }),
    valueContainer: (base) => ({
      ...base,
      height: "2.75rem",
      padding: "0 0.9rem",
      display: "flex",
      alignItems: "center",
    }),
    singleValue: (base) => ({
      ...base,
      color: css("--text-primary") || "#111827",
      fontSize: "0.95rem",
      lineHeight: "1.25rem",
      margin: 0,
    }),
    placeholder: (base) => ({
      ...base,
      color: css("--text-tertiary") || "#9ca3af",
      fontSize: "0.95rem",
      fontWeight: 400,
      lineHeight: "1.25rem",
      margin: 0,
    }),
    indicatorsContainer: (base) => ({
      ...base,
      height: "2.75rem",
      alignItems: "center",
    }),
    indicatorSeparator: () => ({ display: "none" }),
    dropdownIndicator: (base, state) => ({
      ...base,
      color: css("--text-tertiary") || "#9ca3af",
      padding: "0 0.75rem",
      height: "2.75rem",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      transition: "transform 0.2s ease, color 0.15s ease",
      transform: state.selectProps.menuIsOpen ? "rotate(180deg)" : "rotate(0deg)",
      transformOrigin: "center",
      "&:hover": { color: css("--text-secondary") || "#6b7280" },
    }),
    menu: (base) => ({
      ...base,
      backgroundColor: css("--surface-strong") || "#fff",
      border: `1.5px solid ${css("--border-default") || "#d1d5db"}`,
      borderRadius: css("--radius-md") || "0.5rem",
      boxShadow: css("--shadow-md") || "0 4px 16px rgba(0,0,0,.1)",
      overflow: "hidden",
      zIndex: 100,
    }),
    menuPortal: (base) => ({
      ...base,
      zIndex: 300,
    }),
    menuList: (base) => ({
      ...base,
      padding: "0.35rem",
    }),
    option: (base, state) => ({
      ...base,
      fontSize: "0.95rem",
      padding: "0.55rem 0.75rem",
      borderRadius: "0.35rem",
      backgroundColor: state.isSelected
        ? css("--accent-primary") || "#3b82f6"
        : state.isFocused
          ? css("--surface-sunken") || "#f3f4f6"
          : "transparent",
      color: state.isSelected
        ? "#fff"
        : css("--text-primary") || "#111827",
      cursor: "pointer",
      transition: "background-color 0.1s ease",
      "&:active": {
        backgroundColor: state.isSelected
          ? css("--accent-primary") || "#3b82f6"
          : css("--border-default") || "#d1d5db",
      },
    }),
    input: (base) => ({
      ...base,
      color: css("--text-primary") || "#111827",
      margin: 0,
      padding: 0,
      lineHeight: "1.25rem",
    }),
    noOptionsMessage: (base) => ({
      ...base,
      color: css("--text-tertiary") || "#9ca3af",
      fontSize: "0.9rem",
      padding: "0.75rem",
    }),
  };
}

export function Select({
  label,
  name,
  value,
  onChange,
  options,
  placeholder = "Select an option",
  error,
  disabled,
  required,
  searchable = false,
  formatOptionLabel,
}: SelectProps) {
  const selectedOption = options.find((o) => o.value === value) ?? null;

  return (
    <div className="flex flex-col gap-1.5 w-full">
      <label className="text-sm font-semibold text-text-secondary" htmlFor={name}>
        {label}
        {required && <span className="text-error ml-0.5">*</span>}
      </label>
      <ReactSelect<SelectOption>
        inputId={name}
        name={name}
        value={selectedOption}
        onChange={(opt) => onChange(opt?.value ?? "")}
        options={options}
        placeholder={placeholder}
        isDisabled={disabled}
        isClearable={false}
        isSearchable={searchable}
        menuPortalTarget={typeof document !== "undefined" ? document.body : null}
        menuPosition="fixed"
        menuShouldScrollIntoView={false}
        maxMenuHeight={180}
        styles={buildStyles(!!error)}
        aria-invalid={!!error}
        aria-describedby={error ? `${name}-error` : undefined}
        classNamePrefix="rs"
        {...(formatOptionLabel ? { formatOptionLabel } : {})}
      />
      {error && (
        <p id={`${name}-error`} className="text-xs text-error mt-1" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
