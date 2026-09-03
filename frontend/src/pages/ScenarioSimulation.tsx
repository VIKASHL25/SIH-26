import React, { useState } from 'react';
import { api } from '../api/client';
import {
  Compass,
  Mountain,
  Sun,
  Gauge,
  Play,
  AlertCircle,
  Activity,
  CheckCircle2,
} from 'lucide-react';
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

export const ScenarioSimulation: React.FC = () => {
  const [scenarioName, setScenarioName] = useState<string>('high_altitude');
  const [altitude, setAltitude] = useState<number>(5200);
  const [ambientTemp, setAmbientTemp] = useState<number>(-18.0);
  const [durationSteps, setDurationSteps] = useState<number>(40);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [simResults, setSimResults] = useState<any | null>(null);

  const presets = [
    {
      id: 'high_altitude',
      name: 'High Altitude ISR Loiter',
      altitude: 5200,
      ambientTemp: -18.0,
      steps: 40,
      desc: 'Thin air density reduces thermodynamic cooling efficiency and elevates manifold thermal stress.',
    },
    {
      id: 'hot_weather',
      name: 'Desert / Hot Weather Deployment',
      altitude: 1200,
      ambientTemp: 46.0,
      steps: 45,
      desc: 'High ambient temperature severely compresses CHT cooling margins, stressing engine oil lubrication.',
    },
    {
      id: 'rapid_throttle_transitions',
      name: 'Rapid Throttle Maneuvers',
      altitude: 2500,
      ambientTemp: 22.0,
      steps: 30,
      desc: 'Aggressive step transitions in engine load trigger rapid exhaust gas temperature transients.',
    },
    {
      id: 'endurance_mission',
      name: 'Endurance Loiter Mission',
      altitude: 3000,
      ambientTemp: 15.0,
      steps: 50,
      desc: 'Long-duration ISR cruise evaluating steady-state thermal progression and lubricant consumption.',
    },
  ];

  const handleApplyPreset = (p: typeof presets[0]) => {
    setScenarioName(p.id);
    setAltitude(p.altitude);
    setAmbientTemp(p.ambientTemp);
    setDurationSteps(p.steps);
  };

  const handleRunSimulation = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await api.simulateScenario({
        scenario_name: scenarioName,
        altitude_m: altitude,
        ambient_temp_C: ambientTemp,
        duration_steps: durationSteps,
      });

      // Extract raw trajectory from backend (projected_trajectory or simulated_frames)
      const rawTrajectory = res.projected_trajectory || res.simulated_frames || [];
      const normalizedFrames = rawTrajectory.map((item: any, idx: number) => ({
        step: item.step ?? idx + 1,
        cht: Number((item.telemetry?.cht_C ?? item.cht ?? 0).toFixed(1)),
        egt: Number((item.telemetry?.egt_C ?? item.egt ?? 0).toFixed(1)),
        rpm: Math.round(item.telemetry?.rpm ?? item.rpm ?? 0),
        oilPressure: Number((item.telemetry?.oil_pressure_bar ?? item.oilPressure ?? 0).toFixed(2)),
        vibration: Number((item.telemetry?.vibration_rms ?? item.vibration ?? 0).toFixed(3)),
        health: Number((item.predicted_health_pct ?? item.health ?? 100).toFixed(1)),
        status: item.health_status ?? 'NOMINAL',
        fault: item.predicted_fault ?? 'normal',
      }));

      const peakCht = normalizedFrames.length > 0 ? Math.max(...normalizedFrames.map((f: any) => f.cht)) : 0;
      const peakEgt = normalizedFrames.length > 0 ? Math.max(...normalizedFrames.map((f: any) => f.egt)) : 0;
      const finalHealth = normalizedFrames.length > 0 ? normalizedFrames[normalizedFrames.length - 1].health : 100;

      const summary = res.summary || {
        peak_cht: peakCht,
        peak_egt: peakEgt,
        final_health: finalHealth,
        cooling_margin_status: peakCht > 155 ? 'DEGRADED_MARGIN' : 'ACCEPTABLE',
      };

      setSimResults({
        ...res,
        simulated_frames: normalizedFrames,
        summary,
      });
    } catch (err: any) {
      console.error('Scenario simulation execution error:', err);
      setErrorMessage(
        err?.response?.data?.detail || err?.message || 'Failed to execute scenario simulation. Please ensure backend services are running.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const frames = simResults?.simulated_frames || [];

  return (
    <div className="max-w-[1920px] mx-auto p-4 space-y-4">
      {/* Header */}
      <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Compass className="w-5 h-5 text-cyan-400" />
          <div>
            <h2 className="text-sm font-mono font-bold tracking-wider text-slate-100 uppercase">
              Mission Environmental & Operating Scenario Simulator
            </h2>
            <p className="text-[11px] font-mono text-slate-400">
              Thermodynamic physics projection and AI health assessment across high altitude, hot weather, and throttle transients
            </p>
          </div>
        </div>
      </div>

      {/* Error Banner if any */}
      {errorMessage && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-950/40 border border-red-500/50 text-red-300 text-xs font-mono">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Configuration & Presets */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Presets */}
        <div className="lg:col-span-4 bg-avionics-surface border border-avionics-border rounded-lg p-3.5 space-y-3">
          <h3 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase">
            Operational Scenarios
          </h3>

          <div className="space-y-2">
            {presets.map((p) => (
              <button
                key={p.id}
                onClick={() => handleApplyPreset(p)}
                className={`w-full p-2.5 rounded border text-left transition-all ${
                  scenarioName === p.id
                    ? 'bg-cyan-950/40 border-cyan-500/50 text-cyan-200 shadow-glow-cyan'
                    : 'bg-avionics-card border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                <div className="text-xs font-mono font-bold uppercase flex items-center justify-between">
                  <span>{p.name}</span>
                  {scenarioName === p.id && <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />}
                </div>
                <div className="text-[11px] font-mono text-slate-400 mt-1 leading-snug">{p.desc}</div>
                <div className="text-[10px] font-mono text-slate-500 mt-1.5 flex gap-3">
                  <span>Alt: {p.altitude}m</span>
                  <span>Temp: {p.ambientTemp}°C</span>
                  <span>Duration: {p.steps}s</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Controls */}
        <div className="lg:col-span-8 bg-avionics-surface border border-avionics-border rounded-lg p-3.5 space-y-4">
          <h3 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase pb-2 border-b border-slate-800">
            Environmental Parameter Constraints
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Altitude Slider */}
            <div className="bg-avionics-card p-3 rounded border border-slate-800 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                  <Mountain className="w-3.5 h-3.5 text-cyan-400" /> Altitude
                </span>
                <span className="text-xs font-mono font-bold text-cyan-300">{altitude} m</span>
              </div>
              <input
                type="range"
                min="0"
                max="6000"
                step="100"
                value={altitude}
                onChange={(e) => setAltitude(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-800 rounded appearance-none cursor-pointer accent-cyan-400"
              />
              <span className="text-[10px] font-mono text-slate-500 block">Density altitude ceiling (0 - 6,000m)</span>
            </div>

            {/* Ambient Temp Slider */}
            <div className="bg-avionics-card p-3 rounded border border-slate-800 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                  <Sun className="w-3.5 h-3.5 text-amber-400" /> Ambient Temp
                </span>
                <span className="text-xs font-mono font-bold text-amber-300">{ambientTemp}°C</span>
              </div>
              <input
                type="range"
                min="-30"
                max="55"
                step="1"
                value={ambientTemp}
                onChange={(e) => setAmbientTemp(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-800 rounded appearance-none cursor-pointer accent-amber-400"
              />
              <span className="text-[10px] font-mono text-slate-500 block">ISA atmospheric deviation (-30 to +55°C)</span>
            </div>

            {/* Duration Steps */}
            <div className="bg-avionics-card p-3 rounded border border-slate-800 space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                  <Gauge className="w-3.5 h-3.5 text-emerald-400" /> Duration
                </span>
                <span className="text-xs font-mono font-bold text-emerald-300">{durationSteps} steps</span>
              </div>
              <input
                type="range"
                min="10"
                max="100"
                step="5"
                value={durationSteps}
                onChange={(e) => setDurationSteps(Number(e.target.value))}
                className="w-full h-1.5 bg-slate-800 rounded appearance-none cursor-pointer accent-emerald-400"
              />
              <span className="text-[10px] font-mono text-slate-500 block">Simulation ticks (10 - 100 frames)</span>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={handleRunSimulation}
              disabled={isLoading}
              className="flex items-center gap-2 px-5 py-2.5 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-xs font-mono font-bold tracking-wider shadow-glow-cyan transition-all disabled:opacity-50 cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-cyan-400" />
              {isLoading ? 'COMPUTING THERMODYNAMIC RESPONSE...' : 'EXECUTE SCENARIO SIMULATION'}
            </button>
          </div>
        </div>
      </div>

      {/* Simulation Results View */}
      {simResults && (
        <div className="space-y-4">
          {/* Summary KPIs */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3 font-mono">
              <span className="text-[10px] text-slate-400 uppercase block">Simulated Peak CHT</span>
              <span className="text-xl font-bold text-amber-400">{simResults.summary?.peak_cht?.toFixed(1)}°C</span>
            </div>
            <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3 font-mono">
              <span className="text-[10px] text-slate-400 uppercase block">Simulated Peak EGT</span>
              <span className="text-xl font-bold text-red-400">{simResults.summary?.peak_egt?.toFixed(1)}°C</span>
            </div>
            <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3 font-mono">
              <span className="text-[10px] text-slate-400 uppercase block">Cooling Margin Status</span>
              <span
                className={`text-xl font-bold ${
                  simResults.summary?.cooling_margin_status === 'ACCEPTABLE'
                    ? 'text-emerald-400'
                    : 'text-amber-400'
                }`}
              >
                {simResults.summary?.cooling_margin_status || 'NOMINAL'}
              </span>
            </div>
            <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3 font-mono">
              <span className="text-[10px] text-slate-400 uppercase block">Projected Engine Health</span>
              <span className="text-xl font-bold text-emerald-400">
                {simResults.summary?.final_health?.toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Time Series Chart of Simulated Response */}
          {frames.length > 0 && (
            <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 h-[340px] flex flex-col">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-cyan-400" />
                  Simulated Dynamic Response Trajectory ({frames.length} steps evaluated)
                </h3>
                <span className="text-[10px] font-mono text-cyan-400">
                  {simResults.scenario_name || scenarioName}
                </span>
              </div>
              <div className="flex-1 w-full min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={frames}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                    <XAxis dataKey="step" stroke="#64748B" tick={{ fontSize: 10, fill: '#94A3B8' }} />
                    <YAxis stroke="#64748B" tick={{ fontSize: 10, fill: '#94A3B8' }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#111722',
                        borderColor: '#1E293B',
                        borderRadius: '6px',
                        fontFamily: 'monospace',
                        fontSize: '11px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', fontFamily: 'monospace' }} />
                    <Line type="monotone" dataKey="cht" name="Simulated CHT (°C)" stroke="#00F0FF" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="egt" name="Simulated EGT (°C)" stroke="#F59E0B" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="rpm" name="Engine RPM" stroke="#10B981" strokeWidth={1} dot={false} />
                    <Line type="monotone" dataKey="health" name="Projected Health %" stroke="#8B5CF6" strokeWidth={1.5} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
