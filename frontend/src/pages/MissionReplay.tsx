import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import type { MissionReplayResponse, AdvisoryLogItem } from '../api/types';
import {
  History,
  Play,
  Pause,
  RotateCcw,
  FastForward,
  ChevronLeft,
  ChevronRight,
  Activity,
  Calendar,
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
  ReferenceLine,
} from 'recharts';
import { GaugeTile } from '../components/common/GaugeTile';

export const MissionReplay: React.FC = () => {
  const [savedMissions, setSavedMissions] = useState<number[]>([]);
  const [selectedMission, setSelectedMission] = useState<number>(999);
  const [replayData, setReplayData] = useState<MissionReplayResponse | null>(null);
  const [advisories, setAdvisories] = useState<AdvisoryLogItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Client-side playback state
  const [currentIdx, setCurrentIdx] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [replaySpeed, setReplaySpeed] = useState<number>(1.0);
  const playIntervalRef = useRef<number | null>(null);

  // Load list of missions on mount
  useEffect(() => {
    async function loadSavedList() {
      try {
        const res = await api.getSavedMissions();
        if (res.recorded_missions && res.recorded_missions.length > 0) {
          setSavedMissions(res.recorded_missions);
          setSelectedMission(res.recorded_missions[0]);
        } else {
          // Fallback to demo mission
          setSavedMissions([1, 2, 3, 999]);
          setSelectedMission(999);
        }
      } catch (err: any) {
        console.warn('Could not load saved missions:', err?.message);
        setSavedMissions([1, 2, 3, 999]);
        setSelectedMission(999);
      }
    }
    loadSavedList();
  }, []);

  // Fetch full replay trajectory when mission changes
  useEffect(() => {
    if (!selectedMission) return;

    let isMounted = true;
    async function fetchReplay() {
      setIsLoading(true);
      setErrorMsg(null);
      setIsPlaying(false);
      try {
        const [repRes, advRes] = await Promise.allSettled([
          api.getMissionReplay(selectedMission),
          api.getAdvisories(selectedMission),
        ]);

        if (repRes.status === 'fulfilled' && isMounted) {
          setReplayData(repRes.value);
          setCurrentIdx(0);
        } else if (repRes.status === 'rejected' && isMounted) {
          setErrorMsg(`Replay fetch failed: ${repRes.reason?.message || 'Database unavailable'}`);
        }

        if (advRes.status === 'fulfilled' && isMounted) {
          setAdvisories(advRes.value.advisories || []);
        }
      } catch (err: any) {
        if (isMounted) setErrorMsg(err?.message || 'Failed to load mission replay');
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    fetchReplay();

    return () => {
      isMounted = false;
    };
  }, [selectedMission]);

  // Client-side playback timer
  useEffect(() => {
    if (isPlaying && replayData && replayData.frames.length > 0) {
      const delayMs = Math.max(30, Math.round(1000 / replaySpeed));
      playIntervalRef.current = window.setInterval(() => {
        setCurrentIdx((prev) => {
          if (prev >= replayData.frames.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, delayMs);
    } else {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
        playIntervalRef.current = null;
      }
    }

    return () => {
      if (playIntervalRef.current) clearInterval(playIntervalRef.current);
    };
  }, [isPlaying, replaySpeed, replayData]);

  const frames = replayData?.frames || [];
  const currentFrame = frames[currentIdx] || null;
  const summary = replayData?.summary;

  // Chart dataset for full trajectory
  const trajectoryData = frames.map((f: any, i: number) => ({
    idx: i,
    frame: f.frame_index,
    cht: f.telemetry.cht_C,
    egt: f.telemetry.egt_C,
    rpm: f.telemetry.rpm,
    oilPressure: f.telemetry.oil_pressure_bar,
    health: f.predictions?.degradation?.estimated_health_pct ?? 100,
  }));

  return (
    <div className="max-w-[1920px] mx-auto p-4 space-y-4">
      {/* Top Header & Mission Selector */}
      <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <History className="w-5 h-5 text-cyan-400" />
          <div>
            <h2 className="text-sm font-mono font-bold tracking-wider text-slate-100 uppercase">
              Mission Replay & Post-Flight Telemetry Analysis
            </h2>
            <p className="text-[11px] font-mono text-slate-400">
              Synchronized MongoDB Atlas Trajectory Scrubber with Frame-Level Diagnostics
            </p>
          </div>
        </div>

        {/* Mission Picker Dropdown */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-mono text-slate-400 uppercase">
            Select Recorded Mission:
          </label>
          <select
            value={selectedMission}
            onChange={(e) => setSelectedMission(Number(e.target.value))}
            disabled={isLoading}
            className="bg-slate-900 border border-slate-700 text-cyan-300 text-xs font-mono rounded px-3 py-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer"
          >
            {savedMissions.map((id) => (
              <option key={id} value={id}>
                Mission ID #{id} {id === 999 ? '(Synthetic Out-of-Sample)' : ''}
              </option>
            ))}
          </select>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-500/40 text-amber-300 text-xs font-mono">
          {errorMsg}
        </div>
      )}

      {/* Mission Summary KPIs Header */}
      {summary ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3">
            <span className="text-[10px] font-mono text-slate-400 uppercase block">Recorded Frames</span>
            <span className="text-xl font-mono font-bold text-white">{summary.total_frames}</span>
          </div>
          <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3">
            <span className="text-[10px] font-mono text-slate-400 uppercase block">Peak CHT</span>
            <span className="text-xl font-mono font-bold text-amber-400">{summary.max_cht_C?.toFixed(1)}°C</span>
          </div>
          <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3">
            <span className="text-[10px] font-mono text-slate-400 uppercase block">Peak EGT</span>
            <span className="text-xl font-mono font-bold text-red-400">{summary.max_egt_C?.toFixed(1)}°C</span>
          </div>
          <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3">
            <span className="text-[10px] font-mono text-slate-400 uppercase block">Min Oil Pressure</span>
            <span className="text-xl font-mono font-bold text-cyan-400">{summary.min_oil_pressure_bar?.toFixed(2)} bar</span>
          </div>
          <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3">
            <span className="text-[10px] font-mono text-slate-400 uppercase block">Health Delta</span>
            <span className="text-xl font-mono font-bold text-emerald-400">
              {summary.initial_health_pct?.toFixed(1)}% → {summary.final_health_pct?.toFixed(1)}%
            </span>
          </div>
          <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3">
            <span className="text-[10px] font-mono text-slate-400 uppercase block">Total Anomalies</span>
            <span className="text-xl font-mono font-bold text-red-400">
              {summary.total_anomalies_detected || 0}
            </span>
          </div>
        </div>
      ) : frames.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3 font-mono">
            <span className="text-[10px] text-slate-400 uppercase block">Total Frames</span>
            <span className="text-xl font-bold text-white">{frames.length}</span>
          </div>
          <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3 font-mono">
            <span className="text-[10px] text-slate-400 uppercase block">Current Frame</span>
            <span className="text-xl font-bold text-cyan-400">{currentIdx + 1} / {frames.length}</span>
          </div>
          <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3 font-mono">
            <span className="text-[10px] text-slate-400 uppercase block">Trajectory Status</span>
            <span className="text-xl font-bold text-emerald-400">LOGGED COMPLETE</span>
          </div>
          <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3 font-mono">
            <span className="text-[10px] text-slate-400 uppercase block">Logged Advisories</span>
            <span className="text-xl font-bold text-amber-400">{advisories.length}</span>
          </div>
        </div>
      ) : null}

      {/* Scrubbable Replay Controller */}
      <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              disabled={frames.length === 0}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono font-bold tracking-wider transition-all ${
                isPlaying
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-glow-cyan'
              }`}
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5 fill-amber-400" /> : <Play className="w-3.5 h-3.5 fill-cyan-400" />}
              {isPlaying ? 'PAUSE REPLAY' : 'PLAY REPLAY'}
            </button>

            <button
              onClick={() => setCurrentIdx((p) => Math.max(0, p - 1))}
              disabled={frames.length === 0 || currentIdx === 0}
              className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 disabled:opacity-40"
              title="Step 1 frame back"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <button
              onClick={() => setCurrentIdx((p) => Math.min(frames.length - 1, p + 1))}
              disabled={frames.length === 0 || currentIdx >= frames.length - 1}
              className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 disabled:opacity-40"
              title="Step 1 frame forward"
            >
              <ChevronRight className="w-4 h-4" />
            </button>

            <button
              onClick={() => {
                setIsPlaying(false);
                setCurrentIdx(0);
              }}
              disabled={frames.length === 0}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-mono"
              title="Rewind to start"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              REWIND
            </button>
          </div>

          {/* Speed selector */}
          <div className="flex items-center gap-1">
            <span className="text-[11px] font-mono text-slate-400 mr-1 flex items-center gap-1">
              <FastForward className="w-3 h-3" /> Speed:
            </span>
            {[1.0, 2.0, 5.0, 10.0, 25.0].map((s) => (
              <button
                key={s}
                onClick={() => setReplaySpeed(s)}
                className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                  replaySpeed === s
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>

        {/* Timeline Slider with cursor */}
        <div className="flex items-center gap-3 pt-1">
          <span className="text-xs font-mono text-slate-400 min-w-[70px]">
            Frame: {currentIdx + 1} / {frames.length || 0}
          </span>
          <input
            type="range"
            min="0"
            max={Math.max(0, frames.length - 1)}
            value={currentIdx}
            onChange={(e) => {
              setIsPlaying(false);
              setCurrentIdx(Number(e.target.value));
            }}
            disabled={frames.length === 0}
            className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
          />
          <span className="text-xs font-mono text-cyan-400 min-w-[45px] text-right font-bold">
            {frames.length > 0 ? Math.round(((currentIdx + 1) / frames.length) * 100) : 0}%
          </span>
        </div>
      </div>

      {/* Synchronized Gauges for Current Scrubbed Frame */}
      {currentFrame ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-mono font-bold tracking-wider text-slate-300 uppercase flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              Replay Frame Snapshot Telemetry
            </h3>
            <span className="text-xs font-mono text-slate-400">
              Timestamp: {currentFrame.timestamp || `T+${currentFrame.frame_index}s`}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2.5">
            <GaugeTile
              label="Engine RPM"
              value={currentFrame.telemetry.rpm}
              unit="RPM"
              min={1500}
              max={3000}
              nominalLow={1900}
              nominalHigh={2600}
              precision={0}
            />
            <GaugeTile
              label="CHT"
              value={currentFrame.telemetry.cht_C}
              unit="°C"
              min={80}
              max={200}
              nominalLow={110}
              nominalHigh={155}
              precision={1}
            />
            <GaugeTile
              label="EGT"
              value={currentFrame.telemetry.egt_C}
              unit="°C"
              min={500}
              max={900}
              nominalLow={620}
              nominalHigh={740}
              precision={1}
            />
            <GaugeTile
              label="Oil Pressure"
              value={currentFrame.telemetry.oil_pressure_bar}
              unit="bar"
              min={1.0}
              max={7.0}
              nominalLow={3.5}
              nominalHigh={5.5}
              precision={2}
            />
            <GaugeTile
              label="Oil Temp"
              value={currentFrame.telemetry.oil_temperature_C}
              unit="°C"
              min={40}
              max={130}
              nominalLow={75}
              nominalHigh={105}
              precision={1}
            />
            <GaugeTile
              label="Vibration RMS"
              value={currentFrame.telemetry.vibration_rms}
              unit="g-rms"
              min={0.0}
              max={0.6}
              nominalLow={0.05}
              nominalHigh={0.25}
              precision={3}
            />
          </div>
        </div>
      ) : (
        <div className="bg-avionics-surface border border-avionics-border rounded-lg p-8 text-center text-slate-500 font-mono text-xs">
          {isLoading ? 'LOADING FLIGHT TRAJECTORY FROM MONGODB ATLAS...' : 'NO RECORDED REPLAY FRAMES AVAILABLE'}
        </div>
      )}

      {/* Full Trajectory Chart with Scrub Cursor */}
      {trajectoryData.length > 0 && (
        <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 h-[320px] flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase">
              Full Flight Profile Trajectory (Scrub Position Cursor)
            </h3>
            <span className="text-[10px] font-mono text-cyan-400">
              ACTIVE AT FRAME #{currentIdx}
            </span>
          </div>

          <div className="flex-1 w-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trajectoryData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                <XAxis dataKey="frame" stroke="#64748B" tick={{ fontSize: 10, fill: '#94A3B8' }} />
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
                <ReferenceLine x={currentFrame?.frame_index || currentIdx} stroke="#00F0FF" strokeWidth={2} label="NOW" />
                <Line type="monotone" dataKey="cht" name="CHT (°C)" stroke="#00F0FF" dot={false} strokeWidth={1.5} />
                <Line type="monotone" dataKey="egt" name="EGT (°C)" stroke="#F59E0B" dot={false} strokeWidth={1.5} />
                <Line type="monotone" dataKey="rpm" name="RPM" stroke="#10B981" dot={false} strokeWidth={1} />
                <Line type="monotone" dataKey="health" name="Health %" stroke="#8B5CF6" dot={false} strokeWidth={1.5} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Advisory History for this Mission */}
      <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase">
              Mission Logged Advisories & Maintenance History
            </h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
            {advisories.length} RECORDS
          </span>
        </div>

        {advisories.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead className="text-[10px] text-slate-400 uppercase bg-slate-900/80 border-b border-slate-800">
                <tr>
                  <th className="py-2 px-3">Frame</th>
                  <th className="py-2 px-3">Severity</th>
                  <th className="py-2 px-3">Health %</th>
                  <th className="py-2 px-3">RUL (hrs)</th>
                  <th className="py-2 px-3">Advisory Message</th>
                  <th className="py-2 px-3">Recommended Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {advisories.map((adv, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-2 px-3 text-cyan-300 font-bold">{adv.frame_index}</td>
                    <td className="py-2 px-3">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          adv.alert_type?.includes('CRITICAL')
                            ? 'bg-red-500/20 text-red-400'
                            : adv.alert_type?.includes('WARN')
                            ? 'bg-amber-500/20 text-amber-400'
                            : 'bg-emerald-500/10 text-emerald-400'
                        }`}
                      >
                        {adv.alert_type}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-slate-300">{adv.health_index_pct?.toFixed(1)}%</td>
                    <td className="py-2 px-3 text-slate-300">{adv.predicted_rul_hours?.toFixed(1) || 'N/A'}</td>
                    <td className="py-2 px-3 text-slate-200">{adv.message}</td>
                    <td className="py-2 px-3 text-slate-400">{adv.recommended_action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-6 text-center text-slate-500 font-mono text-xs">
            NO ADVISORY RECORDS RECORDED FOR THIS MISSION
          </div>
        )}
      </div>
    </div>
  );
};
