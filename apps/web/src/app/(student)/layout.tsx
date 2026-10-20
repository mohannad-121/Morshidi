import type { Viewport } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";

import { ProtectedBoundary } from "@/auth/protected-boundary";
import { AppShell } from "@/components/navigation/AppShell";

const inter = Inter({
  variable: "--font-inter",
  weight: ["400", "500", "600", "700", "800", "900"],
  subsets: ["latin"],
  display: "swap",
});

export const viewport: Viewport = {
  themeColor: "#05060b",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function StudentLayout({ children }: { children: ReactNode }) {
  return (
    <div className={`${inter.variable} student-font-root`}>
      <ProtectedBoundary>
        <AppShell>
          {children}
        </AppShell>
      </ProtectedBoundary>
    </div>
  );
}
