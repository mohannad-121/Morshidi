"use client";

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
 * 1. 100% authentic, untouched official character artwork (glasses, hair, beard, cream suit).
 * 2. Pristine unified silhouette with zero shoulder gaps, zero detached limbs, and zero facial distortion.
 * 3. Gentle continuous idle breathing while resting or listening.
 * 4. Subtle, natural academic speaking cadence/sway when actively speaking.
 * 5. Reactive atmospheric aura reflecting operational state (explaining, delegating, listening).
 * 6. Full prefers-reduced-motion accessibility compliance.
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
      data-mouth-state="closed"
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

      {/* Main Mascot Container with Unified Silhouette & Motion */}
      <div
        className={`relative ${sizeClasses} ${
          isActuallySpeaking ? "animate-mascot-speaking" : "animate-mascot-breathe"
        } transition-transform duration-500 overflow-visible`}
        style={{
          WebkitMaskImage:
            "linear-gradient(to bottom, black 0%, black 86%, transparent 100%)",
          maskImage:
            "linear-gradient(to bottom, black 0%, black 86%, transparent 100%)",
        }}
        data-testid="mascot-body-container"
      >
        {/* Authentic Official Morshidi Mascot — Pristine Unified Silhouette */}
        <div
          className="relative w-full h-full pointer-events-none"
          data-testid="morshidi-mascot-unified"
        >
          <Image
            src="/brand/mascot/morshidi-mascot.png"
            alt="مرشدي"
            width={777}
            height={759}
            className="w-full h-full object-contain pointer-events-none"
          />
        </div>
      </div>
    </div>
  );
}
