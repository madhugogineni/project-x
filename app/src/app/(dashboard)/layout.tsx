"use client";

import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { ProtectedRoute } from "@/lib/protected-route";
import { ProfileProvider } from "@/lib/profile-context";

type DashboardLayoutProps = {
  children: ReactNode;
};

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <ProtectedRoute>
      <ProfileProvider>
        <AppShell>{children}</AppShell>
      </ProfileProvider>
    </ProtectedRoute>
  );
}
