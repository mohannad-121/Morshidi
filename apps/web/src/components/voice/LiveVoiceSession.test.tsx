import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { LiveVoiceSession } from "./LiveVoiceSession";
import { LiveVoiceButton } from "./LiveVoiceButton";

const mockGetAccessToken = vi.fn().mockResolvedValue("mock-token");
const mockRefreshAccessToken = vi.fn().mockResolvedValue("mock-token");
const mockInvalidateSession = vi.fn();

vi.mock("@/auth/auth-provider", () => ({
  useAuth: () => ({
    getAccessToken: mockGetAccessToken,
    refreshAccessToken: mockRefreshAccessToken,
    invalidateSession: mockInvalidateSession,
  }),
}));

vi.mock("next/image", () => ({
  __esModule: true,
  default: (props: any) => <img {...props} />,
}));

vi.mock("./VoiceVisualizer", () => ({
  VoiceVisualizer: () => <div data-testid="mock-visualizer" />,
}));

vi.mock("@/lib/voice/webrtc-voice-session", async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    WebRTCVoiceSession: class MockWebRTCVoiceSession {
      public callbacks: any;
      private muted = false;
      constructor(api: any, callbacks: any) {
        this.callbacks = callbacks;
      }
      start() {
        this.callbacks?.onStatusChange?.("listening");
        return Promise.resolve();
      }
      switchDialect(d: any) {
        this.callbacks?.onDialectChange?.(d);
      }
      toggleMute() {
        this.muted = !this.muted;
        return this.muted;
      }
      stop() {
        this.callbacks?.onStatusChange?.("ended");
      }
    },
  };
});

beforeEach(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
});

afterEach(() => {
  cleanup();
});

describe("LiveVoiceButton", () => {
  it("renders distinct Arabic label and audio waveform icon", () => {
    const handleClick = vi.fn();
    render(<LiveVoiceButton onClick={handleClick} />);

    const button = screen.getByRole("button", { name: /محادثة صوتية/i });
    expect(button).toBeDefined();
    expect(button.textContent).toContain("محادثة صوتية");

    fireEvent.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("supports compact variant for mobile and header layouts", () => {
    render(<LiveVoiceButton variant="compact" onClick={() => {}} />);
    const button = screen.getByRole("button", { name: /محادثة صوتية/i });
    expect(button.classList.contains("rounded-xl")).toBe(true);
  });
});

describe("LiveVoiceSession", () => {
  it("renders dialog with Arabic labels and dialect switcher when open", async () => {
    const handleClose = vi.fn();
    render(<LiveVoiceSession isOpen={true} onClose={handleClose} threadId="test-thread" />);

    expect(screen.getByRole("dialog", { name: /محادثة صوتية مباشرة مع مرشدي/i })).toBeDefined();
    expect(screen.getByText("العربية الفصحى")).toBeDefined();
    expect(screen.getByText("اللهجة الأردنية")).toBeDefined();
    expect(screen.getByText("English")).toBeDefined();
    expect(screen.getByRole("button", { name: /كتم الميكروفون/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /إنهاء المحادثة/i })).toBeDefined();
  });

  it("switches dialect when clicking dialect button", async () => {
    render(<LiveVoiceSession isOpen={true} onClose={() => {}} />);

    const jordanianBtn = screen.getByText("اللهجة الأردنية");
    fireEvent.click(jordanianBtn);

    await waitFor(() => {
      expect(jordanianBtn.classList.contains("text-[#ffc21a]")).toBe(true);
    });
  });

  it("toggles microphone mute state", async () => {
    render(<LiveVoiceSession isOpen={true} onClose={() => {}} />);

    const muteBtn = screen.getByRole("button", { name: /كتم الميكروفون/i });
    fireEvent.click(muteBtn);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /إلغاء كتم الميكروفون/i })).toBeDefined();
    });
  });

  it("closes when clicking end call button", () => {
    const handleClose = vi.fn();
    render(<LiveVoiceSession isOpen={true} onClose={handleClose} />);

    const endBtn = screen.getByRole("button", { name: /إنهاء المحادثة/i });
    fireEvent.click(endBtn);

    expect(handleClose).toHaveBeenCalledTimes(1);
  });
});
