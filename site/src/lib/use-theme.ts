"use client";

import { useEffect, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "project-x-app-theme";
const THEME_CHANGE_EVENT = "project-x-theme-change";

function getSystemTheme(): Theme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function resolveTheme(): Theme {
  if (typeof window === "undefined") return "light";
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === "light" || saved === "dark") return saved;
  return getSystemTheme();
}

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.style.colorScheme = theme;
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>("light");

  useEffect(() => {
    const initial = resolveTheme();
    setThemeState(initial);
    applyTheme(initial);

    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = (e: MediaQueryListEvent) => {
      if (localStorage.getItem(STORAGE_KEY)) return;
      const systemTheme: Theme = e.matches ? "dark" : "light";
      setThemeState(systemTheme);
      applyTheme(systemTheme);
    };
    const handleThemeSelection = (e: Event) => {
      const nextTheme = (e as CustomEvent<Theme>).detail;
      setThemeState(nextTheme);
      applyTheme(nextTheme);
    };
    mq.addEventListener("change", handleChange);
    window.addEventListener(THEME_CHANGE_EVENT, handleThemeSelection);
    return () => {
      mq.removeEventListener("change", handleChange);
      window.removeEventListener(THEME_CHANGE_EVENT, handleThemeSelection);
    };
  }, []);

  const setTheme = (nextTheme: Theme) => {
    setThemeState(nextTheme);
    localStorage.setItem(STORAGE_KEY, nextTheme);
    applyTheme(nextTheme);
    window.dispatchEvent(new CustomEvent<Theme>(THEME_CHANGE_EVENT, { detail: nextTheme }));
  };

  return { theme, setTheme };
}
