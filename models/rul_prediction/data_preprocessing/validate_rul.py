import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
base_dir = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(base_dir, "..", "data", "aero_piston_RUL_features.csv")

df=pd.read_csv(INPUT_FILE)

print("====================================")
print("RUL DATASET VALIDATION")
print("====================================")
print("Rows:",len(df))
print("Engines:",df["engine_id"].nunique())
print("Columns:",len(df.columns))
print("NaN:",df.isna().sum().sum())
numeric_columns=df.select_dtypes(include=np.number).columns
print("Infinite:",np.isinf(df[numeric_columns]).sum().sum())

# ============================================================
# 1. RUL VALIDATION
# ============================================================

print("\nRUL statistics:")
print(df["rul_hours"].describe())

# ============================================================
# 2. ENGINE LIFETIME VALIDATION
# ============================================================

engine_summary=df.groupby("engine_id").agg(
    start_time=("timestamp_hours","min"),
    end_time=("timestamp_hours","max"),
    max_rul=("rul_hours","max"),
    min_rul=("rul_hours","min")
).reset_index()

engine_summary["lifetime_hours"]=(
    engine_summary["end_time"]
    -engine_summary["start_time"]
)

print("\nEngine lifetime statistics:")
print(
    engine_summary["lifetime_hours"].describe()
)

print("\nEngines outside 20-1000 hours:")

invalid_engines=engine_summary[
    (engine_summary["lifetime_hours"]<20)|
    (engine_summary["lifetime_hours"]>1000)
]

print(len(invalid_engines))

# ============================================================
# 3. RUL MONOTONICITY
# ============================================================

print("\nChecking RUL monotonicity...")

violations=0

for engine_id,group in df.groupby("engine_id"):
    rul=group["rul_hours"].values
    if np.any(np.diff(rul)>1e-6):
        violations+=1

print("Engines with RUL increasing:",violations)

# ============================================================
# 4. DEGRADATION-RELATED CORRELATION
# ============================================================

check_features=[
    "rpm",
    "cht_C",
    "egt_C",
    "oil_temperature_C",
    "oil_pressure_bar",
    "vibration_rms",
    "power_W",
    "fuel_flow_kg_s"
]

print("\nCorrelation with RUL:")

correlations=df[
    check_features+["rul_hours"]
].corr()["rul_hours"].drop(
    "rul_hours"
).sort_values()

print(correlations)

# ============================================================
# 5. HISTORY FEATURE CHECK
# ============================================================

print("\nChecking historical features...")

history_columns=[
    c for c in df.columns
    if "_lag_" in c
]

print(
    "Number of lag features:",
    len(history_columns)
)

print(
    "Example lag features:"
)

print(
    history_columns[:20]
)

# ============================================================
# 6. CHECK THAT LAG IS FROM SAME ENGINE
# ============================================================

print("\nChecking engine boundaries...")

boundary_errors=0

for engine_id,group in df.groupby("engine_id"):
    first_row=group.iloc[0]

    for feature in [
        "rpm",
        "cht_C",
        "egt_C",
        "oil_temperature_C",
        "oil_pressure_bar",
        "vibration_rms"
    ]:
        lag_column=f"{feature}_lag_1"

        if lag_column in group.columns:
            if pd.isna(first_row[lag_column]):
                boundary_errors+=1

print(
    "Boundary errors:",
    boundary_errors
)

# ============================================================
# 7. RANDOM ENGINE RUL TRAJECTORIES
# ============================================================

selected_engines=(
    df["engine_id"]
    .drop_duplicates()
    .sample(
        min(5,df["engine_id"].nunique()),
        random_state=42
    )
)

plt.figure(figsize=(12,6))

for engine_id in selected_engines:

    group=df[
        df["engine_id"]==engine_id
    ]

    plt.plot(
        group["timestamp_hours"],
        group["rul_hours"],
        label=engine_id
    )

plt.xlabel("Operating Time (hours)")
plt.ylabel("RUL (hours)")
plt.title("RUL Trajectories for Sample Engines")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# ============================================================
# 8. VIBRATION VS RUL
# ============================================================

plt.figure(figsize=(10,6))

sample=df.sample(
    min(20000,len(df)),
    random_state=42
)

plt.scatter(
    sample["rul_hours"],
    sample["vibration_rms"],
    s=3,
    alpha=0.3
)

plt.xlabel("RUL (hours)")
plt.ylabel("Vibration RMS")
plt.title("Vibration vs RUL")
plt.grid(True)
plt.tight_layout()
plt.show()

# ============================================================
# 9. EGT VS RUL
# ============================================================

plt.figure(figsize=(10,6))

plt.scatter(
    sample["rul_hours"],
    sample["egt_C"],
    s=3,
    alpha=0.3
)

plt.xlabel("RUL (hours)")
plt.ylabel("EGT (°C)")
plt.title("EGT vs RUL")
plt.grid(True)
plt.tight_layout()
plt.show()

# ============================================================
# 10. FINAL VALIDATION
# ============================================================

print("\n====================================")
print("VALIDATION COMPLETE")
print("====================================")

if len(invalid_engines)==0:
    print("Lifetime range: PASS")
else:
    print("Lifetime range: CHECK")

if violations==0:
    print("RUL monotonicity: PASS")
else:
    print("RUL monotonicity: CHECK")

if boundary_errors==0:
    print("Engine history boundaries: PASS")
else:
    print("Engine history boundaries: CHECK")

if df.isna().sum().sum()==0:
    print("NaN check: PASS")
else:
    print("NaN check: FAIL")

if np.isinf(df[numeric_columns]).sum().sum()==0:
    print("Infinite check: PASS")
else:
    print("Infinite check: FAIL")