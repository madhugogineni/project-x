import type { Metadata } from "next";
import { IBM_Plex_Sans, Sora } from "next/font/google";

import "@/app/globals.css";
import { ThemeScript } from "@/components/theme-script";
import { siteConfig } from "@/lib/site-config";

const displayFont = Sora({
  subsets: ["latin"],
  variable: "--font-display"
});

const bodyFont = IBM_Plex_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600", "700"]
});

export const metadata: Metadata = {
  metadataBase: new URL(siteConfig.links.site),
  title: {
    default: siteConfig.name,
    template: `%s | ${siteConfig.name}`
  },
  description: siteConfig.description
};

type RootLayoutProps = Readonly<{
  children: React.ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html
      lang="en"
      data-theme="light"
      suppressHydrationWarning
      className={`${displayFont.variable} ${bodyFont.variable}`}
    >
      <body>
        <ThemeScript />
        {children}
      </body>
    </html>
  );
}
