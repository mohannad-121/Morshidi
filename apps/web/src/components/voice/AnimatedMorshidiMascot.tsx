"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import type { VoiceSessionStatus } from "@/lib/voice/webrtc-voice-session";
import { ASSISTANT_SPEECH_START_LEVEL } from "@/lib/voice/voice-activity";

export type MascotMouthState = "closed" | "half" | "open";
export type MascotGestureOverride = "auto" | "none" | "left" | "right";

export interface AnimatedMorshidiMascotProps {
  /** Current voice session status. */
  status: VoiceSessionStatus;
  /** Normalized remote assistant audio energy (0.0 to 1.0). */
  assistantAudioLevel?: number;
  /** Normalized student microphone energy (0.0 to 1.0). */
  micAudioLevel?: number;
  /** Optional custom container CSS classes. */
  className?: string;
  /** Compact floating size or standard Live Voice modal size. */
  sizePreset?: "compact" | "standard";
  /** Development/verification control; production callers leave this as auto. */
  gestureOverride?: MascotGestureOverride;
}

const MOUTH_OPEN_LEVEL = 0.14;
const RIG_ROOT = "/brand/mascot/rig";
const OFFICIAL_MASCOT = "/brand/mascot/morshidi-mascot.png";

/**
 * Natural speech cadence controller for the 2D Morshidi mascot.
 * Alternates mouth aperture across a multi-beat syllabic rhythm (~4 syllables/sec)
 * driven by remote assistant audio energy. Attack is immediate; closures during pauses are crisp.
 */
export function getMascotMouthState(
  assistantAudioLevel: number,
  canAnimateSpeech: boolean,
  elapsedMs = 0,
): MascotMouthState {
  if (!canAnimateSpeech || assistantAudioLevel < ASSISTANT_SPEECH_START_LEVEL) {
    return "closed";
  }

  // 4-beat syllabic cycle with organic timing (150ms, 120ms, 170ms, 140ms = 580ms total)
  const PHRASE_DURATION = 580;
  const phraseTime = Math.max(0, elapsedMs) % PHRASE_DURATION;

  let beatProgress = 0;
  if (phraseTime < 150) {
    beatProgress = phraseTime / 150;
  } else if (phraseTime < 270) {
    beatProgress = (phraseTime - 150) / 120;
  } else if (phraseTime < 440) {
    beatProgress = (phraseTime - 270) / 170;
  } else {
    beatProgress = (phraseTime - 440) / 140;
  }

  if (assistantAudioLevel >= MOUTH_OPEN_LEVEL) {
    if (beatProgress < 0.60) return "open";
    if (beatProgress < 0.85) return "half";
    return "closed";
  }

  return beatProgress < 0.70 ? "half" : "closed";
}

/**
 * Source-faithful 2D puppet for the official Morshidi mascot.
 *
 * The body/base never transforms. Remote assistant audio selects one of three
 * mouth-only drawings, while occasional arm transforms pivot around fixed
 * shoulder joints. Student microphone energy affects only the ambient aura.
 */
