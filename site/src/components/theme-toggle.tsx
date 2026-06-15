"use client";

import { useTheme } from "@/lib/use-theme";

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="4.5" fill="currentColor" />
      <path
        d="M12 2.5v2.25M12 19.25v2.25M4.75 12H2.5M21.5 12h-2.25M5.64 5.64l1.59 1.59M16.77 16.77l1.59 1.59M18.36 5.64l-1.59 1.59M7.23 16.77l-1.59 1.59"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.8"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M19 14.5A7.5 7.5 0 0 1 9.5 5a8 8 0 1 0 9.5 9.5Z"
        fill="currentColor"
      />
    </svg>
  );
}

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="theme-toggle" role="group" aria-label="Color theme">
      <button
        type="button"
        className={theme === "light" ? "is-active" : undefined}
        aria-label="Light mode"
        aria-pressed={theme === "light"}
        onClick={() => setTheme("light")}
      >
        <SunIcon />
      </button>
      <button
        type="button"
        className={theme === "dark" ? "is-active" : undefined}
        aria-label="Dark mode"
        aria-pressed={theme === "dark"}
        onClick={() => setTheme("dark")}
      >
        <MoonIcon />
      </button>
    </div>
  );
}
