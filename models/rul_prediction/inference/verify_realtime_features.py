import os
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

BASE_DIR=os.path.dirname(os.path.abspath(__file__))

RAW_FILE=os.path.join(
    BASE_DIR,
    "..",
    "data",
    "aero_piston_RUL_300_engines.csv"
)

FEATURE_FILE=os.path.join(
    BASE_DIR,
    "..",
    "data",
    "aero_piston_RUL_features.csv"
)

MODEL_FILE=os.path.join(
    BASE_DIR,
    "..",
    "models",
    "xgboost_rul_model.json"
)

print("====================================")
print("REAL-TIME FEATURE VERIFICATION")
print("====================================")

# ============================================================
# LOAD DATA
# ============================================================

print("\nLoading raw dataset...")

raw_df=pd.read_csv(
    RAW_FILE
)

print(
    "Raw rows:",
    len(raw_df)
)

print(
    "Raw engines:",
    raw_df["engine_id"].nunique()
)

print("\nLoading feature dataset...")

feature_df=pd.read_csv(
    FEATURE_FILE
)

print(
    "Feature rows:",
    len(feature_df)
)

print(
    "Feature columns:",
    len(feature_df.columns)
)

# ============================================================
# LOAD MODEL
# ============================================================

print("\nLoading XGBoost model...")

model=XGBRegressor()

model.load_model(
    MODEL_FILE
)

model_features=(
    model.get_booster().feature_names
)

print(
    "Model features:",
    len(model_features)
)

# ============================================================
# SELECT ONE ENGINE
# ============================================================

ENGINE_ID="ENG_0001"

print(
    "\nTesting engine:",
    ENGINE_ID
)

raw_engine=raw_df[
    raw_df["engine_id"]==ENGINE_ID
].copy()

feature_engine=feature_df[
    feature_df["engine_id"]==ENGINE_ID
].copy()

raw_engine=raw_engine.sort_values(
    "timestamp_hours"
).reset_index(
    drop=True
)

feature_engine=feature_engine.sort_values(
    "timestamp_hours"
).reset_index(
    drop=True
)

print(
    "Raw engine rows:",
    len(raw_engine)
)

print(
    "Feature engine rows:",
    len(feature_engine)
)

# ============================================================
# FIND FIRST FEATURE ROW
# ============================================================

print("\nFinding first feature row...")

target_timestamp=feature_engine.iloc[0][
    "timestamp_hours"
]

print(
    "First feature timestamp:",
    target_timestamp
)

raw_match=raw_engine[
    np.isclose(
        raw_engine["timestamp_hours"],
        target_timestamp
    )
]

if len(raw_match)==0:

    raise ValueError(
        "Could not find matching raw timestamp."
    )

raw_match=raw_match.iloc[0]

feature_match=feature_engine.iloc[0]

print(
    "Matching raw timestamp found."
)

# ============================================================
# GENERATE FEATURES EXACTLY LIKE rul_features.py
# ============================================================

history=raw_engine[
    raw_engine["timestamp_hours"]
    <=target_timestamp
].copy()

print(
    "History records:",
    len(history)
)

# ============================================================
# FEATURE DEFINITIONS
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

lags=[
    1,
    3,
    6,
    12
]

windows=[
    3,
    6,
    12
]

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

# ============================================================
# CREATE TEMPORARY DATAFRAME
# ============================================================

temp_df=history.copy()

temp_df=temp_df.sort_values(
    "timestamp_hours"
).reset_index(
    drop=True
)

# ============================================================
# LAG FEATURES
# ============================================================

for feature in history_features:

    for lag in lags:

        temp_df[
            f"{feature}_lag_{lag}"
        ]=(
            temp_df[feature]
            .shift(lag)
        )

# ============================================================
# ROLLING MEAN
# ============================================================

for feature in history_features:

    for window in windows:

        temp_df[
            f"{feature}_mean_{window}"
        ]=(
            temp_df[feature]
            .rolling(
                window=window,
                min_periods=1
            )
            .mean()
        )

# ============================================================
# ROLLING STANDARD DEVIATION
# ============================================================

for feature in history_features:

    for window in windows:

        temp_df[
            f"{feature}_std_{window}"
        ]=(
            temp_df[feature]
            .rolling(
                window=window,
                min_periods=2
            )
            .std()
        )

# ============================================================
# SLOPE
# ============================================================

for feature in trend_features:

    for window in [6,12]:

        previous=(
            temp_df[feature]
            .shift(window)
        )

        elapsed_hours=(
            window*10/60
        )

        temp_df[
            f"{feature}_slope_{window}"
        ]=(
            temp_df[feature]-previous
        )/elapsed_hours

