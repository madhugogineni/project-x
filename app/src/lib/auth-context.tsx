"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";

import type { Account } from "@/lib/types";
import {
  apiClient,
  clearStoredTokens,
  getStoredTokens,
  setStoredTokens,
} from "@/lib/api-client";

type AuthState = {
  user: Account | null;
  isLoading: boolean;
  isAuthenticated: boolean;
};

type AuthContextValue = AuthState & {
  login: (accessToken: string, refreshToken: string, account: Account) => void;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  const refreshUser = useCallback(async () => {
    try {
      const account = await apiClient.get<Account>("/auth/me");
      setState({ user: account, isLoading: false, isAuthenticated: true });
    } catch {
      clearStoredTokens();
      setState({ user: null, isLoading: false, isAuthenticated: false });
    }
  }, []);

  useEffect(() => {
    const tokens = getStoredTokens();
    if (tokens) {
      refreshUser();
    } else {
      setState({ user: null, isLoading: false, isAuthenticated: false });
    }
  }, [refreshUser]);

  const login = useCallback(
    (accessToken: string, refreshToken: string, account: Account) => {
      setStoredTokens(accessToken, refreshToken);
      setState({ user: account, isLoading: false, isAuthenticated: true });
    },
    []
  );

  const logout = useCallback(async () => {
    const tokens = getStoredTokens();
    try {
      await apiClient.post("/auth/logout", {
        refresh_token: tokens?.refreshToken ?? null,
      });
    } catch {
      // Continue with local cleanup even if API call fails
    }
    clearStoredTokens();
    setState({ user: null, isLoading: false, isAuthenticated: false });
    router.replace("/login");
  }, [router]);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
