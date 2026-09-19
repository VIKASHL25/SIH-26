import React from 'react';
import { useDigitalTwinStore } from '../../store/useDigitalTwinStore';
import {
  Brain,
  Clock,
  AlertTriangle,
  TrendingDown,
  Layers,
  Wrench,
  Compass,
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

  const feasibility = currentFrame?.mission_feasibility || {
    planned_mission_duration_hours: 10.0,
    mission_elapsed_hours: (currentFrame?.timestamp_s || 0) / 3600.0,
    mission_remaining_time_hours: Math.max(0, 10.0 - (currentFrame?.timestamp_s || 0) / 3600.0),
    mission_completion_margin_hours:
      (rul.predicted_rul_hours || 48.5) - Math.max(0, 10.0 - (currentFrame?.timestamp_s || 0) / 3600.0),
    mission_feasibility_status: 'MISSION_CAPABLE',
    mission_completion_probability_pct: 99.4,
    maintenance_trigger: 'NOMINAL_NO_MAINTENANCE_TRIGGERED',
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

  const diagnostic = currentFrame?.diagnostic || {
    anomaly_detected: false,
    anomaly_score: 0,
    fault_id: null,
    subsystem: null,
    fault: 'normal',
    fault_confidence: 0,
    severity: 'NOMINAL',
    RUL: null,
    time_to_critical: null,
    contributing_features: [],
    explanation: 'System operating within nominal limits.',
    maintenance_advisory: 'No maintenance action required.',
    possible_sensor_drift: false,
  };

  // Degradation Health color coding
  const healthPct = deg.estimated_health_pct;
  const healthColor =
    healthPct < 60 ? 'text-red-400' : healthPct < 80 ? 'text-amber-400' : 'text-emerald-400';
  const healthBg =
    healthPct < 60 ? 'bg-red-500' : healthPct < 80 ? 'bg-amber-500' : 'bg-emerald-500';

  // Unified diagnostic severity color
  const severityColor =
    diagnostic.severity === 'CRITICAL' || diagnostic.severity === 'HIGH'
      ? 'text-red-400'
      : diagnostic.severity === 'WARNING' || diagnostic.severity === 'MODERATE'
      ? 'text-amber-300'
      : 'text-emerald-400';

  // Fault probabilities formatted
  const faultEntries = Object.entries(fault.fault_probabilities || { normal: 1.0 }).sort((a, b) => b[1] - a[1]);

  const faultDisplayNames: Record<string, string> = {
    normal: 'Nominal Envelope',
    overheating: 'Thermal Overheating',
    lubrication_degradation: 'Lubrication Loss',
    injector_degradation: 'Fuel Injector Clog',
    sensor_fault: 'Sensor Drift / Bias',
    misfire: 'Cylinder Misfire',
    vibration_wear: 'Mechanical Vibration Wear',
  };

  // Feasibility status badge color
  const feasibilityStatus = feasibility.mission_feasibility_status || 'MISSION_CAPABLE';
  const feasibilityBadgeClass =
    feasibilityStatus === 'MISSION_CAPABLE'
      ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
      : feasibilityStatus === 'MISSION_AT_RISK'
      ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
      : feasibilityStatus === 'CRITICAL_INSUFFICIENT_RUL'
      ? 'bg-red-500/20 text-red-300 border-red-500/40 animate-pulse'
      : 'bg-slate-800 text-slate-400 border-slate-700';

  return (
    <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 space-y-3">
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

      {/* Existing diagnostic cards */}
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

            <div className="relative w-12 h-12 flex items-center justify-center">
              <svg className="w-12 h-12 transform -rotate-90">
                <circle cx="24" cy="24" r="20" stroke="#1E293B" strokeWidth="4" fill="transparent" />
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

                <div className="text-[11px] font-mono text-slate-400 mt-1 flex items-center justify-between">
                  <span>P10 — P90 CI:</span>
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

        {/* 3. ANOMALY DETECTION */}
        <div
          className={`rounded-lg border p-3 flex flex-col justify-between transition-all duration-300 ${
            anomaly.is_anomaly ? 'bg-red-950/20 border-red-500/50 shadow-glow-critical' : 'bg-avionics-card border-slate-800'
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
                <span className={`font-semibold ${anomaly.anomaly_score > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                  {anomaly.anomaly_score.toFixed(3)}
                </span>
              </div>
              <div>
                <span className="text-slate-500 text-[10px] block">DECISION FUNC</span>
                <span className="text-slate-300 font-semibold">{anomaly.decision_function.toFixed(3)}</span>
              </div>
            </div>
          </div>

          <div className="text-[10px] font-mono text-slate-500 pt-1 border-t border-slate-800/80">
            Threshold: 0.000 | Multi-sensor vector
          </div>
        </div>

        {/* 4. MULTICLASS FAULT CLASSIFICATION */}
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

          <div className="space-y-1 mt-1">
            {faultEntries.slice(0, 3).map(([key, prob]) => (
              <div key={key} className="text-[10px] font-mono">
                <div className="flex justify-between text-slate-400 mb-0.5">
                  <span className="truncate">{faultDisplayNames[key] || key}</span>
                  <span className="text-slate-200 font-semibold ml-1">{(prob * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-900 h-1 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      key === 'normal' ? 'bg-emerald-400' : prob > 0.3 ? 'bg-red-400' : 'bg-cyan-400'
                    }`}
                    style={{ width: `${Math.max(2, prob * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* UNIFIED DIAGNOSTIC RESULT */}
      <div
        className={`rounded-lg border p-3 transition-all duration-300 ${
          diagnostic.severity === 'CRITICAL' || diagnostic.severity === 'HIGH'
            ? 'bg-red-950/20 border-red-500/50 shadow-glow-critical'
            : diagnostic.severity === 'WARNING' || diagnostic.severity === 'MODERATE'
            ? 'bg-amber-950/10 border-amber-500/40'
            : 'bg-avionics-card border-emerald-900/40'
        }`}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wider">
              Unified Diagnostic Assessment
            </span>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-300">
            DIGITAL TWIN + ML
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
          {/* Fault ID */}
          <div>
            <span className="text-[9px] text-slate-500 font-mono block">FAULT ID</span>
            <span className="text-sm text-cyan-300 font-mono font-bold">{diagnostic.fault_id || 'NONE'}</span>
          </div>

          {/* Fault */}
          <div>
            <span className="text-[9px] text-slate-500 font-mono block">FAULT</span>
            <span className="text-sm text-slate-200 font-mono">{diagnostic.fault || 'NORMAL'}</span>
          </div>

          {/* Subsystem */}
          <div>
            <span className="text-[9px] text-slate-500 font-mono block">SUBSYSTEM</span>
            <span className="text-sm text-slate-200 font-mono">{diagnostic.subsystem || 'NONE'}</span>
          </div>

          {/* Confidence */}
          <div>
            <span className="text-[9px] text-slate-500 font-mono block">CONFIDENCE</span>
            <span className="text-sm text-cyan-300 font-mono font-bold">
              {(diagnostic.fault_confidence * 100).toFixed(1)}%
            </span>
          </div>

          {/* Severity */}
          <div>
            <span className="text-[9px] text-slate-500 font-mono block">SEVERITY</span>
            <span className={`text-sm font-mono font-bold ${severityColor}`}>{diagnostic.severity}</span>
          </div>

          {/* Sensor Drift */}
          <div>
            <span className="text-[9px] text-slate-500 font-mono block">SENSOR DRIFT</span>
            <span
              className={`text-sm font-mono font-bold ${
                diagnostic.possible_sensor_drift ? 'text-amber-400' : 'text-emerald-400'
              }`}
            >
              {diagnostic.possible_sensor_drift ? 'DETECTED' : 'NO'}
            </span>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-3">
          {/* Explanation */}
          <div>
            <span className="text-[9px] text-slate-500 font-mono block mb-1">DIAGNOSTIC EXPLANATION</span>
            <p className="text-xs text-slate-300 font-mono leading-relaxed">{diagnostic.explanation}</p>
          </div>

          {/* Maintenance Advisory */}
          <div>
            <span className="text-[9px] text-slate-500 font-mono block mb-1">MAINTENANCE ADVISORY</span>
            <p className="text-xs text-slate-300 font-mono leading-relaxed">{diagnostic.maintenance_advisory}</p>
          </div>
        </div>
      </div>

      {/* 5. MISSION FEASIBILITY & MAINTENANCE TRIGGER BAR */}
      <div className="bg-avionics-card rounded-lg border border-slate-800 p-3 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded bg-cyan-950/40 text-cyan-400 border border-cyan-800/30">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-slate-200 uppercase tracking-wide">
                Mission Feasibility & Duration Check
              </span>
              <span
                className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${feasibilityBadgeClass}`}
              >
                {feasibilityStatus.replace(/_/g, ' ')}
              </span>
            </div>
            <div className="text-[11px] font-mono text-slate-400 mt-0.5 flex flex-wrap items-center gap-3">
              <span>
                Planned Duration:{' '}
                <strong className="text-slate-200">{feasibility.planned_mission_duration_hours.toFixed(1)}h</strong>
              </span>
              <span>
                Remaining Mission:{' '}
                <strong className="text-slate-200">{feasibility.mission_remaining_time_hours.toFixed(1)}h</strong>
              </span>
              <span>
                Completion Margin:{' '}
                <strong
                  className={
                    (feasibility.mission_completion_margin_hours || 0) > 10
                      ? 'text-emerald-400'
                      : (feasibility.mission_completion_margin_hours || 0) > 0
                      ? 'text-amber-400'
                      : 'text-red-400'
                  }
                >
                  {feasibility.mission_completion_margin_hours !== null
                    ? `${feasibility.mission_completion_margin_hours > 0 ? '+' : ''}${feasibility.mission_completion_margin_hours.toFixed(1)}h`
                    : '--'}
                </strong>
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4 w-full md:w-auto justify-between md:justify-end border-t md:border-t-0 border-slate-800/80 pt-2 md:pt-0">
          <div>
            <span className="text-[10px] font-mono text-slate-500 block text-right">COMPLETION PROBABILITY</span>
            <div className="flex items-center gap-2">
              <div className="w-24 bg-slate-900 h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full ${
                    (feasibility.mission_completion_probability_pct || 0) > 90
                      ? 'bg-emerald-500'
                      : (feasibility.mission_completion_probability_pct || 0) > 60
                      ? 'bg-amber-500'
                      : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(0, feasibility.mission_completion_probability_pct || 0))}%` }}
                />
              </div>
              <span className="text-xs font-mono font-bold text-slate-200">
                {feasibility.mission_completion_probability_pct !== null
                  ? `${feasibility.mission_completion_probability_pct.toFixed(1)}%`
                  : '--'}
              </span>
            </div>
          </div>

          <div className="border-l border-slate-800 pl-3">
            <span className="text-[10px] font-mono text-slate-500 block">MAINTENANCE TRIGGER</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <Wrench className="w-3.5 h-3.5 text-cyan-400" />
              <span className="text-xs font-mono font-semibold text-slate-200 truncate max-w-[220px]">
                {feasibility.maintenance_trigger || 'NOMINAL'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