# ============================================================
# DELTA
# ============================================================

for feature in difference_features:

    previous=(
        temp_df[feature]
        .shift(1)
    )

    temp_df[
        f"{feature}_delta"
    ]=(
        temp_df[feature]-previous
    )

# ============================================================
# GET GENERATED ROW
# ============================================================

generated_row=temp_df.iloc[-1].copy()

# ============================================================
# REMOVE LEAKAGE
# ============================================================

generated_features={}

for feature in base_features:

    generated_features[
        feature
    ]=generated_row[feature]

for feature in history_features:

    for lag in lags:

        column=f"{feature}_lag_{lag}"

        generated_features[
            column
        ]=generated_row[column]

for feature in history_features:

    for window in windows:

        mean_column=(
            f"{feature}_mean_{window}"
        )

        std_column=(
            f"{feature}_std_{window}"
        )

        generated_features[
            mean_column
        ]=generated_row[
            mean_column
        ]

        generated_features[
            std_column
        ]=generated_row[
            std_column
        ]

for feature in trend_features:

    for window in [6,12]:

        column=(
            f"{feature}_slope_{window}"
        )

        generated_features[
            column
        ]=generated_row[
            column
        ]

for feature in difference_features:

    column=f"{feature}_delta"

    generated_features[
        column
    ]=generated_row[column]

# timestamp is also used by the baseline model

generated_features[
    "timestamp_hours"
]=generated_row[
    "timestamp_hours"
]

# ============================================================
# CREATE GENERATED DATAFRAME
# ============================================================

generated_df=pd.DataFrame(
    [generated_features]
)

generated_df=generated_df.reindex(
    columns=model_features
)

# ============================================================
# COMPARE FEATURES
# ============================================================

print("\n====================================")
print("FEATURE COMPARISON")
print("====================================")

differences=[]

for feature in model_features:

    realtime_value=generated_df.iloc[0][
        feature
    ]

    training_value=feature_match[
        feature
    ]

    if pd.isna(realtime_value) and pd.isna(training_value):

        difference=0.0

    elif pd.isna(realtime_value) or pd.isna(training_value):

        difference=np.inf

    else:

        difference=abs(
            float(realtime_value)
            -
            float(training_value)
        )

    differences.append({
        "feature":feature,
        "training_value":training_value,
        "realtime_value":realtime_value,
        "absolute_difference":difference
    })

comparison=pd.DataFrame(
    differences
)

comparison=comparison.sort_values(
    "absolute_difference",
    ascending=False
)

print(
    "\nTop 20 differences:"
)

print(
    comparison.head(20).to_string(
        index=False
    )
)

# ============================================================
# SUMMARY
# ============================================================

finite_differences=comparison[
    np.isfinite(
        comparison[
            "absolute_difference"
        ]
    )
][
    "absolute_difference"
]

max_difference=finite_differences.max()

mean_difference=finite_differences.mean()

matching_features=(
    comparison[
        "absolute_difference"
    ]
    <=1e-9
).sum()

print(
    "\nMaximum difference:",
    max_difference
)

print(
    "Mean difference:",
    mean_difference
)

print(
    "Matching features:",
    matching_features,
    "/",
    len(model_features)
)

# ============================================================
# PREDICTION COMPARISON
# ============================================================

print("\n====================================")
print("XGBOOST PREDICTION COMPARISON")
print("====================================")

training_input=feature_match[
    model_features
].to_frame().T

realtime_input=generated_df[
    model_features
]

training_input=training_input.astype(float)

realtime_input=realtime_input.astype(float)

training_prediction=float(
    model.predict(
        training_input
    )[0]
)

realtime_prediction=float(
    model.predict(
        realtime_input
    )[0]
)

prediction_difference=abs(
    training_prediction-
    realtime_prediction
)

print(
    "Training feature row prediction:",
    training_prediction
)

print(
    "Real-time generated prediction:",
    realtime_prediction
)

print(
    "Prediction difference:",
    prediction_difference
)

# ============================================================
# FINAL RESULT
# ============================================================

print("\n====================================")
print("VERIFICATION RESULT")
print("====================================")

if max_difference<=1e-9:

    print(
        "PASS: Real-time features match training features."
    )

else:

    print(
        "FAIL: Real-time features do not match training features."
    )

print(
    "\nFeature comparison saved to:"
)

OUTPUT_FILE=os.path.join(
    BASE_DIR,
    "..",
    "data",
    "realtime_feature_comparison.csv"
)

comparison.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    OUTPUT_FILE
)

print("\n====================================")
print("VERIFICATION COMPLETE")
print("====================================")