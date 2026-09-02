import React, { useMemo } from 'react';
import { useDigitalTwinStore } from '../../store/useDigitalTwinStore';
import type { XaiDriver } from '../../api/types';
import { Sparkles, ShieldCheck, AlertCircle } from 'lucide-react';

export const XaiPanel: React.FC = () => {
  const { currentFrame } = useDigitalTwinStore();
  const xai = currentFrame?.xai || currentFrame?.xai_explanation;

  // Extract and normalize diagnostic drivers
  const drivers: XaiDriver[] = useMemo(() => {
    if (!xai) return [];

    // 1. Direct top_diagnostic_drivers if available
    if (xai.top_diagnostic_drivers && xai.top_diagnostic_drivers.length > 0) {
      return xai.top_diagnostic_drivers.map((d) => ({
        sensor: d.sensor || d.display_name || d.feature || 'Unknown Sensor',
        impact: d.impact || (d.attribution_score && d.attribution_score > 0.05 ? 'ELEVATED' : 'NOMINAL'),
        attribution_score: d.attribution_score ?? d.importance ?? Math.abs(d.shap_value || 0),
        direction: d.direction || 'increases_likelihood',
        direction_text: d.direction_text || `${d.sensor} influence`,
      }));
    }

    // 2. Extract from fault model top_contributors
    if (xai.fault?.top_contributors && xai.fault.top_contributors.length > 0) {
      return xai.fault.top_contributors.map((c) => ({
        sensor: c.display_name || c.feature || 'Telemetry Signal',
        impact: Math.abs(c.shap_value || 0) > 0.2 ? 'HIGH_IMPACT' : 'MODERATE',
        attribution_score: Math.abs(c.shap_value || c.importance || 0),
        direction: c.direction,
        direction_text: c.direction_text,
      }));
    }

    // 3. Extract from anomaly model top_contributors
    if (xai.anomaly?.top_contributors && xai.anomaly.top_contributors.length > 0) {
      return xai.anomaly.top_contributors.map((c) => ({
        sensor: c.display_name || c.feature || 'Telemetry Signal',
        impact: (c.importance || 0) > 0.3 ? 'ANOMALOUS_DEVIATION' : 'NOMINAL',
        attribution_score: c.importance || 0,
        direction: c.direction,
        direction_text: c.direction_text,
      }));
    }

    // Default fallback nominal driver
    return [
      {
        sensor: 'Cylinder Head Temperature (CHT)',
        impact: 'NOMINAL',
        attribution_score: 0.012,
        direction: 'neutral',
        direction_text: 'Within calibrated nominal thermodynamic envelope',
      },
      {
        sensor: 'Exhaust Gas Temperature (EGT)',
        impact: 'NOMINAL',
        attribution_score: 0.009,
        direction: 'neutral',
        direction_text: 'Combustion exhaust baseline normal',
      },
      {
        sensor: 'Engine RPM / Manifold Torque',
        impact: 'NOMINAL',
        attribution_score: 0.007,
        direction: 'neutral',
        direction_text: 'Governed cruising speed matched to throttle demand',
      },
    ];
  }, [xai]);

  // Max score for bar scaling
  const maxScore = Math.max(...drivers.map((d) => d.attribution_score || 0.01), 0.05);

  const interpretation =
    xai?.engineering_interpretation ||
    xai?.fault?.summary ||
    xai?.human_summary ||
    'Propulsion system telemetry adheres strictly to calibrated aero piston engine baseline curves. No thermal, lubrication, or combustion anomalies detected.';

  const recommendations = xai?.recommendations || [
    'Maintain standard cruise throttle and monitored cruising altitude.',
    'Continue real-time CAN bus telemetry acquisition and physics residual synchronization.',
  ];

  return (
    <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase">
            Explainable AI (XAI) & SHAP Root-Cause Attribution
          </h3>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/40 text-cyan-300 border border-cyan-800/40">
          TREE-SHAP EXPLAINER
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Left: Ranked Diagnostic Drivers Horizontal Impact Bar Chart */}
        <div className="lg:col-span-7 bg-avionics-card rounded-lg border border-slate-800 p-3 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Top Diagnostic Drivers (Attribution Ranking)
            </span>
            <span className="text-[10px] font-mono text-slate-500">|SHAP Contribution|</span>
          </div>

          <div className="space-y-2 pt-1">
            {drivers.slice(0, 5).map((d, idx) => {
              const score = d.attribution_score || 0;
              const barWidth = Math.min(100, Math.max(5, (score / maxScore) * 100));
              const isHigh = score > 0.2 || (d.impact && d.impact.includes('HIGH'));
              const isWarning = score > 0.08 || (d.impact && d.impact.includes('ELEVATED'));

              return (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <div className="flex items-center gap-1.5 truncate max-w-[70%]">
                      <span className="text-slate-500 text-[10px] w-3">{idx + 1}.</span>
                      <span className="font-semibold text-slate-200 truncate">
                        {d.sensor || d.feature}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded font-semibold uppercase ${
                          isHigh
                            ? 'bg-red-500/20 text-red-400'
                            : isWarning
                            ? 'bg-amber-500/20 text-amber-400'
                            : 'bg-slate-800 text-cyan-400'
                        }`}
                      >
                        {d.impact || 'NOMINAL'}
                      </span>
                      <span className="font-bold text-slate-300 min-w-[45px] text-right">
                        {score.toFixed(3)}
                      </span>
                    </div>
                  </div>

                  {/* Horizontal attribution bar */}
                  <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        isHigh
                          ? 'bg-red-500 shadow-glow-critical'
                          : isWarning
                          ? 'bg-amber-400'
                          : 'bg-cyan-400 shadow-glow-cyan'
                      }`}
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>

                  {/* Micro explanation text */}
                  {d.direction_text && (
                    <div className="text-[10px] font-mono text-slate-500 truncate pl-4">
                      {d.direction_text}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Engineering Interpretation & Prescriptive Actions */}
        <div className="lg:col-span-5 flex flex-col gap-2.5">
          {/* Engineering Narrative */}
          <div className="bg-avionics-card rounded-lg border border-slate-800 p-3 flex-1">
            <div className="flex items-center gap-1.5 mb-1.5 text-xs font-medium text-slate-400 uppercase tracking-wider">
              <AlertCircle className="w-3.5 h-3.5 text-cyan-400" />
              Automated Engineering Assessment
            </div>
            <p className="text-xs font-mono text-slate-300 leading-relaxed max-h-28 overflow-y-auto pr-1">
              {interpretation}
            </p>
          </div>

          {/* Actionable Recommendations */}
          <div className="bg-avionics-card rounded-lg border border-slate-800 p-3 flex-1">
            <div className="flex items-center gap-1.5 mb-1.5 text-xs font-medium text-slate-400 uppercase tracking-wider">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Autonomous Maintenance Actions
            </div>
            <ul className="space-y-1 text-xs font-mono text-slate-300">
              {recommendations.slice(0, 2).map((rec, i) => (
                <li key={i} className="flex items-start gap-1.5 text-[11px] leading-snug">
                  <span className="text-emerald-400 mt-0.5">•</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
