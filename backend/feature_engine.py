import numpy as np
import pandas as pd
from typing import Optional
from collections import deque
from backend.config import DEFAULT_SENSOR_DEFAULTS

class DigitalTwinFeatureEngine:
    """
    Real-Time Physics & Time-Series Feature Engine for Aero Piston Engine Digital Twin.
    
    Maintains a rolling historical buffer of raw sensor telemetry to compute:
    1. Physics residuals & thermodynamic ratio parameters.
    2. Model 1 (Anomaly Detection) 13-feature vector.
    3. Model 2 (Degradation Detection) 120-feature vector.
    4. Model 3 (Fault Classification) 55-feature vector.
    5. Model 4 (RUL Estimation) 60-feature vector.
    """

    def __init__(self, max_buffer_size: int = 120):
        self.max_buffer_size = max_buffer_size
        self.buffer = deque(maxlen=max_buffer_size)

    def reset(self):
        """Clears the history buffer."""
        self.buffer.clear()

    def process_raw_sample(self, raw_sample: dict) -> dict:
        """
        Cleans, fills defaults, and adds calculated physics residuals to a raw telemetry frame.
        """
        sample = dict(DEFAULT_SENSOR_DEFAULTS)
        sample.update(raw_sample)

        # Handle column naming variations (e.g. throttle vs throttle_pct)
        if "throttle" in raw_sample and "throttle_pct" not in raw_sample:
            sample["throttle_pct"] = float(raw_sample["throttle"])
        elif "throttle_pct" in raw_sample:
            sample["throttle"] = float(raw_sample["throttle_pct"])
        else:
            sample["throttle"] = sample["throttle_pct"]

        if "load" in raw_sample and "load_pct" not in raw_sample:
            sample["load_pct"] = float(raw_sample["load"])
        elif "load_pct" in raw_sample:
            sample["load"] = float(raw_sample["load_pct"])
        else:
            sample["load"] = sample["load_pct"]

        # Ensure timestamp_hours is available for RUL features if present
        if "timestamp_s" in raw_sample and "timestamp_hours" not in sample:
            sample["timestamp_hours"] = float(raw_sample["timestamp_s"]) / 3600.0
        elif "timestamp_hours" not in sample:
            sample["timestamp_hours"] = len(self.buffer) * 10.0 / 3600.0

        # Ensure numeric types
        for k in sample:
            if isinstance(sample[k], (int, float)):
                sample[k] = float(sample[k])

        # Calculate Physics Residuals
        cht_C = sample["cht_C"]
        exp_cht = sample.get("expected_cht_C", cht_C)
        sample["cht_residual"] = cht_C - exp_cht

        egt_C = sample["egt_C"]
        exp_egt = sample.get("expected_egt_C", egt_C)
        sample["egt_residual"] = egt_C - exp_egt

        rpm = sample["rpm"]
        exp_rpm = sample.get("expected_rpm", rpm)
        sample["rpm_residual"] = rpm - exp_rpm

        if "physics_residual_C" not in raw_sample:
            sample["physics_residual_C"] = sample["cht_residual"]

        # Ratios
        air_flow = sample["air_mass_flow_kg_s"]
        fuel_flow = sample["fuel_flow_kg_s"]
        power_W = sample["power_W"]
        torque_Nm = sample["torque_Nm"]

        sample["fuel_air_ratio"] = fuel_flow / (air_flow + 1e-8)
        sample["power_per_fuel"] = power_W / (fuel_flow + 1e-8)
        sample["torque_per_rpm"] = torque_Nm / (rpm + 1e-8)
        sample["power_per_air"] = power_W / (air_flow + 1e-8)
        sample["egt_rpm_ratio"] = egt_C / (rpm + 1e-8)
        sample["fuel_egt_ratio"] = fuel_flow / (egt_C + 1e-8)

        # Append to buffer
        self.buffer.append(sample)

        return sample

    def generate_all_feature_vectors(
        self,
        raw_sample: dict,
        model_manager
    ) -> dict:
        """
        Processes a raw sample and generates feature vectors for all 4 models.
        """
        clean_sample = self.process_raw_sample(raw_sample)

        # Convert buffer to DataFrame for rolling calculations
        history_df = pd.DataFrame(list(self.buffer))

        # 1. Model 1 (Anomaly Detection Features - 13 columns)
        anomaly_df = self._generate_anomaly_features(clean_sample, model_manager.anomaly_feature_cols)

        # 2. Model 2 (Degradation Features - 120 columns)
        degradation_df = self._generate_degradation_features(history_df, model_manager.degradation_feature_cols)

        # 3. Model 3 (Fault Detection Features - 55 columns)
        fault_df = self._generate_fault_features(history_df, model_manager.fault_feature_cols)

        # 4. Model 4 (RUL Features - 60 columns)
        rul_df = self._generate_rul_features(history_df, model_manager.rul_feature_cols)

        return {
            "clean_sample": clean_sample,
            "anomaly": anomaly_df,
            "degradation": degradation_df,
            "fault": fault_df,
            "rul": rul_df
        }

    def _generate_anomaly_features(self, clean_sample: dict, feature_cols: list) -> pd.DataFrame:
        row = {col: clean_sample.get(col, 0.0) for col in feature_cols}
        return pd.DataFrame([row], columns=feature_cols)

    def _generate_degradation_features(self, history_df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
        df = history_df.copy()
        
        target_signals = [
            "rpm", "egt_C", "cht_C", "oil_temperature_C", "oil_pressure_bar",
            "vibration_rms", "fuel_flow_kg_s", "air_mass_flow_kg_s", "rpm_residual", "egt_residual"
        ]

        new_cols = {}
        # Compute Diffs
        for sig in target_signals:
            if sig in df.columns:
                for lag in [1, 5, 10]:
                    new_cols[f"{sig}_diff{lag}"] = df[sig].diff(lag).fillna(0.0)

        # Compute Rolling Means & Stds
        for sig in target_signals:
            if sig in df.columns:
                for w in [5, 15, 30]:
                    new_cols[f"{sig}_rollmean{w}"] = df[sig].rolling(window=w, min_periods=1).mean()
                    new_cols[f"{sig}_rollstd{w}"] = df[sig].rolling(window=w, min_periods=1).std().fillna(0.0)

        df = pd.concat([df, pd.DataFrame(new_cols)], axis=1)

        latest_row = df.iloc[-1]
        feature_dict = {}
        for col in feature_cols:
            feature_dict[col] = float(latest_row[col]) if col in latest_row else 0.0

        return pd.DataFrame([feature_dict], columns=feature_cols)

    def _generate_fault_features(self, history_df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
        df = history_df.copy()
        
        rolling_targets = [
            "cht_C", "egt_C", "oil_temperature_C", "oil_pressure_bar",
            "fuel_flow_kg_s", "vibration_rms", "battery_voltage_V",
            "injection_timing_deg", "physics_residual_C"
        ]

        w = min(15, len(df))
        new_cols = {}
        for sig in rolling_targets:
            if sig in df.columns:
                new_cols[f"{sig}_roll_mean"] = df[sig].rolling(window=w, min_periods=1).mean()
                new_cols[f"{sig}_roll_std"] = df[sig].rolling(window=w, min_periods=1).std().fillna(0.0)
                diff_val = df[sig].diff(w - 1).fillna(0.0) if w > 1 else 0.0
                new_cols[f"{sig}_slope"] = diff_val / max(1.0, float(w))

        df = pd.concat([df, pd.DataFrame(new_cols)], axis=1)

        latest_row = df.iloc[-1]
        feature_dict = {}
        for col in feature_cols:
            feature_dict[col] = float(latest_row[col]) if col in latest_row else 0.0

        return pd.DataFrame([feature_dict], columns=feature_cols)

    def _generate_rul_features(self, history_df: pd.DataFrame, feature_cols: list) -> Optional[pd.DataFrame]:
        # Return None if history buffer has fewer than 13 records (prevents out-of-distribution RUL estimates)
        if len(history_df) < 13:
            return None

        df = history_df.copy()

        history_features = [
            "rpm", "cht_C", "egt_C", "oil_temperature_C", "oil_pressure_bar",
            "vibration_rms", "fuel_flow_kg_s", "power_W", "torque_Nm"
        ]

        lags = [1, 3, 6, 12]
        windows = [3, 6, 12]
        new_cols = {}

        for feat in history_features:
            if feat in df.columns:
                for lag in lags:
                    new_cols[f"{feat}_lag_{lag}"] = df[feat].shift(lag)
                for w in windows:
                    new_cols[f"{feat}_mean_{w}"] = df[feat].rolling(window=w, min_periods=w).mean()
                    new_cols[f"{feat}_std_{w}"] = df[feat].rolling(window=w, min_periods=w).std()

        for feat in ["rpm", "cht_C", "egt_C", "oil_temperature_C", "oil_pressure_bar", "vibration_rms", "fuel_flow_kg_s", "power_W"]:
            if feat in df.columns:
                for w in [6, 12]:
                    prev = df[feat].shift(w)
                    elapsed_hours = w * 10.0 / 60.0
                    new_cols[f"{feat}_slope_{w}"] = (df[feat] - prev) / max(0.001, elapsed_hours)
                new_cols[f"{feat}_delta"] = df[feat].diff(1)

        df = pd.concat([df, pd.DataFrame(new_cols)], axis=1)

        latest_row = df.iloc[-1]
        feature_dict = {}
        for col in feature_cols:
            if col in latest_row:
                val = latest_row[col]
                if pd.isna(val):
                    return None
                feature_dict[col] = float(val)
            else:
                return None

        res_df = pd.DataFrame([feature_dict], columns=feature_cols)
        if res_df.isna().any().any():
            return None

        return res_df
