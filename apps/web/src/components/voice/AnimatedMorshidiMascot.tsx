"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import type { VoiceSessionStatus } from "@/lib/voice/webrtc-voice-session";

export interface AnimatedMorshidiMascotProps {
  /** Current voice session status */
  status: VoiceSessionStatus;
  /** Normalized assistant speech volume (0.0 to 1.0) */
  assistantAudioLevel?: number;
  /** Normalized student microphone volume (0.0 to 1.0) */
  micAudioLevel?: number;
  /** Optional custom container CSS classes */
  className?: string;
  /** Optional size preset: "compact" (mobile header/floating), "standard" (modal desktop/mobile) */
  sizePreset?: "compact" | "standard";
}

export type MascotMouthState = "closed" | "half" | "open";

/**
 * AnimatedMorshidiMascot
 *
 * Renders the official Morshidi academic advisor mascot with:
 * 1. Gentle, clearly visible continuous idle breathing (alive while listening or resting).
 * 2. Speech-synchronized mouth animation (closed, half, open) driven directly by real assistant audio playback energy.
 * 3. Natural, clearly visible explanatory hand gestures while explaining concepts.
 * 4. Reactive aura indicating listening, speaking, and academic verification states.
 * 5. Full prefers-reduced-motion accessibility compliance.
 */
