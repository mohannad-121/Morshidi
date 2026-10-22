import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuthenticatedApiError } from '@/lib/api/authenticated-client';

const { request, auth } = vi.hoisted(() => ({ request: vi.fn(), auth: { isAuthenticated: true } }));
vi.mock('@/auth/auth-provider', () => ({ useAuth: () => auth }));
vi.mock('@/lib/api/use-authenticated-api', () => ({ useAuthenticatedApi: () => client }));
const client = { request };

import { extractSseData, reconnectDelayMs, UniversityLiveSync } from './UniversityLiveSync';

const notice = {
  id: 7,
  event_id: 'event-7',
  summary: 'University notice',
  created_at: '2026-01-01T00:00:00Z',
};

function notifications(values: typeof notice[] = []) {
  return Promise.resolve({ ok: true, json: async () => values });
}

function openStream() {
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const stream = new ReadableStream<Uint8Array>({ start(value) { controller = value; } });
  return { stream, controller };
}

function frame(value: typeof notice) {
  return new TextEncoder().encode(`data: ${JSON.stringify(value)}\n\n`);
}

async function flush() {
  await act(async () => { await Promise.resolve(); await Promise.resolve(); await Promise.resolve(); });
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.clearAllMocks();
  auth.isAuthenticated = true;
});

