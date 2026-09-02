import React, { useState } from 'react';
import { useDigitalTwinStore } from '../../store/useDigitalTwinStore';
import { Bell, AlertTriangle, AlertOctagon, CheckCircle2, Trash2 } from 'lucide-react';

export const AdvisoryFeed: React.FC = () => {
  const { advisoryList, clearAdvisories } = useDigitalTwinStore();
  const [filter, setFilter] = useState<'ALL' | 'CRITICAL' | 'WARNING'>('ALL');

  const filtered = advisoryList.filter((adv) => {
    if (filter === 'ALL') return true;
    return adv.level === filter;
  });

  return (
    <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 flex flex-col h-[280px]">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase">
            Real-Time Maintenance Advisories & Alerts
          </h3>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
            {advisoryList.length} LOGGED
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Filters */}
          <div className="flex items-center rounded border border-slate-800 bg-slate-900 p-0.5 text-[10px] font-mono">
            <button
              onClick={() => setFilter('ALL')}
              className={`px-2 py-0.5 rounded ${
                filter === 'ALL' ? 'bg-cyan-500/20 text-cyan-300 font-bold' : 'text-slate-400'
              }`}
            >
              ALL
            </button>
            <button
              onClick={() => setFilter('CRITICAL')}
              className={`px-2 py-0.5 rounded ${
                filter === 'CRITICAL' ? 'bg-red-500/20 text-red-400 font-bold' : 'text-slate-400'
              }`}
            >
              CRIT
            </button>
            <button
              onClick={() => setFilter('WARNING')}
              className={`px-2 py-0.5 rounded ${
                filter === 'WARNING' ? 'bg-amber-500/20 text-amber-400 font-bold' : 'text-slate-400'
              }`}
            >
              WARN
            </button>
          </div>

          {/* Clear button */}
          {advisoryList.length > 0 && (
            <button
              onClick={clearAdvisories}
              title="Clear advisory feed"
              className="text-slate-500 hover:text-red-400 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Advisory Feed List */}
      <div className="flex-1 overflow-y-auto space-y-2 mt-2 pr-1">
        {filtered.length > 0 ? (
          filtered.map((adv) => {
            const isCrit = adv.level === 'CRITICAL';
            const isWarn = adv.level === 'WARNING';

            const itemBg = isCrit
              ? 'bg-red-950/20 border-red-500/40 text-red-300'
              : isWarn
              ? 'bg-amber-950/20 border-amber-500/40 text-amber-300'
              : 'bg-slate-900/60 border-slate-800 text-slate-300';

            return (
              <div
                key={adv.id}
                className={`p-2 rounded border text-xs font-mono flex items-start gap-2 transition-all ${itemBg}`}
              >
                <div className="mt-0.5 flex-shrink-0">
                  {isCrit ? (
                    <AlertOctagon className="w-4 h-4 text-red-400" />
                  ) : isWarn ? (
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between text-[10px] text-slate-500 mb-0.5">
                    <span className="font-bold uppercase tracking-wider">
                      {isCrit ? 'CRITICAL ALERT' : isWarn ? 'WARNING ADVISORY' : 'NOMINAL ADVISORY'}
                    </span>
                    <span>{adv.timestamp}</span>
                  </div>
                  <p className="leading-snug text-slate-200">{adv.text}</p>
                </div>
              </div>
            );
          })
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 font-mono text-xs space-y-1">
            <CheckCircle2 className="w-5 h-5 text-emerald-500/60" />
            <span>NO ACTIVE SYSTEM ADVISORIES</span>
            <span className="text-[10px] text-slate-600">All subsystems operating within nominal envelope</span>
          </div>
        )}
      </div>
    </div>
  );
};
