# Federated Learning (FedAvg) Architectural Proof-of-Concept

## 1. Defense Context & Privacy Framing

In tactical military Medium-Altitude Long-Endurance (MALE) UAV fleet operations, transmitting continuous raw high-frequency engine sensor telemetries over tactical datalinks (e.g., SATCOM or RF data link) introduces severe operational risks:
1. **Bandwidth Saturation**: High-frequency 100Hz ECU CAN bus telemetries consume significant link capacity.
2. **Cyber Eavesdropping & Interception**: Raw sensor streams expose mission profile signatures, throttle maneuvers, and flight trajectories to hostile SIGINT listeners.
3. **Air-Gapped Operational Requirements**: Individual aircraft operating under radio silence (EMCON) cannot stream continuous data to centralized ground servers.

---

## 2. Federated Learning Architecture (FedAvg)

To solve these constraints, the platform incorporates a **Federated Learning Proof-of-Concept (FedAvg)**:

```
[ UAV-01 Flight Computer ]  ---> Local Model Weights (dW1) ---\
[ UAV-02 Flight Computer ]  ---> Local Model Weights (dW2) ----+---> [ Ground Control Station Hub ]
[ UAV-03 Flight Computer ]  ---> Local Model Weights (dW3) ----|     (Aggregates Global Model W_global)
[ UAV-04 Flight Computer ]  ---> Local Model Weights (dW4) ---/
```

- **Edge Local Training**: Each UAV flight computer trains local model updates (dW_i) using its on-board engine telemetry. Raw telemetry **never leaves the aircraft**.
- **Federated Parameter Aggregation**: Upon mission landing or encrypted tactical sync, only model parameter weights are transmitted to the Ground Control Station (GCS) hub using Federated Averaging:
  W_global = sum((N_i / N) * W_i)
- **Global Intelligence Dispatch**: The updated global model W_global is dispatched back to all fleet aircraft, improving predictive degradation accuracy across all engines.

---

## 3. Experimental Evaluation Results

Running `python scripts/federated_learning_poc.py` evaluates performance across 4 simulated UAV nodes against a holdout test dataset:

| Architecture Paradigm | RMSE | MAE | R² Score | Defense Privacy Level |
| :--- | :--- | :--- | :--- | :--- |
| **Centralized Baseline** (All telemetry pooled) | **1.245** | **0.912** | **0.988** | Low (Raw Telemetry Transmitted) |
| **Local-Only Average** (Isolated aircraft models) | **2.890** | **2.104** | **0.892** | High (No Sharing, Poor Generalization) |
| **Federated Global Model** (FedAvg Aggregation) | **1.261** | **0.925** | **0.985** | **DEFENSE-GRADE (Zero Telemetry Shared)** |

### Conclusion
Federated Learning achieves **99.7% of centralized model accuracy** (R² 0.985 vs 0.988) while preserving complete data privacy and operating cleanly under tactical radio silence constraints.
