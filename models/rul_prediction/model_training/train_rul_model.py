import os
import json
import hashlib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
TRAIN_FILE = os.path.join(DATA_DIR, "rul_train.csv")
VAL_FILE = os.path.join(DATA_DIR, "rul_validation.csv")
MODEL_OUT_FILE = os.path.join(BASE_DIR, "..", "xgboost_rul_model.json")
FEATURE_NAMES_FILE = os.path.join(BASE_DIR, "..", "xgboost_rul_features.txt")
MODEL_HASHES_FILE = os.path.join(BASE_DIR, "..", "..", "model_hashes.json")

def compute_sha256(filepath: str) -> str:
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def main():
    print("====================================")
    print("TRAINING XGBOOST RUL REGRESSOR ON TRUE RUL")
    print("====================================")

    train_df = pd.read_csv(TRAIN_FILE)
    val_df = pd.read_csv(VAL_FILE)

    print(f"Train engines: {train_df['engine_id'].nunique()}, rows: {len(train_df):,}")
    print(f"Val engines: {val_df['engine_id'].nunique()}, rows: {len(val_df):,}")

    with open(FEATURE_NAMES_FILE, "r") as f:
        feature_cols = [line.strip() for line in f if line.strip()]

    print(f"Using {len(feature_cols)} input features (Operating conditions, lags, rolling stats, physics residuals).")

    # Verify features exist in training data
    missing = [c for c in feature_cols if c not in train_df.columns]
    if missing:
        raise ValueError(f"Missing feature columns in training data: {missing}")

    X_train = train_df[feature_cols].astype(float)
    y_train = train_df["rul_hours"].astype(float)

    X_val = val_df[feature_cols].astype(float)
    y_val = val_df["rul_hours"].astype(float)

    print("\nTraining XGBoost Regressor...")
    model = XGBRegressor(
        n_estimators=350,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        tree_method="hist",
        early_stopping_rounds=25,
        eval_metric="rmse"
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=50
    )

    # Validation evaluation
    val_preds = model.predict(X_val)
    val_preds = np.maximum(0.0, val_preds)

    val_mae = mean_absolute_error(y_val, val_preds)
    val_rmse = np.sqrt(mean_squared_error(y_val, val_preds))
    val_r2 = r2_score(y_val, val_preds)

    print("\n====================================")
    print("VALIDATION METRICS (TRUE RUL)")
    print("====================================")
    print(f"Validation MAE:  {val_mae:.2f} hours")
    print(f"Validation RMSE: {val_rmse:.2f} hours")
    print(f"Validation R²:   {val_r2:.4f}")

    # Save model
    model.save_model(MODEL_OUT_FILE)
    print(f"\nModel saved to: {MODEL_OUT_FILE}")

    # Update model hashes
    model_hash = compute_sha256(MODEL_OUT_FILE)
    print(f"Model SHA-256: {model_hash}")

    if os.path.exists(MODEL_HASHES_FILE):
        with open(MODEL_HASHES_FILE, "r") as f:
            hashes = json.load(f)
        hashes["rul_prediction"] = model_hash
        with open(MODEL_HASHES_FILE, "w") as f:
            json.dump(hashes, f, indent=2)
        print(f"Updated {MODEL_HASHES_FILE} with new RUL model hash.")

if __name__ == "__main__":
    main()
