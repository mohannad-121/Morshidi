import { getPublicApiBaseUrl } from "@/lib/config/public-env";

export type ApiErrorCode =
  | "UNAUTHENTICATED"
  | "FORBIDDEN"
  | "VALIDATION_ERROR"
  | "SERVER_ERROR"
  | "SERVICE_UNAVAILABLE"
  | "NETWORK_ERROR";

export class AuthenticatedApiError extends Error {
  constructor(
    public readonly code: ApiErrorCode,
    public readonly status: number | null,
  ) {
    super(code);
    this.name = "AuthenticatedApiError";
  }
}

export interface SessionTokenSource {
  getAccessToken(): Promise<string | null>;
  refreshAccessToken(): Promise<string | null>;
  invalidateSession(): Promise<void>;
}

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export class AuthenticatedApiClient {
  constructor(
    private readonly tokens: SessionTokenSource,
    private readonly fetcher: Fetcher = fetch,
    private readonly baseUrl: string = getPublicApiBaseUrl(),
  ) {}

  async request(path: `/api/v1/me/${string}`, init: RequestInit = {}): Promise<Response> {
    const token = await this.tokens.getAccessToken();
    if (!token) throw new AuthenticatedApiError("UNAUTHENTICATED", 401);

    let response = await this.send(path, init, token);
    if (response.status === 401) {
      const refreshedToken = await this.tokens.refreshAccessToken();
      if (refreshedToken && refreshedToken !== token) {
        response = await this.send(path, init, refreshedToken);
      }
      if (response.status === 401) {
        await this.tokens.invalidateSession();
        throw new AuthenticatedApiError("UNAUTHENTICATED", 401);
      }
    }

    if (response.status === 403) throw new AuthenticatedApiError("FORBIDDEN", 403);
    if (response.status === 422) {
      throw new AuthenticatedApiError("VALIDATION_ERROR", 422);
    }
    if (response.status === 503) {
      throw new AuthenticatedApiError("SERVICE_UNAVAILABLE", 503);
    }
    if (response.status >= 500) {
      throw new AuthenticatedApiError("SERVER_ERROR", response.status);
    }
    return response;
  }

  private async send(
    path: `/api/v1/me/${string}`,
    init: RequestInit,
    token: string,
  ): Promise<Response> {
    const headers = new Headers(init.headers);
    headers.set("Authorization", `Bearer ${token}`);
    try {
      return await this.fetcher(`${this.baseUrl}${path}`, { ...init, headers });
    } catch {
      throw new AuthenticatedApiError("NETWORK_ERROR", null);
    }
  }
}
