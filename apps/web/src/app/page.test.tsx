import { readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import Home from "./page";

let mockAuth = {
  isAuthenticated: false,
  user: null as null | { email: string },
};

vi.mock("@/auth/auth-provider", () => ({
  useAuth: () => mockAuth,
}));

const authoredFork = readFileSync(
  join(process.cwd(), "public/landing-pages/morshidi-sketchbook.html"),
  "utf8",
);

describe("Morshidi Academic Sketchbook homepage", () => {
  beforeEach(() => {
    mockAuth = { isAuthenticated: false, user: null };
    window.location.hash = "";
  });

  test("hosts the dedicated authored-source fork", () => {
    render(<Home />);
    const frame = screen.getByTitle("دفتر مرشدي الأكاديمي التفاعلي");
    expect(frame.getAttribute("src")).toBe(
      "/landing-pages/morshidi-sketchbook.html?destination=%2Flogin",
    );
    expect(frame.getAttribute("sandbox")).toContain("allow-scripts");
  });

  test("preserves the authored interaction engine and nine Morshidi plates", () => {
    expect(authoredFork).toContain("const N=18");
    expect(authoredFork).toContain("const SPAN=0.449");
    expect(authoredFork).toContain("const BETA=0.60");
    expect(authoredFork).toContain("function buildCurl");
    expect(authoredFork).toContain("function applyTurn");
    expect(authoredFork).toContain("function syncZoomLayer");
    expect(authoredFork).toContain("function placeLoupe");
    expect(authoredFork).toContain("function startIntro");
    expect(authoredFork).toContain("addEventListener('keydown'");
    expect(authoredFork).toContain("prefers-reduced-motion");
    expect(authoredFork.match(/file:'\d{2}-[^']+\.webp'/g)).toHaveLength(9);
    expect(authoredFork).not.toContain("marina-bay-sands.png");
  });

  test("selects the authenticated destination without changing the document engine", () => {
    mockAuth = {
      isAuthenticated: true,
      user: { email: "student@example.edu" },
    };
    render(<Home />);
    expect(
      screen
        .getByTitle("دفتر مرشدي الأكاديمي التفاعلي")
        .getAttribute("src"),
    ).toBe("/landing-pages/morshidi-sketchbook.html?destination=%2Fstudent");
  });
});
