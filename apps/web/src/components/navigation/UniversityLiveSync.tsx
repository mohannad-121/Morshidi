"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "@/auth/auth-provider";
import { AuthenticatedApiError } from "@/lib/api/authenticated-client";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";

type Notice = { id: number; event_id: string; summary: string; created_at: string };
const RECONNECT_BASE_MS = 1_000;
const RECONNECT_MAX_MS = 30_000;

export function reconnectDelayMs(attempt: number, random: () => number = Math.random): number {
  const ceiling = Math.min(RECONNECT_MAX_MS, RECONNECT_BASE_MS * (2 ** Math.max(0, attempt)));
  return Math.round(ceiling * (0.5 + Math.min(1, Math.max(0, random())) * 0.5));
}

export function extractSseData(buffer: string): { data: string[]; rest: string } {
  const messages = buffer.split(/\r?\n\r?\n/);
  const rest = messages.pop() || "";
  const data = messages.flatMap((message) => {
    const lines = message.split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).replace(/^ /, ""));
    return lines.length ? [lines.join("\n")] : [];
  });
  return { data, rest };
}

function isNotice(value: unknown): value is Notice {
  if (!value || typeof value !== "object") return false;
  const notice = value as Partial<Notice>;
  return typeof notice.id === "number" && typeof notice.event_id === "string" &&
    typeof notice.summary === "string" && typeof notice.created_at === "string";
}

function isTerminalAuthError(error: unknown): boolean {
  return error instanceof AuthenticatedApiError && (error.status === 401 || error.status === 403);
}

const BellMark = () => <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const SyncMark = () => <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5M5.6 9A7 7 0 0 1 18 6l2 1M4 17l2 1a7 7 0 0 0 12.4-3" strokeLinecap="round" strokeLinejoin="round"/></svg>;

