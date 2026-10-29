"use client";

import { AudioLines, Sparkles } from "lucide-react";

interface LiveVoiceButtonProps {
  onClick: () => void;
  disabled?: boolean;
  className?: string;
  variant?: "floating" | "compact" | "composer";
}

export function LiveVoiceButton({
  onClick,
  disabled = false,
  className = "",
  variant = "composer",
}: LiveVoiceButtonProps) {
  if (variant === "compact") {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border border-amber-500/35 bg-amber-500/10 hover:bg-amber-500/20 text-[#ffc21a] text-xs font-bold shadow-sm transition-all hover:scale-102 active:scale-98 disabled:opacity-40 disabled:pointer-events-none ${className}`}
        aria-label="بدء محادثة صوتية مباشرة مع مرشدي"
        title="محادثة صوتية مباشرة (Speech-to-Speech)"
      >
        <AudioLines size={15} className="animate-pulse" />
        <span>محادثة صوتية</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`relative group inline-flex items-center gap-2.5 px-4 py-2.5 rounded-2xl border border-amber-500/40 bg-gradient-to-r from-amber-500/15 to-purple-500/10 hover:from-amber-500/25 hover:to-purple-500/20 text-[#ffc21a] hover:text-amber-300 font-bold text-xs shadow-md shadow-black/40 transition-all hover:scale-103 active:scale-97 disabled:opacity-40 disabled:pointer-events-none ${className}`}
      aria-label="بدء محادثة صوتية مباشرة مع مرشدي"
      title="محادثة صوتية مباشرة مع مرشدي (GPT-Live)"
    >
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
      </span>
      <AudioLines size={16} />
      <span>محادثة صوتية</span>
      <Sparkles size={13} className="text-amber-400 opacity-80 group-hover:rotate-12 transition-transform" />
    </button>
  );
}

