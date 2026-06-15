"use client";

import type { ReactNode } from "react";
import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { ThemeToggle } from "@/components/theme-toggle";
import { appConfig } from "@/lib/app-config";
import { useAuth } from "@/lib/auth-context";
import { useProfile } from "@/lib/profile-context";

/* ─── Helpers ──────────────────────────────────────────────────────── */
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

const PROFILE_LABEL: Record<string, string> = {
  PRIMARY: "Primary",
  ADVISOR: "Advisor",
  NOMINEE: "Nominee",
};

/* ─── Nav icons ────────────────────────────────────────────────────── */
const navIcons: Record<string, ReactNode> = {
  "/": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
    </svg>
  ),
  "/assets": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <polyline points="3.27 6.96 12 12.01 20.73 6.96" /><line x1="12" y1="22.08" x2="12" y2="12" />
    </svg>
  ),
  "/documents": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  ),
  "/nominees": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  ),
  "/profiles": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
    </svg>
  ),
  "/sessions": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  ),
  "/devices": (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="2" width="14" height="20" rx="2" ry="2" /><line x1="12" y1="18" x2="12.01" y2="18" />
    </svg>
  ),
};

/* ─── AppShell ─────────────────────────────────────────────────────── */
type AppShellProps = { children: ReactNode };

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { profiles, activeProfile, switchProfile } = useProfile();

  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [profileSwitcherOpen, setProfileSwitcherOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const profileSwitcherRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches);
      if (!e.matches) setMobileSidebarOpen(false);
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // Close menus on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
      if (profileSwitcherRef.current && !profileSwitcherRef.current.contains(e.target as Node)) {
        setProfileSwitcherOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const currentNav = appConfig.navigation.find((n) => n.href === pathname);
  const pageTitle = currentNav?.label || "Overview";

  /* ── Shared sidebar content ── */
  const sidebarContent = (
    <>
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-4 h-14 flex-shrink-0 border-b border-border-light">
        <Link
          href="/"
          className="font-display font-bold text-[1.05rem] tracking-tight text-text-primary no-underline hover:opacity-80 transition-opacity"
          onClick={() => setMobileSidebarOpen(false)}
        >
          {appConfig.name}
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col py-3 flex-1 overflow-y-auto" aria-label="Primary navigation">
        {appConfig.navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "flex items-center gap-3 px-3 py-2.5 mx-2 rounded-md text-sm font-medium transition-all duration-[180ms]",
                isActive
                  ? "bg-nav-active-bg text-nav-active font-semibold"
                  : "text-text-secondary hover:bg-nav-hover hover:text-text-primary",
              ].join(" ")}
              aria-current={isActive ? "page" : undefined}
              onClick={() => setMobileSidebarOpen(false)}
            >
              <span className="w-5 h-5 flex-shrink-0">
                {navIcons[item.href] || (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <circle cx="12" cy="12" r="10" />
                  </svg>
                )}
              </span>
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom section: settings, theme, logout, user — hidden on mobile (topbar covers these) */}
      {!isMobile && <div className="flex-shrink-0 border-t border-border-light">
        <div className="flex flex-col py-2">
          <div className="flex items-center justify-between gap-3 px-4 py-2 text-sm text-text-secondary">
            <span>Appearance</span>
            <ThemeToggle />
          </div>

          <Link
            href="/settings"
            className="flex items-center gap-3 px-4 py-2 text-sm text-text-secondary hover:bg-nav-hover hover:text-text-primary transition-colors"
            onClick={() => setMobileSidebarOpen(false)}
          >
            <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            <span>Settings</span>
          </Link>
        </div>

        {/* User card + logout */}
        {user && (
          <div className="border-t border-border-light px-3 py-3 relative" ref={profileSwitcherRef}>
            <div className="flex items-center gap-2.5">
              {/* Clickable user area — opens profile switcher */}
              <button
                type="button"
                className="flex items-center gap-2.5 flex-1 min-w-0 rounded-md px-1 py-1 -mx-1 hover:bg-nav-hover transition-colors text-left"
                onClick={() => setProfileSwitcherOpen((o) => !o)}
              >
                <div className="w-8 h-8 rounded-full bg-accent-subtle text-accent text-xs font-bold grid place-items-center font-display flex-shrink-0 border-2 border-border-light">
                  {getInitials(user.full_name ?? null)}
                </div>
                <div className="flex-1 min-w-0">
                  <span className="block text-sm font-semibold text-text-primary truncate">
                    {user.full_name || "User"}
                  </span>
                  {activeProfile && (
                    <span className="block text-xs text-text-secondary truncate">
                      {PROFILE_LABEL[activeProfile.profile_type] || activeProfile.profile_type} profile
                    </span>
                  )}
                </div>
                <svg className="w-3.5 h-3.5 text-text-tertiary flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="6 9 12 4 18 9" /><polyline points="6 15 12 20 18 15" />
                </svg>
              </button>

              {/* Logout icon */}
              <button
                type="button"
                className="w-8 h-8 flex items-center justify-center rounded-md text-text-tertiary hover:text-error hover:bg-error-subtle transition-colors flex-shrink-0"
                title="Log out"
                onClick={() => { setMobileSidebarOpen(false); logout(); }}
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
                </svg>
              </button>
            </div>

            {/* Profile switcher popup */}
            {profileSwitcherOpen && profiles.length > 0 && (
              <div className="absolute bottom-full left-2 right-2 mb-2 bg-dropdown-bg border border-border-light rounded-xl shadow-dropdown z-[60] py-1 overflow-hidden">
                <div className="px-3 py-2 border-b border-border-light">
                  <span className="text-xs font-semibold text-text-tertiary">Switch profile</span>
                </div>
                {profiles.map((profile) => {
                  const isActive = activeProfile?.id === profile.id;
                  return (
                    <button
                      key={profile.id}
                      type="button"
                      className={[
                        "w-full flex items-center gap-2.5 px-3 py-2.5 text-sm text-left transition-colors",
                        isActive
                          ? "bg-accent-subtle text-accent font-semibold"
                          : "text-text-secondary hover:bg-bg-secondary hover:text-text-primary",
                      ].join(" ")}
                      onClick={() => {
                        switchProfile(profile.id);
                        setProfileSwitcherOpen(false);
                      }}
                    >
                      <span className="flex-1">{PROFILE_LABEL[profile.profile_type] || profile.profile_type}</span>
                      {isActive && (
                        <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>}
    </>
  );

  return (
    <div className="flex min-h-screen bg-bg-primary">
      {/* ── Mobile topbar (hidden on desktop) ── */}
      <header className="fixed top-0 left-0 right-0 z-[100] flex items-center justify-between h-topbar px-4 bg-topbar-bg backdrop-blur-xl border-b border-topbar-border md:hidden">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="w-8 h-8 flex items-center justify-center rounded-md text-text-secondary hover:bg-bg-secondary hover:text-text-primary transition-all duration-[180ms]"
            onClick={() => setMobileSidebarOpen((o) => !o)}
            aria-label="Toggle menu"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="4" y1="7" x2="20" y2="7" /><line x1="4" y1="12" x2="20" y2="12" /><line x1="4" y1="17" x2="20" y2="17" />
            </svg>
          </button>
          <Link
            href="/"
            className="font-display font-bold text-[1.05rem] tracking-tight text-text-primary no-underline hover:opacity-80 transition-opacity"
          >
            {appConfig.name}
          </Link>
        </div>

        {user && (
          <div className="relative" ref={userMenuRef}>
            <button
              type="button"
              className="w-8 h-8 rounded-full bg-accent-subtle text-accent text-xs font-bold border-2 border-border-light hover:border-accent transition-all duration-[180ms] grid place-items-center font-display"
              onClick={() => setUserMenuOpen((o) => !o)}
              aria-haspopup="true"
              aria-expanded={userMenuOpen}
            >
              {getInitials(user.full_name ?? null)}
            </button>

            {userMenuOpen && (
              <div className="absolute right-0 top-[calc(100%+0.5rem)] w-56 bg-dropdown-bg border border-border-light rounded-xl shadow-dropdown z-50 py-1 overflow-hidden">
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
                  onClick={() => { setUserMenuOpen(false); setMobileSidebarOpen(false); }}
                >
                  <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
                  </svg>
                  Profile
                </Link>
                <Link
                  href="/settings"
                  className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-text-secondary hover:bg-bg-secondary hover:text-text-primary transition-colors"
                  onClick={() => { setUserMenuOpen(false); setMobileSidebarOpen(false); }}
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
                  onClick={() => { setUserMenuOpen(false); logout(); }}
                >
                  <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" /><line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                  Log out
                </button>
              </div>
            )}
          </div>
        )}
      </header>

      {/* ── Mobile overlay ── */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 md:hidden"
          onClick={() => setMobileSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar ── */}
      <aside
        className={[
          "fixed left-0 top-0 bottom-0 z-50 flex flex-col bg-nav-bg border-r border-border-light transition-transform duration-200 overflow-hidden",
          "w-[var(--sidebar-w)]",
          // Mobile: offscreen by default, slide in when open. Sits below topbar.
          "md:translate-x-0",
          isMobile
            ? mobileSidebarOpen
              ? "translate-x-0 top-topbar"
              : "-translate-x-full top-topbar"
            : "",
        ].join(" ")}
      >
        {sidebarContent}
      </aside>

      {/* ── Main content ── */}
      <main
        className={[
          "flex-1 min-h-screen px-4 sm:px-6 pb-8 transition-all duration-200 overflow-x-hidden",
          "pt-[calc(var(--topbar-h)+1rem)] md:pt-4",
          "md:ml-[var(--sidebar-w)]",
        ].join(" ")}
      >
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-bold text-text-primary font-display">{pageTitle}</h1>
        </div>
        {children}
      </main>
    </div>
  );
}
