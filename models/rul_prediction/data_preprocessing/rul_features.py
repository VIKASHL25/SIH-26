import os
import pandas as pd
import numpy as np

base_dir = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(base_dir, "..", "data", "aero_piston_RUL_300_engines.csv")
OUTPUT_FILE = os.path.join(base_dir, "..", "data", "aero_piston_RUL_features.csv")

df=pd.read_csv(INPUT_FILE)

print("Raw dataset loaded")
print("Rows:",len(df))
print("Engines:",df["engine_id"].nunique())

df=df.sort_values(
    ["engine_id","timestamp_hours"]
).reset_index(drop=True)

# ============================================================
# FEATURES THAT WILL BE USED BY XGBOOST
# ============================================================

base_features=[
    "altitude_m",
    "ambient_temp_C",
    "pressure_kPa",
    "air_density_kg_m3",
    "throttle",
    "load",
    "rpm",
    "air_mass_flow_kg_s",
    "fuel_flow_kg_s",
    "torque_Nm",
    "power_W",
    "cht_C",
    "egt_C",
    "oil_temperature_C",
    "oil_pressure_bar",
    "vibration_rms"
]

# ============================================================
# FEATURES FOR HISTORICAL ANALYSIS
# ============================================================

history_features=[
    "rpm",
    "cht_C",
    "egt_C",
    "oil_temperature_C",
    "oil_pressure_bar",
    "vibration_rms",
    "fuel_flow_kg_s",
    "power_W",
    "torque_Nm"
]

# ============================================================
# STEP 1: LAG FEATURES
# ============================================================

print("\nCreating lag features...")

lags=[
    1,
    3,
    6,
    12
]

for feature in history_features:
    for lag in lags:
        df[
            f"{feature}_lag_{lag}"
        ]=(
            df.groupby("engine_id")[feature]
            .shift(lag)
        )

# ============================================================
# STEP 2: ROLLING MEAN
# ============================================================

print("Creating rolling mean features...")

windows=[
    3,
    6,
    12
]

for feature in history_features:
    grouped=df.groupby("engine_id")[feature]

    for window in windows:
        df[
            f"{feature}_mean_{window}"
        ]=(
            grouped
            .transform(
                lambda x:
                x.rolling(
                    window=window,
                    min_periods=1
                ).mean()
            )
        )

# ============================================================
# STEP 3: ROLLING STANDARD DEVIATION
# ============================================================

print("Creating rolling standard deviation features...")

for feature in history_features:
    grouped=df.groupby("engine_id")[feature]

    for window in windows:
        df[
            f"{feature}_std_{window}"
        ]=(
            grouped
            .transform(
                lambda x:
                x.rolling(
                    window=window,
                    min_periods=2
                ).std()
            )
        )

# ============================================================
# STEP 4: TREND / SLOPE
# ============================================================

print("Creating trend features...")

trend_features=[
    "rpm",
    "cht_C",
    "egt_C",
    "oil_temperature_C",
    "oil_pressure_bar",
    "vibration_rms",
    "fuel_flow_kg_s",
    "power_W"
]

for feature in trend_features:
    for window in [6,12]:

        previous=(
            df.groupby("engine_id")[feature]
            .shift(window)
        )

        elapsed_hours=(
            window*10/60
        )

        df[
            f"{feature}_slope_{window}"
        ]=(
            df[feature]-previous
        )/elapsed_hours

# ============================================================
# STEP 5: FIRST DIFFERENCE
# ============================================================

print("Creating difference features...")

difference_features=[
    "rpm",
    "cht_C",
    "egt_C",
    "oil_temperature_C",
    "oil_pressure_bar",
    "vibration_rms",
    "fuel_flow_kg_s",
    "power_W"
]

for feature in difference_features:

    previous=(
        df.groupby("engine_id")[feature]
        .shift(1)
    )

    df[
        f"{feature}_delta"
    ]=(
        df[feature]-previous
    )

# ============================================================
# STEP 6: REMOVE DATA LEAKAGE
# ============================================================

print("Removing leakage columns...")

df=df.drop(
    columns=[
        "degradation",
        "health_index"
    ]
)

# ============================================================
# STEP 7: REMOVE FIRST 2 HOURS
# ============================================================

print("Removing records without sufficient history...")

df=df.groupby(
    "engine_id",
    group_keys=False
).apply(
    lambda x:
    x.iloc[12:]
)

df=df.reset_index(
    drop=True
)

# ============================================================
# STEP 8: HANDLE INFINITE VALUES
# ============================================================

df=df.replace(
    [np.inf,-np.inf],
    np.nan
)

# ============================================================
# STEP 9: REMOVE ROWS WITH MISSING HISTORY
# ============================================================

history_columns=[
    c for c in df.columns
    if (
        "_lag_" in c
        or "_std_" in c
        or "_slope_" in c
        or "_delta" in c
    )
]

df=df.dropna(
    subset=history_columns
)

# ============================================================
# STEP 10: FINAL CHECK
# ============================================================

print("\nChecking dataset...")

numeric_columns=df.select_dtypes(
    include=np.number
).columns

nan_count=df.isna().sum().sum()

inf_count=np.isinf(
    df[numeric_columns]
).sum().sum()

print("NaN values:",nan_count)
print("Infinite values:",inf_count)

# ============================================================
# STEP 11: SAVE
# ============================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)

# ============================================================
# FINAL INFORMATION
# ============================================================

print("\n====================================")
print("RUL FEATURE DATASET CREATED")
print("====================================")

print(
    "Number of engines:",
    df["engine_id"].nunique()
)

print(
    "Total rows:",
    len(df)
)

print(
    "Total columns:",
    len(df.columns)
)

print(
    "Minimum RUL:",
    df["rul_hours"].min()
)

print(
    "Maximum RUL:",
    df["rul_hours"].max()
)

print(
    "\nFirst 5 rows:"
)

print(
    df.head()
)

print(
    f"\nSaved to: {OUTPUT_FILE}"
)