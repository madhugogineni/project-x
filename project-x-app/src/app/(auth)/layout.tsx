import type { ReactNode } from "react";

import { AuthTopbar } from "@/components/auth-topbar";
import { PublicOnlyRoute } from "@/lib/public-only-route";

type AuthLayoutProps = {
  children: ReactNode;
};

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <PublicOnlyRoute>
      <AuthTopbar />
      <div className="min-h-screen flex flex-col items-center bg-bg-primary pt-[calc(var(--topbar-h)+2rem)] pb-12 px-4">
        {children}
      </div>
    </PublicOnlyRoute>
  );
}
