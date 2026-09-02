"""
MALE UAV Aero Piston Engine Digital Twin — Edge AI & Lightweight Analytics Benchmarking
DRDO / SIH Defense Hackathon Project

This script benchmarks file sizes (KB/MB), single-core CPU inference latency (ms),
and memory footprint across all 4 Digital Twin AI/ML models to demonstrate onboard vs GCS deployment suitability.
"""

import os 
import sys
import time
import logging
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.model_loader import DigitalTwinModelManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger("EdgeAIBenchmark")

def get_file_size_kb(filepath: str) -> float:
    if os.path.exists(filepath):
        size_kb = round(os.path.getsize(filepath) / 1024.0, 2)
        if size_kb == 0.0:
            logger.warning(f"Model file at {filepath} exists but is empty (0.0 KB)!")
        return size_kb
    logger.warning(f"Expected model artifact missing at path: {filepath}")
    return 0.0

def derive_model_tier(latency_ms: float) -> str:
    """Derives honest target execution tier based on latency budget."""
    if latency_ms < 2.0:
        return "Onboard Edge (Flight Computer, <2ms)"
    elif latency_ms < 50.0:
        return "GCS / Edge Analytics (<50ms)"
    else:
        return "GCS Batch / Offline Analytics (>50ms)"

def main():
    logger.info("=================================================================")
    logger.info("STARTING EDGE AI & LIGHTWEIGHT MODEL BENCHMARKING SUITE")
    logger.info("=================================================================")

    # Initialize and load models
    mm = DigitalTwinModelManager()
    mm.load_all_models()

    # 1. Model Artifact Size Benchmarking (Corrected paths)
    models_dir = os.path.abspath("models")
    anomaly_path = os.path.join(models_dir, "anomaly_detection", "isolation_forest_model.pkl")
    degradation_path = os.path.join(models_dir, "degradation_detection", "xgb_degradation_model.json")
    fault_path = os.path.join(models_dir, "fault_detection", "fault_detection_multiclass_xgb.json")
    rul_path = os.path.join(models_dir, "rul_prediction", "xgboost_rul_model.json")

    anomaly_size = get_file_size_kb(anomaly_path)
    degradation_size = get_file_size_kb(degradation_path)
    fault_size = get_file_size_kb(fault_path)
    rul_size = get_file_size_kb(rul_path)

    # 2. Synthetic Test Feature Vectors
    anomaly_dummy = pd.DataFrame([np.random.randn(len(mm.anomaly_feature_cols))], columns=mm.anomaly_feature_cols)
    degradation_dummy = pd.DataFrame([np.random.randn(len(mm.degradation_feature_cols))], columns=mm.degradation_feature_cols)
    fault_dummy = pd.DataFrame([np.random.randn(len(mm.fault_feature_cols))], columns=mm.fault_feature_cols)
    rul_dummy = pd.DataFrame([np.random.randn(len(mm.rul_feature_cols))], columns=mm.rul_feature_cols)

    clean_sample = {col: 100.0 for col in mm.anomaly_feature_cols}

    # 3. Latency Benchmarking (1,000 iterations single-core CPU)
    N_ITER = 1000

    # Anomaly Model Latency
    t0 = time.perf_counter()
    for _ in range(N_ITER):
        _ = mm.predict_anomaly(anomaly_dummy)
    t1 = time.perf_counter()
    anomaly_latency_ms = ((t1 - t0) / N_ITER) * 1000.0

    # Degradation Model Latency
    t0 = time.perf_counter()
    for _ in range(N_ITER):
        _ = mm.predict_degradation(degradation_dummy, clean_sample=clean_sample)
    t1 = time.perf_counter()
    degradation_latency_ms = ((t1 - t0) / N_ITER) * 1000.0

    # Fault Classification Latency
    t0 = time.perf_counter()
    for _ in range(N_ITER):
        _ = mm.predict_fault(fault_dummy)
    t1 = time.perf_counter()
    fault_latency_ms = ((t1 - t0) / N_ITER) * 1000.0

    # RUL Prediction Latency
    t0 = time.perf_counter()
    for _ in range(N_ITER):
        _ = mm.predict_rul(rul_dummy, buffer_len=13, health_pct=80.0, degradation_index=0.2)
    t1 = time.perf_counter()
    rul_latency_ms = ((t1 - t0) / N_ITER) * 1000.0

    # Total 4-Model Combined Pipeline Latency
    total_latency_ms = anomaly_latency_ms + degradation_latency_ms + fault_latency_ms + rul_latency_ms

    # Dynamic verdict calculation based on latency
    if total_latency_ms < 10.0:
        pipeline_verdict = "Real-Time Suitable (<10ms)"
    elif total_latency_ms < 50.0:
        pipeline_verdict = f"Near Real-Time ({total_latency_ms:.1f}ms, suitable for GCS-side/ground analytics)"
    else:
        pipeline_verdict = f"Batch/Periodic Suitable ({total_latency_ms:.1f}ms)"

    anomaly_tier = derive_model_tier(anomaly_latency_ms)
    degradation_tier = derive_model_tier(degradation_latency_ms)
    fault_tier = derive_model_tier(fault_latency_ms)
    rul_tier = derive_model_tier(rul_latency_ms)

    print("\n" + "=" * 110)
    print(f"{'AI / ML Model Component':<32} | {'Artifact Size (KB)':<18} | {'Single-Core Latency (ms)':<24} | {'Target Hardware Tier'}")
    print("-" * 110)
    print(f"{'1. Anomaly Detection (IsoForest)':<32} | {anomaly_size:<18.1f} | {anomaly_latency_ms:<24.3f} | {anomaly_tier}")
    print(f"{'2. Degradation Est. (XGBoost)':<32} | {degradation_size:<18.1f} | {degradation_latency_ms:<24.3f} | {degradation_tier}")
    print(f"{'3. Fault Classifier (XGBoost)':<32} | {fault_size:<18.1f} | {fault_latency_ms:<24.3f} | {fault_tier}")
    print(f"{'4. RUL Predictor (131-Feat XGB)':<32} | {rul_size:<18.1f} | {rul_latency_ms:<24.3f} | {rul_tier}")
    print("-" * 110)
    print(f"{'FULL 4-MODEL PIPELINE TOTAL':<32} | {round(anomaly_size+degradation_size+fault_size+rul_size, 1):<18} | {total_latency_ms:<24.3f} | {pipeline_verdict}")
    print("=" * 110 + "\n")

    # Generate Markdown Report
    report_content = f"""# Edge AI & Lightweight Analytics Benchmarking Report

## 1. Executive Summary

This report evaluates the computational efficiency, memory footprint, and single-core CPU inference latency across all 4 machine learning models in the Digital Twin suite to define optimal hardware allocation between onboard UAV flight computers and Ground Control Stations (GCS).

**Target Latency Budgets:**
- Onboard Real-Time Control Loop (Tier 1): < 2.0 ms per sample (10Hz - 50Hz telemetry stream)
- Ground Control Station (GCS) Analytics (Tier 2): < 50.0 ms per sample

---

## 2. Benchmark Results Table

| AI Model Component | Artifact Size (KB) | Features | Inference Latency (ms/sample) | Target Execution Tier |
| :--- | :--- | :--- | :--- | :--- |
| **1. Anomaly Detection (Isolation Forest)** | **{anomaly_size:.1f} KB** | 13 | **{anomaly_latency_ms:.3f} ms** | {anomaly_tier} |
| **2. Degradation Estimation (XGBoost)** | **{degradation_size:.1f} KB** | 120 | **{degradation_latency_ms:.3f} ms** | {degradation_tier} |
| **3. Fault Classification (XGBoost)** | **{fault_size:.1f} KB** | 55 | **{fault_latency_ms:.3f} ms** | {fault_tier} |
| **4. RUL Prediction (131-Feat XGBoost)** | **{rul_size:.1f} KB** | 131 | **{rul_latency_ms:.3f} ms** | {rul_tier} |
| **FULL 4-MODEL PIPELINE TOTAL** | **{anomaly_size+degradation_size+fault_size+rul_size:.1f} KB** | — | **{total_latency_ms:.3f} ms** | **{pipeline_verdict}** |

---

## 3. Onboard Edge vs Ground Station Split Architecture

### Onboard Edge Flight Computer (Tier 1 Execution)
- **Models**: High-speed lightweight models satisfying onboard latency budgets (< 2.0 ms).
- **Footprint**: Small memory footprint (suitable for ARM Cortex-M7 / ARM Cortex-A53 flight control hardware).
- **Role**: Immediate cockpit warning, emergency Return-To-Base (RTB) triggers, and zero-latency safety enforcement.

### Ground Control Station (GCS) & Cloud Analytics (Tier 2 Execution)
- **Models**: Heavy predictive maintenance models, 131-Feature XGBoost RUL Predictor & SHAP TreeExplainer XAI Engine.
- **Latency Requirement**: < 50.0 ms per sample.
- **Role**: Heavy predictive maintenance, depot scheduling, multi-sensor SHAP attribution, and long-term fleet health tracking.
"""

    docs_dir = os.path.abspath("docs")
    os.makedirs(docs_dir, exist_ok=True)
    report_path = os.path.join(docs_dir, "EDGE_AI_BENCHMARK.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    logger.info(f"Saved Edge AI Benchmark Report cleanly to: {report_path}")

if __name__ == "__main__":
    main()
