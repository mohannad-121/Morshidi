"use client";

import { VoiceApiService, VoiceSessionResponse } from "@/lib/api/voice-api";
import { AssistantSpeechGate, measureAudioLevel } from "./voice-activity";

export type VoiceSessionStatus =
  | "idle"
  | "requesting_permissions"
  | "connecting"
  | "listening"
  | "speaking"
  | "delegating"
  | "reconnecting"
  | "error"
  | "ended";

export type SpokenDialect = "msa" | "jordanian" | "english";

export interface ConfirmedSpeechTurn {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: string;
}

export interface VoiceSessionCallbacks {
  onStatusChange?: (status: VoiceSessionStatus) => void;
  onDialectChange?: (dialect: SpokenDialect) => void;
  onDelegationProgress?: (toolName: string | null) => void;
  onInterimTranscript?: (text: string, speaker: "user" | "assistant") => void;
  onTurnConfirmed?: (turn: ConfirmedSpeechTurn) => void;
  onError?: (errorMessage: string) => void;
  onAudioLevels?: (levels: { micLevel: number; assistantLevel: number }) => void;
  onSessionExpired?: () => void;
}

const TOOL_NAMES_AR: Record<string, string> = {
  get_remaining_requirements: "فحص الساعات المتبقية ومتطلبات التخرج",
  get_student_academic_summary: "استرجاع السجل الأكاديمي المعتمد",
  get_course_eligibility: "التحقق من الأهلية والمتطلبات السابقة",
  get_eligible_courses: "حصر المواد المؤهلة للتسجيل",
  get_course_recommendations: "تجهيز التوصيات الأكاديمية المقترحة",
  get_course_information: "استرجاع بيانات الخطة ووصف المادة",
  compare_courses: "مقارنة المواد المحددة",
  get_semester_plan: "بناء مقترح الفصل القادم",
  get_degree_path: "محاكاة مسار التخرج متعدد الفصول",
  run_academic_what_if: "تنفيذ سيناريو 'ماذا لو' الافتراضي",
  get_current_enrollments: "مراجعة المواد المسجلة حالياً",
  get_student_progress: "حساب نسبة التقدم في الخطة",
  search_university_policies: "البحث في اللوائح والأنظمة الجامعية",
  switch_dialect: "تحديث لهجة المحادثة",
};

export class WebRTCVoiceSession {
  private pc: RTCPeerConnection | null = null;
  private dc: RTCDataChannel | null = null;
  private localStream: MediaStream | null = null;
  private audioEl: HTMLAudioElement | null = null;

  // Web Audio API for real acoustic measurement
  private audioContext: AudioContext | null = null;
  private micAnalyser: AnalyserNode | null = null;
  private assistantAnalyser: AnalyserNode | null = null;
  private animFrameId: number | null = null;

  private sessionData: VoiceSessionResponse | null = null;
  private status: VoiceSessionStatus = "idle";
  private isMuted: boolean = false;
  private currentDialect: SpokenDialect = "msa";
  private startTime: number | null = null;

  private lastUserText: string = "";
  private currentAssistantText: string = "";
  private expirationTimer: ReturnType<typeof setTimeout> | null = null;
  private assistantSpeechGate = new AssistantSpeechGate();

  private handleBeforeUnload = () => {
    this.stop();
  };

  constructor(
    private readonly voiceApi: VoiceApiService,
    private readonly callbacks: VoiceSessionCallbacks = {},
  ) {}

  getStatus(): VoiceSessionStatus {
    return this.status;
  }

  getDialect(): SpokenDialect {
    return this.currentDialect;
  }

  isMicMuted(): boolean {
    return this.isMuted;
  }

  private setStatus(status: VoiceSessionStatus) {
    this.status = status;
    this.callbacks.onStatusChange?.(status);
  }

