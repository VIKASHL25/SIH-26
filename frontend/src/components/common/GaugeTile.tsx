import React, { useMemo } from 'react';
import { ResponsiveContainer, LineChart, Line, YAxis } from 'recharts';

export interface GaugeTileProps {
  label: string;
  value: number;
  unit: string;
  min: number;
  max: number;
  nominalLow: number;
  nominalHigh: number;
  warningHigh?: number;
  warningLow?: number;
  expectedValue?: number;
  precision?: number;
  history?: number[];
  icon?: React.ReactNode;
}

export const GaugeTile: React.FC<GaugeTileProps> = ({
  label,
  value,
  unit,
  min,
  max,
  nominalLow,
  nominalHigh,
  warningHigh = max,
  warningLow = min,
  expectedValue,
  precision = 1,
  history = [],
  icon,
}) => {
  // Determine severity status
  const isCritical = value > warningHigh || value < warningLow;
  const isWarning = !isCritical && (value > nominalHigh || value < nominalLow);

  const statusColor = isCritical
    ? 'text-red-400'
    : isWarning
    ? 'text-amber-400'
    : 'text-cyan-400';

  const statusBg = isCritical
    ? 'border-red-500/40 bg-red-950/15 shadow-glow-critical'
    : isWarning
    ? 'border-amber-500/30 bg-amber-950/10'
    : 'border-avionics-border bg-avionics-surface hover:border-slate-700';

  // Calculate arc values for 180° semi-circle dial
  const clampedValue = Math.min(Math.max(value, min), max);
  const normalizedVal = (clampedValue - min) / (max - min || 1);

  // Sparkline data
  const sparklineData = useMemo(() => {
    return history.slice(-25).map((v, i) => ({ idx: i, val: v }));
  }, [history]);

  // SVG Arc calculation for 180-degree semi-circle gauge
  const radius = 46;
  const strokeWidth = 7;
  const circumference = Math.PI * radius; // Half-circle arc length
  const strokeDashoffset = circumference - normalizedVal * circumference;

  return (
    <div
      className={`relative flex flex-col justify-between rounded-lg border p-3.5 transition-all duration-300 ${statusBg}`}
    >
      {/* Top Header */}
      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="flex items-center gap-1.5 min-w-0">
          {icon && <span className="text-slate-400">{icon}</span>}
          <span className="text-xs font-medium text-slate-300 tracking-wider truncate uppercase">
            {label}
          </span>
        </div>
        <span
          className={`text-[10px] font-mono px-1.5 py-0.5 rounded uppercase font-semibold ${
            isCritical
              ? 'bg-red-500/20 text-red-400 border border-red-500/40'
              : isWarning
              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
              : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
          }`}
        >
          {isCritical ? 'CRITICAL' : isWarning ? 'WARN' : 'NORM'}
        </span>
      </div>

      {/* Gauge Visualization & Numeric Value */}
      <div className="flex items-center justify-between gap-2 my-1">
        {/* Semi-circular gauge SVG */}
        <div className="relative w-24 h-14 flex items-end justify-center overflow-hidden">
          <svg className="w-24 h-24 absolute top-0" viewBox="0 0 100 100">
            {/* Background track (semi-circle) */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke="#1E293B"
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset="0"
              transform="rotate(180 50 50)"
              strokeLinecap="round"
            />
            {/* Active value track */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke={isCritical ? '#EF4444' : isWarning ? '#F59E0B' : '#00F0FF'}
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              transform="rotate(180 50 50)"
              strokeLinecap="round"
              className="transition-all duration-300"
            />
          </svg>
          {/* Min & Max labels at base of arc */}
          <div className="w-full flex justify-between px-1 text-[9px] font-mono text-slate-500 absolute bottom-0">
            <span>{min}</span>
            <span>{max}</span>
          </div>
        </div>

        {/* Big Numeric Readout */}
        <div className="flex flex-col items-end">
          <div className="flex items-baseline gap-1">
            <span className={`text-2xl font-bold font-mono tracking-tight ${statusColor}`}>
              {value !== undefined && value !== null ? value.toFixed(precision) : '--'}
            </span>
            <span className="text-xs font-mono text-slate-400">{unit}</span>
          </div>

          {/* Expected Physics Model Reference if available */}
          {expectedValue !== undefined && (
            <div className="text-[11px] font-mono text-slate-400 mt-0.5 flex items-center gap-1">
              <span className="text-slate-500">Exp:</span>
              <span className="text-slate-300">{expectedValue.toFixed(precision)}</span>
              {value !== undefined && (
                <span
                  className={`text-[10px] ${
                    Math.abs(value - expectedValue) > (nominalHigh - nominalLow) * 0.15
                      ? 'text-amber-400'
                      : 'text-slate-400'
                  }`}
                >
                  (Δ{(value - expectedValue > 0 ? '+' : '') + (value - expectedValue).toFixed(precision)})
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Rolling Sparkline */}
      <div className="h-8 w-full mt-1 pt-1 border-t border-slate-800/60">
        {sparklineData.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparklineData}>
              <YAxis domain={['dataMin - 1', 'dataMax + 1']} hide />
              <Line
                type="monotone"
                dataKey="val"
                stroke={isCritical ? '#EF4444' : isWarning ? '#F59E0B' : '#00F0FF'}
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-[10px] font-mono text-slate-600">
            AWAITING TELEMETRY STREAM
          </div>
        )}
      </div>
    </div>
  );
};
