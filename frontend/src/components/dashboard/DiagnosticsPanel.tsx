import React from 'react';
import { useDigitalTwinStore } from '../../store/useDigitalTwinStore';
import {
  Brain,
  Clock,
  AlertTriangle,
  TrendingDown,
  Layers,
} from 'lucide-react';

export const DiagnosticsPanel: React.FC = () => {
  const { currentFrame } = useDigitalTwinStore();

  const deg = currentFrame?.degradation_estimation || {
    estimated_health_pct: 95.0,
    degradation_index: 0.05,
  };

  const rul = currentFrame?.rul_prediction || {
    status: 'PREDICTED',
    predicted_rul_hours: 48.5,
    rul_lower_bound_p10: 44.0,
    rul_upper_bound_p90: 52.0,
    uncertainty_std_hours: 2.3,
    confidence_level: 'HIGH',
  };

  const anomaly = currentFrame?.anomaly_detection || {
    is_anomaly: false,
    anomaly_score: -0.15,
    decision_function: 0.15,
  };

  const fault = currentFrame?.fault_classification || {
    predicted_fault: 'normal',
    confidence: 0.98,
    fault_probabilities: {
      normal: 0.98,
      overheating: 0.01,
      lubrication_degradation: 0.005,
      injector_degradation: 0.003,
      sensor_fault: 0.002,
    },
  };

  // Degradation Health color coding
  const healthPct = deg.estimated_health_pct;
  const healthColor =
    healthPct < 60
      ? 'text-red-400'
      : healthPct < 80
      ? 'text-amber-400'
      : 'text-emerald-400';
  const healthBg =
    healthPct < 60
      ? 'bg-red-500'
      : healthPct < 80
      ? 'bg-amber-500'
      : 'bg-emerald-500';

  // Fault probabilities formatted
  const faultEntries = Object.entries(fault.fault_probabilities || { normal: 1.0 }).sort(
    (a, b) => b[1] - a[1]
  );

  const faultDisplayNames: Record<string, string> = {
    normal: 'Nominal Envelope',
    overheating: 'Thermal Overheating',
    lubrication_degradation: 'Lubrication Loss',
    injector_degradation: 'Fuel Injector Clog',
    sensor_fault: 'Sensor Drift / Bias',
  };

  return (
    <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase">
            AI/ML Predictive Health & Diagnostics
          </h3>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/40 text-cyan-300 border border-cyan-800/40">
          4 MODELS SYNCHRONIZED
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* 1. DEGRADATION ESTIMATION GAUGE */}
        <div className="bg-avionics-card rounded-lg border border-slate-800 p-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <TrendingDown className="w-3.5 h-3.5 text-cyan-400" />
              Engine Health Index
            </span>
            <span className="text-[10px] font-mono text-slate-500">XGBoost Regressor</span>
          </div>

          <div className="my-3 flex items-center justify-between">
            <div>
              <div className={`text-3xl font-mono font-bold tracking-tight ${healthColor}`}>
                {healthPct.toFixed(1)}%
              </div>
              <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                Degradation Index: <span className="text-slate-200">{deg.degradation_index.toFixed(3)}</span>
              </div>
            </div>

            {/* Circular meter mini preview */}
            <div className="relative w-12 h-12 flex items-center justify-center">
              <svg className="w-12 h-12 transform -rotate-90">
                <circle
                  cx="24"
                  cy="24"
                  r="20"
                  stroke="#1E293B"
                  strokeWidth="4"
                  fill="transparent"
                />
                <circle
                  cx="24"
                  cy="24"
                  r="20"
                  stroke={healthPct < 60 ? '#EF4444' : healthPct < 80 ? '#F59E0B' : '#10B981'}
                  strokeWidth="4"
                  fill="transparent"
                  strokeDasharray={125.6}
                  strokeDashoffset={125.6 - (125.6 * healthPct) / 100}
                  strokeLinecap="round"
                />
              </svg>
            </div>
          </div>

          {/* Health progress bar */}
          <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
            <div
              className={`h-full ${healthBg} transition-all duration-300`}
              style={{ width: `${Math.max(0, Math.min(100, healthPct))}%` }}
            />
          </div>
        </div>

        {/* 2. REMAINING USEFUL LIFE (RUL) CARD */}
        <div className="bg-avionics-card rounded-lg border border-slate-800 p-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              Remaining Useful Life
            </span>
            <span
              className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold uppercase ${
                rul.confidence_level === 'HIGH'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : rul.confidence_level === 'MEDIUM'
                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                  : 'bg-slate-800 text-slate-400'
              }`}
            >
              {rul.confidence_level || 'EVAL'}
            </span>
          </div>

          <div className="my-2">
            {rul.status === 'COLLECTING_HISTORY' ? (
              <div className="py-2">
                <span className="text-lg font-mono font-bold text-amber-400">BUFFERING</span>
                <p className="text-[11px] font-mono text-slate-400">
                  {rul.records_available || 0} / {rul.records_required || 13} frames buffered
                </p>
              </div>
            ) : (
              <div>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-3xl font-mono font-bold text-cyan-300">
                    {rul.predicted_rul_hours !== null && rul.predicted_rul_hours !== undefined
                      ? rul.predicted_rul_hours.toFixed(1)
                      : '--'}
                  </span>
                  <span className="text-xs font-mono text-slate-400 font-semibold">HOURS</span>
                </div>

                {/* Confidence Bounds Band (P10 - P90) */}
                <div className="text-[11px] font-mono text-slate-400 mt-1 flex items-center justify-between">
                  <span>90% CI:</span>
                  <span className="text-slate-200">
                    {rul.rul_lower_bound_p10?.toFixed(1) || '--'}h — {rul.rul_upper_bound_p90?.toFixed(1) || '--'}h
                  </span>
                </div>
              </div>
            )}
          </div>

          <div className="text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-800/80 flex justify-between">
            <span>Uncertainty ±σ:</span>
            <span className="text-slate-400">
              {rul.uncertainty_std_hours ? `±${rul.uncertainty_std_hours.toFixed(2)} hrs` : 'N/A'}
            </span>
          </div>
        </div>

        {/* 3. ANOMALY DETECTION (Isolation Forest) */}
        <div
          className={`rounded-lg border p-3 flex flex-col justify-between transition-all duration-300 ${
            anomaly.is_anomaly
              ? 'bg-red-950/20 border-red-500/50 shadow-glow-critical'
              : 'bg-avionics-card border-slate-800'
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <AlertTriangle
                className={`w-3.5 h-3.5 ${anomaly.is_anomaly ? 'text-red-400 animate-pulse' : 'text-cyan-400'}`}
              />
              Anomaly Detection
            </span>
            <span className="text-[10px] font-mono text-slate-500">Isolation Forest</span>
          </div>

          <div className="my-2">
            <div className="flex items-center gap-2">
              <span
                className={`text-xl font-mono font-bold tracking-wider uppercase ${
                  anomaly.is_anomaly ? 'text-red-400' : 'text-emerald-400'
                }`}
              >
                {anomaly.is_anomaly ? 'ANOMALY DETECTED' : 'ENVELOPE NOMINAL'}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 mt-2 pt-1 font-mono text-[11px]">
              <div>
                <span className="text-slate-500 text-[10px] block">ANOMALY SCORE</span>
                <span
                  className={`font-semibold ${
                    anomaly.anomaly_score > 0 ? 'text-red-400' : 'text-emerald-400'
                  }`}
                >
                  {anomaly.anomaly_score.toFixed(3)}
                </span>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block">DECISION FUNC</span>
                <span className="text-slate-300 font-semibold">
                  {anomaly.decision_function.toFixed(3)}
                </span>
              </div>
            </div>
          </div>

          <div className="text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-800/80">
            Threshold: 0.000 | Multi-sensor vector
          </div>
        </div>

        {/* 4. MULTICLASS FAULT CLASSIFICATION (XGBoost) */}
        <div className="bg-avionics-card rounded-lg border border-slate-800 p-3 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-cyan-400" />
              Fault Classification
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 font-bold">
              {(fault.confidence * 100).toFixed(1)}% CONF
            </span>
          </div>

          {/* Predicted class pill */}
          <div className="my-1.5">
            <div
              className={`px-2 py-1 rounded text-xs font-mono font-bold uppercase tracking-wide border ${
                fault.predicted_fault === 'normal'
                  ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                  : 'bg-red-500/20 text-red-300 border-red-500/40 shadow-glow-critical'
              }`}
            >
              {faultDisplayNames[fault.predicted_fault] || fault.predicted_fault.toUpperCase()}
            </div>
          </div>

          {/* Fault probabilities distribution bars */}
          <div className="space-y-1 mt-1">
            {faultEntries.slice(0, 3).map(([key, prob]) => (
              <div key={key} className="text-[10px] font-mono">
                <div className="flex justify-between text-slate-400 mb-0.5">
                  <span className="truncate">{faultDisplayNames[key] || key}</span>
                  <span className="text-slate-200 font-semibold ml-1">
                    {(prob * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="w-full bg-slate-900 h-1 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      key === 'normal'
                        ? 'bg-emerald-400'
                        : prob > 0.3
                        ? 'bg-red-400'
                        : 'bg-cyan-400'
                    }`}
                    style={{ width: `${Math.max(2, prob * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
