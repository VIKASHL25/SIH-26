"""
anomaly_features_batch.py

Batch reproduction of the anomaly-detection feature vector computed by
`backend/feature_engine.py`'s `_generate_anomaly_features` /
`process_raw_sample` in the live SIH-26 system.

IMPORTANT: unlike the fault-classification model, the live anomaly model
uses ONLY the current timestep's raw values + physics residuals — no
lag or rolling-window features. This is intentional in the live system
(see `DigitalTwinFeatureEngine._generate_anomaly_features`, which builds
its row straight from `clean_sample`, not from `history_df`). Training on
anything more than this would create features the live system can never
supply at inference time.
"""

import pandas as pd

# Hardcoded in model_loader.py's DigitalTwinModelManager.__init__ — not
# loaded from an external json file, so there's no feature_cols.json to
# replace for this model. Kept here verbatim, in the same order.
ANOMALY_FEATURE_COLS = [
    "cht_C",
    "egt_C",
    "oil_temperature_C",
    "oil_pressure_bar",
    "vibration_rms",
    "battery_voltage_V",
    "alternator_current_A",
    "alternator_health",
    "injection_timing_deg",
    "cht_residual",
    "egt_residual",
    "rpm_residual",
    "physics_residual_C",
]


def engineer_anomaly_features(data: pd.DataFrame) -> pd.DataFrame:
    """Adds the 4 physics-residual columns needed for the anomaly feature
    set. The other 9 columns are already raw sensor values present in the
    historical CSV as-is — exactly what `process_raw_sample` passes through
    unchanged for a live sample."""
    df = data.copy()
    df["cht_residual"] = df["cht_C"] - df["expected_cht_C"]
    df["egt_residual"] = df["egt_C"] - df["expected_egt_C"]
    df["rpm_residual"] = df["rpm"] - df["expected_rpm"]
    # physics_residual_C already exists in the CSV/live sample as-is.
    return df
