import type { Viewport } from "next";
import type { ReactNode } from "react";

import { ProtectedBoundary } from "@/auth/protected-boundary";
import { AppShell } from "@/components/navigation/AppShell";

export const viewport: Viewport = {
  themeColor: "#05060b",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function StudentLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedBoundary>
      <AppShell>
        {children}
      </AppShell>
    </ProtectedBoundary>
  );
}
