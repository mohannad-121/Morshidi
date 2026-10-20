import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const source = (path: string) => readFileSync(join(process.cwd(), path), "utf8");

describe("student UI typography", () => {
  it("self-hosts the scoped Inter and IBM Plex Sans Arabic font variables", () => {
    const studentLayout = source("src/app/(student)/layout.tsx");
    const rootLayout = source("src/app/layout.tsx");

    expect(studentLayout).toContain('variable: "--font-inter"');
    expect(studentLayout).toContain('weight: ["400", "500", "600", "700", "800", "900"]');
    expect(studentLayout).toContain('subsets: ["latin"]');
    expect(studentLayout).toContain('display: "swap"');
    expect(rootLayout).toContain('variable: "--font-plex-arabic"');
    expect(rootLayout).toContain('weight: ["400", "500", "600", "700"]');
    expect(rootLayout).toContain('subsets: ["arabic", "latin"]');
  });

  it("uses one student font stack with inherited controls and tabular numerals", () => {
    const css = source("src/app/globals.css");

    expect(css).toContain('--font-ui: -apple-system, BlinkMacSystemFont, "SF Pro Arabic", "SF Pro Display", var(--font-inter), var(--font-plex-arabic), "Segoe UI", Tahoma, sans-serif;');
    expect(css).toContain("font-family: var(--font-ui);");
    expect(css).toContain("font-variant-numeric: tabular-nums;");
    expect(css).toContain(".app-shell :where(button, input, select, textarea, summary, kbd, .badge, .font-mono) { font-family: inherit; }");
  });
});
