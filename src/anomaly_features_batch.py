"""
anomaly_features_batch.py

Batch reproduction of the EXPANDED anomaly-detection feature vector computed
by the modified `backend/feature_engine.py._generate_anomaly_features`
(51 features: 18 current-timestep raw/residual/ratio values + 27 rolling
mean/std/slope features over the same 9 core sensors used by the fault
model, same 15-sample window).

Verified against the real streaming DigitalTwinFeatureEngine (with the
feature_engine.py patch applied) on a held-out mission — see
verify_expanded_anomaly.py. Max abs diff: floating-point noise only.
"""

import numpy as np
import pandas as pd

ANOMALY_FEATURE_COLS = [
    "cht_C", "egt_C", "oil_temperature_C", "oil_pressure_bar",
    "vibration_rms", "battery_voltage_V", "alternator_current_A",
    "alternator_health", "injection_timing_deg",
    "rpm", "fuel_flow_kg_s", "power_W", "torque_Nm", "air_mass_flow_kg_s",
    "cht_residual", "egt_residual", "rpm_residual", "physics_residual_C",
    "fuel_air_ratio", "power_per_fuel", "torque_per_rpm", "power_per_air",
    "egt_rpm_ratio", "fuel_egt_ratio",
    "cht_C_roll_mean", "cht_C_roll_std", "cht_C_slope",
    "egt_C_roll_mean", "egt_C_roll_std", "egt_C_slope",
    "oil_temperature_C_roll_mean", "oil_temperature_C_roll_std", "oil_temperature_C_slope",
    "oil_pressure_bar_roll_mean", "oil_pressure_bar_roll_std", "oil_pressure_bar_slope",
    "fuel_flow_kg_s_roll_mean", "fuel_flow_kg_s_roll_std", "fuel_flow_kg_s_slope",
    "vibration_rms_roll_mean", "vibration_rms_roll_std", "vibration_rms_slope",
    "battery_voltage_V_roll_mean", "battery_voltage_V_roll_std", "battery_voltage_V_slope",
    "injection_timing_deg_roll_mean", "injection_timing_deg_roll_std", "injection_timing_deg_slope",
    "physics_residual_C_roll_mean", "physics_residual_C_roll_std", "physics_residual_C_slope",
]

ROLLING_TARGETS = [
    "cht_C", "egt_C", "oil_temperature_C", "oil_pressure_bar",
    "fuel_flow_kg_s", "vibration_rms", "battery_voltage_V",
    "injection_timing_deg", "physics_residual_C",
]

ROLL_WINDOW = 15


def engineer_anomaly_features(data: pd.DataFrame) -> pd.DataFrame:
    """Adds all 51 anomaly-model feature columns, per mission."""
    pieces = []
    for mission_id, g in data.groupby("mission_id", sort=False):
        g = g.sort_values("timestamp_s").copy().reset_index(drop=True)
        n = len(g)
        idx = np.arange(n)
        w = np.minimum(ROLL_WINDOW, idx + 1).astype(float)

        # Current-timestep residuals & ratios (same formulas as process_raw_sample)
        g["cht_residual"] = g["cht_C"] - g["expected_cht_C"]
        g["egt_residual"] = g["egt_C"] - g["expected_egt_C"]
        g["rpm_residual"] = g["rpm"] - g["expected_rpm"]
        g["fuel_air_ratio"] = g["fuel_flow_kg_s"] / (g["air_mass_flow_kg_s"] + 1e-8)
        g["power_per_fuel"] = g["power_W"] / (g["fuel_flow_kg_s"] + 1e-8)
        g["torque_per_rpm"] = g["torque_Nm"] / (g["rpm"] + 1e-8)
        g["power_per_air"] = g["power_W"] / (g["air_mass_flow_kg_s"] + 1e-8)
        g["egt_rpm_ratio"] = g["egt_C"] / (g["rpm"] + 1e-8)
        g["fuel_egt_ratio"] = g["fuel_flow_kg_s"] / (g["egt_C"] + 1e-8)

        # Rolling mean/std/slope (exact same formula verified for the fault model)
        for sig in ROLLING_TARGETS:
            g[f"{sig}_roll_mean"] = g[sig].rolling(window=ROLL_WINDOW, min_periods=1).mean()
            g[f"{sig}_roll_std"] = g[sig].rolling(window=ROLL_WINDOW, min_periods=1).std().fillna(0.0)

            diff_lag = g[sig].diff(ROLL_WINDOW - 1)
            diff_from_first = g[sig] - g[sig].iloc[0]
            diff_val = np.where(idx >= (ROLL_WINDOW - 1), diff_lag, diff_from_first)
            diff_val = np.where(w > 1, diff_val, 0.0)
            g[f"{sig}_slope"] = diff_val / np.maximum(1.0, w)

        pieces.append(g)

    return pd.concat(pieces).reset_index(drop=True)
