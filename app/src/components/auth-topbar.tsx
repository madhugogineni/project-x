"use client";

import Link from "next/link";
import { ThemeToggle } from "@/components/theme-toggle";
import { appConfig } from "@/lib/app-config";

export function AuthTopbar() {
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
        <ThemeToggle />
      </div>
    </header>
  );
}
