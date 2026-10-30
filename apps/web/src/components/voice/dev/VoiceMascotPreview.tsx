"use client";

import { useState } from "react";
import type { VoiceSessionStatus } from "@/lib/voice/webrtc-voice-session";
import {
  AnimatedMorshidiMascot,
  type MascotGestureOverride,
} from "../AnimatedMorshidiMascot";
import { LiveVoiceSession } from "../LiveVoiceSession";

const PREVIEW_STATUSES: VoiceSessionStatus[] = [
  "idle",
  "listening",
  "speaking",
  "delegating",
  "ended",
];

export function VoiceMascotPreview() {
  const [status, setStatus] = useState<VoiceSessionStatus>("idle");
  const [assistantAudioLevel, setAssistantAudioLevel] = useState(0);
  const [micAudioLevel, setMicAudioLevel] = useState(0);
  const [gestureOverride, setGestureOverride] =
    useState<MascotGestureOverride>("auto");
  const [showProductionModal, setShowProductionModal] = useState(false);

  return (
    <main
      className="min-h-screen bg-[#080808] px-4 py-8 text-slate-100 sm:px-8"
      data-testid="voice-mascot-preview"
    >
      <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section className="relative flex min-h-[520px] items-center justify-center overflow-hidden rounded-[32px] border border-white/10 bg-[radial-gradient(circle_at_50%_35%,rgba(255,194,26,0.12),transparent_42%),linear-gradient(145deg,#171717,#0b0b0b)] p-8">
          <AnimatedMorshidiMascot
            status={status}
            assistantAudioLevel={assistantAudioLevel}
            micAudioLevel={micAudioLevel}
            gestureOverride={gestureOverride}
          />
        </section>

        <aside className="rounded-[28px] border border-white/10 bg-[#111] p-6 shadow-2xl shadow-black/50">
          <p className="text-xs font-bold uppercase tracking-[0.22em] text-[#ffc21a]">
            Development-only harness
          </p>
          <h1 className="mt-3 text-2xl font-semibold">Morshidi motion states</h1>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Mocked UI state and audio energy only. This page never starts a voice session.
          </p>

          <button
            type="button"
            onClick={() => setShowProductionModal(true)}
            className="mt-5 min-h-11 w-full rounded-xl border border-[#ffc21a]/45 bg-[#ffc21a]/10 px-4 py-2 text-sm font-semibold text-[#ffd45a] transition-colors hover:bg-[#ffc21a]/15"
          >
            Open real modal shell
          </button>

          <div className="mt-6 grid grid-cols-2 gap-2" aria-label="Mascot state">
            {PREVIEW_STATUSES.map((previewStatus) => (
              <button
                key={previewStatus}
                type="button"
                aria-pressed={status === previewStatus}
                onClick={() => setStatus(previewStatus)}
                className="min-h-11 rounded-xl border border-white/10 px-3 py-2 text-sm font-medium capitalize text-slate-300 transition-colors hover:border-[#ffc21a]/50 hover:text-white aria-pressed:border-[#ffc21a]/60 aria-pressed:bg-[#ffc21a]/15 aria-pressed:text-[#ffd45a]"
              >
                {previewStatus}
              </button>
            ))}
          </div>

          <label className="mt-7 block text-sm font-medium text-slate-200">
            Assistant audio: {assistantAudioLevel.toFixed(2)}
            <input
              data-testid="assistant-audio-level"
              className="mt-3 block w-full accent-[#ffc21a]"
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={assistantAudioLevel}
              onChange={(event) => setAssistantAudioLevel(Number(event.target.value))}
            />
          </label>

          <label className="mt-6 block text-sm font-medium text-slate-200">
            Student microphone: {micAudioLevel.toFixed(2)}
            <input
              data-testid="microphone-audio-level"
              className="mt-3 block w-full accent-purple-500"
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={micAudioLevel}
              onChange={(event) => setMicAudioLevel(Number(event.target.value))}
            />
          </label>

          <fieldset className="mt-6">
            <legend className="text-sm font-medium text-slate-200">Gesture verification</legend>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {(["auto", "none", "left", "right"] as const).map((gesture) => (
                <button
                  key={gesture}
                  type="button"
                  aria-pressed={gestureOverride === gesture}
                  onClick={() => setGestureOverride(gesture)}
                  className="min-h-11 rounded-xl border border-white/10 px-3 py-2 text-sm font-medium capitalize text-slate-300 transition-colors hover:border-[#ffc21a]/50 hover:text-white aria-pressed:border-[#ffc21a]/60 aria-pressed:bg-[#ffc21a]/15 aria-pressed:text-[#ffd45a]"
                >
                  {gesture}
                </button>
              ))}
            </div>
          </fieldset>

          <dl className="mt-7 grid gap-2 rounded-2xl border border-white/[0.07] bg-black/30 p-4 text-xs">
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Status</dt>
              <dd data-testid="preview-status" className="font-semibold text-slate-200">
                {status}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Gesture</dt>
              <dd data-testid="preview-gesture" className="font-semibold text-slate-200">
                {gestureOverride}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Speaking motion</dt>
              <dd data-testid="preview-speaking" className="font-semibold text-slate-200">
                {String(
                  (status === "speaking" || assistantAudioLevel >= 0.035) &&
                    !["delegating", "ended", "error"].includes(status),
                )}
              </dd>
            </div>
          </dl>
        </aside>
      </div>

      <LiveVoiceSession
        isOpen={showProductionModal}
        onClose={() => setShowProductionModal(false)}
      />
    </main>
  );
}
