import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
const { request, auth } = vi.hoisted(() => ({ request: vi.fn(), auth: { isAuthenticated: true } }));
vi.mock('@/auth/auth-provider', () => ({ useAuth: () => auth }));
vi.mock('@/lib/api/use-authenticated-api', () => ({ useAuthenticatedApi: () => client }));
const client = { request };
import { UniversityLiveSync } from './UniversityLiveSync';
afterEach(() => { vi.useRealTimers(); vi.clearAllMocks(); auth.isAuthenticated = true; });
describe('university notifications', () => {
  it('loads notifications and exposes the expanded state', async () => {
    request.mockImplementation((path: string) => path.endsWith('notifications')
      ? Promise.resolve({ ok: true, json: async () => [{ id: 1, event_id: 'event', summary: 'University notice', created_at: '2026-01-01T00:00:00Z' }] })
      : Promise.reject(new Error('offline')));
    render(<UniversityLiveSync />);
    const bell = screen.getByRole('button', { name: 'الإشعارات' });
    expect(bell.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(bell);
    expect(bell.getAttribute('aria-expanded')).toBe('true');
    expect(await screen.findByText('University notice')).toBeTruthy();
  });
  it('aborts the stream and stops the single polling interval on unmount', async () => {
    vi.useFakeTimers();
    let streamSignal: AbortSignal | undefined;
    request.mockImplementation((path: string, init: RequestInit) => {
      if (path.endsWith('notifications')) return Promise.resolve({ ok: true, json: async () => [] });
      streamSignal = init.signal as AbortSignal;
      return Promise.resolve({ ok: true, body: new ReadableStream({ start(controller) { controller.close(); } }) });
    });
    const view = render(<UniversityLiveSync />);
    await act(async () => { await Promise.resolve(); await Promise.resolve(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(request.mock.calls.filter(([path]) => path.endsWith('notifications'))).toHaveLength(2);
    view.unmount();
    expect(streamSignal?.aborted).toBe(true);
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000); });
    expect(request.mock.calls.filter(([path]) => path.endsWith('notifications'))).toHaveLength(2);
  });
  it('does not request notifications without authentication', () => {
    auth.isAuthenticated = false;
    render(<UniversityLiveSync />);
    expect(request).not.toHaveBeenCalled();
  });
});
