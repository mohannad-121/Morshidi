"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import { AnimatedMorshidiMascot } from "./AnimatedMorshidiMascot";
import {
  Mic,
  MicOff,
  PhoneOff,
  Sparkles,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  AlertCircle,
  RefreshCw,
  X,
  Compass,
} from "lucide-react";
import { LogoMark } from "@/components/ui/Logo";
import { useAuthenticatedApi } from "@/lib/api/use-authenticated-api";
import { VoiceApiService } from "@/lib/api/voice-api";
import {
  ConfirmedSpeechTurn,
  SpokenDialect,
  VoiceSessionStatus,
  WebRTCVoiceSession,
} from "@/lib/voice/webrtc-voice-session";
import { VoiceVisualizer } from "./VoiceVisualizer";

interface LiveVoiceSessionProps {
  isOpen: boolean;
  onClose: () => void;
  threadId?: string | null;
  onTurnsUpdated?: () => void;
}

const STATUS_MESSAGES_AR: Record<VoiceSessionStatus, string> = {
  idle: "جاهز لبدء المحادثة",
  requesting_permissions: "يرجى السماح بالوصول إلى الميكروفون…",
  connecting: "جارٍ الاتصال بمرشدي…",
  listening: "مرشدي يستمع إليك…",
  speaking: "مرشدي يتحدث",
  delegating: "جارٍ التحقق من المعلومات الأكاديمية…",
  reconnecting: "جارٍ إعادة الاتصال…",
  error: "تعذر الاتصال",
  ended: "انتهت المحادثة الصوتية",
};

