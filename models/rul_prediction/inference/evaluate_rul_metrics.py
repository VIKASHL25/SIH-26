import os
import json
import numpy as np
import pandas as pd
from xgboost import XGBRegressor, DMatrix
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
TEST_FILE = os.path.join(DATA_DIR, "rul_test.csv")
MODEL_FILE = os.path.join(BASE_DIR, "..", "xgboost_rul_model.json")
FEATURE_NAMES_FILE = os.path.join(BASE_DIR, "..", "xgboost_rul_features.txt")
DOCS_DIR = os.path.join(BASE_DIR, "..", "..", "..", "docs")

def calculate_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    errors = y_pred - y_true
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    
    # Non-zero true RUL for MAPE
    nz_mask = y_true > 1.0
    mape = float(np.mean(np.abs(errors[nz_mask] / y_true[nz_mask])) * 100.0) if np.sum(nz_mask) > 0 else 0.0

    return {
        "mae_hours": round(mae, 2),
        "rmse_hours": round(rmse, 2),
        "r2_score": round(r2, 4),
        "mape_pct": round(mape, 2),
        "mean_error_hours": round(float(np.mean(errors)), 2),
        "error_p25_hours": round(float(np.percentile(errors, 25)), 2),
        "error_p50_median": round(float(np.percentile(errors, 50)), 2),
        "error_p75_hours": round(float(np.percentile(errors, 75)), 2),
        "total_test_samples": int(len(y_true))
    }

