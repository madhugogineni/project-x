"use client";

import { useEffect, useState } from "react";

type Theme = "light" | "dark";

const storageKey = "project-x-app-theme";

function resolveTheme(savedTheme: string | null) {
  if (savedTheme === "light" || savedTheme === "dark") {
    return savedTheme;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.style.colorScheme = theme;
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
    const nextTheme = resolveTheme(window.localStorage.getItem(storageKey));

    setTheme(nextTheme);
    applyTheme(nextTheme);

    const handleChange = (event: MediaQueryListEvent) => {
      if (window.localStorage.getItem(storageKey)) {
        return;
      }

      const systemTheme = event.matches ? "dark" : "light";
      setTheme(systemTheme);
      applyTheme(systemTheme);
    };

    mediaQuery.addEventListener("change", handleChange);

    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  const updateTheme = (nextTheme: Theme) => {
    setTheme(nextTheme);
    window.localStorage.setItem(storageKey, nextTheme);
    applyTheme(nextTheme);
  };

  return (
    <div
      className="inline-flex items-center gap-0.5 p-1 rounded-md border border-border-default bg-surface-strong"
      role="group"
      aria-label="Color theme"
    >
      <button
        type="button"
        className={[
          "inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-all duration-[180ms]",
          theme === "light"
            ? "bg-bg-secondary text-text-primary shadow-sm"
            : "text-text-tertiary hover:text-text-secondary",
        ].join(" ")}
        aria-pressed={theme === "light"}
        onClick={() => updateTheme("light")}
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
        <span>Light</span>
      </button>
      <button
        type="button"
        className={[
          "inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-all duration-[180ms]",
          theme === "dark"
            ? "bg-bg-secondary text-text-primary shadow-sm"
            : "text-text-tertiary hover:text-text-secondary",
        ].join(" ")}
        aria-pressed={theme === "dark"}
        onClick={() => updateTheme("dark")}
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 12.79A9 9 0 1 1 11.21 3A7 7 0 0 0 21 12.79Z" />
        </svg>
        <span>Dark</span>
      </button>
    </div>
  );
}
