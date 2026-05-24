"use client";

import { useProfile } from "@/lib/profile-context";
import { Button } from "@/components/button";
import type { ProfileType } from "@/lib/types";

const PROFILE_TYPE_META: Record<ProfileType, { label: string; description: string; icon: React.ReactNode }> = {
  PRIMARY: {
    label: "Primary",
    description: "Your main profile. Manage assets, nominees, and documents.",
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
  },
  ADVISOR: {
    label: "Advisor",
    description: "Manage assets and nominees on behalf of primary account holders who have granted you access.",
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
  NOMINEE: {
    label: "Nominee",
    description: "View assets and documents shared with you by a primary account holder after a release is triggered.",
    icon: (
      <svg className="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
    ),
  },
};

export default function ProfilesPage() {
  const { profiles, activeProfile, isLoading, switchProfile } = useProfile();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <span className="w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div>
      <p className="text-sm text-text-secondary mb-6">
        Switch between your profiles to access different contexts. Your active
        profile determines what data you see and what actions you can take.
      </p>

      {profiles.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center bg-surface-strong rounded-xl border border-border-light shadow-sm">
          <h3 className="text-base font-semibold text-text-primary mb-1">No profiles found</h3>
          <p className="text-sm text-text-secondary max-w-sm">
            Your account does not have any profiles yet. This usually means
            account setup is incomplete.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {profiles.map((profile) => {
            const meta = PROFILE_TYPE_META[profile.profile_type];
            const isActive = activeProfile?.id === profile.id;

            return (
              <div
                key={profile.id}
                className={[
                  "relative flex flex-col gap-4 p-5 rounded-xl border shadow-sm transition-all duration-[180ms]",
                  isActive
                    ? "bg-accent-subtle border-accent ring-2 ring-accent/20"
                    : "bg-surface-strong border-border-light hover:border-border-strong",
                ].join(" ")}
              >
                {isActive && (
                  <span className="absolute top-3 right-3 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-accent text-white">
                    Active
                  </span>
                )}

                <div className="flex items-center gap-3">
                  <div
                    className={[
                      "w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0",
                      isActive
                        ? "bg-accent text-white"
                        : "bg-bg-secondary text-text-secondary",
                    ].join(" ")}
                  >
                    {meta.icon}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-text-primary">{meta.label}</h3>
                    <span className="text-xs text-text-tertiary">
                      {profile.profile_type}
                    </span>
                  </div>
                </div>

                <p className="text-sm text-text-secondary leading-relaxed">
                  {meta.description}
                </p>

                {!isActive && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => switchProfile(profile.id)}
                    className="mt-auto self-start"
                  >
                    Switch to {meta.label.toLowerCase()}
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
