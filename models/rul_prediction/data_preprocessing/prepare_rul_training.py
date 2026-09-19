import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

base_dir = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(base_dir, "..", "data", "aero_piston_RUL_features.csv")
TRAIN_FILE = os.path.join(base_dir, "..", "data", "rul_train.csv")
VAL_FILE = os.path.join(base_dir, "..", "data", "rul_validation.csv")
TEST_FILE = os.path.join(base_dir, "..", "data", "rul_test.csv")

RANDOM_STATE = 42

print("====================================")
print("PREPARING RUL TRAINING DATA")
print("====================================")

df = pd.read_csv(INPUT_FILE)
print("Total rows:", len(df))
print("Total engines:", df["engine_id"].nunique())

# 1. Unique engines
engines = df["engine_id"].unique()

# 2. Train / Temp split (70% train, 30% temp)
train_engines, temp_engines = train_test_split(
    engines,
    test_size=0.30,
    random_state=RANDOM_STATE
)

# 3. Validation / Test split (15% val, 15% test)
val_engines, test_engines = train_test_split(
    temp_engines,
    test_size=0.50,
    random_state=RANDOM_STATE
)

print("\nEngine split:")
print("Training engines:", len(train_engines))
print("Validation engines:", len(val_engines))
print("Test engines:", len(test_engines))

# 4. Create datasets
train_df = df[df["engine_id"].isin(train_engines)].copy()
val_df = df[df["engine_id"].isin(val_engines)].copy()
test_df = df[df["engine_id"].isin(test_engines)].copy()

# 5. Chronological sort within each engine
train_df = train_df.sort_values(["engine_id", "timestamp_hours"]).reset_index(drop=True)
val_df = val_df.sort_values(["engine_id", "timestamp_hours"]).reset_index(drop=True)
test_df = test_df.sort_values(["engine_id", "timestamp_hours"]).reset_index(drop=True)

# 6. Validate engine separation
train_set = set(train_engines)
val_set = set(val_engines)
test_set = set(test_engines)

print("\nChecking engine separation (Must be 0 overlap):")
print("Train and Validation overlap:", len(train_set & val_set))
print("Train and Test overlap:", len(train_set & test_set))
print("Validation and Test overlap:", len(val_set & test_set))

# 7. Check target leakage
leakage_columns = ["degradation", "health_index"]
remaining_leakage = [c for c in leakage_columns if c in df.columns]
print("\nLeakage columns remaining in features:", remaining_leakage)

# 8. Save
train_df.to_csv(TRAIN_FILE, index=False)
val_df.to_csv(VAL_FILE, index=False)
test_df.to_csv(TEST_FILE, index=False)

print("\n====================================")
print("SPLIT COMPLETE - NO DATA LEAKAGE")
print("====================================")
print("TRAIN      - Engines:", train_df["engine_id"].nunique(), "| Rows:", len(train_df), f"| RUL: {train_df['rul_hours'].min():.1f}h - {train_df['rul_hours'].max():.1f}h")
print("VALIDATION - Engines:", val_df["engine_id"].nunique(), "| Rows:", len(val_df), f"| RUL: {val_df['rul_hours'].min():.1f}h - {val_df['rul_hours'].max():.1f}h")
print("TEST       - Engines:", test_df["engine_id"].nunique(), "| Rows:", len(test_df), f"| RUL: {test_df['rul_hours'].min():.1f}h - {test_df['rul_hours'].max():.1f}h")