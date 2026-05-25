"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import type { PaginatedResponse, Profile } from "@/lib/types";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

const PROFILE_ID_KEY = "project-x-active-profile-id";

function getStoredProfileId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(PROFILE_ID_KEY);
}

function setStoredProfileId(profileId: string) {
  localStorage.setItem(PROFILE_ID_KEY, profileId);
}

function clearStoredProfileId() {
  localStorage.removeItem(PROFILE_ID_KEY);
}

type ProfileContextValue = {
  profiles: Profile[];
  activeProfile: Profile | null;
  isLoading: boolean;
  switchProfile: (profileId: string) => void;
  refreshProfiles: () => Promise<void>;
};

const ProfileContext = createContext<ProfileContextValue | null>(null);

export function ProfileProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [activeProfile, setActiveProfile] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshProfiles = useCallback(async () => {
    try {
      const data = await apiClient.get<PaginatedResponse<Profile>>("/profiles");
      setProfiles(data.items);

      const storedId = getStoredProfileId();
      const match = storedId ? data.items.find((p) => p.id === storedId) : null;

      if (match) {
        setActiveProfile(match);
      } else {
        // Default to PRIMARY profile
        const primary =
          data.items.find((p) => p.profile_type === "PRIMARY") ?? data.items[0] ?? null;
        if (primary) {
          setActiveProfile(primary);
          setStoredProfileId(primary.id);
        }
      }
    } catch {
      setProfiles([]);
      setActiveProfile(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (isAuthenticated) {
      refreshProfiles();
    } else {
      setProfiles([]);
      setActiveProfile(null);
      clearStoredProfileId();
      setIsLoading(false);
    }
  }, [isAuthenticated, authLoading, refreshProfiles]);

  const switchProfile = useCallback(
    (profileId: string) => {
      const match = profiles.find((p) => p.id === profileId);
      if (match) {
        setActiveProfile(match);
        setStoredProfileId(match.id);
      }
    },
    [profiles]
  );

  return (
    <ProfileContext.Provider
      value={{ profiles, activeProfile, isLoading, switchProfile, refreshProfiles }}
    >
      {children}
    </ProfileContext.Provider>
  );
}

export function useProfile(): ProfileContextValue {
  const context = useContext(ProfileContext);
  if (!context) {
    throw new Error("useProfile must be used within a ProfileProvider");
  }
  return context;
}
