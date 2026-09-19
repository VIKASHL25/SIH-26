import os
import pandas as pd
import numpy as np

base_dir = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(base_dir, "..", "data", "aero_piston_RUL_300_engines.csv")
OUTPUT_FILE = os.path.join(base_dir, "..", "data", "aero_piston_RUL_features.csv")

os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

df = pd.read_csv(INPUT_FILE)
print("Raw dataset loaded")
print("Rows:", len(df))
print("Engines:", df["engine_id"].nunique())

df = df.sort_values(["engine_id", "timestamp_hours"]).reset_index(drop=True)

base_features = [
    "altitude_m", "ambient_temp_C", "pressure_kPa", "air_density_kg_m3",
    "throttle", "load", "rpm", "air_mass_flow_kg_s", "fuel_flow_kg_s",
    "torque_Nm", "power_W", "cht_C", "egt_C", "oil_temperature_C",
    "oil_pressure_bar", "vibration_rms"
]

history_features = [
    "rpm", "cht_C", "egt_C", "oil_temperature_C", "oil_pressure_bar",
    "vibration_rms", "fuel_flow_kg_s", "power_W", "torque_Nm"
]

# Step 1: Lags
print("\nCreating lag features...")
lags = [1, 3, 6, 12]
for feature in history_features:
    for lag in lags:
        df[f"{feature}_lag_{lag}"] = df.groupby("engine_id")[feature].shift(lag)

# Step 2: Rolling Mean
print("Creating rolling mean features...")
windows = [3, 6, 12]
for feature in history_features:
    grouped = df.groupby("engine_id")[feature]
    for window in windows:
        df[f"{feature}_mean_{window}"] = grouped.transform(lambda x: x.rolling(window=window, min_periods=1).mean())

# Step 3: Rolling Standard Deviation
print("Creating rolling std features...")
for feature in history_features:
    grouped = df.groupby("engine_id")[feature]
    for window in windows:
        df[f"{feature}_std_{window}"] = grouped.transform(lambda x: x.rolling(window=window, min_periods=2).std())

# Step 4: Slopes
print("Creating trend features...")
trend_features = [
    "rpm", "cht_C", "egt_C", "oil_temperature_C", "oil_pressure_bar",
    "vibration_rms", "fuel_flow_kg_s", "power_W"
]
for feature in trend_features:
    for window in [6, 12]:
        previous = df.groupby("engine_id")[feature].shift(window)
        elapsed_hours = window * 10.0 / 60.0
        df[f"{feature}_slope_{window}"] = (df[feature] - previous) / elapsed_hours

# Step 5: Deltas
print("Creating difference features...")
difference_features = [
    "rpm", "cht_C", "egt_C", "oil_temperature_C", "oil_pressure_bar",
    "vibration_rms", "fuel_flow_kg_s", "power_W"
]
for feature in difference_features:
    previous = df.groupby("engine_id")[feature].shift(1)
    df[f"{feature}_delta"] = df[feature] - previous

# Step 6: Remove Leakage Columns
print("Removing leakage columns (degradation, health_index)...")
leak_cols = [c for c in ["degradation", "health_index"] if c in df.columns]
df = df.drop(columns=leak_cols)

# Step 7: Filter Initial History Window (first 12 frames per engine)
print("Removing records without sufficient history (cumcount < 12)...")
df = df[df.groupby("engine_id").cumcount() >= 12].reset_index(drop=True)

# Step 8: Handle Infinite Values
df = df.replace([np.inf, -np.inf], np.nan)

# Step 9: Drop NaNs
history_columns = [c for c in df.columns if any(k in c for k in ["_lag_", "_std_", "_slope_", "_delta"])]
df = df.dropna(subset=history_columns).reset_index(drop=True)

print("\nFinal feature check:")
nan_count = df.isna().sum().sum()
print("NaN values:", nan_count)
print("Engines:", df["engine_id"].nunique())
print("Rows:", len(df))
print("Columns:", len(df.columns))

df.to_csv(OUTPUT_FILE, index=False)
print(f"Saved to: {OUTPUT_FILE}")