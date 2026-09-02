import React, { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { useDigitalTwinStore } from '../../store/useDigitalTwinStore';
import { LineChart as ChartIcon, Flame, Gauge, Droplets } from 'lucide-react';

type ChartMode = 'thermal' | 'propulsion' | 'lubrication';

export const LiveCharts: React.FC = () => {
  const { frameHistory, currentFrame } = useDigitalTwinStore();
  const [mode, setMode] = useState<ChartMode>('thermal');

  // Prepare chart dataset from frame history
  const chartData = frameHistory.map((frame) => {
    const chtRes =
      frame.physics_model.cht_residual ??
      frame.physics_model.cht_residual_C ??
      (frame.telemetry.cht_C - frame.physics_model.expected_cht_C);

    const egtRes =
      frame.physics_model.egt_residual ??
      frame.physics_model.egt_residual_C ??
      (frame.telemetry.egt_C - frame.physics_model.expected_egt_C);

    const rpmRes =
      frame.physics_model.rpm_residual ??
      (frame.telemetry.rpm - frame.physics_model.expected_rpm);

    return {
      frame: frame.frame_index,
      timestamp: frame.timestamp_s,

      // Thermal
      cht: frame.telemetry.cht_C,
      expectedCht: frame.physics_model.expected_cht_C,
      chtResidual: Number(chtRes.toFixed(2)),

      egt: frame.telemetry.egt_C,
      expectedEgt: frame.physics_model.expected_egt_C,
      egtResidual: Number(egtRes.toFixed(2)),

      // Propulsion
      rpm: frame.telemetry.rpm,
      expectedRpm: frame.physics_model.expected_rpm,
      rpmResidual: Number(rpmRes.toFixed(1)),
      throttle: frame.telemetry.throttle_pct,
      load: frame.telemetry.load_pct,

      // Lubrication & Mechanical
      oilPressure: frame.telemetry.oil_pressure_bar,
      oilTemp: frame.telemetry.oil_temperature_C,
      vibration: frame.telemetry.vibration_rms,
    };
  });

  // Current residuals for quick inspection badge
  const curPhys = currentFrame?.physics_model;
  const currentChtRes =
    curPhys?.cht_residual ??
    curPhys?.cht_residual_C ??
    ((currentFrame?.telemetry.cht_C || 0) - (curPhys?.expected_cht_C || 0));

  const currentEgtRes =
    curPhys?.egt_residual ??
    curPhys?.egt_residual_C ??
    ((currentFrame?.telemetry.egt_C || 0) - (curPhys?.expected_egt_C || 0));

  return (
    <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 flex flex-col h-[380px]">
      {/* Chart Header & Tab Navigation */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-2 pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <ChartIcon className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase">
            Physics-Informed Digital Twin Tracking
          </h3>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
            ROLLING 120 FRAMES
          </span>
        </div>

        {/* Residual Badges */}
        <div className="hidden sm:flex items-center gap-2 font-mono text-[11px]">
          <span className="text-slate-400">CHT Δ Residual:</span>
          <span
            className={`font-bold px-1.5 py-0.5 rounded ${
              Math.abs(currentChtRes) > 5.0
                ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                : Math.abs(currentChtRes) > 2.5
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
            }`}
          >
            {currentChtRes > 0 ? `+${currentChtRes.toFixed(2)}` : currentChtRes.toFixed(2)} °C
          </span>

          <span className="text-slate-400 ml-2">EGT Δ Residual:</span>
          <span
            className={`font-bold px-1.5 py-0.5 rounded ${
              Math.abs(currentEgtRes) > 15.0
                ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                : Math.abs(currentEgtRes) > 8.0
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
            }`}
          >
            {currentEgtRes > 0 ? `+${currentEgtRes.toFixed(2)}` : currentEgtRes.toFixed(2)} °C
          </span>
        </div>

        {/* Mode Tabs */}
        <div className="flex items-center gap-1 bg-slate-900 p-1 rounded border border-slate-800">
          <button
            onClick={() => setMode('thermal')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono font-medium transition-all ${
              mode === 'thermal'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Flame className="w-3 h-3" />
            Thermal (CHT/EGT)
          </button>
          <button
            onClick={() => setMode('propulsion')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono font-medium transition-all ${
              mode === 'propulsion'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Gauge className="w-3 h-3" />
            RPM Dynamics
          </button>
          <button
            onClick={() => setMode('lubrication')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono font-medium transition-all ${
              mode === 'lubrication'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Droplets className="w-3 h-3" />
            Oil & Vibration
          </button>
        </div>
      </div>

      {/* Main Chart Area */}
      <div className="flex-1 w-full min-h-0">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            {mode === 'thermal' ? (
              <LineChart data={chartData} margin={{ top: 5, right: 15, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                <XAxis dataKey="frame" stroke="#64748B" tick={{ fontSize: 10, fill: '#94A3B8' }} />
                <YAxis
                  yAxisId="temp"
                  domain={['auto', 'auto']}
                  stroke="#64748B"
                  tick={{ fontSize: 10, fill: '#94A3B8' }}
                  label={{ value: 'Temp (°C)', angle: -90, position: 'insideLeft', fill: '#64748B', fontSize: 10 }}
                />
                <YAxis
                  yAxisId="res"
                  orientation="right"
                  domain={[-20, 20]}
                  stroke="#64748B"
                  tick={{ fontSize: 9, fill: '#64748B' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111722',
                    borderColor: '#1E293B',
                    borderRadius: '6px',
                    fontFamily: 'monospace',
                    fontSize: '11px',
                    color: '#F1F5F9',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', fontFamily: 'monospace' }} />
                <Line
                  yAxisId="temp"
                  type="monotone"
                  dataKey="cht"
                  name="CHT Measured"
                  stroke="#00F0FF"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  yAxisId="temp"
                  type="monotone"
                  dataKey="expectedCht"
                  name="CHT Expected (Physics)"
                  stroke="#0284C7"
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  yAxisId="temp"
                  type="monotone"
                  dataKey="egt"
                  name="EGT Measured"
                  stroke="#F59E0B"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  yAxisId="temp"
                  type="monotone"
                  dataKey="expectedEgt"
                  name="EGT Expected (Physics)"
                  stroke="#B45309"
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  yAxisId="res"
                  type="monotone"
                  dataKey="chtResidual"
                  name="CHT Residual (°C)"
                  stroke="#EF4444"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            ) : mode === 'propulsion' ? (
              <LineChart data={chartData} margin={{ top: 5, right: 15, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                <XAxis dataKey="frame" stroke="#64748B" tick={{ fontSize: 10, fill: '#94A3B8' }} />
                <YAxis
                  yAxisId="rpm"
                  domain={['dataMin - 100', 'dataMax + 100']}
                  stroke="#64748B"
                  tick={{ fontSize: 10, fill: '#94A3B8' }}
                  label={{ value: 'RPM', angle: -90, position: 'insideLeft', fill: '#64748B', fontSize: 10 }}
                />
                <YAxis
                  yAxisId="pct"
                  orientation="right"
                  domain={[0, 100]}
                  stroke="#64748B"
                  tick={{ fontSize: 10, fill: '#94A3B8' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111722',
                    borderColor: '#1E293B',
                    borderRadius: '6px',
                    fontFamily: 'monospace',
                    fontSize: '11px',
                    color: '#F1F5F9',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', fontFamily: 'monospace' }} />
                <Line
                  yAxisId="rpm"
                  type="monotone"
                  dataKey="rpm"
                  name="Engine RPM"
                  stroke="#00F0FF"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  yAxisId="rpm"
                  type="monotone"
                  dataKey="expectedRpm"
                  name="Expected RPM"
                  stroke="#0284C7"
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  yAxisId="pct"
                  type="monotone"
                  dataKey="throttle"
                  name="Throttle %"
                  stroke="#10B981"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  yAxisId="pct"
                  type="monotone"
                  dataKey="load"
                  name="Engine Load %"
                  stroke="#8B5CF6"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            ) : (
              <LineChart data={chartData} margin={{ top: 5, right: 15, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                <XAxis dataKey="frame" stroke="#64748B" tick={{ fontSize: 10, fill: '#94A3B8' }} />
                <YAxis
                  yAxisId="oil"
                  domain={[0, 7]}
                  stroke="#64748B"
                  tick={{ fontSize: 10, fill: '#94A3B8' }}
                  label={{ value: 'Oil (bar)', angle: -90, position: 'insideLeft', fill: '#64748B', fontSize: 10 }}
                />
                <YAxis
                  yAxisId="vib"
                  orientation="right"
                  domain={[0, 0.5]}
                  stroke="#64748B"
                  tick={{ fontSize: 10, fill: '#94A3B8' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111722',
                    borderColor: '#1E293B',
                    borderRadius: '6px',
                    fontFamily: 'monospace',
                    fontSize: '11px',
                    color: '#F1F5F9',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', fontFamily: 'monospace' }} />
                <Line
                  yAxisId="oil"
                  type="monotone"
                  dataKey="oilPressure"
                  name="Oil Pressure (bar)"
                  stroke="#00F0FF"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  yAxisId="oil"
                  type="monotone"
                  dataKey="oilTemp"
                  name="Oil Temp (°C)"
                  stroke="#F59E0B"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  yAxisId="vib"
                  type="monotone"
                  dataKey="vibration"
                  name="Vibration RMS (g)"
                  stroke="#EF4444"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            )}
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-slate-500 font-mono text-xs">
            CONNECTING TO TELEMETRY STREAM...
          </div>
        )}
      </div>
    </div>
  );
};
