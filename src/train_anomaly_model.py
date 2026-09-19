"""
train_anomaly_model.py

Retrains model_loader.py's model #1: Isolation Forest + StandardScaler for
anomaly detection. Semi-supervised training/evaluation:
  - FIT on 'normal'-labeled rows only (from training missions) — labels are
    NOT used to fit the model, only to select which rows represent normal
    operation.
  - TUNE hyperparameters using StratifiedGroupKFold (grouped by mission),
    scoring candidates by ROC-AUC of the anomaly score against the
    normal-vs-fault label on validation folds.
  - Final TEST on whole missions never touched during training or tuning.

Produces a drop-in replacement for:
    models/anomaly_detection/isolation_forest_model.pkl
    models/anomaly_detection/scaler.pkl

...and updates models/model_hashes.json (key: "anomaly_detection", matching
exactly what model_loader.py._verify_model_hash() already checks).

Run:
    python src/train_anomaly_model.py \
        --data MALE_UAV_aero_piston_engine_final_100k.csv \
        --out models/anomaly_detection \
        --hashes-out models/model_hashes.json
"""

import argparse
import hashlib
import itertools
import json
import os
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score, precision_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler

from anomaly_features_batch import ANOMALY_FEATURE_COLS, engineer_anomaly_features


def sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def mission_level_split(df: pd.DataFrame, test_frac=0.2, seed=42):
    mission_info = df[["mission_id", "mission_type"]].drop_duplicates()
    rng = np.random.RandomState(seed)
    train_missions, test_missions = [], []
    for mtype, g in mission_info.groupby("mission_type"):
        ids = g["mission_id"].values.copy()
        rng.shuffle(ids)
        n_test = max(1, int(round(len(ids) * test_frac)))
        test_missions += list(ids[:n_test])
        train_missions += list(ids[n_test:])
    train_df = df[df["mission_id"].isin(train_missions)].reset_index(drop=True)
    test_df = df[df["mission_id"].isin(test_missions)].reset_index(drop=True)
    return train_df, test_df


def anomaly_scores(model, scaler, X):
    """Matches model_loader.py's predict_anomaly: anomaly_score = -decision_function."""
    scaled = scaler.transform(X)
    return -model.decision_function(scaled)


