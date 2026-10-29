import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { WebRTCVoiceSession } from "./webrtc-voice-session";
import { VoiceApiService } from "@/lib/api/voice-api";

describe("WebRTCVoiceSession", () => {
  let mockVoiceApi: {
    createSession: ReturnType<typeof vi.fn>;
    delegateTool: ReturnType<typeof vi.fn>;
    syncTurn: ReturnType<typeof vi.fn>;
    endSession: ReturnType<typeof vi.fn>;
  };

  let mockDataChannel: {
    send: ReturnType<typeof vi.fn>;
    close: ReturnType<typeof vi.fn>;
    readyState: string;
    onopen: (() => void) | null;
    onclose: (() => void) | null;
    onerror: ((e: any) => void) | null;
    onmessage: ((e: { data: string }) => void) | null;
  };

  let mockPeerConnection: {
    addTrack: ReturnType<typeof vi.fn>;
    createOffer: ReturnType<typeof vi.fn>;
    setLocalDescription: ReturnType<typeof vi.fn>;
    setRemoteDescription: ReturnType<typeof vi.fn>;
    createDataChannel: ReturnType<typeof vi.fn>;
    close: ReturnType<typeof vi.fn>;
    connectionState: string;
    ontrack: ((event: any) => void) | null;
    onconnectionstatechange: (() => void) | null;
  };

  let mockMediaStream: {
    getAudioTracks: ReturnType<typeof vi.fn>;
    getTracks: ReturnType<typeof vi.fn>;
  };

  let mockTrack: {
    enabled: boolean;
    stop: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    mockTrack = {
      enabled: true,
      stop: vi.fn(),
    };

    mockMediaStream = {
      getAudioTracks: vi.fn().mockReturnValue([mockTrack]),
      getTracks: vi.fn().mockReturnValue([mockTrack]),
    };

    // Mock navigator.mediaDevices.getUserMedia
    Object.defineProperty(global, "navigator", {
      value: {
        mediaDevices: {
          getUserMedia: vi.fn().mockResolvedValue(mockMediaStream),
        },
      },
      writable: true,
    });

    mockDataChannel = {
      send: vi.fn(),
      close: vi.fn(),
      readyState: "open",
      onopen: null,
      onclose: null,
      onerror: null,
      onmessage: null,
    };

    mockPeerConnection = {
      addTrack: vi.fn(),
      createOffer: vi.fn().mockResolvedValue({ sdp: "v=0\r\no=Browser ..." }),
      setLocalDescription: vi.fn().mockResolvedValue(undefined),
      setRemoteDescription: vi.fn().mockResolvedValue(undefined),
      createDataChannel: vi.fn().mockReturnValue(mockDataChannel),
      close: vi.fn(),
      connectionState: "connected",
      ontrack: null,
      onconnectionstatechange: null,
    };

    // Mock RTCPeerConnection global with proper constructible class
    class MockPeerConnectionClass {
      addTrack = mockPeerConnection.addTrack;
      createOffer = mockPeerConnection.createOffer;
      setLocalDescription = mockPeerConnection.setLocalDescription;
      setRemoteDescription = mockPeerConnection.setRemoteDescription;
      createDataChannel = mockPeerConnection.createDataChannel;
      close = mockPeerConnection.close;
      connectionState = "connected";
      ontrack = null;
      onconnectionstatechange = null;
    }
    (global as any).RTCPeerConnection = MockPeerConnectionClass;

    // Mock Audio global with proper constructible class
    class MockAudioClass {
      autoplay = true;
      play = vi.fn().mockResolvedValue(undefined);
      pause = vi.fn();
      srcObject = null;
      currentTime = 0;
    }
    (global as any).Audio = MockAudioClass;

    mockVoiceApi = {
      createSession: vi.fn().mockResolvedValue({
        session_id: "sess_live_123",
        sdp_answer: "v=0\r\no=OpenAI ...",
        model: "gpt-live-1",
        voice: "alloy",
        endpoint_type: "live",
        max_duration_seconds: 900,
        default_language: "ar",
        default_dialect: "msa",
        tools: ["get_remaining_requirements"],
        university_id: "uni-hash-1",
      }),
      delegateTool: vi.fn().mockResolvedValue({
        call_id: "del_1",
        tool_name: "get_remaining_requirements",
        output: { remaining_credit_hours: 12 },
        summary_text: "يتبقى عليك 12 ساعة معتمدة لإتمام متطلبات الخطة.",
        ok: true,
      }),
      syncTurn: vi.fn().mockResolvedValue({ synced: true }),
      endSession: vi.fn().mockResolvedValue(undefined),
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("establishes session via server-mediated SDP offer/answer without client OpenAI token", async () => {
    const onStatusChange = vi.fn();
    const session = new WebRTCVoiceSession(mockVoiceApi as unknown as VoiceApiService, {
      onStatusChange,
    });

    await session.start("thread-abc");

    // Browser created offer and sent to backend
    expect(mockPeerConnection.createOffer).toHaveBeenCalledTimes(1);
    expect(mockVoiceApi.createSession).toHaveBeenCalledWith({
      thread_id: "thread-abc",
      sdp_offer: "v=0\r\no=Browser ...",
    });

    // Remote description applied directly from backend response
    expect(mockPeerConnection.setRemoteDescription).toHaveBeenCalledWith({
      type: "answer",
      sdp: "v=0\r\no=OpenAI ...",
    });
  });

  it("handles GPT-Live client delegation with session.delegation.created and replies with session.commentary.append", async () => {
    const onDelegationProgress = vi.fn();
    const session = new WebRTCVoiceSession(mockVoiceApi as unknown as VoiceApiService, {
      onDelegationProgress,
    });

    await session.start("thread-abc");

    // Simulate incoming GPT-Live delegation event
    mockDataChannel.onmessage?.({
      data: JSON.stringify({
        type: "session.delegation.created",
        delegation_id: "del_live_999",
        delegation: {
          id: "del_live_999",
          name: "get_remaining_requirements",
          arguments: "{}",
        },
      }),
    });

    await new Promise((r) => setTimeout(r, 10));

    // Verified backend tool execution called
    expect(mockVoiceApi.delegateTool).toHaveBeenCalledWith(
      expect.objectContaining({
        call_id: "del_live_999",
        tool_name: "get_remaining_requirements",
      })
    );

    // Verified commentary sent back on data channel
    expect(mockDataChannel.send).toHaveBeenCalledWith(
      JSON.stringify({
        type: "session.commentary.append",
        delegation_id: "del_live_999",
        content: "يتبقى عليك 12 ساعة معتمدة لإتمام متطلبات الخطة.",
      })
    );
  });

  it("cancels assistant speech immediately on user barge-in (speech_started)", async () => {
    const session = new WebRTCVoiceSession(mockVoiceApi as unknown as VoiceApiService);
    await session.start();

    // Trigger barge-in event
    mockDataChannel.onmessage?.({
      data: JSON.stringify({
        type: "input_audio_buffer.speech_started",
      }),
    });

    expect(mockDataChannel.send).toHaveBeenCalledWith(
      JSON.stringify({ type: "response.cancel" })
    );
  });

  it("supports in-session dialect switching to Jordanian without restart", async () => {
    const onDialectChange = vi.fn();
    const session = new WebRTCVoiceSession(mockVoiceApi as unknown as VoiceApiService, {
      onDialectChange,
    });

    await session.start();
    session.switchDialect("jordanian");

    expect(onDialectChange).toHaveBeenCalledWith("jordanian");
    expect(session.getDialect()).toBe("jordanian");
    expect(mockDataChannel.send).toHaveBeenCalledWith(
      expect.stringContaining("الطالب اختار التحدث باللهجة الأردنية")
    );
  });

  it("records actual wall-clock duration and terminates session on stop()", async () => {
    const session = new WebRTCVoiceSession(mockVoiceApi as unknown as VoiceApiService);
    await session.start();

    // Fast forward clock
    await new Promise((r) => setTimeout(r, 50));

    session.stop();

    expect(mockVoiceApi.endSession).toHaveBeenCalledWith(
      "sess_live_123",
      expect.any(Number)
    );
    expect(session.getStatus()).toBe("ended");
    expect(mockTrack.stop).toHaveBeenCalled();
  });
});
