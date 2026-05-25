"use client";

import Link from "next/link";
import { appConfig } from "@/lib/app-config";
import { useTheme } from "@/lib/use-theme";

export function AuthTopbar() {
  const { theme, toggle } = useTheme();

  return (
    <header className="fixed top-0 left-0 right-0 z-[100] flex items-center justify-between h-topbar px-5 bg-topbar-bg backdrop-blur-xl border-b border-topbar-border">
      <div className="flex items-center">
        <Link
          href="/"
          className="font-display font-bold text-[1.05rem] tracking-tight text-text-primary no-underline hover:opacity-80 transition-opacity"
        >
          {appConfig.name}
        </Link>
      </div>

      <div className="flex items-center">
        <button
          type="button"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-text-secondary border border-border-default rounded-sm bg-transparent hover:bg-bg-secondary hover:border-border-strong hover:text-text-primary transition-all duration-[180ms]"
          onClick={toggle}
          aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
        >
          {theme === "light" ? (
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3A7 7 0 0 0 21 12.79Z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
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
          )}
          <span className="hidden sm:inline">{theme === "light" ? "Dark" : "Light"}</span>
        </button>
      </div>
    </header>
  );
}