describe('university notifications', () => {
  it('loads notifications before opening one scoped SSE connection', async () => {
    const live = openStream();
    request.mockImplementation((path: string) => path.endsWith('notifications')
      ? notifications([notice])
      : Promise.resolve({ ok: true, body: live.stream }));
    render(<UniversityLiveSync />);
    const bell = screen.getByRole('button', { name: 'الإشعارات' });
    fireEvent.click(bell);
    expect(await screen.findByText('University notice')).toBeTruthy();
    expect(request.mock.calls.filter(([path]) => path.endsWith('university-stream'))).toHaveLength(1);
  });

  it('reconnects after an unexpected clean stream closure', async () => {
    vi.useFakeTimers();
    vi.spyOn(Math, 'random').mockReturnValue(0);
    const replacement = openStream();
    let streams = 0;
    request.mockImplementation((path: string) => {
      if (path.endsWith('notifications')) return notifications();
      streams += 1;
      if (streams === 1) return Promise.resolve({
        ok: true,
        body: new ReadableStream<Uint8Array>({ start(controller) { controller.close(); } }),
      });
      return Promise.resolve({ ok: true, body: replacement.stream });
    });
    render(<UniversityLiveSync />);
    await flush();
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    expect(streams).toBe(2);
    expect(request.mock.calls.filter(([path]) => path.endsWith('notifications')).length).toBeGreaterThanOrEqual(2);
  });

  it('reconnects after a recoverable network failure', async () => {
    vi.useFakeTimers();
    vi.spyOn(Math, 'random').mockReturnValue(0);
    const replacement = openStream();
    let streams = 0;
    request.mockImplementation((path: string) => {
      if (path.endsWith('notifications')) return notifications();
      streams += 1;
      return streams === 1
        ? Promise.reject(new AuthenticatedApiError('NETWORK_ERROR', null))
        : Promise.resolve({ ok: true, body: replacement.stream });
    });
    render(<UniversityLiveSync />);
    await flush();
    await act(async () => { await vi.advanceTimersByTimeAsync(500); });
    expect(streams).toBe(2);
  });

  it('does not retry a terminal authentication failure', async () => {
    vi.useFakeTimers();
    request.mockImplementation((path: string) => path.endsWith('notifications')
      ? notifications()
      : Promise.reject(new AuthenticatedApiError('UNAUTHENTICATED', 401)));
    render(<UniversityLiveSync />);
    await flush();
    await act(async () => { await vi.advanceTimersByTimeAsync(180_000); });
    expect(request.mock.calls.filter(([path]) => path.endsWith('university-stream'))).toHaveLength(1);
    expect(request.mock.calls.filter(([path]) => path.endsWith('notifications'))).toHaveLength(1);
  });

  it('aborts the stream and stops polling on unmount', async () => {
    vi.useFakeTimers();
    const live = openStream();
    let streamSignal: AbortSignal | undefined;
    request.mockImplementation((path: string, init: RequestInit) => {
      if (path.endsWith('notifications')) return notifications();
      streamSignal = init.signal as AbortSignal;
      return Promise.resolve({ ok: true, body: live.stream });
    });
    const view = render(<UniversityLiveSync />);
    await flush();
    view.unmount();
    expect(streamSignal?.aborted).toBe(true);
    await act(async () => { await vi.advanceTimersByTimeAsync(120_000); });
    expect(request.mock.calls.filter(([path]) => path.endsWith('notifications'))).toHaveLength(1);
  });

  it('cleans up the active stream on logout', async () => {
    const live = openStream();
    let streamSignal: AbortSignal | undefined;
    request.mockImplementation((path: string, init: RequestInit) => {
      if (path.endsWith('notifications')) return notifications();
      streamSignal = init.signal as AbortSignal;
      return Promise.resolve({ ok: true, body: live.stream });
    });
    const view = render(<UniversityLiveSync />);
    await flush();
    auth.isAuthenticated = false;
    view.rerender(<UniversityLiveSync />);
    expect(streamSignal?.aborted).toBe(true);
  });

  it('deduplicates repeated SSE frames and increments unread once', async () => {
    const live = openStream();
    request.mockImplementation((path: string) => path.endsWith('notifications')
      ? notifications()
      : Promise.resolve({ ok: true, body: live.stream }));
    render(<UniversityLiveSync />);
    await flush();
    await act(async () => { live.controller.enqueue(frame(notice)); live.controller.enqueue(frame(notice)); });
    expect(await screen.findByText('1')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /الإشعارات/ }));
    expect(screen.getAllByText('University notice')).toHaveLength(1);
  });

  it('reconciles an SSE notice with polling without duplicating it or unread state', async () => {
    vi.useFakeTimers();
    const live = openStream();
    let polls = 0;
    request.mockImplementation((path: string) => {
      if (path.endsWith('notifications')) return notifications(polls++ === 0 ? [] : [notice]);
      return Promise.resolve({ ok: true, body: live.stream });
    });
    render(<UniversityLiveSync />);
    await flush();
    await act(async () => { live.controller.enqueue(frame(notice)); });
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(screen.getByText('1')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /الإشعارات/ }));
    expect(screen.getAllByText('University notice')).toHaveLength(1);
  });

  it('establishes fresh polling and streaming after a browser-style remount', async () => {
    const streams = [openStream(), openStream()];
    let streamIndex = 0;
    request.mockImplementation((path: string) => path.endsWith('notifications')
      ? notifications([notice])
      : Promise.resolve({ ok: true, body: streams[streamIndex++].stream }));
    const first = render(<UniversityLiveSync />);
    await flush();
    first.unmount();
    render(<UniversityLiveSync />);
    await waitFor(() => expect(request.mock.calls.filter(([path]) => path.endsWith('university-stream'))).toHaveLength(2));
    expect(request.mock.calls.filter(([path]) => path.endsWith('notifications'))).toHaveLength(2);
  });

  it('does not request notifications without authentication', () => {
    auth.isAuthenticated = false;
    render(<UniversityLiveSync />);
    expect(request).not.toHaveBeenCalled();
  });
});

describe('SSE helpers', () => {
  it('parses CRLF, multi-line data, and ignores heartbeat comments', () => {
    expect(extractSseData(': keep-alive\r\n\r\ndata: one\r\ndata: two\r\n\r\npartial')).toEqual({
      data: ['one\ntwo'],
      rest: 'partial',
    });
  });

  it('uses bounded exponential backoff with bounded jitter', () => {
    expect(reconnectDelayMs(0, () => 0)).toBe(500);
    expect(reconnectDelayMs(1, () => 1)).toBe(2_000);
    expect(reconnectDelayMs(20, () => 1)).toBe(30_000);
    expect(reconnectDelayMs(20, () => 0)).toBe(15_000);
  });
});
