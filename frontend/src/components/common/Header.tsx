import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { Radio, RotateCw, Play, Pause, X, Cpu, Activity, CheckCircle2, Award, Info, Plane, Shield, Layers } from 'lucide-react';
import { useDigitalTwinStore } from '../../store/useDigitalTwinStore';
import { api } from '../../api/client';
import { HealthBadge } from './HealthBadge';

interface HeaderProps {
  onReconnect?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onReconnect }) => {
  const { currentFrame, wsStatus, playbackState, selectedMissionId, setPlaybackState } = useDigitalTwinStore();
  const location = useLocation();
  const navigate = useNavigate();
  const [showAboutModal, setShowAboutModal] = useState(false);

  const handleTogglePlay = async () => {
    try {
      if (playbackState === 'RUNNING') {
        setPlaybackState('PAUSED');
        await api.pauseSimulation();
      } else {
        setPlaybackState('RUNNING');
        await api.startSimulation();
      }
    } catch (err) {
      console.error('Failed to toggle playback from header:', err);
    }
  };

  // Close modal on Escape key
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      setShowAboutModal(false);
    }
  }, []);

  useEffect(() => {
    if (showAboutModal) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [showAboutModal, handleKeyDown]);

  // UTC Clock
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toUTCString().replace('GMT', 'UTC'));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const navLinks = [
    { to: '/', label: 'Live Dashboard' },
    { to: '/replay', label: 'Mission Replay' },
    { to: '/fleet', label: 'Fleet & Depot' },
    { to: '/scenario', label: 'Scenario Sim' },
  ];

  const wsStatusColors = {
    CONNECTED: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10 shadow-glow-nominal',
    CONNECTING: 'text-amber-400 border-amber-500/30 bg-amber-500/10 animate-pulse',
    DISCONNECTED: 'text-red-400 border-red-500/30 bg-red-500/10',
    ERROR: 'text-red-500 border-red-500/40 bg-red-950/30',
  }[wsStatus];

  return (
    <header className="border-b border-avionics-border bg-avionics-surface/95 backdrop-blur sticky top-0 z-50">
      {/* Top Tactical Status Bar */}
      <div className="max-w-[1920px] mx-auto px-4 py-2 flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80">
        {/* Left: Branding & UAV Platform */}
        <div className="flex items-center gap-3">
          <div 
            onClick={() => setShowAboutModal(true)}
            className="flex items-center gap-2.5 cursor-pointer group hover:opacity-95 transition-all select-none"
            title="Click to view Project GARUD Details & System Architecture"
          >
            {/* Logo Image -> triggers modal */}
            <div className="relative group block flex-shrink-0">
              <img
                src="/garud-logo.png"
                alt="GARUD Logo"
                className="w-9 h-9 rounded-full object-cover border border-amber-500/50 shadow-glow-amber group-hover:scale-105 group-hover:border-amber-400 group-hover:shadow-amber-500/30 transition-all bg-slate-900"
              />
              <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-400 border-2 border-slate-900 rounded-full" />
            </div>

            {/* Brand Title & Platform */}
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base tracking-widest bg-gradient-to-r from-amber-300 via-yellow-200 to-amber-400 bg-clip-text text-transparent drop-shadow-sm font-sans group-hover:brightness-125 transition-all">
                  GARUD
                </span>
                <span className="h-3 w-px bg-slate-700" />
                <span className="font-mono text-xs font-bold tracking-wider text-slate-200">
                  TAPAS-BH-201
                </span>
                <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 uppercase">
                  MALE UAV
                </span>

                {/* Tactical Info Pill Button */}
                <span
                  className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-500/15 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-[10px] font-mono transition-all ml-1"
                >
                  <Info className="w-3 h-3 text-amber-400" />
                  <span className="hidden sm:inline">INTEL</span>
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-medium tracking-wide">
                AI Digital Twin System • Aero-Engine Health & Reliability
              </p>
            </div>
          </div>

          <div className="hidden lg:block h-6 w-px bg-slate-800" />

          {/* Active Mission Badge */}
          <div className="hidden lg:flex items-center gap-2 font-mono text-xs text-slate-300">
            <span className="text-slate-500">MISSION:</span>
            <span className="font-semibold text-cyan-300">
              {currentFrame ? `ID-${currentFrame.mission_id}` : selectedMissionId ? `ID-${selectedMissionId}` : 'ID-999'}
            </span>
            <span className="px-1.5 py-0.5 rounded bg-slate-800/80 text-[10px] text-slate-300 border border-slate-700">
              {currentFrame?.mission_type || 'ISR_SURVEILLANCE'}
            </span>
          </div>
        </div>

        {/* Center: Mission Progress / Telemetry Frame Stats */}
        <div className="flex items-center gap-4 font-mono text-xs">
          {currentFrame && (
            <div className="flex items-center gap-3 bg-avionics-card px-3 py-1 rounded border border-slate-800">
              <div className="flex items-center gap-1.5">
                <span className="text-slate-500 text-[10px]">FRAME:</span>
                <span className="font-bold text-white">
                  {currentFrame.frame_index}
                  <span className="text-slate-500 font-normal"> / {currentFrame.total_frames}</span>
                </span>
              </div>
              <div className="w-20 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-cyan-400 h-full transition-all duration-300"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.round((currentFrame.frame_index / (currentFrame.total_frames || 1)) * 100)
                    )}%`,
                  }}
                />
              </div>
              <div className="flex items-center gap-1 text-[11px]">
                <span className="text-slate-500">SPEED:</span>
                <span className="text-cyan-300 font-bold">{currentFrame.playback_speed || 1.0}x</span>
              </div>
            </div>
          )}

          {/* Playback State Pill */}
          <button
            onClick={handleTogglePlay}
            title={`Simulation state: ${playbackState || 'PAUSED'} (Click to toggle)`}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-semibold border uppercase transition-all cursor-pointer ${
              playbackState === 'RUNNING'
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50 shadow-glow-nominal animate-pulse'
                : 'bg-amber-500/15 text-amber-400 border-amber-500/40 hover:bg-amber-500/25'
            }`}
          >
            {playbackState === 'RUNNING' ? (
              <Play className="w-3 h-3 fill-emerald-400" />
            ) : (
              <Pause className="w-3 h-3 fill-amber-400" />
            )}
            <span>{playbackState === 'RUNNING' ? 'STREAM: RUNNING' : 'STREAM: PAUSED'}</span>
          </button>
        </div>

        {/* Right: Health Badge, WS Status & Clock */}
        <div className="flex items-center gap-3 font-mono text-xs">
          {/* Overall Health Status */}
          <HealthBadge status={currentFrame?.health_status || 'NOMINAL'} size="md" />

          {/* WebSocket Status Indicator */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded border text-xs font-semibold ${wsStatusColors}`}>
            <Radio className="w-3 h-3" />
            <span className="uppercase text-[10px] tracking-wider">
              {wsStatus === 'CONNECTED' ? 'WS LIVE' : wsStatus}
            </span>
            {onReconnect && wsStatus !== 'CONNECTED' && (
              <button
                onClick={onReconnect}
                title="Reconnect WebSocket"
                className="ml-1 hover:text-white transition-colors cursor-pointer"
              >
                <RotateCw className="w-3 h-3" />
              </button>
            )}
          </div>

          {/* UTC Clock */}
          <div className="hidden sm:block text-slate-400 text-xs tracking-wider bg-slate-900/80 px-2 py-1 rounded border border-slate-800">
            {utcTime || 'UTC 00:00:00'}
          </div>
        </div>
      </div>

      {/* Navigation Bar */}
      <div className="max-w-[1920px] mx-auto px-4 flex items-center justify-between">
        <nav className="flex items-center space-x-1 py-1">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.to;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                className={`px-3.5 py-1.5 rounded text-xs font-semibold uppercase tracking-wider transition-all duration-200 border ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/40 shadow-glow-cyan'
                    : 'text-slate-400 border-transparent hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                {link.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="hidden md:flex items-center gap-3 text-[11px] font-mono text-slate-500">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-cyan-400" /> CAN-FD 1Mbps
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> FADEC ECU-A
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-400" /> SHAP XAI Engine
          </span>
        </div>
      </div>

      {/* Project GARUD Mission & Architecture Modal (Portal to body to always stay in front) */}
      {showAboutModal && createPortal(
        <div 
          onClick={() => setShowAboutModal(false)}
          className="fixed inset-0 z-[99999] flex items-start justify-center bg-black/85 backdrop-blur-md px-4 pt-16 sm:pt-20 pb-8 overflow-y-auto animate-fade-in"
        >
          <div 
            onClick={(e) => e.stopPropagation()}
            className="bg-avionics-surface border-2 border-amber-500/60 rounded-2xl max-w-3xl w-full p-5 sm:p-7 shadow-[0_10px_50px_rgba(0,0,0,0.9),0_0_50px_rgba(245,158,11,0.25)] relative max-h-[82vh] overflow-y-auto text-slate-200 space-y-4 my-auto"
          >
            {/* Ambient Background Glow */}
            <div className="absolute top-0 right-0 w-72 h-72 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

            {/* Close Button */}
            <button
              onClick={() => setShowAboutModal(false)}
              className="absolute top-4 right-4 p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors cursor-pointer"
              title="Close (Esc)"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Header: Centered/Aligned Emblem + Titles */}
            <div className="flex flex-col sm:flex-row items-center gap-5 pb-4 border-b border-slate-800">
              <img
                src="/garud-logo.png"
                alt="GARUD Insignia"
                className="w-24 h-24 rounded-full object-cover border-2 border-amber-400 shadow-glow-amber bg-slate-950 flex-shrink-0"
              />
              <div className="text-center sm:text-left flex-1">
                <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                  <h2 className="text-2xl font-black tracking-widest bg-gradient-to-r from-amber-300 via-yellow-200 to-amber-400 bg-clip-text text-transparent font-sans">
                    PROJECT GARUD
                  </h2>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold">
                    DRDO PS-26054
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                    GCS LEVEL-4
                  </span>
                </div>
                <p className="text-xs font-semibold text-amber-300/90 mt-1.5 uppercase tracking-wide leading-relaxed">
                  AI-Enabled Digital Twin System for Aero-Engine Health Monitoring, Fault Prediction and Mission Reliability
                </p>
                <div className="flex flex-wrap items-center justify-center sm:justify-start gap-3 text-slate-400 font-mono text-[11px] mt-2">
                  <span className="flex items-center gap-1 text-slate-300">
                    <Plane className="w-3.5 h-3.5 text-cyan-400" /> DRDO TAPAS-BH-201 (MALE UAV)
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1 text-slate-300">
                    <Shield className="w-3.5 h-3.5 text-emerald-400" /> Rotax 914 Turbocharged Engine
                  </span>
                </div>
              </div>
            </div>

            {/* Section 1: Platform & Operational Specs Grid */}
            <div className="bg-slate-900/70 p-3.5 rounded-lg border border-slate-800">
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400 mb-2.5 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5" /> Platform Specifications & Telemetry Bus
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
                  <div className="text-slate-500 text-[10px]">FLIGHT CEILING</div>
                  <div className="text-white font-bold text-sm">35,000 FT</div>
                  <div className="text-slate-400 text-[10px]">Cruise: 18,500 FT</div>
                </div>
                <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
                  <div className="text-slate-500 text-[10px]">PROPULSION</div>
                  <div className="text-white font-bold text-sm">115 HP</div>
                  <div className="text-slate-400 text-[10px]">Rotax 914 Turbo Boxer</div>
                </div>
                <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
                  <div className="text-slate-500 text-[10px]">TELEMETRY LINK</div>
                  <div className="text-white font-bold text-sm">CAN-FD</div>
                  <div className="text-slate-400 text-[10px]">1 Mbps // 10Hz Sampling</div>
                </div>
                <div className="bg-slate-950/60 p-2.5 rounded border border-slate-800/80">
                  <div className="text-slate-500 text-[10px]">DATA CHANNELS</div>
                  <div className="text-white font-bold text-sm">20+ SENSORS</div>
                  <div className="text-slate-400 text-[10px]">CHT, EGT, MAP, RPM, Oil</div>
                </div>
              </div>
            </div>

            {/* Section 2: AI Subsystems Matrix */}
            <div>
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-amber-400 mb-2.5 flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5" /> AI/ML Digital Twin Intelligence Modules
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 flex items-start gap-2.5">
                  <div className="p-2 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 flex-shrink-0 mt-0.5">
                    <Cpu className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-slate-200 font-semibold">XGBoost RUL Prediction</div>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      Prognostic Remaining Useful Life estimation with 95.8% accuracy and Tree-SHAP root-cause feature attribution.
                    </p>
                  </div>
                </div>

                <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 flex items-start gap-2.5">
                  <div className="p-2 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex-shrink-0 mt-0.5">
                    <CheckCircle2 className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-slate-200 font-semibold">Autoencoder Anomaly Core</div>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      Unsupervised reconstruction residual error modeling detecting sub-threshold degradation prior to critical failure.
                    </p>
                  </div>
                </div>

                <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 flex items-start gap-2.5">
                  <div className="p-2 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex-shrink-0 mt-0.5">
                    <Activity className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-slate-200 font-semibold">Random Forest Classifier</div>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      Instant fault classification mapping multi-channel anomalies to turbo, cylinder, ignition, or oil subsystems.
                    </p>
                  </div>
                </div>

                <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 flex items-start gap-2.5">
                  <div className="p-2 rounded bg-blue-500/10 border border-blue-500/30 text-blue-400 flex-shrink-0 mt-0.5">
                    <Award className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-slate-200 font-semibold">Bayesian MICE Imputation</div>
                    <p className="text-slate-400 text-[11px] mt-0.5">
                      Multivariate Imputation by Chained Equations recovering missing telemetry packets under electronic warfare dropouts.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer with Direct Page Shortcuts */}
            <div className="pt-3 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 font-mono text-[11px]">
              <div className="flex items-center gap-2 text-slate-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <span>GCS Digital Twin Online & Ready</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setShowAboutModal(false);
                    navigate('/scenario');
                  }}
                  className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 rounded transition-colors cursor-pointer"
                >
                  Scenario Sim →
                </button>
                <button
                  onClick={() => setShowAboutModal(false)}
                  className="px-4 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 rounded transition-colors cursor-pointer font-semibold"
                >
                  Close (Esc)
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </header>
  );
};
