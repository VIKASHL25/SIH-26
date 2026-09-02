import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useTelemetryStream } from './hooks/useTelemetryStream';
import { Header } from './components/common/Header';
import { LiveDashboard } from './pages/LiveDashboard';
import { MissionReplay } from './pages/MissionReplay';
import { FleetOverview } from './pages/FleetOverview';
import { ScenarioSimulation } from './pages/ScenarioSimulation';
import { Shield, Database, Cpu, Radio } from 'lucide-react';

export const App: React.FC = () => {
  // Initialize continuous WebSocket telemetry stream at application root
  const { reconnect } = useTelemetryStream();

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-avionics-bg text-slate-100 flex flex-col selection:bg-cyan-500/30 selection:text-cyan-200">
        {/* Top Tactical Header */}
        <Header onReconnect={reconnect} />

        {/* Page Content */}
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<LiveDashboard />} />
            <Route path="/replay" element={<MissionReplay />} />
            <Route path="/fleet" element={<FleetOverview />} />
            <Route path="/scenario" element={<ScenarioSimulation />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        {/* Avionics Footer */}
        <footer className="border-t border-slate-800/80 bg-avionics-surface/90 py-2.5 px-4 font-mono text-[11px] text-slate-500">
          <div className="max-w-[1920px] mx-auto flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Shield className="w-3.5 h-3.5 text-cyan-400" />
              <span>DRDO PS-26054: AI-Enabled Real-Time Digital Twin System for Aero Piston Engines in MALE UAVs</span>
            </div>

            <div className="flex items-center gap-4 text-slate-400">
              <span className="flex items-center gap-1">
                <Radio className="w-3 h-3 text-emerald-400" />
                CAN-FD Bus Ingestion
              </span>
              <span className="flex items-center gap-1">
                <Cpu className="w-3 h-3 text-cyan-400" />
                4 AI/ML Models + Tree-SHAP
              </span>
              <span className="flex items-center gap-1">
                <Database className="w-3 h-3 text-blue-400" />
                MongoDB Atlas Synchronized
              </span>
            </div>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
};

export default App;
