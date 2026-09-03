import React, { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { Radio, Shield, RotateCw, Play, Pause } from 'lucide-react';
import { useDigitalTwinStore } from '../../store/useDigitalTwinStore';
import { api } from '../../api/client';
import { HealthBadge } from './HealthBadge';

interface HeaderProps {
  onReconnect?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onReconnect }) => {
  const { currentFrame, wsStatus, playbackState, selectedMissionId, setPlaybackState } = useDigitalTwinStore();
  const location = useLocation();

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
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400 shadow-glow-cyan">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-bold tracking-wider text-white">
                  DRDO // TAPAS-BH-201
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                  MALE UAV
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium tracking-wide">
                Aero Piston Engine Digital Twin Framework
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
                className="ml-1 hover:text-white transition-colors"
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
    </header>
  );
};
