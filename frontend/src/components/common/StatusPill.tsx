import React from 'react';

interface StatusPillProps {
  label: string;
  variant?: 'cyan' | 'green' | 'amber' | 'red' | 'slate';
  dot?: boolean;
  className?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({
  label,
  variant = 'cyan',
  dot = true,
  className = '',
}) => {
  const variantStyles = {
    cyan: 'bg-cyan-950/40 text-cyan-300 border-cyan-800/50 shadow-glow-cyan',
    green: 'bg-emerald-950/40 text-emerald-300 border-emerald-800/50',
    amber: 'bg-amber-950/40 text-amber-300 border-amber-800/50',
    red: 'bg-red-950/40 text-red-300 border-red-800/50',
    slate: 'bg-slate-900 text-slate-300 border-slate-700',
  }[variant];

  const dotColors = {
    cyan: 'bg-cyan-400',
    green: 'bg-emerald-400',
    amber: 'bg-amber-400',
    red: 'bg-red-400',
    slate: 'bg-slate-400',
  }[variant];

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-medium border uppercase tracking-wider ${variantStyles} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors}`} />}
      <span>{label}</span>
    </span>
  );
};
