import type { ReactNode } from "react";

import { ProtectedBoundary } from "@/auth/protected-boundary";

export default function StudentLayout({ children }: { children: ReactNode }) {
  return (
    <ProtectedBoundary>
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {children}
      </div>
    </ProtectedBoundary>
  );
}
