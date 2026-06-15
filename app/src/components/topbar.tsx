"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";

import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/auth-context";
import { useProfile } from "@/lib/profile-context";
import { appConfig } from "@/lib/app-config";

/* ─── helpers ────────────────────────────────────────────────────────── */
function getInitials(name: string | null): string {
  if (!name) return "U";
  return name
    .split(" ")
    .filter(Boolean)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

/* ─── Topbar ─────────────────────────────────────────────────────────── */
type TopbarProps = {
  onSidebarToggle?: () => void;
};

const PROFILE_LABEL: Record<string, string> = {
  PRIMARY: "Primary",
  ADVISOR: "Advisor",
  NOMINEE: "Nominee",
};

export function Topbar({ onSidebarToggle }: TopbarProps) {
  const { user, logout } = useAuth();
  const { activeProfile } = useProfile();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isAuthenticated = !!user;

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const onMenuEnter = () => {
    if (menuTimeout.current) clearTimeout(menuTimeout.current);
    setMenuOpen(true);
  };
  const onMenuLeave = () => {
    menuTimeout.current = setTimeout(() => setMenuOpen(false), 200);
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-[100] flex items-center justify-between h-topbar px-5 bg-topbar-bg backdrop-blur-xl border-b border-topbar-border">
      {/* Left */}
      <div className="flex items-center gap-3">
        {isAuthenticated && onSidebarToggle && (
          <button
            type="button"
            className="w-8 h-8 flex items-center justify-center rounded-md text-text-secondary hover:bg-bg-secondary hover:text-text-primary transition-all duration-[180ms]"
            onClick={onSidebarToggle}
            aria-label="Toggle sidebar"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="4" y1="7" x2="20" y2="7" />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="17" x2="20" y2="17" />
            </svg>
          </button>
        )}
        <Link
          href={isAuthenticated ? "/" : "/login"}
          className="font-display font-bold text-[1.05rem] tracking-tight text-text-primary no-underline hover:opacity-80 transition-opacity"
        >
          {appConfig.name}
        </Link>
      </div>

      {/* Right */}
      <div className="flex items-center gap-2">
        {isAuthenticated ? (
          /* ── Authenticated: greeting + avatar dropdown ── */
          <>
            <div className="hidden sm:flex items-center gap-2 mr-1">
              <span className="text-sm text-text-secondary">
                {user.full_name || ""}
              </span>
              {activeProfile && (
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[0.65rem] font-semibold bg-accent-subtle text-accent leading-none">
                  {PROFILE_LABEL[activeProfile.profile_type] || activeProfile.profile_type}
                </span>
              )}
            </div>

            <div
              className="relative"
              ref={menuRef}
              onMouseEnter={onMenuEnter}
              onMouseLeave={onMenuLeave}
            >
              <button
                type="button"
                className="w-8 h-8 rounded-full bg-accent-subtle text-accent text-xs font-bold border-2 border-border-light hover:border-accent hover:shadow-[0_0_0_3px_var(--accent-primary-subtle)] transition-all duration-[180ms] grid place-items-center font-display"
                aria-haspopup="true"
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((o) => !o)}
              >
                {getInitials(user.full_name ?? null)}
              </button>

              {menuOpen && (
                <div
                  className="absolute right-0 top-[calc(100%+0.5rem)] w-56 bg-dropdown-bg border border-border-light rounded-xl shadow-dropdown z-50 py-1 overflow-hidden"
                  role="menu"
                >
                  {/* User info */}
                  <div className="px-4 py-3 border-b border-border-light">
                    <span className="block text-sm font-semibold text-text-primary truncate">
                      {user.full_name || "User"}
                    </span>
                    <span className="block text-xs text-text-tertiary truncate mt-0.5">
                      {user.email || user.phone || ""}
                    </span>
                    {activeProfile && (
                      <span className="inline-flex items-center px-1.5 py-0.5 mt-1.5 rounded text-[0.65rem] font-semibold bg-accent-subtle text-accent leading-none">
                        {PROFILE_LABEL[activeProfile.profile_type] || activeProfile.profile_type} profile
                      </span>
                    )}
                  </div>

                  <Link
                    href="/profiles"
                    className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-text-secondary hover:bg-bg-secondary hover:text-text-primary transition-colors"
                    role="menuitem"
                    onClick={() => setMenuOpen(false)}
                  >
                    <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                    Profile
                  </Link>

                  <Link
                    href="/settings"
                    className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-text-secondary hover:bg-bg-secondary hover:text-text-primary transition-colors"
                    role="menuitem"
                    onClick={() => setMenuOpen(false)}
                  >
                    <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="3" />
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
                    </svg>
                    Settings
                  </Link>

                  <div className="flex items-center justify-between gap-2.5 px-4 py-2.5 text-sm text-text-secondary">
                    <span>Appearance</span>
                    <ThemeToggle />
                  </div>

                  <div className="border-t border-border-light my-1" />

                  <button
                    type="button"
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-error hover:bg-error-subtle transition-colors text-left"
                    role="menuitem"
                    onClick={() => { setMenuOpen(false); logout(); }}
                  >
                    <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                      <polyline points="16 17 21 12 16 7" />
                      <line x1="21" y1="12" x2="9" y2="12" />
                    </svg>
                    Log out
                  </button>
                </div>
              )}
            </div>
          </>
        ) : (
          <ThemeToggle />
        )}
      </div>
    </header>
  );
}
