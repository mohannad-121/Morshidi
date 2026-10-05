import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import {
  AuthProvider,
  useAuth,
} from "@/auth/auth-provider";
import { ProtectedBoundary } from "@/auth/protected-boundary";
import { FakeAuthClient, fakeSession } from "@/test/fake-auth-client";

const replace = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh }),
  useSearchParams: () => new URLSearchParams(),
}));

function Harness() {
  const auth = useAuth();
  return (
    <div>
      <span data-testid="status">{auth.status}</span>
      <span>{auth.user?.email}</span>
      <button onClick={() => void auth.signIn("student@example.com", "password")}>دخول</button>
      <button onClick={() => void auth.signOut()}>خروج</button>
    </div>
  );
}

test("starts loading and resolves a valid session as authenticated without rendering tokens", async () => {
  let resolveSession!: (value: Awaited<ReturnType<FakeAuthClient["auth"]["getSession"]>>) => void;
  const client = new FakeAuthClient(fakeSession());
  client.auth.getSession = () =>
    new Promise((resolve) => {
      resolveSession = resolve;
    });
  render(<AuthProvider client={client}><Harness /></AuthProvider>);
  expect(screen.getByTestId("status").textContent).toBe("loading");
  expect(document.body.textContent).not.toContain("current-access-token");
  resolveSession({ data: { session: fakeSession() }, error: null });
  await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
  expect(screen.getByText("student@example.com")).toBeTruthy();
  expect(document.body.textContent).not.toContain("private-refresh-token");
});

test("no session resolves as unauthenticated", async () => {
  render(<AuthProvider client={new FakeAuthClient()}><Harness /></AuthProvider>);
  await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));
});

test("email/password sign-in succeeds and failure remains safe", async () => {
  const success = new FakeAuthClient();
  const view = render(<AuthProvider client={success}><Harness /></AuthProvider>);
  await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));
  await userEvent.click(screen.getByRole("button", { name: "دخول" }));
  await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
  view.unmount();

  const failure = new FakeAuthClient();
  failure.signInError = true;
  render(<AuthProvider client={failure}><Harness /></AuthProvider>);
  await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));
  await userEvent.click(screen.getByRole("button", { name: "دخول" }));
  expect(screen.getByTestId("status").textContent).toBe("unauthenticated");
  expect(document.body.textContent).not.toContain("private");
});

test("sign-out clears authenticated and protected transient UI", async () => {
  const client = new FakeAuthClient(fakeSession());
  function ProtectedHarness() {
    const auth = useAuth();
    return (
      <ProtectedBoundary>
        <p>بيانات أكاديمية مؤقتة</p>
        <button onClick={() => void auth.signOut()}>خروج</button>
      </ProtectedBoundary>
    );
  }
  render(<AuthProvider client={client}><ProtectedHarness /></AuthProvider>);
  await screen.findByText("بيانات أكاديمية مؤقتة");
  fireEvent.click(screen.getByRole("button", { name: "خروج" }));
  await waitFor(() => expect(screen.queryByText("بيانات أكاديمية مؤقتة")).toBeNull());
  expect(client.signOutCalls).toBe(1);
  expect(replace).toHaveBeenCalledWith("/login");
});

test("protected content never renders while loading or unauthenticated", async () => {
  const client = new FakeAuthClient();
  render(
    <AuthProvider client={client}>
      <ProtectedBoundary><p>خاص</p></ProtectedBoundary>
    </AuthProvider>,
  );
  expect(screen.queryByText("خاص")).toBeNull();
  expect(screen.getByRole("status")).toBeTruthy();
  await waitFor(() => expect(screen.queryByText("خاص")).toBeNull());
});

test("mapUniversityLoginError returns expected Arabic translations for standard error codes", async () => {
  const { mapUniversityLoginError } = await import("@/auth/auth-provider");
  expect(mapUniversityLoginError("INVALID_CREDENTIALS")).toBe("تأكد من الرقم الجامعي وكلمة المرور.");
  expect(mapUniversityLoginError("RATE_LIMITED")).toBe("تمت محاولات تسجيل دخول كثيرة. حاول مرة أخرى بعد قليل.");
  expect(mapUniversityLoginError("UNIVERSITY_UNAVAILABLE")).toBe("خدمة الجامعة غير متاحة مؤقتًا. حاول مرة أخرى لاحقًا.");
  expect(mapUniversityLoginError("ACADEMIC_SYNC_UNAVAILABLE")).toBe("تعذر مزامنة بياناتك الأكاديمية حاليًا. حاول مرة أخرى لاحقًا.");
  expect(mapUniversityLoginError("IDENTITY_CONFLICT")).toBe("تعذر ربط حسابك الجامعي بحساب مرشدي. يرجى التواصل مع الدعم.");
  expect(mapUniversityLoginError("SESSION_ISSUANCE_FAILED")).toBe("تم التحقق من الحساب، لكن تعذر بدء جلسة مرشدي. حاول مرة أخرى.");
  expect(mapUniversityLoginError("UNKNOWN_CODE")).toBe("تعذر تسجيل الدخول. حاول مرة أخرى.");
  expect(mapUniversityLoginError()).toBe("تعذر تسجيل الدخول. حاول مرة أخرى.");
});

test("signInWithUniversity sends post to university-login and calls setSession", async () => {
  const client = new FakeAuthClient();
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      session: {
        access_token: "backend-issued-access-token",
        refresh_token: "backend-issued-refresh-token",
        token_type: "bearer",
        expires_in: 3600,
      },
      user: {
        id: "internal-shadow-user-uuid",
        email: "202310001@std.morshidi.edu.jo",
      },
    }),
  });
  global.fetch = fetchMock;

  function UniHarness() {
    const auth = useAuth();
    return (
      <div>
        <span data-testid="status">{auth.status}</span>
        <button
          onClick={async () => {
            await auth.signInWithUniversity("202310001", "student-secret-pass");
          }}
        >
          دخول جامعي
        </button>
      </div>
    );
  }

  render(
    <AuthProvider client={client}>
      <UniHarness />
    </AuthProvider>,
  );

  await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("unauthenticated"));
  await userEvent.click(screen.getByRole("button", { name: "دخول جامعي" }));

  await waitFor(() => expect(client.setSessionCalls).toBe(1));
  expect(client.lastSetSession).toEqual({
    access_token: "backend-issued-access-token",
    refresh_token: "backend-issued-refresh-token",
  });
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining("/api/v1/auth/university-login"),
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        student_id: "202310001",
        password: "student-secret-pass",
      }),
    }),
  );
  await waitFor(() => expect(screen.getByTestId("status").textContent).toBe("authenticated"));
});
