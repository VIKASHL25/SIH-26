import React, { useState } from 'react';
import { api } from '../../api/client';
import { useDigitalTwinStore } from '../../store/useDigitalTwinStore';
import { Zap, RotateCcw, Check, SlidersHorizontal } from 'lucide-react';

interface PresetScenario {
  name: string;
  overrides: Record<string, number>;
  desc: string;
}

export const FaultInjectionPanel: React.FC = () => {
  const { activeFaultOverrides, setActiveFaultOverrides } = useDigitalTwinStore();

  const [paramKey, setParamKey] = useState<string>('cht_C');
  const [deltaVal, setDeltaVal] = useState<number>(35.0);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [notification, setNotification] = useState<string | null>(null);

  const parameterOptions = [
    { key: 'cht_C', label: 'Cylinder Head Temp (°C)', defaultVal: 35.0 },
    { key: 'egt_C', label: 'Exhaust Gas Temp (°C)', defaultVal: 60.0 },
    { key: 'oil_pressure_bar', label: 'Oil Pressure (bar)', defaultVal: -2.2 },
    { key: 'oil_temperature_C', label: 'Oil Temp (°C)', defaultVal: 25.0 },
    { key: 'vibration_rms', label: 'Vibration RMS (g)', defaultVal: 0.22 },
    { key: 'fuel_flow_kg_s', label: 'Fuel Flow (kg/s)', defaultVal: -0.002 },
    { key: 'rpm', label: 'Engine RPM', defaultVal: -350.0 },
    { key: 'battery_voltage_V', label: 'Battery Voltage (V)', defaultVal: -4.5 },
  ];

  const presets: PresetScenario[] = [
    {
      name: 'Thermal Overheating',
      overrides: { cht_C: 42.0, egt_C: 55.0 },
      desc: '+42°C CHT, +55°C EGT',
    },
    {
      name: 'Lubrication Loss',
      overrides: { oil_pressure_bar: -2.3, oil_temperature_C: 22.0 },
      desc: '-2.3 bar Oil Press, +22°C Temp',
    },
    {
      name: 'Vibration / Mechanical',
      overrides: { vibration_rms: 0.28, rpm: -250.0 },
      desc: '+0.28g Vib, -250 RPM',
    },
    {
      name: 'Fuel Injector Lean',
      overrides: { fuel_flow_kg_s: -0.0018, egt_C: 45.0 },
      desc: '-0.0018 kg/s Fuel, +45°C EGT',
    },
  ];

  const handleApplyCustom = async () => {
    setIsSubmitting(true);
    setNotification(null);
    try {
      const merged = { ...activeFaultOverrides, [paramKey]: deltaVal };
      const res = await api.injectFault(merged);
      setActiveFaultOverrides(res.active_overrides || merged);
      setNotification(`Injected ${paramKey} ${deltaVal > 0 ? '+' : ''}${deltaVal}`);
    } catch (err: any) {
      console.error('Fault injection failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApplyPreset = async (overrides: Record<string, number>, name: string) => {
    setIsSubmitting(true);
    setNotification(null);
    try {
      const merged = { ...activeFaultOverrides, ...overrides };
      const res = await api.injectFault(merged);
      setActiveFaultOverrides(res.active_overrides || merged);
      setNotification(`Preset activated: ${name}`);
    } catch (err: any) {
      console.error('Preset fault injection failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClear = async () => {
    setIsSubmitting(true);
    setNotification(null);
    try {
      await api.clearFaults();
      setActiveFaultOverrides({});
      setNotification('All synthetic fault overrides cleared.');
    } catch (err: any) {
      console.error('Clear faults failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const hasActiveOverrides = Object.keys(activeFaultOverrides).length > 0;

  return (
    <div className="bg-avionics-surface border border-avionics-border rounded-lg p-3.5 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" />
          <h3 className="text-xs font-mono font-bold tracking-wider text-slate-200 uppercase">
            Synthetic Fault Injection & "What-If" Analysis
          </h3>
        </div>

        {hasActiveOverrides ? (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/40 animate-pulse font-bold">
            OVERRIDE ACTIVE ({Object.keys(activeFaultOverrides).length})
          </span>
        ) : (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
            NOMINAL STREAM
          </span>
        )}
      </div>

      {/* Preset Quick Injectors */}
      <div>
        <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block mb-1.5">
          Quick Fault Scenario Presets:
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {presets.map((p) => (
            <button
              key={p.name}
              onClick={() => handleApplyPreset(p.overrides, p.name)}
              disabled={isSubmitting}
              className="p-2 rounded bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-amber-500/40 text-left transition-all group disabled:opacity-50"
            >
              <div className="text-xs font-mono font-bold text-slate-200 group-hover:text-amber-400 transition-colors">
                {p.name}
              </div>
              <div className="text-[10px] font-mono text-slate-500 truncate mt-0.5">
                {p.desc}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Custom Parameter Delta Override Form */}
      <div className="pt-2 border-t border-slate-800 flex flex-wrap items-center gap-2.5">
        <div className="flex items-center gap-1.5 min-w-[180px] flex-1">
          <label className="text-[11px] font-mono text-slate-400 whitespace-nowrap">
            Param:
          </label>
          <select
            value={paramKey}
            onChange={(e) => {
              setParamKey(e.target.value);
              const found = parameterOptions.find((o) => o.key === e.target.value);
              if (found) setDeltaVal(found.defaultVal);
            }}
            className="w-full bg-slate-900 border border-slate-700 text-cyan-300 text-xs font-mono rounded px-2 py-1.5 focus:outline-none"
          >
            {parameterOptions.map((opt) => (
              <option key={opt.key} value={opt.key}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1.5 w-36">
          <label className="text-[11px] font-mono text-slate-400 whitespace-nowrap">
            Delta:
          </label>
          <input
            type="number"
            step="any"
            value={deltaVal}
            onChange={(e) => setDeltaVal(parseFloat(e.target.value) || 0)}
            className="w-full bg-slate-900 border border-slate-700 text-slate-100 text-xs font-mono rounded px-2 py-1.5 focus:outline-none focus:border-cyan-500"
          />
        </div>

        <button
          onClick={handleApplyCustom}
          disabled={isSubmitting}
          className="px-3 py-1.5 rounded bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-xs font-mono font-bold tracking-wider transition-all disabled:opacity-50 whitespace-nowrap flex items-center gap-1"
        >
          <SlidersHorizontal className="w-3 h-3" />
          INJECT OVERRIDE
        </button>

        {hasActiveOverrides && (
          <button
            onClick={handleClear}
            disabled={isSubmitting}
            className="px-3 py-1.5 rounded bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/40 text-xs font-mono font-bold tracking-wider transition-all disabled:opacity-50 whitespace-nowrap flex items-center gap-1"
          >
            <RotateCcw className="w-3 h-3" />
            CLEAR ALL FAULTS
          </button>
        )}
      </div>

      {/* Active Overrides Badges */}
      {hasActiveOverrides && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1 font-mono text-xs">
          <span className="text-slate-500 text-[10px]">CURRENT OVERRIDES:</span>
          {Object.entries(activeFaultOverrides).map(([key, val]) => (
            <span
              key={key}
              className="px-2 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-500/30 text-[11px]"
            >
              {key}: {val > 0 ? `+${val}` : val}
            </span>
          ))}
        </div>
      )}

      {/* Status notification toast */}
      {notification && (
        <div className="text-[11px] font-mono text-emerald-400 flex items-center gap-1">
          <Check className="w-3 h-3 text-emerald-400" />
          <span>{notification}</span>
        </div>
      )}
    </div>
  );
};