def main():
    print("====================================")
    print("COMPREHENSIVE RUL MODEL EVALUATION")
    print("====================================")

    os.makedirs(DOCS_DIR, exist_ok=True)

    if not os.path.exists(TEST_FILE):
        raise FileNotFoundError(f"Test dataset not found at {TEST_FILE}. Run data preparation first.")

    test_df = pd.read_csv(TEST_FILE)
    print(f"Test engines: {test_df['engine_id'].nunique()}, test rows: {len(test_df):,}")

    with open(FEATURE_NAMES_FILE, "r") as f:
        feature_cols = [line.strip() for line in f if line.strip()]

    model = XGBRegressor()
    model.load_model(MODEL_FILE)
    print(f"Loaded XGBoost model from {MODEL_FILE}")

    X_test = test_df[feature_cols].astype(float)
    y_test = test_df["rul_hours"].astype(float).values

    # Point Predictions
    y_pred_raw = model.predict(X_test)
    y_pred = np.maximum(0.0, y_pred_raw)

    test_df["predicted_rul"] = y_pred
    test_df["prediction_error"] = y_pred - y_test

    # Uncertainty Quantification (P10 / P90 via iteration variance)
    booster = model.get_booster()
    dmat = DMatrix(X_test.values, feature_names=feature_cols)
    num_trees = booster.num_boosted_rounds()
    checkpoints = np.linspace(max(1, num_trees // 5), num_trees, 10, dtype=int)
    
    tree_preds = np.column_stack([
        booster.predict(dmat, iteration_range=(0, int(cp)))
        for cp in checkpoints
    ])
    tree_std = np.std(tree_preds, axis=1)
    adjusted_std = np.maximum(1.5, tree_std * 0.25 + y_pred * 0.03)

    test_df["uncertainty_std"] = adjusted_std
    test_df["rul_p10"] = np.maximum(0.0, y_pred - 1.645 * adjusted_std)
    test_df["rul_p90"] = y_pred + 1.645 * adjusted_std

    # 1. Overall Metrics
    overall_metrics = calculate_metrics(y_test, y_pred)
    print("\n--- OVERALL TEST METRICS ---")
    for k, v in overall_metrics.items():
        print(f"  {k:22}: {v}")

    # 2. Lifecycle Phase Breakdown (Early, Mid, Late)
    early_mask = y_test > 200.0
    mid_mask = (y_test >= 50.0) & (y_test <= 200.0)
    late_mask = y_test < 50.0

    lifecycle_breakdown = {
        "early_life_gt_200h": calculate_metrics(y_test[early_mask], y_pred[early_mask]) if np.sum(early_mask) > 0 else None,
        "mid_life_50_to_200h": calculate_metrics(y_test[mid_mask], y_pred[mid_mask]) if np.sum(mid_mask) > 0 else None,
        "late_life_lt_50h": calculate_metrics(y_test[late_mask], y_pred[late_mask]) if np.sum(late_mask) > 0 else None
    }

    # 3. Fault Mode Breakdown (Feedback Item 13)
    fault_mode_metrics = {}
    if "fault_mode" in test_df.columns:
        for fault, grp in test_df.groupby("fault_mode"):
            fault_mode_metrics[str(fault)] = calculate_metrics(grp["rul_hours"], grp["predicted_rul"])

    print("\n--- FAULT MODE BREAKDOWN ---")
    for mode, m in fault_mode_metrics.items():
        print(f"  Mode: {mode:25} | MAE: {m['mae_hours']:5.2f}h | RMSE: {m['rmse_hours']:5.2f}h | R^2: {m['r2_score']:.4f}")

    # Save comprehensive JSON report
    report = {
        "overall_metrics": overall_metrics,
        "lifecycle_metrics": lifecycle_breakdown,
        "fault_mode_metrics": fault_mode_metrics
    }

    report_path = os.path.join(DOCS_DIR, "rul_evaluation_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nEvaluation metrics report saved to: {report_path}")

    # 4. Generate Publication-Quality Plots (Feedback Item 7)
    if plt is not None:
        fig, axs = plt.subplots(2, 2, figsize=(16, 12))

        # Plot A: Complete Degradation-to-Failure Trajectory for Sample Test Engines
        sample_engines = test_df["engine_id"].drop_duplicates().head(4).tolist()
        colors = ["#0284c7", "#059669", "#d97706", "#dc2626"]

        ax_traj = axs[0, 0]
        for eng, color in zip(sample_engines, colors):
            eng_data = test_df[test_df["engine_id"] == eng].sort_values("timestamp_hours")
            fault_name = eng_data["fault_mode"].iloc[0] if "fault_mode" in eng_data.columns else "Nominal"
            
            ax_traj.plot(eng_data["timestamp_hours"], eng_data["rul_hours"], label=f"{eng} (True - {fault_name})", color=color, linestyle="--", linewidth=2.0)
            ax_traj.plot(eng_data["timestamp_hours"], eng_data["predicted_rul"], label=f"{eng} (Pred P50)", color=color, linewidth=2.2)
            ax_traj.fill_between(eng_data["timestamp_hours"], eng_data["rul_p10"], eng_data["rul_p90"], color=color, alpha=0.15)

        ax_traj.set_title("Actual vs Predicted RUL over Complete Degradation Cycles", fontsize=12, fontweight="bold")
        ax_traj.set_xlabel("Flight Operating Time (Hours)", fontsize=10)
        ax_traj.set_ylabel("Remaining Useful Life (Hours)", fontsize=10)
        ax_traj.legend(loc="upper right", fontsize=8)
        ax_traj.grid(True, alpha=0.3)

        # Plot B: Actual RUL vs Predicted RUL Parity Scatter
        ax_scat = axs[0, 1]
        sample_pts = test_df.sample(min(5000, len(test_df)), random_state=42)
        scatter = ax_scat.scatter(sample_pts["rul_hours"], sample_pts["predicted_rul"], c=sample_pts["uncertainty_std"], cmap="viridis", alpha=0.5, s=12)
        max_val = max(sample_pts["rul_hours"].max(), sample_pts["predicted_rul"].max())
        ax_scat.plot([0, max_val], [0, max_val], 'r--', linewidth=2, label="Ideal Parity (y = x)")
        ax_scat.set_title(f"Parity Plot: Actual vs Predicted RUL (R^2 = {overall_metrics['r2_score']:.4f})", fontsize=12, fontweight="bold")
        ax_scat.set_xlabel("Actual RUL (Hours)", fontsize=10)
        ax_scat.set_ylabel("Predicted RUL (Hours)", fontsize=10)
        cbar = fig.colorbar(scatter, ax=ax_scat)
        cbar.set_label("Uncertainty Std +/- sigma (Hours)", fontsize=9)
        ax_scat.legend(loc="upper left", fontsize=9)
        ax_scat.grid(True, alpha=0.3)

        # Plot C: Prediction Error Distribution
        ax_err = axs[1, 0]
        errors = test_df["prediction_error"]
        ax_err.hist(errors, bins=60, color="#0284c7", edgecolor="black", alpha=0.7)
        ax_err.axvline(0, color="red", linestyle="--", linewidth=1.5, label="Zero Error Line")
        ax_err.axvline(np.mean(errors), color="orange", linestyle="-", linewidth=1.5, label=f"Mean Error ({np.mean(errors):.2f}h)")
        ax_err.set_title(f"Prediction Error Distribution (MAE = {overall_metrics['mae_hours']:.2f}h, RMSE = {overall_metrics['rmse_hours']:.2f}h)", fontsize=12, fontweight="bold")
        ax_err.set_xlabel("Prediction Error: (Predicted - Actual) [Hours]", fontsize=10)
        ax_err.set_ylabel("Sample Count", fontsize=10)
        ax_err.legend(loc="upper right", fontsize=9)
        ax_err.grid(True, alpha=0.3)

        # Plot D: Error by Fault/Degradation Mode Bar Chart
        ax_bar = axs[1, 1]
        if fault_mode_metrics:
            modes = list(fault_mode_metrics.keys())
            maes = [fault_mode_metrics[m]["mae_hours"] for m in modes]
            rmses = [fault_mode_metrics[m]["rmse_hours"] for m in modes]
            x = np.arange(len(modes))
            width = 0.35

            ax_bar.bar(x - width/2, maes, width, label="MAE (h)", color="#0284c7", alpha=0.85)
            ax_bar.bar(x + width/2, rmses, width, label="RMSE (h)", color="#e11d48", alpha=0.85)
            ax_bar.set_xticks(x)
            ax_bar.set_xticklabels([m.replace("_", "\n") for m in modes], fontsize=8)
            ax_bar.set_title("RUL Prediction Accuracy Across Specific Degradation Modes", fontsize=12, fontweight="bold")
            ax_bar.set_ylabel("Error (Hours)", fontsize=10)
            ax_bar.legend(loc="upper right", fontsize=9)
            ax_bar.grid(True, alpha=0.3)

        plt.tight_layout()
        plot_path = os.path.join(DOCS_DIR, "rul_evaluation_trajectory.png")
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"Publication-ready evaluation plot saved to: {plot_path}")

if __name__ == "__main__":
    main()
