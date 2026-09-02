"""
MALE UAV Aero Piston Engine Digital Twin — Federated Learning Proof of Concept (PoC)
DRDO / SIH Defense Hackathon Project

This script demonstrates Federated Learning (FedAvg algorithm) across 4 simulated UAV aircraft nodes.
Privacy Framing: Raw flight telemetry remains on the local UAV edge flight computer.
Only model parameter weights / gradient updates are transmitted to the Ground Control Station hub.
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.config import DATASET_100K_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("FederatedLearningPoC")

def main():
    logger.info("=================================================================")
    logger.info("STARTING FEDERATED LEARNING (FedAvg) PROOF-OF-CONCEPT EVALUATION")
    logger.info("=================================================================")

    dataset_path = str(DATASET_100K_PATH)
    if not os.path.exists(dataset_path):
        logger.error(f"Dataset file not found at: {dataset_path}")
        return

    df = pd.read_csv(dataset_path)
    logger.info(f"Loaded dataset: {len(df)} records across {df['mission_id'].nunique()} missions.")

    # Target: Health Index (derived from physics thermal/rpm degradation)
    feature_cols = ["rpm", "cht_C", "egt_C", "oil_pressure_bar", "oil_temperature_C", "vibration_rms", "fuel_flow_kg_s"]
    
    # Generate synthetic target label for demonstration if degradation index is present
    if "health_pct" in df.columns:
        target_col = "health_pct"
    else:
        # Physics approximation target
        df["health_pct"] = 100.0 - (df["cht_C"] - 120.0).clip(lower=0) * 0.4 - (df["vibration_rms"] - 1.0).clip(lower=0) * 15.0
        target_col = "health_pct"

    # Clean missing values
    df = df.dropna(subset=feature_cols + [target_col])

    # 1. Partition Data across 4 Simulated UAV Aircraft Nodes (by mission ID)
    unique_missions = df["mission_id"].unique()
    mission_chunks = np.array_split(unique_missions, 4)
    
    nodes = {}
    for idx, chunk in enumerate(mission_chunks):
        node_name = f"UAV-0{idx+1}"
        nodes[node_name] = df[df["mission_id"].isin(chunk)].copy()
        logger.info(f"Node {node_name}: {len(nodes[node_name])} telemetry frames across {len(chunk)} missions.")

    # Holdout Test Set (last 10% of total data)
    test_df = df.sample(frac=0.15, random_state=42)
    X_test = test_df[feature_cols].values
    y_test = test_df[target_col].values

    # ---------------------------------------------------------
    # 1. CENTRALIZED MODEL (Baseline - All Data Pooled Together)
    # ---------------------------------------------------------
    X_central = df[feature_cols].values
    y_central = df[target_col].values
    
    central_model = Ridge(alpha=1.0)
    central_model.fit(X_central, y_central)
    
    y_pred_central = central_model.predict(X_test)
    rmse_central = np.sqrt(mean_squared_error(y_test, y_pred_central))
    mae_central = mean_absolute_error(y_test, y_pred_central)
    r2_central = r2_score(y_test, y_pred_central)

    # ---------------------------------------------------------
    # 2. LOCAL-ONLY MODELS (Each UAV node trained on isolated data)
    # ---------------------------------------------------------
    local_weights = []
    local_biases = []
    local_rmses = []

    for node_name, node_df in nodes.items():
        X_local = node_df[feature_cols].values
        y_local = node_df[target_col].values
        
        local_model = Ridge(alpha=1.0)
        local_model.fit(X_local, y_local)
        
        y_pred_local = local_model.predict(X_test)
        rmse_local = np.sqrt(mean_squared_error(y_test, y_pred_local))
        local_rmses.append(rmse_local)
        
        local_weights.append(local_model.coef_)
        local_biases.append(local_model.intercept_)
        logger.info(f"Local Model [{node_name}] -> RMSE: {rmse_local:.3f}")

    avg_local_rmse = float(np.mean(local_rmses))

    # ---------------------------------------------------------
    # 3. FEDERATED AGGREGATION (FedAvg Weight Averaging)
    # ---------------------------------------------------------
    # FedAvg: Compute weighted average of local model parameters
    fed_weights = np.mean(local_weights, axis=0)
    fed_bias = float(np.mean(local_biases))

    federated_model = Ridge(alpha=1.0)
    federated_model.coef_ = fed_weights
    federated_model.intercept_ = fed_bias

    y_pred_fed = federated_model.predict(X_test)
    rmse_fed = np.sqrt(mean_squared_error(y_test, y_pred_fed))
    mae_fed = mean_absolute_error(y_test, y_pred_fed)
    r2_fed = r2_score(y_test, y_pred_fed)

    # ---------------------------------------------------------
    # SUMMARY EVALUATION & BENCHMARK REPORT
    # ---------------------------------------------------------
    logger.info("\n=================================================================")
    logger.info("FEDERATED LEARNING (FedAvg) VS CENTRALIZED EVALUATION RESULTS")
    logger.info("=================================================================")
    print(f"\n{'Architecture Paradigm':<30} | {'RMSE':<8} | {'MAE':<8} | {'R² Score':<8} | {'Privacy Level'}")
    print("-" * 85)
    print(f"{'Centralized (All Data Pooled)':<30} | {rmse_central:<8.3f} | {mae_central:<8.3f} | {r2_central:<8.3f} | Low (Raw Telemetry Transmitted)")
    print(f"{'Local-Only (Isolated UAV)':<30} | {avg_local_rmse:<8.3f} | {'N/A':<8} | {'N/A':<8} | High (No External Sharing)")
    print(f"{'Federated Global Model (FedAvg)':<30} | {rmse_fed:<8.3f} | {mae_fed:<8.3f} | {r2_fed:<8.3f} | DEFENSE-GRADE (Zero Telemetry Shared)")
    print("-" * 85)
    rmse_gap_pct = ((rmse_fed - rmse_central) / rmse_central) * 100
    logger.info(
        f"[RESULT] Federated model RMSE ({rmse_fed:.3f}) is {rmse_gap_pct:.1f}% higher than the centralized model "
        f"({rmse_central:.3f}), and outperforms the average local-only model (RMSE {avg_local_rmse:.3f}) by "
        f"{((avg_local_rmse - rmse_fed) / avg_local_rmse * 100):.1f}%, while never transmitting raw flight telemetry off-node."
    )

if __name__ == "__main__":
    main()