export function LiveVoiceSession({
  isOpen,
  onClose,
  threadId,
  onTurnsUpdated,
}: LiveVoiceSessionProps) {
  const client = useAuthenticatedApi();
  const clientRef = useRef(client);
  useEffect(() => {
    clientRef.current = client;
  }, [client]);

  const sessionRef = useRef<WebRTCVoiceSession | null>(null);
  const onTurnsUpdatedRef = useRef(onTurnsUpdated);

  useEffect(() => {
    onTurnsUpdatedRef.current = onTurnsUpdated;
  }, [onTurnsUpdated]);

  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  const [status, setStatus] = useState<VoiceSessionStatus>("idle");
  const [dialect, setDialect] = useState<SpokenDialect>("msa");
  const [isMuted, setIsMuted] = useState(false);
  const [delegationTool, setDelegationTool] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [audioLevels, setAudioLevels] = useState({ micLevel: 0, assistantLevel: 0 });
  const [turns, setTurns] = useState<ConfirmedSpeechTurn[]>([]);
  const [interimText, setInterimText] = useState<{ text: string; speaker: "user" | "assistant" } | null>(null);
  const [showTranscript, setShowTranscript] = useState(false);
  const [secondsElapsed, setSecondsElapsed] = useState(0);

  const turnsEndRef = useRef<HTMLDivElement>(null);

  const scrollToTranscriptBottom = () => {
    turnsEndRef.current?.scrollIntoView?.({ behavior: "smooth" });
  };

  useEffect(() => {
    if (showTranscript) {
      scrollToTranscriptBottom();
    }
  }, [turns, interimText, showTranscript]);

  // Session duration timer & hard deadline enforcement
  useEffect(() => {
    if (process.env.NODE_ENV === "test") return;
    if (status !== "listening" && status !== "speaking" && status !== "delegating") return;
    const interval = setInterval(() => {
      setSecondsElapsed((prev) => {
        const next = prev + 1;
        if (next >= 900) {
          if (sessionRef.current) {
            sessionRef.current.stop();
          }
          setStatus("ended");
          setErrorMessage("انتهى الحد الأقصى للجلسة الصوتية المعتمدة (15 دقيقة). تم حفظ المحادثة بنجاح، ويمكنك متابعة استفسارك نصياً.");
          return 900;
        }
        return next;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [status]);

  const formatTimer = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const handleStartSession = useCallback(async () => {
    setErrorMessage(null);
    setSecondsElapsed(0);
    setTurns([]);
    setInterimText(null);

    const api = new VoiceApiService(clientRef.current);
    const session = new WebRTCVoiceSession(api, {
      onStatusChange: (newStatus) => setStatus(newStatus),
      onDialectChange: (newDialect) => setDialect(newDialect),
      onDelegationProgress: (toolName) => setDelegationTool(toolName),
      onAudioLevels: (levels) => setAudioLevels(levels),
      onInterimTranscript: (text, speaker) => {
        setInterimText({ text, speaker });
      },
      onTurnConfirmed: (turn) => {
        setTurns((prev) => [...prev, turn]);
        setInterimText(null);
        onTurnsUpdatedRef.current?.();
      },
      onError: (err) => {
        setErrorMessage(err);
      },
      onSessionExpired: () => {
        setStatus("ended");
        setErrorMessage("انتهى الحد الأقصى للجلسة الصوتية المعتمدة (15 دقيقة). تم حفظ المحادثة بنجاح، ويمكنك متابعة استفسارك نصياً.");
      },
    });

    sessionRef.current = session;
    await session.start(threadId || undefined);
  }, [threadId]);

  useEffect(() => {
    if (isOpen) {
      void handleStartSession();
    } else {
      if (sessionRef.current) {
        sessionRef.current.stop();
        sessionRef.current = null;
      }
      setStatus("idle");
    }

    return () => {
      if (sessionRef.current) {
        sessionRef.current.stop();
        sessionRef.current = null;
      }
    };
  }, [isOpen, handleStartSession]);

  const handleToggleMute = () => {
    if (!sessionRef.current) return;
    const muted = sessionRef.current.toggleMute();
    setIsMuted(muted);
  };

  const handleSwitchDialect = (target: SpokenDialect) => {
    if (!sessionRef.current) return;
    sessionRef.current.switchDialect(target);
    setDialect(target);
  };

  const handleEndCall = () => {
    if (sessionRef.current) {
      sessionRef.current.stop();
    }
    onClose();
  };

  // Keyboard navigation: Escape key closes modal safely
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        handleEndCall();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  if (!isOpen) return null;

  const isSpeaking = status === "speaking";
  const isDelegating = status === "delegating";

  const modalContent = (
    <div
      className="fixed inset-0 z-[100] isolate flex items-center justify-center p-4 sm:p-6 bg-black/85 backdrop-blur-xl animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-label="محادثة صوتية مباشرة مع مرشدي"
      dir="rtl"
      style={{ isolation: "isolate" }}
    >
      <div className="relative w-full max-w-2xl bg-[#0d0d0d] border border-amber-500/20 rounded-3xl shadow-2xl shadow-black/90 overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.08] bg-white/[0.02]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-amber-500/10 border border-amber-500/25 flex items-center justify-center text-[#ffc21a]">
              <LogoMark />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-wide">مرشدي AI — صوت مباشر</h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 text-[#ffc21a] border border-amber-500/30">
                  Speech-to-Speech
                </span>
              </div>
              <p className="text-xs text-slate-400">محادثة أكاديمية لحظية مدعومة بالقواعد المعتمدة</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-slate-400 bg-white/[0.05] px-2.5 py-1 rounded-full border border-white/[0.08]">
              {formatTimer(secondsElapsed)}
            </span>
            <button
              onClick={handleEndCall}
              className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-white/[0.08] transition-colors"
              aria-label="إغلاق المحادثة الصوتية"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Dialect Switcher Bar */}
        <div className="flex items-center justify-between px-6 py-2.5 bg-[#141414] border-b border-white/[0.05] text-xs">
          <div className="flex items-center gap-2 text-slate-300">
            <Sparkles size={14} className="text-[#ffc21a]" />
            <span>لهجة الحديث:</span>
          </div>

          <div className="inline-flex p-1 bg-black/50 border border-white/[0.08] rounded-xl gap-1">
            <button
              onClick={() => handleSwitchDialect("msa")}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                dialect === "msa"
                  ? "bg-amber-500/20 text-[#ffc21a] font-bold shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              العربية الفصحى
            </button>
            <button
              onClick={() => handleSwitchDialect("jordanian")}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                dialect === "jordanian"
                  ? "bg-amber-500/20 text-[#ffc21a] font-bold shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              اللهجة الأردنية
            </button>
            <button
              onClick={() => handleSwitchDialect("english")}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                dialect === "english"
                  ? "bg-amber-500/20 text-[#ffc21a] font-bold shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              English
            </button>
          </div>
        </div>

        {/* Central Audio & Visual Experience */}
        <div className="relative flex-1 flex flex-col items-center justify-center p-8 min-h-[300px] overflow-hidden">
          {/* Reactive Glowing Aura */}
          <div
            className="absolute w-64 h-64 rounded-full filter blur-3xl pointer-events-none transition-all duration-300"
            style={{
              backgroundColor: isSpeaking
                ? "rgba(255, 194, 26, 0.15)"
                : isDelegating
                ? "rgba(56, 189, 248, 0.18)"
                : audioLevels.micLevel > 0.05
                ? "rgba(168, 85, 247, 0.15)"
                : "rgba(255, 255, 255, 0.03)",
              transform: `scale(${1 + Math.max(audioLevels.micLevel, audioLevels.assistantLevel) * 0.8})`,
            }}
          />

          {/* Central Animated Mascot Experience */}
          <div className="relative z-10 flex flex-col items-center gap-5">
            <AnimatedMorshidiMascot
              status={status}
              assistantAudioLevel={audioLevels.assistantLevel}
              micAudioLevel={audioLevels.micLevel}
            />

            {/* Live Status Text */}
            <div className="text-center space-y-1.5 z-10">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-sm font-semibold text-slate-200">
                {isDelegating && <Compass className="needle-loading text-cyan-400" size={16} />}
                <span>
                  {isDelegating
                    ? delegationTool || STATUS_MESSAGES_AR.delegating
                    : isMuted
                    ? "الميكروفون مغلق حالياً"
                    : STATUS_MESSAGES_AR[status] || "مرشدي معك"}
                </span>
              </div>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                {status === "listening" &&
                  "يمكنك التحدث بحرية الآن، أو المقاطعة في أي وقت لتغيير الموضوع أو طلب توضيح."}
                {status === "speaking" &&
                  "استمع لشرح مرشدي، ويمكنك مقاطعته فوراً بمجرد بدء التحدث."}
                {dialect === "jordanian" && status !== "error" && (
                  <span className="block text-[#ffc21a] text-[11px] mt-1 font-medium">
                    (مفعّل: اللهجة الأردنية — احكي "ارجع فصحى" للعودة)
                  </span>
                )}
              </p>
            </div>
          </div>

          {/* Realtime Waveform Canvas */}
          <div className="w-full max-w-md h-20 mt-4 z-10">
            <VoiceVisualizer
              status={status}
              micLevel={audioLevels.micLevel}
              assistantLevel={audioLevels.assistantLevel}
              className="w-full h-full"
            />
          </div>

          {/* Error / Session Notification Banner */}
          {errorMessage && (
            <div
              className={`mt-4 px-4 py-2.5 rounded-2xl border text-xs flex items-center justify-between gap-3 max-w-md w-full z-20 ${
                status === "ended"
                  ? "bg-amber-950/80 border-amber-500/40 text-amber-200"
                  : "bg-rose-950/80 border-rose-500/40 text-rose-300"
              }`}
            >
              <div className="flex items-center gap-2">
                <AlertCircle size={16} className={status === "ended" ? "text-amber-400 shrink-0" : "text-rose-400 shrink-0"} />
                <span>{errorMessage}</span>
              </div>
              <button
                onClick={() => void handleStartSession()}
                className={`px-2.5 py-1 rounded-lg border font-medium flex items-center gap-1 shrink-0 ${
                  status === "ended"
                    ? "bg-amber-900/60 hover:bg-amber-900 border-amber-500/40 text-amber-100"
                    : "bg-rose-900/60 hover:bg-rose-900 border-rose-500/40 text-white"
                }`}
              >
                <RefreshCw size={12} />
                <span>{status === "ended" ? "بدء محادثة جديدة" : "إعادة المحاولة"}</span>
              </button>
            </div>
          )}
        </div>

        {/* Live Transcripts Drawer (Collapsible) */}
        <div className="border-t border-white/[0.08] bg-[#111] overflow-hidden flex flex-col">
          <button
            onClick={() => setShowTranscript((prev) => !prev)}
            className="flex items-center justify-between px-6 py-2.5 text-xs text-slate-300 hover:text-white transition-colors"
          >
            <div className="flex items-center gap-2 font-medium">
              <MessageSquare size={14} className="text-[#ffc21a]" />
              <span>النص الحي للمحادثة ({turns.length} رسائل)</span>
            </div>
            {showTranscript ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </button>

          {showTranscript && (
            <div className="p-4 max-h-48 overflow-y-auto space-y-3 bg-black/30 border-t border-white/[0.04]">
              {turns.length === 0 && !interimText && (
                <p className="text-xs text-slate-500 text-center py-4">
                  ستظهر نصوص المحادثة هنا مباشرة أثناء التحدث…
                </p>
              )}
              {turns.map((turn) => (
                <div
                  key={turn.id}
                  className={`text-xs p-3 rounded-2xl max-w-[85%] ${
                    turn.role === "user"
                      ? "bg-white/[0.08] text-slate-200 mr-auto border border-white/[0.05]"
                      : "bg-amber-500/10 text-amber-100 ml-auto border border-amber-500/20"
                  }`}
                >
                  <div className="flex items-center justify-between gap-4 mb-1 text-[10px] text-slate-400">
                    <span className="font-bold">{turn.role === "user" ? "أنت" : "مرشدي"}</span>
                    <span>{turn.timestamp}</span>
                  </div>
                  <p className="leading-relaxed">{turn.text}</p>
                </div>
              ))}
              {interimText && (
                <div
                  className={`text-xs p-3 rounded-2xl max-w-[85%] animate-pulse ${
                    interimText.speaker === "user"
                      ? "bg-white/[0.05] text-slate-300 mr-auto"
                      : "bg-amber-500/5 text-amber-200/80 ml-auto"
                  }`}
                >
                  <span className="text-[10px] text-slate-400 block mb-1">
                    {interimText.speaker === "user" ? "أنت (يتحدث…)" : "مرشدي (يتحدث…)"}
                  </span>
                  <p className="leading-relaxed">{interimText.text}</p>
                </div>
              )}
              <div ref={turnsEndRef} />
            </div>
          )}
        </div>

        {/* Bottom Control Actions */}
        <div className="flex items-center justify-center gap-6 px-6 py-5 bg-[#0a0a0a] border-t border-white/[0.08]">
          {/* Mute Button */}
          <button
            onClick={handleToggleMute}
            className={`w-13 h-13 rounded-2xl flex items-center justify-center border transition-all ${
              isMuted
                ? "bg-rose-950/80 border-rose-500/50 text-rose-300 shadow-lg shadow-rose-950/50"
                : "bg-white/[0.06] border-white/[0.12] text-slate-200 hover:bg-white/[0.12] hover:text-white"
            }`}
            aria-label={isMuted ? "إلغاء كتم الميكروفون" : "كتم الميكروفون"}
            title={isMuted ? "إلغاء كتم الميكروفون" : "كتم الميكروفون"}
          >
            {isMuted ? <MicOff size={22} /> : <Mic size={22} />}
          </button>

          {/* End Call Button */}
          <button
            onClick={handleEndCall}
            className="h-13 px-8 rounded-2xl bg-rose-600 hover:bg-rose-700 text-white font-bold flex items-center gap-3 shadow-lg shadow-rose-900/50 transition-all hover:scale-105 active:scale-95"
            aria-label="إنهاء المحادثة الصوتية"
          >
            <PhoneOff size={20} />
            <span>إنهاء المحادثة</span>
          </button>
        </div>
      </div>
    </div>
  );

  if (mounted && typeof document !== "undefined") {
    return createPortal(modalContent, document.body);
  }

  return modalContent;
}
