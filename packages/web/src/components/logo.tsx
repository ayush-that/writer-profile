interface LogoProps {
  className?: string;
}

export function CadenceLogo({ className = "w-8 h-8" }: LogoProps) {
  return (
    <svg viewBox="0 0 40 40" fill="none" className={className}>
      <defs>
        <linearGradient id="cadence-gradient" x1="0" y1="0" x2="40" y2="40">
          <stop offset="0%" stopColor="#FF6B1A" />
          <stop offset="100%" stopColor="#FF5300" />
        </linearGradient>
        <linearGradient id="cadence-shine" x1="0" y1="0" x2="0" y2="40">
          <stop offset="0%" stopColor="white" stopOpacity="0.3" />
          <stop offset="50%" stopColor="white" stopOpacity="0" />
        </linearGradient>
      </defs>

      <rect width="40" height="40" rx="12" fill="url(#cadence-gradient)" />
      <rect width="40" height="40" rx="12" fill="url(#cadence-shine)" />

      <g>
        <path
          d="M10 20C10 20 12 14 14 14C16 14 16 26 18 26C20 26 20 14 22 14"
          stroke="white"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
          opacity="0.9"
        />
        <path
          d="M22 14C24 14 24 26 26 26C28 26 28 14 30 14"
          stroke="white"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
          opacity="0.9"
        />
      </g>

      <circle cx="33" cy="10" r="3" fill="white" opacity="0.4" />
    </svg>
  );
}
