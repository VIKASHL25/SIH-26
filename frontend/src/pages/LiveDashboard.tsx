import React from 'react';
import { useDigitalTwinStore } from '../store/useDigitalTwinStore';
import { PlaybackControls } from '../components/dashboard/PlaybackControls';
import { TelemetryGrid } from '../components/dashboard/TelemetryGrid';
import { LiveCharts } from '../components/dashboard/LiveCharts';
import { DiagnosticsPanel } from '../components/dashboard/DiagnosticsPanel';
import { XaiPanel } from '../components/dashboard/XaiPanel';
import { FaultInjectionPanel } from '../components/dashboard/FaultInjectionPanel';
import { AdvisoryFeed } from '../components/dashboard/AdvisoryFeed';
import { Radio } from 'lucide-react';

export const LiveDashboard: React.FC = () => {
  const { wsStatus } = useDigitalTwinStore();

  return (
    <div className="max-w-[1920px] mx-auto p-4 space-y-4">
      {/* Playback Controls & Mission Header */}
      <PlaybackControls />

      {/* Connection warning banner if offline */}
      {wsStatus !== 'CONNECTED' && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-amber-950/30 border border-amber-500/40 text-amber-300 text-xs font-mono">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 animate-pulse text-amber-400" />
            <span>
              LIVE TELEMETRY STREAM IS {wsStatus}: Attempting auto-reconnect to ws://localhost:8000/ws/telemetry...
            </span>
          </div>
          <span className="text-[10px] text-slate-400">
            Ensure backend services are running (python services/run_all_services.py)
          </span>
        </div>
      )}

      {/* Primary Sensor Gauges Matrix */}
      <TelemetryGrid />

      {/* Middle Row: Live Physics Charts + Real-time Advisory Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-8">
          <LiveCharts />
        </div>
        <div className="lg:col-span-4">
          <AdvisoryFeed />
        </div>
      </div>

      {/* AI/ML Predictive Health & Diagnostics (Degradation, RUL, Anomaly, Fault) */}
      <DiagnosticsPanel />

      {/* Explainable AI (XAI) & SHAP Root-Cause Attribution */}
      <XaiPanel />

      {/* Synthetic Fault Injection & "What-If" Analysis */}
      <FaultInjectionPanel />
    </div>
  );
};
