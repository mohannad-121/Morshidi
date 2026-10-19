import type { ReactNode } from "react";
import { ProtectedBoundary } from "@/auth/protected-boundary";
import { InstitutionalShell } from "./_components/InstitutionalShell";

export default function InstitutionalLayout({ children }: { children: ReactNode }) {
  return <ProtectedBoundary><InstitutionalShell>{children}</InstitutionalShell></ProtectedBoundary>;
}
