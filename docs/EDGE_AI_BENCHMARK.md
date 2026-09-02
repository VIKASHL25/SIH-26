# Edge AI & Lightweight Analytics Benchmarking Report

## 1. Executive Summary

This report evaluates the computational efficiency, memory footprint, and single-core CPU inference latency across all 4 machine learning models in the Digital Twin suite to define optimal hardware allocation between onboard UAV flight computers and Ground Control Stations (GCS).

**Target Latency Budgets:**
- Onboard Real-Time Control Loop (Tier 1): < 2.0 ms per sample (10Hz - 50Hz telemetry stream)
- Ground Control Station (GCS) Analytics (Tier 2): < 50.0 ms per sample

---

## 2. Benchmark Results Table

| AI Model Component | Artifact Size (KB) | Features | Inference Latency (ms/sample) | Target Execution Tier |
| :--- | :--- | :--- | :--- | :--- |
| **1. Anomaly Detection (Isolation Forest)** | **5739.6 KB** | 13 | **41.679 ms** | GCS / Edge Analytics (<50ms) |
| **2. Degradation Estimation (XGBoost)** | **9362.5 KB** | 120 | **1.922 ms** | Onboard Edge (Flight Computer, <2ms) |
| **3. Fault Classification (XGBoost)** | **1707.7 KB** | 55 | **9.134 ms** | GCS / Edge Analytics (<50ms) |
| **4. RUL Prediction (131-Feat XGBoost)** | **9010.8 KB** | 131 | **10.875 ms** | GCS / Edge Analytics (<50ms) |
| **FULL 4-MODEL PIPELINE TOTAL** | **25820.5 KB** | — | **63.610 ms** | **Batch/Periodic Suitable (63.6ms)** |

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