  async start(threadId?: string): Promise<void> {
    if (this.status !== "idle" && this.status !== "ended" && this.status !== "error") {
      return;
    }

    try {
      this.setStatus("requesting_permissions");

      // 1. Request microphone access with high quality speech preprocessing
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 24000,
        },
      });
      this.localStream = stream;

      this.setStatus("connecting");

      // 2. Initialize WebRTC peer connection
      const pc = new RTCPeerConnection();
      this.pc = pc;

      // 3. Setup remote audio element
      const audioEl = new Audio();
      audioEl.autoplay = true;
      this.audioEl = audioEl;

      // 4. Setup Web Audio API analysers for real-time visualization
      this.setupAudioAnalysis(stream, pc);

      pc.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          audioEl.srcObject = event.streams[0];
          this.connectRemoteAudioToAnalyser(event.streams[0]);
        }
      };

      // 5. Add local audio tracks to peer connection
      stream.getAudioTracks().forEach((track) => {
        pc.addTrack(track, stream);
      });

      // 6. Setup WebRTC data channel for OpenAI Live/Realtime events
      const dc = pc.createDataChannel("oai-events");
      this.dc = dc;

      dc.onopen = () => {
        this.setStatus("listening");
        this.startLevelMonitoring();
      };

      dc.onclose = () => {
        if (this.status !== "ended") {
          this.setStatus("ended");
        }
      };

      dc.onerror = (e) => {
        console.error("WebRTC data channel error:", e);
      };

      dc.onmessage = (event) => {
        this.handleRealtimeEvent(event.data);
      };

      pc.onconnectionstatechange = () => {
        if (pc.connectionState === "disconnected" || pc.connectionState === "failed") {
          this.callbacks.onError?.("انقطع الاتصال بجلسة الصوت المباشر.");
          this.setStatus("error");
          this.cleanup();
        }
      };

      // 7. Create local SDP offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // 8. Server-mediated session establishment:
      // Browser sends SDP offer to authenticated Morshidi backend.
      // Backend calls POST /v1/live/sessions with transport: { type: "webrtc", sdp: offer.sdp }
      // and returns provider's SDP answer and session metadata.
      const session = await this.voiceApi.createSession({
        thread_id: threadId,
        sdp_offer: offer.sdp,
      });
      this.sessionData = session;
      this.currentDialect = (session.default_dialect as SpokenDialect) || "msa";
      this.callbacks.onDialectChange?.(this.currentDialect);
      this.startTime = Date.now();

      const isLive = session.endpoint_type === "live" || (!session.endpoint_type && Boolean(session.sdp_answer));

      if (isLive) {
        if (!session.sdp_answer) {
          throw new Error("لم يتم استلام توصيف SDP صالح من خادم الصوت.");
        }
        await pc.setRemoteDescription({
          type: "answer",
          sdp: session.sdp_answer,
        });
      } else {
        // Fallback flow for gpt-realtime-2.1 with client_secret
        if (!session.client_secret) {
          throw new Error("بيانات تفويض جلسة الصوت البديلة غير متوفرة.");
        }
        const sdpUrl = `https://api.openai.com/v1/realtime?model=${encodeURIComponent(session.model)}`;
        const sdpRes = await fetch(sdpUrl, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.client_secret}`,
            "Content-Type": "application/sdp",
          },
          body: offer.sdp,
        });

        if (!sdpRes.ok) {
          throw new Error(`OpenAI WebRTC handshake failed (${sdpRes.status})`);
        }

        const answerSdp = await sdpRes.text();
        await pc.setRemoteDescription({
          type: "answer",
          sdp: answerSdp,
        });
      }

      // 9. Enforce server-authoritative session expiration deadline
      const maxDurationSec = session.max_duration_seconds || 900;
      if (this.expirationTimer) {
        clearTimeout(this.expirationTimer);
      }
      this.expirationTimer = setTimeout(() => {
        this.handleSessionExpired();
      }, maxDurationSec * 1000);

      if (typeof window !== "undefined") {
        window.addEventListener("beforeunload", this.handleBeforeUnload);
      }

    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "تعذر بدء الجلسة الصوتية.";
      this.setStatus("error");
      this.callbacks.onError?.(message);
      this.cleanup();
    }
  }

  private setupAudioAnalysis(micStream: MediaStream, pc: RTCPeerConnection) {
    try {
      if (typeof window === "undefined") return;
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      this.audioContext = ctx;
      if (ctx.state === "suspended") {
        void ctx.resume().catch(() => {});
      }

      // Microphone analyser
      const micSource = ctx.createMediaStreamSource(micStream);
      const micAnalyser = ctx.createAnalyser();
      micAnalyser.fftSize = 256;
      micSource.connect(micAnalyser);
      this.micAnalyser = micAnalyser;

      // Assistant analyser
      const assistantAnalyser = ctx.createAnalyser();
      assistantAnalyser.fftSize = 256;
      this.assistantAnalyser = assistantAnalyser;
    } catch (e) {
      console.warn("Web Audio API not fully available for visualization:", e);
    }
  }

  private connectRemoteAudioToAnalyser(remoteStream: MediaStream) {
    if (!this.audioContext || !this.assistantAnalyser) return;
    try {
      if (this.audioContext.state === "suspended") {
        void this.audioContext.resume().catch(() => {});
      }
      const remoteSource = this.audioContext.createMediaStreamSource(remoteStream);
      remoteSource.connect(this.assistantAnalyser);

      // Connect to audioContext.destination via gain=0.
      // This is crucial: Chrome's Web Audio thread will only continuously pull
      // audio samples from a MediaStreamSource through an AnalyserNode if the graph
      // terminates at destination. The gain of 0 ensures no duplicate audio / echo,
      // while guaranteeing that getByteFrequencyData receives live audio frames.
      const silenceGain = this.audioContext.createGain();
      silenceGain.gain.value = 0;
      this.assistantAnalyser.connect(silenceGain);
      silenceGain.connect(this.audioContext.destination);
    } catch (e) {
      console.warn("Could not connect remote stream to analyser:", e);
    }
  }

  private startLevelMonitoring() {
    const micData = new Uint8Array(128);
    const micTimeData = new Uint8Array(128);
    const assistantData = new Uint8Array(128);
    const assistantTimeData = new Uint8Array(128);

    const update = () => {
      if (this.status === "ended" || this.status === "error" || this.status === "idle") {
        return;
      }

      let micLevel = 0;
      let assistantLevel = 0;

      if (this.micAnalyser && !this.isMuted) {
        micLevel = measureAudioLevel(this.micAnalyser, micData, micTimeData);
      }

      if (this.assistantAnalyser) {
        assistantLevel = measureAudioLevel(
          this.assistantAnalyser,
          assistantData,
          assistantTimeData,
        );

        // Primary Audio-Driven Speaking Detection:
        // Physical remote output is the source of truth. Separate start/release
        // thresholds plus a short hold prevent flicker during natural pauses.
        const now = Date.now();
        const wasAudioActive = this.assistantSpeechGate.isActive();
        const isAudioActive = this.assistantSpeechGate.update(assistantLevel, now);
        if (isAudioActive) {
          if (this.status === "listening" || this.status === "delegating") {
            this.setStatus("speaking");
          }
        } else if (wasAudioActive && this.status === "speaking") {
          this.setStatus("listening");
        }
      }

      this.callbacks.onAudioLevels?.({ micLevel, assistantLevel });
      if (typeof window !== "undefined" && typeof requestAnimationFrame === "function") {
        this.animFrameId = requestAnimationFrame(update);
      }
    };

    if (typeof window !== "undefined" && typeof requestAnimationFrame === "function") {
      this.animFrameId = requestAnimationFrame(update);
    }
  }

  private handleRealtimeEvent(raw: string) {
    try {
      const event = JSON.parse(raw);
      const type = event.type as string;

      switch (type) {
        // Interruption & Speech Detection (GPT-Live & Realtime)
        case "input_audio_buffer.speech_started":
        case "session.input_transcript.started":
          // User started speaking — IMMEDIATELY cancel assistant speech and stop playback
          if (this.audioEl) {
            this.audioEl.pause();
            this.audioEl.currentTime = 0;
          }
          this.sendRealtimeEvent({ type: "response.cancel" });
          this.assistantSpeechGate.reset();
          this.setStatus("listening");
          this.currentAssistantText = "";
          break;

        case "input_audio_buffer.speech_stopped":
        case "session.input_transcript.stopped":
          // User stopped speaking
          break;

        case "session.input_transcript.delta":
          if (event.delta) {
            this.callbacks.onInterimTranscript?.(event.delta, "user");
          }
          break;

        case "session.input_transcript.done":
        case "conversation.item.input_audio_transcription.completed": {
          const userText = (event.transcript || event.text || "").trim();
          if (userText) {
            this.lastUserText = userText;
            this.callbacks.onTurnConfirmed?.({
              id: event.item_id || String(Date.now()),
              role: "user",
              text: this.lastUserText,
              timestamp: new Date().toLocaleTimeString("ar-JO-u-nu-latn", { hour: "2-digit", minute: "2-digit" }),
            });
          }
          break;
        }

        // Assistant Audio Streaming & Transcripts (GPT-Live & Realtime fallback)
        case "response.created":
        case "session.output_item.added":
          this.currentAssistantText = "";
          break;

        case "session.output_transcript.delta":
        case "response.audio_transcript.delta": {
          this.setStatus("speaking");
          const delta = event.delta || event.transcript || "";
          if (delta) {
            this.currentAssistantText += delta;
            this.callbacks.onInterimTranscript?.(this.currentAssistantText, "assistant");
          }
          break;
        }

        case "output_audio_buffer.started":
        case "response.audio.started":
          this.setStatus("speaking");
          break;

        case "output_audio_buffer.stopped":
        case "response.audio.done":
          this.assistantSpeechGate.reset();
          if (this.status === "speaking") {
            this.setStatus("listening");
          }
          break;

        case "session.output_transcript.done":
        case "response.audio_transcript.done":
          if (this.currentAssistantText.trim()) {
            this.callbacks.onTurnConfirmed?.({
              id: event.item_id || String(Date.now()),
              role: "assistant",
              text: this.currentAssistantText.trim(),
              timestamp: new Date().toLocaleTimeString("ar-JO-u-nu-latn", { hour: "2-digit", minute: "2-digit" }),
            });

            // Sync confirmed turn with backend
            if (this.lastUserText && this.sessionData?.session_id) {
              const turnId = crypto.randomUUID();
              void this.voiceApi.syncTurn({
                thread_id: this.sessionData.university_id,
                user_transcript: this.lastUserText,
                assistant_transcript: this.currentAssistantText.trim(),
                client_turn_id: turnId,
              });
              this.lastUserText = "";
            }
          }
          if (!this.assistantSpeechGate.isActive()) {
            this.setStatus("listening");
          }
          break;

        // Client Delegation: GPT-Live protocol (session.delegation.created)
        case "session.delegation.created": {
          const delId = (event.delegation_id || event.delegation?.id || event.id) as string;
          const delTool = (event.delegation?.name || event.tool_name || event.name || event.function?.name) as string | undefined;
          const delArgs = typeof event.delegation?.arguments === "string"
            ? event.delegation.arguments
            : JSON.stringify(event.delegation?.arguments || event.arguments || {});
          void this.handleDelegatedToolCall(delId, delTool, delArgs, "gpt-live", event.metadata || event.delegation);
          break;
        }

        // Client Delegation: Realtime function calling protocol (gpt-realtime-2.1 fallback)
        case "response.output_item.done":
          if (event.item && event.item.type === "function_call") {
            const callId = event.item.call_id;
            const name = event.item.name;
            const args = event.item.arguments;
            void this.handleDelegatedToolCall(callId, name, args, "realtime");
          }
          break;

        case "error":
          console.error("OpenAI Voice session error:", event.error);
          this.callbacks.onError?.(event.error?.message || "حدث خطأ في محرك الصوت.");
          break;

        default:
          break;
      }
    } catch (err) {
      console.error("Failed to parse realtime event:", err);
    }
  }

  private async handleDelegatedToolCall(
    callId: string,
    toolName?: string,
    args: string = "{}",
    protocol: "gpt-live" | "realtime" = "gpt-live",
    metadata?: Record<string, unknown>,
  ) {
    this.setStatus("delegating");
    const friendlyToolName = (toolName && TOOL_NAMES_AR[toolName]) || toolName || "استرجاع السجل الأكاديمي المعتمد";
    this.callbacks.onDelegationProgress?.(friendlyToolName);

    try {
      const res = await this.voiceApi.delegateTool({
        call_id: callId,
        tool_name: toolName,
        arguments: args,
        user_transcript: this.lastUserText,
        metadata: metadata,
        thread_id: this.sessionData?.university_id,
      });

      if ((toolName === "switch_dialect" || res.tool_name === "switch_dialect") && res.ok) {
        try {
          const parsed = JSON.parse(args) as { dialect?: SpokenDialect };
          if (parsed.dialect) {
            this.currentDialect = parsed.dialect;
            this.callbacks.onDialectChange?.(this.currentDialect);
          }
        } catch {
          // ignore
        }
      }

      if (protocol === "gpt-live") {
        // GPT-Live Client Delegation Response: session.commentary.append
        // Return concise, verified academic summary under 800 chars
        const commentary = res.summary_text || (typeof res.output === "string" ? res.output : JSON.stringify(res.output));
        this.sendRealtimeEvent({
          type: "session.commentary.append",
          delegation_id: callId,
          content: commentary.slice(0, 800),
        });
      } else {
        // Realtime Function Calling Response
        this.sendRealtimeEvent({
          type: "conversation.item.create",
          item: {
            type: "function_call_output",
            call_id: callId,
            output: JSON.stringify(res.output),
          },
        });
        this.sendRealtimeEvent({
          type: "response.create",
        });
      }

    } catch (err) {
      console.error("Delegation execution failed:", err);
      if (protocol === "gpt-live") {
        this.sendRealtimeEvent({
          type: "session.commentary.append",
          delegation_id: callId,
          content: "تعذر استرجاع المعلومة الأكاديمية المطلوبة حالياً من السجلات المعتمدة.",
        });
      } else {
        this.sendRealtimeEvent({
          type: "conversation.item.create",
          item: {
            type: "function_call_output",
            call_id: callId,
            output: JSON.stringify({ ok: false, error: "DELEGATION_FAILED" }),
          },
        });
        this.sendRealtimeEvent({ type: "response.create" });
      }
    } finally {
      this.callbacks.onDelegationProgress?.(null);
    }
  }

  sendRealtimeEvent(event: Record<string, unknown>): void {
    if (this.dc && this.dc.readyState === "open") {
      this.dc.send(JSON.stringify(event));
    }
  }

  switchDialect(targetDialect: SpokenDialect): void {
    this.currentDialect = targetDialect;
    this.callbacks.onDialectChange?.(targetDialect);

    const dialectInstruction =
      targetDialect === "jordanian"
        ? "الطالب اختار التحدث باللهجة الأردنية. تحدث من الآن فصاعداً باللهجة الأردنية البيضاء الطبيعية في جميع الردود."
        : targetDialect === "english"
        ? "The student requested English. Speak naturally in English."
        : "تحدث الآن باللغة العربية الفصحى المعاصرة والسليمة.";

    this.sendRealtimeEvent({
      type: "session.update",
      session: {
        instructions: dialectInstruction,
      },
    });

    // Also inform the model verbally to confirm
    this.sendRealtimeEvent({
      type: "response.create",
      response: {
        instructions: dialectInstruction,
      },
    });
  }

  toggleMute(): boolean {
    if (!this.localStream) return this.isMuted;
    this.isMuted = !this.isMuted;
    this.localStream.getAudioTracks().forEach((track) => {
      track.enabled = !this.isMuted;
    });
    return this.isMuted;
  }

  private handleSessionExpired(): void {
    if (this.status === "ended") return;
    this.setStatus("ended");
    this.callbacks.onSessionExpired?.();
    const actualDurationSeconds = this.startTime ? (Date.now() - this.startTime) / 1000 : undefined;
    if (this.sessionData?.session_id) {
      void this.voiceApi.endSession(this.sessionData.session_id, actualDurationSeconds);
    }
    this.cleanup();
  }

  stop(): void {
    if (this.status === "ended") {
      return;
    }
    this.setStatus("ended");
    const actualDurationSeconds = this.startTime ? (Date.now() - this.startTime) / 1000 : undefined;
    if (this.sessionData?.session_id) {
      void this.voiceApi.endSession(this.sessionData.session_id, actualDurationSeconds);
    }
    this.cleanup();
  }

  private cleanup(): void {
    this.startTime = null;
    this.assistantSpeechGate.reset();
    if (this.expirationTimer !== null) {
      clearTimeout(this.expirationTimer);
      this.expirationTimer = null;
    }

    if (typeof window !== "undefined") {
      window.removeEventListener("beforeunload", this.handleBeforeUnload);
    }

    if (this.animFrameId !== null) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }

    if (this.localStream) {
      this.localStream.getTracks().forEach((t) => t.stop());
      this.localStream = null;
    }

    if (this.dc) {
      try {
        this.dc.close();
      } catch {
        // ignore
      }
      this.dc = null;
    }

    if (this.pc) {
      try {
        this.pc.close();
      } catch {
        // ignore
      }
      this.pc = null;
    }

    if (this.audioEl) {
      try {
        this.audioEl.pause();
      } catch {
        // ignore
      }
      this.audioEl.srcObject = null;
      this.audioEl = null;
    }

    if (this.audioContext) {
      void this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
  }
}
