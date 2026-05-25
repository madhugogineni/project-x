"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function OverviewPage() {
  const { user } = useAuth();

  return (
    <div>
      {/* Welcome strip */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 p-6 bg-surface-strong rounded-xl border border-border-light shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-text-primary">
            {user?.full_name ? `Welcome, ${user.full_name}` : "Welcome back"}
          </h2>
          <p className="text-sm text-text-secondary mt-1">
            Here is a snapshot of your continuity setup.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-success-subtle text-success">
            Phone verified
          </span>
          {user?.email && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-info-subtle text-info">
              {user.email}
            </span>
          )}
        </div>
      </section>

      {/* Summary cards */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* Assets */}
        <div className="flex flex-col gap-3 p-5 bg-surface-strong rounded-xl border border-border-light shadow-sm hover:shadow-md transition-shadow">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#EFF6FF", color: "#2563EB" }}>
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-text-primary font-display">0</span>
            <span className="text-sm text-text-secondary">Asset containers</span>
          </div>
          <Link href="/assets" className="flex items-center gap-1 text-sm text-accent font-medium hover:text-accent-hover transition-colors">
            Add assets
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
          </Link>
        </div>

        {/* Nominees */}
        <div className="flex flex-col gap-3 p-5 bg-surface-strong rounded-xl border border-border-light shadow-sm hover:shadow-md transition-shadow">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#F5F3FF", color: "#7C3AED" }}>
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-text-primary font-display">0</span>
            <span className="text-sm text-text-secondary">Nominees</span>
          </div>
          <Link href="/nominees" className="flex items-center gap-1 text-sm text-accent font-medium hover:text-accent-hover transition-colors">
            Add nominees
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
          </Link>
        </div>

        {/* Documents */}
        <div className="flex flex-col gap-3 p-5 bg-surface-strong rounded-xl border border-border-light shadow-sm hover:shadow-md transition-shadow">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#ECFDF5", color: "#059669" }}>
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-text-primary font-display">0</span>
            <span className="text-sm text-text-secondary">Documents</span>
          </div>
          <Link href="/documents" className="flex items-center gap-1 text-sm text-accent font-medium hover:text-accent-hover transition-colors">
            Upload
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
          </Link>
        </div>

        {/* Profiles */}
        <div className="flex flex-col gap-3 p-5 bg-surface-strong rounded-xl border border-border-light shadow-sm hover:shadow-md transition-shadow">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#FFF7ED", color: "#EA580C" }}>
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-text-primary font-display">1</span>
            <span className="text-sm text-text-secondary">Profiles</span>
          </div>
          <Link href="/profiles" className="flex items-center gap-1 text-sm text-accent font-medium hover:text-accent-hover transition-colors">
            View
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-3.5 h-3.5"><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></svg>
          </Link>
        </div>
      </section>

      {/* Quick setup steps */}
      <section>
        <h3 className="text-base font-bold text-text-primary mb-4">Get started</h3>
        <div className="flex flex-col divide-y divide-border-light bg-surface-strong rounded-xl border border-border-light shadow-sm overflow-hidden">
          <Link href="/assets" className="flex items-center gap-4 p-5 hover:bg-bg-secondary transition-colors no-underline">
            <span className="w-8 h-8 rounded-full bg-accent-subtle text-accent text-sm font-bold flex items-center justify-center flex-shrink-0">
              1
            </span>
            <div className="flex-1 min-w-0">
              <strong className="text-sm font-semibold text-text-primary block">
                Add your first asset container
              </strong>
              <p className="text-sm text-text-secondary mt-0.5">
                Organize accounts, policies, and holdings into structured containers.
              </p>
            </div>
            <svg className="w-5 h-5 text-text-tertiary flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
          </Link>
          <Link href="/nominees" className="flex items-center gap-4 p-5 hover:bg-bg-secondary transition-colors no-underline">
            <span className="w-8 h-8 rounded-full bg-accent-subtle text-accent text-sm font-bold flex items-center justify-center flex-shrink-0">
              2
            </span>
            <div className="flex-1 min-w-0">
              <strong className="text-sm font-semibold text-text-primary block">
                Assign nominees
              </strong>
              <p className="text-sm text-text-secondary mt-0.5">
                Designate who should have access to your financial information.
              </p>
            </div>
            <svg className="w-5 h-5 text-text-tertiary flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
          </Link>
          <Link href="/documents" className="flex items-center gap-4 p-5 hover:bg-bg-secondary transition-colors no-underline">
            <span className="w-8 h-8 rounded-full bg-accent-subtle text-accent text-sm font-bold flex items-center justify-center flex-shrink-0">
              3
            </span>
            <div className="flex-1 min-w-0">
              <strong className="text-sm font-semibold text-text-primary block">
                Upload supporting documents
              </strong>
              <p className="text-sm text-text-secondary mt-0.5">
                Attach statements and ownership proofs to the encrypted vault.
              </p>
            </div>
            <svg className="w-5 h-5 text-text-tertiary flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
          </Link>
        </div>
      </section>
    </div>
  );
}
