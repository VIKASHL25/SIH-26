"""
train_anomaly_pca.py

Retrains the anomaly detection model as PCA reconstruction-error scoring
over the expanded 51-feature set — replacing Isolation Forest, which
underperformed on this feature set (see README.md for the comparison and
why: IF's random-split mechanism degrades with many correlated features;
PCA explicitly models the correlation structure, which is exactly what
these rolling-stat + residual + ratio features have plenty of).

Requires the accompanying patches to be applied in the target repo:
    - backend/feature_engine.py  (_generate_anomaly_features, expanded)
    - backend/model_loader.py    (anomaly_feature_cols list + predict_anomaly
                                   rewritten for reconstruction-error scoring)
    - backend/config.py          (ANOMALY_MODEL_PATH renamed, ANOMALY_THRESHOLD
                                   recalibrated for the new score scale)
See README.md for exact diffs.

Run:
    python src/train_anomaly_pca.py \
        --data MALE_UAV_aero_piston_engine_final_100k.csv \
        --out models/anomaly_detection \
        --hashes-out models/model_hashes.json
"""

import argparse
import hashlib
import json
import os
import time

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.metrics import precision_score, recall_score, roc_auc_score
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


def reconstruction_error(scaler, pca, X):
    Xs = scaler.transform(X)
    Xr = pca.inverse_transform(pca.transform(Xs))
    return np.sum((Xs - Xr) ** 2, axis=1)


def main(data_path, out_dir, hashes_out, n_components, threshold_percentile, seed):
    t0 = time.time()

    print(f"[1/6] Loading {data_path} ...")
    df = pd.read_csv(data_path)
    df = df.sort_values(["mission_id", "timestamp_s"]).reset_index(drop=True)
    print(f"      {df.shape[0]} rows, {df['mission_id'].nunique()} missions")

    print("[2/6] Engineering expanded 51-feature set ...")
    df_feat = engineer_anomaly_features(df)
    print(f"      {len(ANOMALY_FEATURE_COLS)} features")

    print("[3/6] Splitting by mission (stratified per fault type; final test held out) ...")
    train_df, test_df = mission_level_split(df_feat, test_frac=0.2, seed=seed)
    train_normal = train_df[train_df["fault_type"] == "normal"]
    print(f"      {train_df['mission_id'].nunique()} train missions / "
          f"{test_df['mission_id'].nunique()} test missions "
          f"({len(train_normal)} normal training rows)")

    print(f"[4/6] Fitting StandardScaler + PCA (n_components={n_components}) on normal rows only ...")
    scaler = StandardScaler().fit(train_normal[ANOMALY_FEATURE_COLS])
    pca = PCA(n_components=n_components, random_state=seed).fit(
        scaler.transform(train_normal[ANOMALY_FEATURE_COLS])
    )
    explained = float(np.sum(pca.explained_variance_ratio_))
    print(f"      {n_components} components explain {explained:.1%} of normal-operation variance")

    print(f"[5/6] Calibrating threshold at the {threshold_percentile}th percentile of "
          "normal training reconstruction error, evaluating on held-out missions ...")
    train_err = reconstruction_error(scaler, pca, train_normal[ANOMALY_FEATURE_COLS])
    threshold = float(np.percentile(train_err, threshold_percentile))

    test_err = reconstruction_error(scaler, pca, test_df[ANOMALY_FEATURE_COLS])
    test_y = (test_df["fault_type"] != "normal").astype(int)
    test_auc = roc_auc_score(test_y, test_err)
    test_pred = (test_err >= threshold).astype(int)
    precision = precision_score(test_y, test_pred, zero_division=0)
    recall = recall_score(test_y, test_pred, zero_division=0)
    print(f"      Threshold: {threshold:.4f}")
    print(f"      Test ROC-AUC: {test_auc:.4f}")
    print(f"      At this threshold: precision={precision:.4f}, recall={recall:.4f}")

    latencies = []
    for mission_id, g in test_df.groupby("mission_id"):
        g = g.sort_values("timestamp_s").reset_index(drop=True)
        if (g["fault_type"] == "normal").all():
            continue
        onset_idx = g[g["fault_type"] != "normal"].index.min()
        g_err = reconstruction_error(scaler, pca, g[ANOMALY_FEATURE_COLS])
        flagged_after_onset = np.where(g_err[onset_idx:] >= threshold)[0]
        if len(flagged_after_onset) > 0:
            latencies.append(int(flagged_after_onset[0]))
    mean_latency = float(np.mean(latencies)) if latencies else None
    print(f"      Mean detection latency after fault onset: {mean_latency} timesteps "
          f"(over {len(latencies)} fault missions)")

    print("[6/6] Saving PCA model + scaler (joblib) and hashing ...")
    os.makedirs(out_dir, exist_ok=True)
    model_path = os.path.join(out_dir, "anomaly_pca_model.pkl")
    scaler_path = os.path.join(out_dir, "scaler.pkl")
    manifest_path = os.path.join(out_dir, "anomaly_detection_manifest.json")

    joblib.dump(pca, model_path)
    joblib.dump(scaler, scaler_path)
    model_size_mb = round(os.path.getsize(model_path) / 1e6, 3)

    manifest = {
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "problem_statement": "SIH 2026 / DRDO PS 26054 - MALE UAV aero piston engine anomaly detection",
        "algorithm": "PCA reconstruction error (replaces Isolation Forest — "
                     "see README.md for the comparison and rationale)",
        "source_data": data_path,
        "n_rows": int(df.shape[0]),
        "n_missions": int(df["mission_id"].nunique()),
        "feature_count": len(ANOMALY_FEATURE_COLS),
        "feature_cols": ANOMALY_FEATURE_COLS,
        "n_components": n_components,
        "explained_variance_ratio": explained,
        "threshold_percentile": threshold_percentile,
        "anomaly_threshold": threshold,
        "requires_repo_patch": "feature_engine.py, model_loader.py, and config.py all "
                                "need the accompanying patch — see README.md.",
        "training_note": "Fit on 'normal'-labeled rows only; fault labels used solely "
                          "for threshold calibration and evaluation, never for fitting.",
        "model_size_mb": model_size_mb,
        "metrics": {
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
    hashes["anomaly_scaler_unverified"] = sha256_of_file(scaler_path)
    os.makedirs(os.path.dirname(hashes_out) or ".", exist_ok=True)
    with open(hashes_out, "w") as f:
        json.dump(hashes, f, indent=2)

    print(f"      Saved to {out_dir}/ ({model_size_mb} MB)")
    print(f"      anomaly_detection SHA-256: {model_hash}")
    print(f"      Updated {hashes_out}")
    print(f"      Done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="MALE_UAV_aero_piston_engine_final_100k.csv")
    parser.add_argument("--out", default="models/anomaly_detection")
    parser.add_argument("--hashes-out", default="models/model_hashes.json")
    parser.add_argument("--n_components", type=int, default=10)
    parser.add_argument("--threshold_percentile", type=float, default=95.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    main(args.data, args.out, args.hashes_out, args.n_components, args.threshold_percentile, args.seed)