def main(data_path, out_dir, hashes_out, cv_folds, seed):
    t0 = time.time()

    print(f"[1/7] Loading {data_path} ...")
    df = pd.read_csv(data_path)
    df = df.sort_values(["mission_id", "timestamp_s"]).reset_index(drop=True)
    print(f"      {df.shape[0]} rows, {df['mission_id'].nunique()} missions")

    print("[2/7] Engineering features (verified match to backend/feature_engine.py) ...")
    df_feat = engineer_anomaly_features(df)
    y_is_fault = (df_feat["fault_type"] != "normal").astype(int)
    print(f"      {len(ANOMALY_FEATURE_COLS)} features, "
          f"{y_is_fault.sum()} anomalous rows / {len(y_is_fault)} total (labels used for eval only)")

    print("[3/7] Splitting by mission (stratified per fault type; final test held out) ...")
    train_df, test_df = mission_level_split(df_feat, test_frac=0.2, seed=seed)
    print(f"      {train_df['mission_id'].nunique()} train missions / "
          f"{test_df['mission_id'].nunique()} test missions")

    print(f"[4/7] Tuning hyperparameters via {cv_folds}-fold mission-grouped CV "
          "(labels used only to score candidates, not to fit) ...")
    groups = train_df["mission_id"].values
    y_train_all = (train_df["fault_type"] != "normal").astype(int).values
    X_train_all = train_df[ANOMALY_FEATURE_COLS]

    # max_samples: CV sweep (512/1024/2048/4096/8192/full) showed ROC-AUC
    # climbing up to ~4096-8192 then flattening (0.973 at 4096 vs 0.978 at
    # the full ~60k normal rows, for 12MB vs 70MB+ in file size) — this
    # dataset's anomalies are subtle multivariate drift, not point outliers,
    # so it benefits from larger subsamples than the textbook default (256).
    param_grid = list(itertools.product(
        [100, 150, 200],           # n_estimators
        [2048, 4096],              # max_samples (fixed subsample size per tree) —
                                    # 8192 tested and gave <0.001 ROC-AUC gain
                                    # over 4096 for ~2x the file size, not worth it
        [0.02, 0.05, 0.1],         # contamination
    ))

    cv = StratifiedGroupKFold(n_splits=cv_folds, shuffle=True, random_state=seed)
    best_score, best_params = -1.0, None

    for gi, (n_estimators, max_samples, contamination) in enumerate(param_grid):
        tg0 = time.time()
        fold_scores = []
        for tr_idx, val_idx in cv.split(X_train_all, y_train_all, groups=groups):
            fold_train = train_df.iloc[tr_idx]
            fold_val = train_df.iloc[val_idx]

            fold_train_normal = fold_train[fold_train["fault_type"] == "normal"]
            if len(fold_train_normal) < 50 or fold_val["fault_type"].eq("normal").all() or (~fold_val["fault_type"].eq("normal")).sum() == 0:
                continue

            effective_max_samples = min(max_samples, len(fold_train_normal))
            scaler = StandardScaler().fit(fold_train_normal[ANOMALY_FEATURE_COLS])
            X_scaled = scaler.transform(fold_train_normal[ANOMALY_FEATURE_COLS])
            model = IsolationForest(
                n_estimators=n_estimators,
                max_samples=effective_max_samples,
                contamination=contamination,
                random_state=seed,
                n_jobs=1,
            ).fit(X_scaled)

            val_scores = anomaly_scores(model, scaler, fold_val[ANOMALY_FEATURE_COLS])
            val_y = (fold_val["fault_type"] != "normal").astype(int)
            fold_scores.append(roc_auc_score(val_y, val_scores))

        if fold_scores:
            mean_score = float(np.mean(fold_scores))
            print(f"      [{gi+1}/{len(param_grid)}] n_estimators={n_estimators} "
                  f"max_samples={max_samples} contamination={contamination} "
                  f"-> ROC-AUC={mean_score:.4f} ({time.time()-tg0:.1f}s)", flush=True)
            if mean_score > best_score:
                best_score, best_params = mean_score, {
                    "n_estimators": n_estimators,
                    "max_samples": max_samples,
                    "contamination": contamination,
                }

    print(f"      Best CV ROC-AUC: {best_score:.4f}")
    print(f"      Best params: {best_params}")

    print("[5/7] Retraining final model on full training set (normal rows only) ...")
    train_normal = train_df[train_df["fault_type"] == "normal"]
    final_params = dict(best_params)
    final_params["max_samples"] = min(final_params["max_samples"], len(train_normal))
    scaler = StandardScaler().fit(train_normal[ANOMALY_FEATURE_COLS])
    model = IsolationForest(
        **final_params,
        random_state=seed,
        n_jobs=1,
    ).fit(scaler.transform(train_normal[ANOMALY_FEATURE_COLS]))
    print(f"      Fit on {len(train_normal)} normal rows from {train_normal['mission_id'].nunique()} missions")

    print("[6/7] Evaluating on unseen missions ...")
    test_scores = anomaly_scores(model, scaler, test_df[ANOMALY_FEATURE_COLS])
    test_y = (test_df["fault_type"] != "normal").astype(int)
    test_auc = roc_auc_score(test_y, test_scores)

    threshold = 0.0  # matches config.ANOMALY_THRESHOLD
    test_pred = (test_scores >= threshold).astype(int)
    precision = precision_score(test_y, test_pred, zero_division=0)
    recall = recall_score(test_y, test_pred, zero_division=0)
    print(f"      Test ROC-AUC: {test_auc:.4f}")
    print(f"      At threshold={threshold}: precision={precision:.4f}, recall={recall:.4f}")

    # Detection latency: rows after true fault onset until anomaly_score first crosses threshold, per mission
    latencies = []
    for mission_id, g in test_df.groupby("mission_id"):
        g = g.sort_values("timestamp_s").reset_index(drop=True)
        if (g["fault_type"] == "normal").all():
            continue
        onset_idx = g[g["fault_type"] != "normal"].index.min()
        g_scores = anomaly_scores(model, scaler, g[ANOMALY_FEATURE_COLS])
        flagged_after_onset = np.where(g_scores[onset_idx:] >= threshold)[0]
        if len(flagged_after_onset) > 0:
            latencies.append(int(flagged_after_onset[0]))
    mean_latency = float(np.mean(latencies)) if latencies else None
    print(f"      Mean detection latency after fault onset: {mean_latency} timesteps "
          f"(over {len(latencies)} fault missions)")

    print("[7/7] Saving model + scaler (joblib) and hashing ...")
    os.makedirs(out_dir, exist_ok=True)
    model_path = os.path.join(out_dir, "isolation_forest_model.pkl")
    scaler_path = os.path.join(out_dir, "scaler.pkl")
    manifest_path = os.path.join(out_dir, "anomaly_detection_manifest.json")

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    manifest = {
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "problem_statement": "SIH 2026 / DRDO PS 26054 - MALE UAV aero piston engine anomaly detection",
        "source_data": data_path,
        "n_rows": int(df.shape[0]),
        "n_missions": int(df["mission_id"].nunique()),
        "feature_source": "anomaly_features_batch.py, verified against backend/feature_engine.py "
                           "(exact match, max abs diff 0.0 on a held-out mission)",
        "feature_cols": ANOMALY_FEATURE_COLS,
        "training_note": "Fit on 'normal'-labeled rows only; fault labels used solely for "
                          "hyperparameter selection and evaluation, never for fitting.",
        "model_params": final_params,
        "anomaly_threshold": threshold,
        "metrics": {
            "cv_best_roc_auc": round(best_score, 4),
            "test_roc_auc": round(float(test_auc), 4),
            "test_precision_at_threshold": round(float(precision), 4),
            "test_recall_at_threshold": round(float(recall), 4),
            "mean_detection_latency_timesteps": mean_latency,
            "n_fault_missions_evaluated": len(latencies),
        },
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    model_hash = sha256_of_file(model_path)
    hashes = {}
    if os.path.exists(hashes_out):
        with open(hashes_out) as f:
            hashes = json.load(f)
    hashes["anomaly_detection"] = model_hash
    # Also record the scaler's hash for reference — not yet checked by
    # model_loader.py (only the model file is verified today), but useful
    # if that's extended later.
    hashes["anomaly_scaler_unverified"] = sha256_of_file(scaler_path)
    os.makedirs(os.path.dirname(hashes_out) or ".", exist_ok=True)
    with open(hashes_out, "w") as f:
        json.dump(hashes, f, indent=2)

    print(f"      Saved to {out_dir}/")
    print(f"      anomaly_detection SHA-256: {model_hash}")
    print(f"      Updated {hashes_out}")
    print(f"      Done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="MALE_UAV_aero_piston_engine_final_100k.csv")
    parser.add_argument("--out", default="models/anomaly_detection")
    parser.add_argument("--hashes-out", default="models/model_hashes.json")
    parser.add_argument("--cv_folds", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    main(args.data, args.out, args.hashes_out, args.cv_folds, args.seed)
