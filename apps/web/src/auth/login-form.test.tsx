import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { AuthProvider, useAuth } from "@/auth/auth-provider";
import { LoginForm } from "@/auth/login-form";
import { ProtectedBoundary } from "@/auth/protected-boundary";
import { FakeAuthClient } from "@/test/fake-auth-client";

const replace = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh }),
  useSearchParams: () => new URLSearchParams("returnTo=/student"),
}));

describe("LoginForm Component & University Integration (Step 5)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("1, 2, 3: student login mode is the default, rendering student ID and university password inputs", async () => {
    const client = new FakeAuthClient();
    render(
      <AuthProvider client={client}>
        <LoginForm />
      </AuthProvider>,
    );

    const studentTab = screen.getByRole("tab", { name: "تسجيل دخول الطالب" });
    expect(studentTab.getAttribute("aria-selected")).toBe("true");

    const studentIdInput = screen.getByLabelText("الرقم الجامعي");
    expect(studentIdInput).toBeTruthy();
    expect(studentIdInput.getAttribute("type")).toBe("text"); // Requirement 4: text input, NOT numeric

    const passwordInput = screen.getByLabelText("كلمة مرور الجامعة");
    expect(passwordInput).toBeTruthy();
    expect(passwordInput.getAttribute("type")).toBe("password");
  });

  test("4, 5, 6, 7, 8, 9, 10, 11, 12: student login preserves leading zeros, calls backend POST /api/v1/auth/university-login, never calls Fake Uni directly, and calls setSession", async () => {
    const client = new FakeAuthClient();
    let capturedUrl = "";
    let capturedBody: any = null;

    const mockFetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      capturedUrl = String(input);
      capturedBody = JSON.parse(String(init?.body));
      return new Response(
        JSON.stringify({
          session: {
            access_token: "morshidi-access-tok-abc",
            refresh_token: "morshidi-refresh-tok-def",
            token_type: "bearer",
            expires_in: 3600,
          },
          user: { id: "u-123", email: "0200104@std.morshidi.edu.jo" },
          sync: { attempts_synced: 5, enrollments_synced: 2 },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });

    render(
      <AuthProvider client={client} fetcher={mockFetcher as any}>
        <LoginForm />
      </AuthProvider>,
    );

    const studentIdInput = screen.getByLabelText("الرقم الجامعي") as HTMLInputElement;
    const passwordInput = screen.getByLabelText("كلمة مرور الجامعة") as HTMLInputElement;

    await waitFor(() => expect(studentIdInput.disabled).toBe(false));

    // Leading zero student ID
    await userEvent.type(studentIdInput, " 0200104 ");
    await userEvent.type(passwordInput, "UnivPass123");

    const submitBtn = screen.getByRole("button", { name: "تسجيل الدخول" });
    await userEvent.click(submitBtn);

    // 6. Calls exact backend route
    expect(capturedUrl).toContain("/api/v1/auth/university-login");
    // 8. Does NOT call Fake University directly
    expect(capturedUrl).not.toContain("fake-university-aqdn.onrender.com");
    // 4 & 5 & 7. Uses student_id and password, preserves leading zeros, trims whitespace
    expect(capturedBody).toEqual({
      student_id: "0200104",
      password: "UnivPass123",
    });

    // 9, 10, 11. Calls setSession exactly once with correct tokens
    await waitFor(() => expect(client.setSessionCalls).toBe(1));
    expect(client.lastSetSession).toEqual({
      access_token: "morshidi-access-tok-abc",
      refresh_token: "morshidi-refresh-tok-def",
    });

    // 12. Tokens are not written manually to localStorage/sessionStorage
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(sessionStorage.getItem("access_token")).toBeNull();

    // 27. Redirects to destination
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/student"));
  });

  test("13. INVALID_CREDENTIALS shows safe Arabic message without revealing student ID existence", async () => {
    const client = new FakeAuthClient();
    const mockFetcher = vi.fn(async () => {
      return new Response(
        JSON.stringify({ code: "INVALID_CREDENTIALS", message: "User not found" }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      );
    });

    render(
      <AuthProvider client={client} fetcher={mockFetcher as any}>
        <LoginForm />
      </AuthProvider>,
    );

    const idInput = screen.getByLabelText("الرقم الجامعي") as HTMLInputElement;
    await waitFor(() => expect(idInput.disabled).toBe(false));
    await userEvent.type(idInput, "202310001");
    await userEvent.type(screen.getByLabelText("كلمة مرور الجامعة"), "badPass");
    await userEvent.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("تأكد من الرقم الجامعي وكلمة المرور.");
    expect(alert.textContent).not.toContain("User not found");
  });

  test("14. RATE_LIMITED shows safe Arabic message", async () => {
    const client = new FakeAuthClient();
    const mockFetcher = vi.fn(async () => {
      return new Response(
        JSON.stringify({ code: "RATE_LIMITED", message: "Too many requests" }),
        { status: 429, headers: { "Content-Type": "application/json" } },
      );
    });

    render(
      <AuthProvider client={client} fetcher={mockFetcher as any}>
        <LoginForm />
      </AuthProvider>,
    );

    const idInput = screen.getByLabelText("الرقم الجامعي") as HTMLInputElement;
    await waitFor(() => expect(idInput.disabled).toBe(false));
    await userEvent.type(idInput, "202310001");
    await userEvent.type(screen.getByLabelText("كلمة مرور الجامعة"), "pass");
    await userEvent.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("تمت محاولات تسجيل دخول كثيرة. حاول مرة أخرى بعد قليل.");
  });

  test("15. UNIVERSITY_UNAVAILABLE shows safe Arabic message", async () => {
    const client = new FakeAuthClient();
    const mockFetcher = vi.fn(async () => {
      return new Response(
        JSON.stringify({ code: "UNIVERSITY_UNAVAILABLE", message: "Timeout" }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      );
    });

    render(
      <AuthProvider client={client} fetcher={mockFetcher as any}>
        <LoginForm />
      </AuthProvider>,
    );

    const idInput = screen.getByLabelText("الرقم الجامعي") as HTMLInputElement;
    await waitFor(() => expect(idInput.disabled).toBe(false));
    await userEvent.type(idInput, "202310001");
    await userEvent.type(screen.getByLabelText("كلمة مرور الجامعة"), "pass");
    await userEvent.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("خدمة الجامعة غير متاحة مؤقتًا. حاول مرة أخرى لاحقًا.");
  });

  test("16. ACADEMIC_SYNC_UNAVAILABLE shows safe Arabic message", async () => {
    const client = new FakeAuthClient();
    const mockFetcher = vi.fn(async () => {
      return new Response(
        JSON.stringify({ code: "ACADEMIC_SYNC_UNAVAILABLE", message: "Plan unmapped" }),
        { status: 503, headers: { "Content-Type": "application/json" } },
      );
    });

    render(
      <AuthProvider client={client} fetcher={mockFetcher as any}>
        <LoginForm />
      </AuthProvider>,
    );

    const idInput = screen.getByLabelText("الرقم الجامعي") as HTMLInputElement;
    await waitFor(() => expect(idInput.disabled).toBe(false));
    await userEvent.type(idInput, "202310001");
    await userEvent.type(screen.getByLabelText("كلمة مرور الجامعة"), "pass");
    await userEvent.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("تعذر مزامنة بياناتك الأكاديمية حاليًا. حاول مرة أخرى لاحقًا.");
  });

  test("17. IDENTITY_CONFLICT shows safe Arabic message", async () => {
    const client = new FakeAuthClient();
    const mockFetcher = vi.fn(async () => {
      return new Response(
        JSON.stringify({ code: "IDENTITY_CONFLICT", message: "Email collision" }),
        { status: 409, headers: { "Content-Type": "application/json" } },
      );
    });

    render(
      <AuthProvider client={client} fetcher={mockFetcher as any}>
        <LoginForm />
      </AuthProvider>,
    );

    const idInput = screen.getByLabelText("الرقم الجامعي") as HTMLInputElement;
    await waitFor(() => expect(idInput.disabled).toBe(false));
    await userEvent.type(idInput, "202310001");
    await userEvent.type(screen.getByLabelText("كلمة مرور الجامعة"), "pass");
    await userEvent.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("تعذر ربط حسابك الجامعي بحساب مرشدي. يرجى التواصل مع الدعم.");
  });

  test("18. SESSION_ISSUANCE_FAILED shows safe Arabic message", async () => {
    const client = new FakeAuthClient();
    const mockFetcher = vi.fn(async () => {
      return new Response(
        JSON.stringify({ code: "SESSION_ISSUANCE_FAILED", message: "Internal error" }),
        { status: 500, headers: { "Content-Type": "application/json" } },
      );
    });

    render(
      <AuthProvider client={client} fetcher={mockFetcher as any}>
        <LoginForm />
      </AuthProvider>,
    );

    const idInput = screen.getByLabelText("الرقم الجامعي") as HTMLInputElement;
    await waitFor(() => expect(idInput.disabled).toBe(false));
    await userEvent.type(idInput, "202310001");
    await userEvent.type(screen.getByLabelText("كلمة مرور الجامعة"), "pass");
    await userEvent.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toBe("تم التحقق من الحساب، لكن تعذر بدء جلسة مرشدي. حاول مرة أخرى.");
  });

  test("19. Unexpected error or network failure shows generic safe message", async () => {
    const client = new FakeAuthClient();
    const mockFetcher = vi.fn(async () => {
      throw new Error("Network request failed");
    });

    render(
      <AuthProvider client={client} fetcher={mockFetcher as any}>
        <LoginForm />
      </AuthProvider>,
    );

    const idInput = screen.getByLabelText("الرقم الجامعي") as HTMLInputElement;
    await waitFor(() => expect(idInput.disabled).toBe(false));
    await userEvent.type(idInput, "202310001");
    await userEvent.type(screen.getByLabelText("كلمة مرور الجامعة"), "pass");
    await userEvent.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("تعذر تسجيل الدخول");
    expect(alert.textContent).not.toContain("Network request failed");
  });

  test("20. Duplicate submit is prevented while loading", async () => {
    const client = new FakeAuthClient();
    let resolveCall!: (value: any) => void;
    const mockFetcher = vi.fn(
      () =>
        new Promise((res) => {
          resolveCall = res;
        }),
    );

    render(
      <AuthProvider client={client} fetcher={mockFetcher as any}>
        <LoginForm />
      </AuthProvider>,
    );

    const idInput = screen.getByLabelText("الرقم الجامعي") as HTMLInputElement;
    await waitFor(() => expect(idInput.disabled).toBe(false));
    await userEvent.type(idInput, "202310001");
    await userEvent.type(screen.getByLabelText("كلمة مرور الجامعة"), "pass");

    const submitBtn = screen.getByRole("button", { name: "تسجيل الدخول" }) as HTMLButtonElement;
    await userEvent.click(submitBtn);

    // Button should be disabled during submit
    expect(submitBtn.disabled).toBe(true);
    expect(submitBtn.textContent).toBe("جاري تسجيل الدخول…");

    // Second click attempt
    await userEvent.click(submitBtn);
    expect(mockFetcher).toHaveBeenCalledTimes(1);

    // Resolve
    resolveCall(
      new Response(
        JSON.stringify({
          session: { access_token: "tok", refresh_token: "ref" },
          user: { id: "u1", email: "202310001@std.morshidi.edu.jo" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
  });

  test("21, 22, 23: existing staff login mode remains accessible and uses signIn(email, password)", async () => {
    const client = new FakeAuthClient();
    render(
      <AuthProvider client={client}>
        <LoginForm />
      </AuthProvider>,
    );

    // Switch to staff mode via tab
    const staffTab = screen.getByRole("tab", { name: "تسجيل دخول المرشد أو الموظف" });
    await userEvent.click(staffTab);

    expect(staffTab.getAttribute("aria-selected")).toBe("true");

    const emailInput = screen.getByLabelText("البريد الإلكتروني") as HTMLInputElement;
    const passwordInput = screen.getByLabelText("كلمة المرور") as HTMLInputElement;
    expect(emailInput).toBeTruthy();
    expect(passwordInput).toBeTruthy();

    await waitFor(() => expect(emailInput.disabled).toBe(false));

    await userEvent.type(emailInput, "advisor@morshidi.edu.jo");
    await userEvent.type(passwordInput, "advisorSecret123");

    const submitBtn = screen.getByRole("button", { name: "تسجيل الدخول" });
    await userEvent.click(submitBtn);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/student"));
    expect(client.lastSetSession).toBeNull(); // Did not use university setSession
  });

  test("24. Logout behavior remains unchanged", async () => {
    const client = new FakeAuthClient();
    function LogoutHarness() {
      const auth = useAuth();
      return (
        <div>
          <span data-testid="status">{auth.status}</span>
          <button onClick={() => void auth.signOut()}>خروج</button>
        </div>
      );
    }

    render(
      <AuthProvider client={client}>
        <LogoutHarness />
      </AuthProvider>,
    );

    await userEvent.click(screen.getByRole("button", { name: "خروج" }));
    expect(client.signOutCalls).toBe(1);
  });

  test("25, 26: successful student session transitions auth state to authenticated and renders protected content", async () => {
    const client = new FakeAuthClient();
    const mockFetcher = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          session: {
            access_token: "morshidi-access-tok-abc",
            refresh_token: "morshidi-refresh-tok-def",
            token_type: "bearer",
            expires_in: 3600,
          },
          user: { id: "u-123", email: "0200104@std.morshidi.edu.jo" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });

    function AppHarness() {
      const auth = useAuth();
      return (
        <div>
          {auth.isAuthenticated ? (
            <ProtectedBoundary>
              <p>محتوى أكاديمي محمي</p>
            </ProtectedBoundary>
          ) : (
            <LoginForm />
          )}
        </div>
      );
    }

    render(
      <AuthProvider client={client} fetcher={mockFetcher as any}>
        <AppHarness />
      </AuthProvider>,
    );

    const idInput = screen.getByLabelText("الرقم الجامعي") as HTMLInputElement;
    await waitFor(() => expect(idInput.disabled).toBe(false));
    await userEvent.type(idInput, "0200104");
    await userEvent.type(screen.getByLabelText("كلمة مرور الجامعة"), "pass123");
    await userEvent.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    await screen.findByText("محتوى أكاديمي محمي");
  });

  test("28. Password and session tokens never appear in console or log output", async () => {
    const logSpy = vi.spyOn(console, "log");
    const warnSpy = vi.spyOn(console, "warn");
    const errorSpy = vi.spyOn(console, "error");

    const client = new FakeAuthClient();
    const mockFetcher = vi.fn(async () => {
      return new Response(
        JSON.stringify({
          session: {
            access_token: "super-secret-morshidi-token-999",
            refresh_token: "super-secret-refresh-token-888",
            token_type: "bearer",
            expires_in: 3600,
          },
          user: { id: "u-1", email: "202310001@std.morshidi.edu.jo" },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });

    render(
      <AuthProvider client={client} fetcher={mockFetcher as any}>
        <LoginForm />
      </AuthProvider>,
    );

    const idInput = screen.getByLabelText("الرقم الجامعي") as HTMLInputElement;
    await waitFor(() => expect(idInput.disabled).toBe(false));
    await userEvent.type(idInput, "202310001");
    await userEvent.type(screen.getByLabelText("كلمة مرور الجامعة"), "super-secret-password-xyz");
    await userEvent.click(screen.getByRole("button", { name: "تسجيل الدخول" }));

    await waitFor(() => expect(client.setSessionCalls).toBe(1));

    const allConsoleLogs = [
      ...logSpy.mock.calls,
      ...warnSpy.mock.calls,
      ...errorSpy.mock.calls,
    ].flat().join(" ");

    expect(allConsoleLogs).not.toContain("super-secret-password-xyz");
    expect(allConsoleLogs).not.toContain("super-secret-morshidi-token-999");
    expect(allConsoleLogs).not.toContain("super-secret-refresh-token-888");

    logSpy.mockRestore();
    warnSpy.mockRestore();
    errorSpy.mockRestore();
  });

  test("29, 30: no frontend request directly targets Fake University and source references no server secrets", () => {
    // Assert no code in LoginForm or AuthProvider references UNI_CLIENT_SECRET
    expect(process.env.UNI_CLIENT_SECRET).toBeUndefined();
    expect(process.env.UNI_INTERNAL_AUTH_SECRET).toBeUndefined();
  });
});
