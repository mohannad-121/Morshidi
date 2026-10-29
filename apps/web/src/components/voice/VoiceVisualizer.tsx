"use client";

import { useEffect, useRef } from "react";
import type { VoiceSessionStatus } from "@/lib/voice/webrtc-voice-session";

interface VoiceVisualizerProps {
  status: VoiceSessionStatus;
  micLevel: number;
  assistantLevel: number;
  className?: string;
}

export function VoiceVisualizer({
  status,
  micLevel,
  assistantLevel,
  className = "",
}: VoiceVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const phaseRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number | null = null;
    let isRunning = true;

    const render = () => {
      if (!isRunning) return;

      phaseRef.current += 0.05;
      const phase = phaseRef.current;

      const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
      const width = canvas.clientWidth || 300;
      const height = canvas.clientHeight || 80;

      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr;
        canvas.height = height * dpr;
      }

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, width, height);

      const centerY = height / 2;
      const isAssistant = status === "speaking";
      const isUser = status === "listening" && micLevel > 0.05;
      const isDelegating = status === "delegating";

      const primaryColor = isAssistant
        ? "rgba(255, 194, 26, " // Gold when assistant speaks
        : isUser
        ? "rgba(168, 85, 247, " // Purple when student speaks
        : isDelegating
        ? "rgba(56, 189, 248, " // Blue/Cyan when checking academic data
        : "rgba(148, 163, 184, "; // Muted slate when quiet

      const energy = isAssistant
        ? Math.max(0.15, assistantLevel * 1.5)
        : isUser
        ? Math.max(0.15, micLevel * 1.8)
        : isDelegating
        ? 0.35
        : 0.08;

      for (let waveIndex = 0; waveIndex < 3; waveIndex++) {
        ctx.beginPath();
        const waveOffset = waveIndex * (Math.PI / 3);
        const waveSpeed = 1 + waveIndex * 0.4;
        const waveAmp = (height * 0.28) * energy * (1 - waveIndex * 0.2);

        ctx.moveTo(0, centerY);
        for (let x = 0; x <= width; x += 4) {
          const normX = x / width;
          const envelope = Math.sin(normX * Math.PI);
          const y =
            centerY +
            Math.sin(normX * 10 * waveSpeed + phase * waveSpeed + waveOffset) *
              waveAmp *
              envelope;
          ctx.lineTo(x, y);
        }

        ctx.strokeStyle = `${primaryColor}${0.7 - waveIndex * 0.2})`;
        ctx.lineWidth = waveIndex === 0 ? 3 : 1.5;
        ctx.lineCap = "round";
        ctx.stroke();
      }

      ctx.restore();
      if (isRunning && typeof window !== "undefined" && process.env.NODE_ENV !== "test") {
        animId = requestAnimationFrame(render);
      }
    };

    render();
    return () => {
      isRunning = false;
      if (animId !== null) {
        cancelAnimationFrame(animId);
      }
    };
  }, [status, micLevel, assistantLevel]);

  return (
    <div className={`relative flex items-center justify-center overflow-hidden ${className}`}>
      <canvas
        ref={canvasRef}
        className="w-full h-full block"
        aria-hidden="true"
      />
    </div>
  );
}
