"use client";

import type { Session, User } from "@supabase/supabase-js";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { getPublicApiBaseUrl } from "@/lib/config/public-env";
import { createClient } from "@/lib/supabase/client";

type AuthStatus =
  | "loading"
  | "authenticated"
  | "unauthenticated"
  | "configuration_error";

interface AuthResult<T> {
  data: T;
  error: { message: string } | null;
}

export interface AuthClientPort {
  auth: {
    getSession(): Promise<AuthResult<{ session: Session | null }>>;
    refreshSession(): Promise<AuthResult<{ session: Session | null }>>;
    setSession(currentSession: {
      access_token: string;
      refresh_token: string;
    }): Promise<AuthResult<{ session: Session | null; user: User | null }>>;
    signInWithPassword(credentials: {
      email: string;
      password: string;
    }): Promise<AuthResult<{ session: Session | null; user: User | null }>>;
    signOut(options?: { scope?: "global" | "local" | "others" }): Promise<{
      error: { message: string } | null;
    }>;
    onAuthStateChange(
      callback: (event: string, session: Session | null) => void,
    ): { data: { subscription: { unsubscribe(): void } } };
  };
}

export interface AuthContextValue {
  status: AuthStatus;
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  signIn(email: string, password: string): Promise<{ ok: boolean }>;
  signInWithUniversity(
    studentId: string,
    password: string,
  ): Promise<{ ok: boolean; error?: string; errorCode?: string }>;
  signOut(): Promise<{ ok: boolean }>;
  getAccessToken(): Promise<string | null>;
  refreshAccessToken(): Promise<string | null>;
  invalidateSession(): Promise<void>;
}

export function mapUniversityLoginError(code?: string): string {
  switch (code) {
    case "INVALID_CREDENTIALS":
      return "تأكد من الرقم الجامعي وكلمة المرور.";
    case "RATE_LIMITED":
      return "تمت محاولات تسجيل دخول كثيرة. حاول مرة أخرى بعد قليل.";
    case "UNIVERSITY_UNAVAILABLE":
      return "خدمة الجامعة غير متاحة مؤقتًا. حاول مرة أخرى لاحقًا.";
    case "ACADEMIC_SYNC_UNAVAILABLE":
      return "تعذر مزامنة بياناتك الأكاديمية حاليًا. حاول مرة أخرى لاحقًا.";
    case "IDENTITY_CONFLICT":
      return "تعذر ربط حسابك الجامعي بحساب مرشدي. يرجى التواصل مع الدعم.";
    case "SESSION_ISSUANCE_FAILED":
      return "تم التحقق من الحساب، لكن تعذر بدء جلسة مرشدي. حاول مرة أخرى.";
    default:
      return "تعذر تسجيل الدخول. حاول مرة أخرى.";
  }
}

const AuthContext = createContext<AuthContextValue | null>(null);

function resolveSession(
  session: Session | null,
): Pick<AuthContextValue, "status" | "user"> {
  return session
    ? { status: "authenticated", user: session.user }
    : { status: "unauthenticated", user: null };
}

