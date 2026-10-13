import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import Home from "./page";

let mockAuth = {
  isAuthenticated: false,
  user: null as null | { email: string; user_metadata: { full_name: string } },
};

vi.mock("@/auth/auth-provider", () => ({
  useAuth: () => mockAuth,
}));

describe("Morshidi homepage", () => {
  beforeEach(() => {
    mockAuth = { isAuthenticated: false, user: null };
  });

  test("presents the complete academic decision narrative to a visitor", () => {
    const { container } = render(<Home />);

    expect(screen.getByRole("heading", { name: /اعرف طريقك الأكاديمي/ })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "طبقة ذكاء بينك وبين تعقيد خطتك الدراسية." })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "مسار واحد متصل. بلا قفزات غامضة." })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "الذكاء الاصطناعي يشرح. القواعد الأكاديمية تقرّر." })).toBeTruthy();
    expect(container.querySelector("#the-path")).toBeTruthy();
    expect(container.querySelector("#the-plan")).toBeTruthy();
    expect(container.querySelector("#insights")).toBeTruthy();

    const entryLinks = screen.getAllByRole("link", { name: /ابدأ من سجلك الجامعي/ });
    expect(entryLinks).toHaveLength(2);
    entryLinks.forEach((link) => expect(link.getAttribute("href")).toBe("/login"));
  });

  test("returns an authenticated student to their academic center", () => {
    mockAuth = {
      isAuthenticated: true,
      user: { email: "student@example.edu", user_metadata: { full_name: "ليان أحمد" } },
    };

    render(<Home />);

    expect(screen.getByText("مرحباً بعودتك، ليان أحمد")).toBeTruthy();
    const centerLinks = screen.getAllByRole("link", { name: /افتح مركزك الأكاديمي/ });
    expect(centerLinks).toHaveLength(2);
    centerLinks.forEach((link) => expect(link.getAttribute("href")).toBe("/student"));
  });
});