export function AnimatedMorshidiMascot({
  status,
  assistantAudioLevel = 0,
  micAudioLevel = 0,
  className = "",
  sizePreset = "standard",
  gestureOverride = "auto",
}: AnimatedMorshidiMascotProps) {
  const isAudioActive = assistantAudioLevel >= ASSISTANT_SPEECH_START_LEVEL;
  const canAnimateSpeech =
    (status === "speaking" || isAudioActive) &&
    status !== "delegating" &&
    status !== "ended" &&
    status !== "error";

  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const speechStartTimeRef = useRef<number | null>(null);
  const [speechElapsedMs, setSpeechElapsedMs] = useState(0);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPrefersReducedMotion(mediaQuery.matches);
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener("change", handler);
    return () => mediaQuery.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    if (prefersReducedMotion || !canAnimateSpeech || !isAudioActive) {
      speechStartTimeRef.current = null;
      setSpeechElapsedMs(0);
      return;
    }

    if (speechStartTimeRef.current === null) {
      speechStartTimeRef.current = performance.now();
    }

    let animationFrameId: number;
    let lastUpdate = performance.now();

    const updateCadence = (now: number) => {
      // ~25fps cadence update rate for mouth frames
      if (now - lastUpdate >= 40) {
        lastUpdate = now;
        if (speechStartTimeRef.current !== null) {
          setSpeechElapsedMs(now - speechStartTimeRef.current);
        }
      }
      animationFrameId = requestAnimationFrame(updateCadence);
    };

    animationFrameId = requestAnimationFrame(updateCadence);
    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [canAnimateSpeech, isAudioActive, prefersReducedMotion]);

  const effectiveElapsedMs =
    !prefersReducedMotion && canAnimateSpeech && isAudioActive && speechStartTimeRef.current !== null
      ? Math.max(speechElapsedMs, performance.now() - speechStartTimeRef.current)
      : 0;

  const mouthState = getMascotMouthState(assistantAudioLevel, canAnimateSpeech, effectiveElapsedMs);
  const isDelegating = status === "delegating";
  const isListening = status === "listening" && !isAudioActive;

  const sizeClasses =
    sizePreset === "compact"
      ? "h-[117px] w-[120px] sm:h-[136px] sm:w-[140px]"
      : "h-[180px] w-[185px] sm:h-[239px] sm:w-[245px]";

  const auraGlowColor = canAnimateSpeech
    ? "rgba(255, 194, 26, 0.25)"
    : isDelegating
      ? "rgba(56, 189, 248, 0.28)"
      : isListening && micAudioLevel > 0.05
        ? "rgba(168, 85, 247, 0.25)"
        : "rgba(255, 255, 255, 0.05)";
  const auraScale = 1 + Math.max(assistantAudioLevel, micAudioLevel) * 0.45;

  return (
    <div
      className={`relative flex select-none items-center justify-center ${className}`}
      role="img"
      aria-label="مرشدي — المرشد الأكاديمي الذكي"
      data-testid="animated-morshidi-mascot"
      data-status={status}
      data-speaking={canAnimateSpeech}
      data-motion={canAnimateSpeech ? "mouth-and-hands" : "still-body"}
      data-size-preset={sizePreset}
      data-mouth-state={mouthState}
      data-gesture={gestureOverride}
    >
      <div
        className="pointer-events-none absolute -z-10 rounded-full blur-2xl transition-all duration-300"
        style={{
          width: "85%",
          height: "85%",
          backgroundColor: auraGlowColor,
          transform: `scale(${auraScale})`,
        }}
        aria-hidden="true"
        data-testid="mascot-aura"
      />

      <div
        className={`relative overflow-visible ${sizeClasses}`}
        style={{
          WebkitMaskImage:
            "linear-gradient(to bottom, black 0%, black 86%, transparent 100%)",
          maskImage:
            "linear-gradient(to bottom, black 0%, black 86%, transparent 100%)",
        }}
        data-testid="mascot-body-container"
      >
        <div className="pointer-events-none absolute inset-0" data-testid="mascot-shoulder-underlay">
          <Image
            src={`${RIG_ROOT}/shoulder-restoration.png`}
            alt=""
            aria-hidden="true"
            width={975}
            height={800}
            loading="eager"
            unoptimized
            className="mascot-rig-shoulder-restoration h-full w-full object-contain"
          />
        </div>

        <div
          className="mascot-rig-body pointer-events-none absolute inset-0"
          data-testid="mascot-body-base"
        >
          <Image
            src={OFFICIAL_MASCOT}
            alt=""
            aria-hidden="true"
            width={975}
            height={800}
            loading="eager"
            unoptimized
            className="mascot-rig-body-image h-full w-full object-contain"
          />
          <span className="mascot-joint-anchor mascot-joint-left" data-testid="body-joint-left" />
          <span className="mascot-joint-anchor mascot-joint-right" data-testid="body-joint-right" />
        </div>

        <div
          className="mascot-rig-arm mascot-rig-arm-left pointer-events-none absolute inset-0"
          data-speaking={canAnimateSpeech}
          data-gesture={gestureOverride}
          data-testid="mascot-arm-left"
        >
          <Image
            src={OFFICIAL_MASCOT}
            alt=""
            aria-hidden="true"
            width={975}
            height={800}
            loading="eager"
            unoptimized
            className="mascot-rig-left-image h-full w-full object-contain"
          />
          <span className="mascot-joint-anchor mascot-joint-left" data-testid="arm-joint-left" />
        </div>

        <div
          className="mascot-rig-arm mascot-rig-arm-right pointer-events-none absolute inset-0"
          data-speaking={canAnimateSpeech}
          data-gesture={gestureOverride}
          data-testid="mascot-arm-right"
        >
          <Image
            src={OFFICIAL_MASCOT}
            alt=""
            aria-hidden="true"
            width={975}
            height={800}
            loading="eager"
            unoptimized
            className="mascot-rig-right-image h-full w-full object-contain"
          />
          <span className="mascot-joint-anchor mascot-joint-right" data-testid="arm-joint-right" />
        </div>

        <div className="pointer-events-none absolute inset-0" data-testid="mascot-mouth-layer">
          {(["closed", "half", "open"] as const).map((state) => (
            <Image
              key={state}
              src={`${RIG_ROOT}/mouth-${state}.svg`}
              alt=""
              aria-hidden="true"
              width={975}
              height={800}
              loading="eager"
              unoptimized
              className="mascot-mouth-frame absolute inset-0 h-full w-full object-contain"
              data-mouth-frame={state}
              data-active={mouthState === state}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
