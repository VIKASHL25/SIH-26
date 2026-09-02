import React from 'react';

interface HealthBadgeProps {
  status?: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const HealthBadge: React.FC<HealthBadgeProps> = ({
  status = 'NOMINAL',
  className = '',
  size = 'md',
}) => {
  const normStatus = status.toUpperCase();

  let colorClasses = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 shadow-glow-nominal';
  let dotColor = 'bg-emerald-400';
  let label = 'NOMINAL';

  if (normStatus.includes('WARN') || normStatus.includes('DEGRADED')) {
    colorClasses = 'bg-amber-500/15 text-amber-400 border-amber-500/40 shadow-glow-warning';
    dotColor = 'bg-amber-400';
    label = 'WARNING';
  } else if (normStatus.includes('CRIT') || normStatus.includes('FAULT') || normStatus.includes('ERROR')) {
    colorClasses = 'bg-red-500/20 text-red-400 border-red-500/50 shadow-glow-critical animate-pulse';
    dotColor = 'bg-red-500';
    label = normStatus.includes('CRIT') ? 'CRITICAL ALERT' : 'PROPULSION FAULT';
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-xs font-semibold tracking-wider',
    lg: 'px-4 py-1.5 text-sm font-bold tracking-widest',
  }[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border uppercase font-mono transition-all duration-300 ${sizeClasses} ${colorClasses} ${className}`}
    >
      <span className={`w-2 h-2 rounded-full ${dotColor} animate-ping-slow`} />
      <span>{label}</span>
    </span>
  );
};
