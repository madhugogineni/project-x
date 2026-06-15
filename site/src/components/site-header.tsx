"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ThemeToggle } from "@/components/theme-toggle";
import { siteConfig } from "@/lib/site-config";

const navItems = [
  { href: "#pillars", label: "What it does" },
  { href: "#workflow", label: "How it works" },
  { href: "#safeguards", label: "Built for safety" }
] as const;

export function SiteHeader() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  useEffect(() => {
    const updateScrollState = () => {
      setIsScrolled(window.scrollY > 12);
    };

    updateScrollState();
    window.addEventListener("scroll", updateScrollState, { passive: true });

    return () => window.removeEventListener("scroll", updateScrollState);
  }, []);

  useEffect(() => {
    if (!isMenuOpen) {
      return;
    }

    const closeMenuOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsMenuOpen(false);
      }
    };

    window.addEventListener("keydown", closeMenuOnEscape);
    return () => window.removeEventListener("keydown", closeMenuOnEscape);
  }, [isMenuOpen]);

  return (
    <header
      className={`site-header${isScrolled ? " site-header--scrolled" : ""}${
        isMenuOpen ? " site-header--menu-open" : ""
      }`}
    >
      <button
        className={`site-menu-button${isMenuOpen ? " is-open" : ""}`}
        type="button"
        aria-controls="site-navigation"
        aria-expanded={isMenuOpen}
        aria-label={isMenuOpen ? "Close navigation menu" : "Open navigation menu"}
        onClick={() => setIsMenuOpen((open) => !open)}
      >
        <span />
        <span />
      </button>
      <Link className="site-header__brand" href="/">
        {siteConfig.name}
      </Link>
      <nav
        className={`site-nav${isMenuOpen ? " site-nav--open" : ""}`}
        id="site-navigation"
        aria-label="Page sections"
      >
        {navItems.map((item) => (
          <a
            key={item.href}
            className="site-nav__link"
            href={item.href}
            onClick={() => setIsMenuOpen(false)}
          >
            {item.label}
          </a>
        ))}
        <div className="site-nav__mobile-tools">
          <span>Appearance</span>
          <ThemeToggle />
        </div>
      </nav>
      <div className="site-header__actions">
        <ThemeToggle />
        <Link className="header-app-button" href={siteConfig.links.app}>
          Go to app
        </Link>
      </div>
    </header>
  );
}