export function UniversityLiveSync() {
  const auth = useAuth();
  const api = useAuthenticatedApi();
  const [items, setItems] = useState<Notice[]>([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [connected, setConnected] = useState(false);
  const seenEventIds = useRef(new Set<string>());

  const update = useCallback((incoming: Notice[], announce: boolean) => {
    const valid = incoming.filter(isNotice);
    const byEvent = new Map(valid.map((notice) => [notice.event_id, notice]));
    const fresh = [...byEvent.values()].filter((notice) => !seenEventIds.current.has(notice.event_id));
    for (const notice of byEvent.values()) seenEventIds.current.add(notice.event_id);
    if (byEvent.size) {
      setItems((previous) => {
        const merged = new Map(previous.map((item) => [item.event_id, item]));
        for (const notice of byEvent.values()) merged.set(notice.event_id, notice);
        return [...merged.values()].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 30);
      });
    }
    if (announce && fresh.length) setUnread((count) => count + fresh.length);
    setLastSync(new Date());
    return fresh;
  }, []);

  const poll = useCallback(async (signal?: AbortSignal) => {
    const response = await api.request("/api/v1/me/university-notifications", { signal });
    if (!response.ok) throw new Error("sync unavailable");
    const notices = await response.json() as Notice[];
    if (!signal?.aborted) update(notices, false);
  }, [api, update]);

  useEffect(() => {
    if (!auth.isAuthenticated) return;
    const lifecycle = new AbortController();
    let streamController: AbortController | null = null;
    let retryTimer: number | null = null;
    let terminalAuthFailure = false;

    const reconcile = async () => {
      if (lifecycle.signal.aborted || terminalAuthFailure) return;
      try {
        await poll(lifecycle.signal);
      } catch (error) {
        if (isTerminalAuthError(error)) terminalAuthFailure = true;
      }
    };

    const waitForRetry = (delay: number) => new Promise<void>((resolve) => {
      if (lifecycle.signal.aborted) return resolve();
      const finish = () => {
        if (retryTimer !== null) window.clearTimeout(retryTimer);
        retryTimer = null;
        lifecycle.signal.removeEventListener("abort", finish);
        resolve();
      };
      retryTimer = window.setTimeout(finish, delay);
      lifecycle.signal.addEventListener("abort", finish, { once: true });
    });

    const runStream = async () => {
      await reconcile();
      let failedAttempts = 0;
      while (!lifecycle.signal.aborted && !terminalAuthFailure) {
        streamController = new AbortController();
        const abortStream = () => streamController?.abort();
        lifecycle.signal.addEventListener("abort", abortStream, { once: true });
        let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
        let receivedNotice = false;
        try {
          const response = await api.request("/api/v1/me/university-stream", { signal: streamController.signal });
          if (!response.ok || !response.body) throw new Error("stream unavailable");
          if (lifecycle.signal.aborted) break;
          setConnected(true);
          reader = response.body.getReader();
          const decoder = new TextDecoder("utf-8");
          let buffer = "";
          while (!lifecycle.signal.aborted) {
            const part = await reader.read();
            if (part.done) throw new Error("stream ended");
            if (lifecycle.signal.aborted) break;
            buffer += decoder.decode(part.value, { stream: true });
            const extracted = extractSseData(buffer);
            buffer = extracted.rest;
            for (const data of extracted.data) {
              try {
                const notice = JSON.parse(data) as unknown;
                if (!isNotice(notice)) continue;
                const fresh = update([notice], true);
                if (!fresh.length) continue;
                receivedNotice = true;
                window.dispatchEvent(new CustomEvent("morshidi:university-event", { detail: notice }));
              } catch { /* Ignore malformed data frames and keep the scoped stream open. */ }
            }
          }
        } catch (error) {
          if (!lifecycle.signal.aborted && isTerminalAuthError(error)) terminalAuthFailure = true;
        } finally {
          lifecycle.signal.removeEventListener("abort", abortStream);
          if (reader) {
            void reader.cancel().catch(() => undefined);
            reader.releaseLock();
          }
          streamController = null;
          if (!lifecycle.signal.aborted) setConnected(false);
        }
        if (lifecycle.signal.aborted || terminalAuthFailure) break;
        await reconcile();
        if (lifecycle.signal.aborted || terminalAuthFailure) break;
        failedAttempts = receivedNotice ? 0 : failedAttempts + 1;
        await waitForRetry(reconnectDelayMs(Math.max(0, failedAttempts - 1)));
      }
    };

    const refresh = () => { void reconcile(); };
    const onVisibility = () => { if (document.visibilityState === "visible") refresh(); };
    const fallback = window.setInterval(refresh, 60_000);
    document.addEventListener("visibilitychange", onVisibility);
    void runStream();
    return () => {
      lifecycle.abort();
      streamController?.abort();
      if (retryTimer !== null) window.clearTimeout(retryTimer);
      window.clearInterval(fallback);
      document.removeEventListener("visibilitychange", onVisibility);
    };

  }, [api, auth.isAuthenticated, poll, update]);

  const syncLabel = useMemo(() => lastSync ? lastSync.toLocaleTimeString("ar-JO", { hour: "2-digit", minute: "2-digit" }) : "—", [lastSync]);

  return <div className="notification-wrap">
    <button type="button" onClick={() => { setOpen((value) => !value); setUnread(0); }} aria-label={`الإشعارات${unread ? `، ${unread} جديدة` : ""}`} aria-expanded={open}
      className="icon-button relative focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent">
      <BellMark />
      {unread > 0 && <span className="absolute -left-1 -top-1 min-w-4 rounded-full bg-[#B8672E] px-1 text-[10px] text-white">{unread}</span>}
    </button>
    {open && <div className="absolute left-0 top-12 z-50 w-[min(22rem,90vw)] rounded-2xl border border-border/30 bg-surface-muted p-3 shadow-xl" dir="rtl">
      <div className="flex items-center justify-between border-b border-border/20 pb-2"><strong className="text-sm text-foreground">إشعارات الجامعة</strong><button type="button" onClick={() => void poll().catch(() => setConnected(false))} className="rounded-lg p-1 text-accent" aria-label="تحديث الإشعارات"><SyncMark /></button></div>
      <p className="py-2 text-[10px] text-tertiary">{connected ? "متصل" : "مزامنة دورية"} · آخر تحديث {syncLabel}</p>
      <ul className="max-h-72 space-y-2 overflow-y-auto">{items.length ? items.map(item => <li key={item.id} className="rounded-xl border border-border/15 bg-surface p-2 text-xs text-foreground">{item.summary}<time className="mt-1 block text-[10px] text-tertiary" dir="ltr">{new Date(item.created_at).toLocaleString("ar-JO")}</time></li>) : <li className="py-6 text-center text-xs text-tertiary">لا إشعارات جديدة</li>}</ul>
    </div>}
  </div>;
}
