import { AuthenticatedApiClient } from "@/lib/api/authenticated-client";

export interface VoiceSessionResponse {
  session_id: string;
  sdp_answer?: string | null;
  client_secret?: string | null;
  expires_at?: number;
  model: string;
  voice: string;
  max_duration_seconds: number;
  default_language: string;
  default_dialect: string;
  tools: string[];
  university_id: string;
  endpoint_type?: "live" | "realtime";
}

export interface VoiceSessionRequest {
  thread_id?: string;
  sdp_offer?: string;
}

export interface VoiceDelegateRequest {
  call_id: string;
  tool_name?: string;
  arguments?: string;
  thread_id?: string;
  user_transcript?: string;
  metadata?: Record<string, unknown>;
}

export interface VoiceDelegateResponse {
  call_id: string;
  tool_name: string;
  output: unknown;
  summary_text?: string;
  ok: boolean;
}

export interface VoiceTurnSyncRequest {
  thread_id: string;
  user_transcript: string;
  assistant_transcript: string;
  client_turn_id: string;
}

export interface VoiceTurnSyncResponse {
  synced: boolean;
  user_message_id?: string;
  assistant_message_id?: string;
  error?: string;
}

export interface VoiceStatusResponse {
  enabled: boolean;
  configured: boolean;
  model: string;
  voice: string;
  max_duration_seconds: number;
  remaining_daily_quota: number;
  daily_usage: number;
}

export class VoiceApiService {
  constructor(private readonly client: AuthenticatedApiClient) {}

  async getStatus(): Promise<VoiceStatusResponse> {
    const res = await this.client.request("/api/v1/me/voice/status", {
      method: "GET",
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch voice status (${res.status})`);
    }
    return res.json() as Promise<VoiceStatusResponse>;
  }

  async createSession(options?: string | VoiceSessionRequest): Promise<VoiceSessionResponse> {
    const payload = typeof options === "string" ? { thread_id: options } : (options || {});
    const res = await this.client.request("/api/v1/me/voice/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      let detail = "تعذر بدء الجلسة الصوتية";
      try {
        const body = (await res.json()) as { detail?: string };
        if (body.detail) detail = body.detail;
      } catch {
        // fallback
      }
      throw new Error(detail);
    }
    return res.json() as Promise<VoiceSessionResponse>;
  }

  async delegateTool(request: VoiceDelegateRequest): Promise<VoiceDelegateResponse> {
    const res = await this.client.request("/api/v1/me/voice/delegate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      throw new Error(`Tool delegation failed (${res.status})`);
    }
    return res.json() as Promise<VoiceDelegateResponse>;
  }

  async syncTurn(request: VoiceTurnSyncRequest): Promise<VoiceTurnSyncResponse> {
    const res = await this.client.request("/api/v1/me/voice/sync-turn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    if (!res.ok) {
      return { synced: false, error: `HTTP ${res.status}` };
    }
    return res.json() as Promise<VoiceTurnSyncResponse>;
  }

  async endSession(sessionId?: string, actualDurationSeconds?: number): Promise<void> {
    try {
      await this.client.request("/api/v1/me/voice/end-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          actual_duration_seconds: actualDurationSeconds,
        }),
      });
    } catch {
      // Best-effort cleanup
    }
  }
}

