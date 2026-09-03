import React, { useState, useEffect } from 'react';
import { Play, Pause, StepForward, FastForward, AlertCircle } from 'lucide-react';
import { api } from '../../api/client';
import { useDigitalTwinStore } from '../../store/useDigitalTwinStore';

export const PlaybackControls: React.FC = () => {
  const {
    currentFrame,
    playbackState,
    playbackSpeed,
    selectedMissionId,
    availableMissions,
    setPlaybackState,
    setPlaybackSpeed,
    setSelectedMissionId,
    setAvailableMissions,
    pushFrame,
  } = useDigitalTwinStore();

  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Fetch available missions on mount
  useEffect(() => {
    async function fetchMissions() {
      try {
        const data = await api.listMissions();
        if (data.available_mission_ids && data.available_mission_ids.length > 0) {
          setAvailableMissions(data.available_mission_ids);
          if (!selectedMissionId) {
            setSelectedMissionId(data.active_mission_id || data.available_mission_ids[0]);
          }
        }
      } catch (err: any) {
        console.warn('Could not fetch mission list:', err?.message);
        setAvailableMissions([1, 2, 3, 999]);
        if (!selectedMissionId) setSelectedMissionId(999);
      }
    }
    fetchMissions();
  }, [setAvailableMissions, setSelectedMissionId, selectedMissionId]);

  // Mission Load Handler
  const handleLoadMission = async (missionId: number) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      await api.loadMission(missionId);
      setSelectedMissionId(missionId);
      setPlaybackState('PAUSED');
    } catch (err: any) {
      setErrorMsg(`Failed to load mission ${missionId}: ${err?.message || 'Server error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Play Handler
  const handlePlay = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    setPlaybackState('RUNNING');
    try {
      await api.startSimulation();
    } catch (err: any) {
      setPlaybackState('PAUSED');
      setErrorMsg(`Failed to start: ${err?.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Pause Handler
  const handlePause = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    setPlaybackState('PAUSED');
    try {
      await api.pauseSimulation();
    } catch (err: any) {
      setPlaybackState('RUNNING');
      setErrorMsg(`Failed to pause: ${err?.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Step Handler
  const handleStep = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const frame = await api.stepSimulation();
      pushFrame(frame);
    } catch (err: any) {
      setErrorMsg(`Step error: ${err?.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Speed Handler
  const handleSpeed = async (speed: number) => {
    try {
      await api.setSpeed(speed);
      setPlaybackSpeed(speed);
    } catch (err: any) {
      console.error('Speed change error:', err);
    }
  };

  // Seek Handler
  const handleSeek = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const frameIdx = parseInt(e.target.value, 10);
    try {
      await api.seekFrame(frameIdx);
    } catch (err: any) {
      console.error('Seek error:', err);
    }
  };

  const currentFrameIdx = currentFrame?.frame_index || 0;
  const totalFrames = currentFrame?.total_frames || 2500;
  const speeds = [0.25, 0.5, 1.0, 2.0, 5.0, 10.0];

  return (
    <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left: Mission Selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">
            Active Mission:
          </label>
          <select
            value={selectedMissionId || ''}
            onChange={(e) => handleLoadMission(Number(e.target.value))}
            disabled={isLoading}
            className="bg-slate-900 border border-slate-700 text-cyan-300 text-xs font-mono rounded px-2.5 py-1.5 focus:outline-none focus:border-cyan-500 cursor-pointer disabled:opacity-50"
          >
            {availableMissions.map((id) => (
              <option key={id} value={id}>
                Mission #{id} {id === 999 ? '(Synthetic Out-of-Sample Demo)' : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Center: Play, Pause, Step Buttons */}
        <div className="flex items-center gap-2">
          {playbackState === 'RUNNING' ? (
            <button
              onClick={handlePause}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-mono font-bold tracking-wider transition-all"
            >
              <Pause className="w-3.5 h-3.5 fill-amber-400" />
              PAUSE
            </button>
          ) : (
            <button
              onClick={handlePlay}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 text-xs font-mono font-bold tracking-wider shadow-glow-cyan transition-all"
            >
              <Play className="w-3.5 h-3.5 fill-cyan-400" />
              STREAM LIVE
            </button>
          )}

          <button
            onClick={handleStep}
            disabled={isLoading || playbackState === 'RUNNING'}
            title="Advance 1 simulation frame"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-mono font-medium disabled:opacity-40 transition-all"
          >
            <StepForward className="w-3.5 h-3.5" />
            STEP
          </button>
        </div>

        {/* Right: Speed Multiplier */}
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <FastForward className="w-3 h-3" /> Speed:
          </span>
          <div className="flex items-center rounded border border-slate-800 bg-slate-900/90 overflow-hidden">
            {speeds.map((s) => (
              <button
                key={s}
                onClick={() => handleSpeed(s)}
                className={`px-2 py-1 text-[11px] font-mono transition-colors ${
                  Math.abs(playbackSpeed - s) < 0.05
                    ? 'bg-cyan-500/20 text-cyan-300 font-bold border-b border-cyan-400'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Frame Scrubber / Seek Bar */}
      <div className="flex items-center gap-3 pt-1 border-t border-slate-800/80">
        <span className="text-[11px] font-mono text-slate-400 whitespace-nowrap min-w-[70px]">
          F: {currentFrameIdx} / {totalFrames}
        </span>
        <input
          type="range"
          min="0"
          max={totalFrames - 1}
          value={currentFrameIdx}
          onChange={handleSeek}
          className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400 focus:outline-none"
        />
        <span className="text-[11px] font-mono text-cyan-400 whitespace-nowrap min-w-[45px] text-right">
          {Math.round((currentFrameIdx / (totalFrames || 1)) * 100)}%
        </span>
      </div>

      {/* Error alert if any */}
      {errorMsg && (
        <div className="flex items-center gap-2 p-2 rounded bg-red-950/40 border border-red-500/40 text-red-300 text-xs font-mono">
          <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
};
