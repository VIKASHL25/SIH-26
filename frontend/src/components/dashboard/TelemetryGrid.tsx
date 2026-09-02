import React, { useMemo } from 'react';
import { GaugeTile } from '../common/GaugeTile';
import type { GaugeTileProps } from '../common/GaugeTile';
import { useDigitalTwinStore } from '../../store/useDigitalTwinStore';
import {
  Gauge,
  Flame,
  Thermometer,
  Droplets,
  Activity,
  Fuel,
  Zap,
  Mountain,
  Compass,
  Sliders,
} from 'lucide-react';

export const TelemetryGrid: React.FC = () => {
  const { currentFrame, frameHistory } = useDigitalTwinStore();

  const tel = currentFrame?.telemetry || {
    rpm: 0,
    throttle_pct: 0,
    load_pct: 0,
    cht_C: 0,
    egt_C: 0,
    oil_temperature_C: 0,
    oil_pressure_bar: 0,
    fuel_flow_kg_s: 0,
    vibration_rms: 0,
    battery_voltage_V: 0,
    alternator_current_A: 0,
    altitude_m: 0,
    ambient_temp_C: 0,
  };

  const phys = currentFrame?.physics_model;

  // Extract rolling history arrays for sparklines
  const histories = useMemo(() => {
    return {
      rpm: frameHistory.map((f) => f.telemetry.rpm),
      cht_C: frameHistory.map((f) => f.telemetry.cht_C),
      egt_C: frameHistory.map((f) => f.telemetry.egt_C),
      oil_pressure_bar: frameHistory.map((f) => f.telemetry.oil_pressure_bar),
      oil_temperature_C: frameHistory.map((f) => f.telemetry.oil_temperature_C),
      vibration_rms: frameHistory.map((f) => f.telemetry.vibration_rms),
      fuel_flow_kg_s: frameHistory.map((f) => f.telemetry.fuel_flow_kg_s),
      battery_voltage_V: frameHistory.map((f) => f.telemetry.battery_voltage_V),
      alternator_current_A: frameHistory.map((f) => f.telemetry.alternator_current_A),
      altitude_m: frameHistory.map((f) => f.telemetry.altitude_m),
      ambient_temp_C: frameHistory.map((f) => f.telemetry.ambient_temp_C),
      throttle_pct: frameHistory.map((f) => f.telemetry.throttle_pct),
    };
  }, [frameHistory]);

  const tileConfigs: GaugeTileProps[] = [
    {
      label: 'Engine RPM',
      value: tel.rpm,
      unit: 'RPM',
      min: 1500,
      max: 3000,
      nominalLow: 1900,
      nominalHigh: 2600,
      warningHigh: 2750,
      warningLow: 1750,
      expectedValue: phys?.expected_rpm,
      precision: 0,
      history: histories.rpm,
      icon: <Gauge className="w-3.5 h-3.5" />,
    },
    {
      label: 'Cylinder Head Temp',
      value: tel.cht_C,
      unit: '°C',
      min: 80,
      max: 200,
      nominalLow: 110,
      nominalHigh: 155,
      warningHigh: 165,
      warningLow: 95,
      expectedValue: phys?.expected_cht_C,
      precision: 1,
      history: histories.cht_C,
      icon: <Thermometer className="w-3.5 h-3.5" />,
    },
    {
      label: 'Exhaust Gas Temp',
      value: tel.egt_C,
      unit: '°C',
      min: 500,
      max: 900,
      nominalLow: 620,
      nominalHigh: 740,
      warningHigh: 780,
      warningLow: 580,
      expectedValue: phys?.expected_egt_C,
      precision: 1,
      history: histories.egt_C,
      icon: <Flame className="w-3.5 h-3.5" />,
    },
    {
      label: 'Oil Pressure',
      value: tel.oil_pressure_bar,
      unit: 'bar',
      min: 1.0,
      max: 7.0,
      nominalLow: 3.5,
      nominalHigh: 5.5,
      warningHigh: 6.2,
      warningLow: 3.0,
      precision: 2,
      history: histories.oil_pressure_bar,
      icon: <Droplets className="w-3.5 h-3.5" />,
    },
    {
      label: 'Oil Temperature',
      value: tel.oil_temperature_C,
      unit: '°C',
      min: 40,
      max: 130,
      nominalLow: 75,
      nominalHigh: 105,
      warningHigh: 115,
      warningLow: 60,
      precision: 1,
      history: histories.oil_temperature_C,
      icon: <Thermometer className="w-3.5 h-3.5" />,
    },
    {
      label: 'Vibration RMS',
      value: tel.vibration_rms,
      unit: 'g-rms',
      min: 0.0,
      max: 0.6,
      nominalLow: 0.05,
      nominalHigh: 0.25,
      warningHigh: 0.35,
      warningLow: 0.0,
      precision: 3,
      history: histories.vibration_rms,
      icon: <Activity className="w-3.5 h-3.5" />,
    },
    {
      label: 'Fuel Mass Flow',
      value: tel.fuel_flow_kg_s,
      unit: 'kg/s',
      min: 0.001,
      max: 0.01,
      nominalLow: 0.0035,
      nominalHigh: 0.0068,
      warningHigh: 0.008,
      warningLow: 0.0025,
      precision: 4,
      history: histories.fuel_flow_kg_s,
      icon: <Fuel className="w-3.5 h-3.5" />,
    },
    {
      label: 'Battery Bus Voltage',
      value: tel.battery_voltage_V,
      unit: 'V',
      min: 20.0,
      max: 32.0,
      nominalLow: 26.5,
      nominalHigh: 28.8,
      warningHigh: 30.0,
      warningLow: 24.5,
      precision: 1,
      history: histories.battery_voltage_V,
      icon: <Zap className="w-3.5 h-3.5" />,
    },
    {
      label: 'Alternator Current',
      value: tel.alternator_current_A,
      unit: 'A',
      min: 5.0,
      max: 45.0,
      nominalLow: 15.0,
      nominalHigh: 32.0,
      warningHigh: 38.0,
      warningLow: 10.0,
      precision: 1,
      history: histories.alternator_current_A,
      icon: <Zap className="w-3.5 h-3.5" />,
    },
    {
      label: 'GPS Altitude',
      value: tel.altitude_m,
      unit: 'm',
      min: 0,
      max: 6000,
      nominalLow: 500,
      nominalHigh: 5000,
      warningHigh: 5500,
      warningLow: 100,
      precision: 0,
      history: histories.altitude_m,
      icon: <Mountain className="w-3.5 h-3.5" />,
    },
    {
      label: 'Ambient Temp',
      value: tel.ambient_temp_C,
      unit: '°C',
      min: -30,
      max: 55,
      nominalLow: -15,
      nominalHigh: 40,
      warningHigh: 48,
      warningLow: -25,
      precision: 1,
      history: histories.ambient_temp_C,
      icon: <Compass className="w-3.5 h-3.5" />,
    },
    {
      label: 'Throttle Position',
      value: tel.throttle_pct,
      unit: '%',
      min: 0,
      max: 100,
      nominalLow: 20,
      nominalHigh: 90,
      warningHigh: 98,
      warningLow: 10,
      precision: 1,
      history: histories.throttle_pct,
      icon: <Sliders className="w-3.5 h-3.5" />,
    },
  ];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-mono font-bold tracking-wider text-slate-300 uppercase flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          Real-Time Sensor Telemetry Matrix (CAN 2.0B Decoded)
        </h3>
        <span className="text-[10px] font-mono text-slate-500">
          12 CHANNELS ACTIVE
        </span>
      </div>

      {/* Grid of Gauges */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2.5">
        {tileConfigs.map((cfg) => (
          <GaugeTile key={cfg.label} {...cfg} />
        ))}
      </div>
    </div>
  );
};
