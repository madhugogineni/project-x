"use client";

import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/auth-context";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="flex flex-col gap-5 mt-1">
      {/* Profile Information */}
      <div className="bg-surface-strong border border-border-light rounded-xl shadow-sm p-6">
        <h4 className="text-sm font-bold text-text-primary mb-4">Profile</h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-text-tertiary">Full name</span>
            <span className="text-sm text-text-primary">{user?.full_name || "Not set"}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-text-tertiary">Phone</span>
            <span className="text-sm text-text-primary">{user?.phone || "–"}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-text-tertiary">Email</span>
            <span className="text-sm text-text-primary">{user?.email || "–"}</span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-text-tertiary">Phone verified</span>
            <span className="text-sm text-text-primary">
              {user?.phone_verified ? "Yes" : "No"}
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-text-tertiary">Email verified</span>
            <span className="text-sm text-text-primary">
              {user?.email_verified ? "Yes" : "No"}
            </span>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-text-tertiary">Account status</span>
            <span className="text-sm text-text-primary">{user?.status || "–"}</span>
          </div>
        </div>
      </div>

      {/* Appearance */}
      <div className="bg-surface-strong border border-border-light rounded-xl shadow-sm p-6">
        <h4 className="text-sm font-bold text-text-primary mb-4">Appearance</h4>
        <div className="flex items-center gap-4">
          <span className="text-xs font-semibold text-text-tertiary">Theme</span>
          <ThemeToggle />
        </div>
      </div>
    </div>
  );
}