export function AnimatedMorshidiMascot({
  status,
  assistantAudioLevel = 0,
  micAudioLevel = 0,
  className = "",
  sizePreset = "standard",
}: AnimatedMorshidiMascotProps) {
  // Real assistant audio energy presence
  const isAudioActive = assistantAudioLevel >= 0.035;

  // Assistant is actively speaking if status is explicitly "speaking" OR if speech audio energy is playing
  const isActuallySpeaking =
    (status === "speaking" || isAudioActive) &&
    status !== "delegating" &&
    status !== "ended" &&
    status !== "error";

  const isDelegating = status === "delegating";
  const isListening = status === "listening" && !isAudioActive;

  // Speech-synchronized mouth state tracking with jitter-prevention hold
  const [mouthState, setMouthState] = useState<MascotMouthState>("closed");
  const lastStateChangeRef = useRef<number>(0);
  const currentMouthRef = useRef<MascotMouthState>("closed");

  useEffect(() => {
    // When assistant is not speaking, mouth immediately returns to closed resting state
    if (!isActuallySpeaking) {
      if (currentMouthRef.current !== "closed") {
        currentMouthRef.current = "closed";
        setMouthState("closed");
      }
      return;
    }

    const now = Date.now();
    let targetMouth: MascotMouthState = "closed";

    // Dynamic threshold: peaks/emphasis switch to full open; intermediate syllables to half
    if (assistantAudioLevel >= 0.14) {
      targetMouth = "open";
    } else if (assistantAudioLevel >= 0.035) {
      targetMouth = "half";
    } else {
      // Quiet pause between syllables in an active speech turn
      targetMouth = "closed";
    }

    // Immediate open on speech attack; 70ms minimum frame hold on closing to prevent 60Hz flicker
    const timeSinceChange = now - lastStateChangeRef.current;
    if (targetMouth !== currentMouthRef.current) {
      if (targetMouth === "open" || timeSinceChange >= 70) {
        currentMouthRef.current = targetMouth;
        lastStateChangeRef.current = now;
        setMouthState(targetMouth);
      }
    }
  }, [isActuallySpeaking, assistantAudioLevel]);

  // Size styling: Desktop 220–260px, Mobile 170–200px (standard modal)
  const sizeClasses =
    sizePreset === "compact"
      ? "w-[120px] h-[117px] sm:w-[140px] sm:h-[136px]"
      : "w-[185px] h-[180px] sm:w-[245px] sm:h-[239px]";

  // Reactive glow color based on operational state
  const auraGlowColor = isActuallySpeaking
    ? "rgba(255, 194, 26, 0.25)" // Rich Gold when explaining
    : isDelegating
    ? "rgba(56, 189, 248, 0.28)" // Bright Cyan when verifying academic rules
    : isListening && micAudioLevel > 0.05
    ? "rgba(168, 85, 247, 0.25)" // Purple when actively listening to student
    : "rgba(255, 255, 255, 0.05)"; // Gentle ambient

  const auraScale = 1 + Math.max(assistantAudioLevel, micAudioLevel) * 0.45;

  return (
    <div
      className={`relative flex items-center justify-center select-none ${className}`}
      role="img"
      aria-label="مرشدي — المرشد الأكاديمي الذكي"
      data-testid="animated-morshidi-mascot"
      data-status={status}
      data-speaking={isActuallySpeaking}
      data-mouth-state={mouthState}
    >
      {/* Dynamic Atmospheric Aura behind Mascot */}
      <div
        className="absolute rounded-full filter blur-2xl pointer-events-none transition-all duration-300 -z-10"
        style={{
          width: "85%",
          height: "85%",
          backgroundColor: auraGlowColor,
          transform: `scale(${auraScale})`,
        }}
        aria-hidden="true"
      />

      {/* Main Mascot Container with Idle Breathing */}
      <div
        className={`relative ${sizeClasses} animate-mascot-breathe overflow-visible`}
        style={{
          WebkitMaskImage:
            "linear-gradient(to bottom, black 0%, black 86%, transparent 100%)",
          maskImage:
            "linear-gradient(to bottom, black 0%, black 86%, transparent 100%)",
        }}
      >
        {/* Layer 1: Torso Base with Synchronized Mouth Variations (Behind Arms) */}
        {/* Closed Mouth (Default / Resting / Listening) */}
        <div
          className="absolute inset-0 w-full h-full pointer-events-none transition-opacity duration-75"
          style={{ opacity: mouthState === "closed" ? 1 : 0 }}
          data-testid="torso-closed"
        >
          <Image
            src="/brand/mascot/torso-closed.png"
            alt="مرشدي"
            width={777}
            height={759}
            className="w-full h-full object-contain pointer-events-none"
          />
        </div>

        {/* Half Open Mouth (Soft / Intermediate Syllables) */}
        <div
          className="absolute inset-0 w-full h-full pointer-events-none transition-opacity duration-75"
          style={{ opacity: mouthState === "half" ? 1 : 0 }}
          data-testid="torso-half"
        >
          <Image
            src="/brand/mascot/torso-half.png"
            alt=""
            width={777}
            height={759}
            className="w-full h-full object-contain pointer-events-none"
            aria-hidden="true"
          />
        </div>

        {/* Full Open Mouth (Emphasis / Vowels / Speech Peaks) */}
        <div
          className="absolute inset-0 w-full h-full pointer-events-none transition-opacity duration-75"
          style={{ opacity: mouthState === "open" ? 1 : 0 }}
          data-testid="torso-open"
        >
          <Image
            src="/brand/mascot/torso-open.png"
            alt=""
            width={777}
            height={759}
            className="w-full h-full object-contain pointer-events-none"
            aria-hidden="true"
          />
        </div>

        {/* Layer 2: Left Arm (Viewer's Left) — Positioned ON TOP of Torso for Unobscured Gesture */}
        <div
          className={`absolute inset-0 w-full h-full pointer-events-none transition-transform duration-500 ${
            isActuallySpeaking ? "animate-mascot-gesture-left" : ""
          }`}
          data-testid="arm-left-container"
        >
          <Image
            src="/brand/mascot/arm-left.png"
            alt=""
            width={777}
            height={759}
            className="w-full h-full object-contain pointer-events-none"
            aria-hidden="true"
          />
        </div>

        {/* Layer 3: Right Arm (Viewer's Right) — Positioned ON TOP of Torso for Unobscured Gesture */}
        <div
          className={`absolute inset-0 w-full h-full pointer-events-none transition-transform duration-500 ${
            isActuallySpeaking ? "animate-mascot-gesture-right" : ""
          }`}
          data-testid="arm-right-container"
        >
          <Image
            src="/brand/mascot/arm-right.png"
            alt=""
            width={777}
            height={759}
            className="w-full h-full object-contain pointer-events-none"
            aria-hidden="true"
          />
        </div>
      </div>
    </div>
  );
}
