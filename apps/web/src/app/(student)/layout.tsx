import type { ReactNode } from "react";

import { ProtectedBoundary } from "@/auth/protected-boundary";
import { AppShell } from "@/components/navigation/AppShell";

export default function StudentLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedBoundary>
      <AppShell>
        {children}
      </AppShell>
    </ProtectedBoundary>
  );
}
