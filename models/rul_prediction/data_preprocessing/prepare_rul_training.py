import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

base_dir = os.path.dirname(os.path.abspath(__file__))

INPUT_FILE = os.path.join(base_dir, "..", "data", "aero_piston_RUL_features.csv")

TRAIN_FILE = os.path.join(base_dir, "..", "data", "rul_train.csv")
VAL_FILE = os.path.join(base_dir, "..", "data", "rul_validation.csv")
TEST_FILE = os.path.join(base_dir, "..", "data", "rul_test.csv")

RANDOM_STATE=42

print("====================================")
print("PREPARING RUL TRAINING DATA")
print("====================================")

df=pd.read_csv(INPUT_FILE)

print("Total rows:",len(df))
print("Total engines:",df["engine_id"].nunique())

# ============================================================
# 1. GET UNIQUE ENGINES
# ============================================================

engines=df["engine_id"].unique()

print("\nTotal engines:",len(engines))

# ============================================================
# 2. TRAIN / TEMPORARY SPLIT
# ============================================================

train_engines,temp_engines=train_test_split(
    engines,
    test_size=0.30,
    random_state=RANDOM_STATE
)

# ============================================================
# 3. VALIDATION / TEST SPLIT
# ============================================================

val_engines,test_engines=train_test_split(
    temp_engines,
    test_size=0.50,
    random_state=RANDOM_STATE
)

print("\nEngine split:")
print("Training engines:",len(train_engines))
print("Validation engines:",len(val_engines))
print("Test engines:",len(test_engines))

# ============================================================
# 4. CREATE DATASETS
# ============================================================

train_df=df[
    df["engine_id"].isin(train_engines)
].copy()

val_df=df[
    df["engine_id"].isin(val_engines)
].copy()

test_df=df[
    df["engine_id"].isin(test_engines)
].copy()

# ============================================================
# 5. SORT DATA
# ============================================================

train_df=train_df.sort_values(
    ["engine_id","timestamp_hours"]
)

val_df=val_df.sort_values(
    ["engine_id","timestamp_hours"]
)

test_df=test_df.sort_values(
    ["engine_id","timestamp_hours"]
)

# ============================================================
# 6. VALIDATE ENGINE SEPARATION
# ============================================================

train_set=set(train_engines)
val_set=set(val_engines)
test_set=set(test_engines)

print("\nChecking engine separation...")

print(
    "Train ∩ Validation:",
    len(train_set & val_set)
)

print(
    "Train ∩ Test:",
    len(train_set & test_set)
)

print(
    "Validation ∩ Test:",
    len(val_set & test_set)
)

# ============================================================
# 7. CHECK TARGET LEAKAGE
# ============================================================

leakage_columns=[
    "degradation",
    "health_index"
]

remaining_leakage=[
    c for c in leakage_columns
    if c in df.columns
]

print("\nLeakage columns remaining:")

print(remaining_leakage)

# ============================================================
# 8. SAVE
# ============================================================

train_df.to_csv(
    TRAIN_FILE,
    index=False
)

val_df.to_csv(
    VAL_FILE,
    index=False
)

test_df.to_csv(
    TEST_FILE,
    index=False
)

# ============================================================
# 9. DATASET STATISTICS
# ============================================================

print("\n====================================")
print("SPLIT COMPLETE")
print("====================================")

print("\nTRAIN")
print("Engines:",train_df["engine_id"].nunique())
print("Rows:",len(train_df))
print("RUL range:",train_df["rul_hours"].min(),"to",train_df["rul_hours"].max())

print("\nVALIDATION")
print("Engines:",val_df["engine_id"].nunique())
print("Rows:",len(val_df))
print("RUL range:",val_df["rul_hours"].min(),"to",val_df["rul_hours"].max())

print("\nTEST")
print("Engines:",test_df["engine_id"].nunique())
print("Rows:",len(test_df))
print("RUL range:",test_df["rul_hours"].min(),"to",test_df["rul_hours"].max())

print("\nFiles created:")
print(TRAIN_FILE)
print(VAL_FILE)
print(TEST_FILE)