export function AuthProvider({
  children,
  client: injectedClient,
  fetcher: injectedFetcher,
}: {
  children: ReactNode;
  client?: AuthClientPort;
  fetcher?: typeof fetch;
}) {
  const [client] = useState<AuthClientPort | null>(() => {
    if (injectedClient) return injectedClient;
    try {
      return createClient() as unknown as AuthClientPort;
    } catch {
      return null;
    }
  });
  const [status, setStatus] = useState<AuthStatus>(
    client ? "loading" : "configuration_error",
  );
  const [user, setUser] = useState<User | null>(null);

  const applySession = useCallback((session: Session | null) => {
    const next = resolveSession(session);
    setStatus(next.status);
    setUser(next.user);
  }, []);

  useEffect(() => {
    if (!client) return;
    let active = true;
    void client.auth.getSession().then(({ data, error }) => {
      if (!active) return;
      if (error) applySession(null);
      else applySession(data.session);
    });
    const { data } = client.auth.onAuthStateChange((_event, session) => {
      if (active) applySession(session);
    });
    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, [applySession, client]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      if (!client) return { ok: false };
      const { data, error } = await client.auth.signInWithPassword({ email, password });
      if (error || !data.session) {
        applySession(null);
        return { ok: false };
      }
      applySession(data.session);
      return { ok: true };
    },
    [applySession, client],
  );

  const signInWithUniversity = useCallback(
    async (studentId: string, password: string) => {
      const cleanStudentId = studentId.trim();
      if (!cleanStudentId || !password) {
        return {
          ok: false,
          error: "تأكد من الرقم الجامعي وكلمة المرور.",
          errorCode: "INVALID_CREDENTIALS",
        };
      }

      if (!client) {
        return {
          ok: false,
          error: "تعذر تسجيل الدخول. حاول مرة أخرى.",
          errorCode: "SESSION_ISSUANCE_FAILED",
        };
      }

      try {
        let apiBaseUrl = "";
        try {
          apiBaseUrl = getPublicApiBaseUrl();
        } catch {
          apiBaseUrl = "";
        }
        const fetchFn = injectedFetcher || fetch;
        const response = await fetchFn(`${apiBaseUrl}/api/v1/auth/university-login`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept": "application/json",
          },
          body: JSON.stringify({
            student_id: cleanStudentId,
            password,
          }),
        });

        if (!response.ok) {
          let errorCode = "UNKNOWN_ERROR";
          try {
            const errorBody = await response.json();
            if (errorBody && typeof errorBody === "object") {
              errorCode =
                errorBody.error_code ||
                (errorBody.detail && errorBody.detail.code) ||
                errorBody.code ||
                errorBody.error ||
                (response.status === 401
                  ? "INVALID_CREDENTIALS"
                  : response.status === 429
                    ? "RATE_LIMITED"
                    : response.status === 409
                      ? "IDENTITY_CONFLICT"
                      : "UNKNOWN_ERROR");
            }
          } catch {
            errorCode =
              response.status === 401
                ? "INVALID_CREDENTIALS"
                : response.status === 429
                  ? "RATE_LIMITED"
                  : response.status === 409
                    ? "IDENTITY_CONFLICT"
                    : "UNKNOWN_ERROR";
          }
          return {
            ok: false,
            error: mapUniversityLoginError(errorCode),
            errorCode,
          };
        }

        const data = await response.json();
        const sessionPayload = data?.session;
        if (!sessionPayload?.access_token || !sessionPayload?.refresh_token) {
          return {
            ok: false,
            error: mapUniversityLoginError("SESSION_ISSUANCE_FAILED"),
            errorCode: "SESSION_ISSUANCE_FAILED",
          };
        }

        const { data: sessionData, error: sessionError } = await client.auth.setSession({
          access_token: sessionPayload.access_token,
          refresh_token: sessionPayload.refresh_token,
        });

        if (sessionError || !sessionData?.session) {
          applySession(null);
          return {
            ok: false,
            error: mapUniversityLoginError("SESSION_ISSUANCE_FAILED"),
            errorCode: "SESSION_ISSUANCE_FAILED",
          };
        }

        applySession(sessionData.session);
        return { ok: true };
      } catch {
        return {
          ok: false,
          error: "تعذر تسجيل الدخول. حاول مرة أخرى.",
          errorCode: "NETWORK_ERROR",
        };
      }
    },
    [applySession, client, injectedFetcher],
  );

  const signOut = useCallback(async () => {
    if (!client) return { ok: false };
    const { error } = await client.auth.signOut();
    if (error) return { ok: false };
    applySession(null);
    return { ok: true };
  }, [applySession, client]);

  const getAccessToken = useCallback(async () => {
    if (!client) return null;
    const { data, error } = await client.auth.getSession();
    if (error || !data.session) {
      applySession(null);
      return null;
    }
    applySession(data.session);
    return data.session.access_token;
  }, [applySession, client]);

  const refreshAccessToken = useCallback(async () => {
    if (!client) return null;
    const { data, error } = await client.auth.refreshSession();
    if (error || !data.session) {
      applySession(null);
      return null;
    }
    applySession(data.session);
    return data.session.access_token;
  }, [applySession, client]);

  const invalidateSession = useCallback(async () => {
    if (client) await client.auth.signOut({ scope: "local" });
    applySession(null);
  }, [applySession, client]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      isLoading: status === "loading",
      isAuthenticated: status === "authenticated",
      signIn,
      signInWithUniversity,
      signOut,
      getAccessToken,
      refreshAccessToken,
      invalidateSession,
    }),
    [
      getAccessToken,
      invalidateSession,
      refreshAccessToken,
      signIn,
      signInWithUniversity,
      signOut,
      status,
      user,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
