interface CircularProgressProps {
  value: number;
  max: number;
  size?: number;
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
  className?: string;
}

export function CircularProgress({
  value,
  max,
  size = 120,
  strokeWidth = 10,
  label,
  sublabel,
  className = "",
}: CircularProgressProps) {
  const safeMax = Number(max) || 0;
  const safeValue = Number(value) || 0;
  const percentage = safeMax > 0 ? Math.min(100, Math.max(0, Math.round((safeValue / safeMax) * 100))) : 0;

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className={`relative flex flex-col items-center justify-center ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="rotate-[-90deg]"
        aria-hidden="true"
      >
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#EDE2C5"
          strokeWidth={strokeWidth}
          fill="none"
          strokeOpacity={0.6}
        />
        {/* Progress fill */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#A66F00"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="none"
          className="transition-all duration-700 ease-out"
        />
      </svg>
      {/* Center text */}
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-xl font-bold font-mono text-[#28241C]">{percentage}%</span>
        {label ? <span className="text-[10px] font-semibold text-[#726B5E]">{label}</span> : null}
      </div>
      {sublabel ? <span className="mt-2 text-xs text-[#726B5E]">{sublabel}</span> : null}
    </div>
  );
}
