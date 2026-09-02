# 🚀 MALE UAV Aero Piston Engine Digital Twin Framework
### *Next-Generation Physics-Informed Predictive Health Monitoring, Real-Time AI/ML Diagnostics, Explainable AI (XAI), CAN Telemetry & MongoDB Atlas Persistence*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0%2B-eb5424.svg)](https://xgboost.readthedocs.io/)
[![SHAP](https://img.shields.io/badge/SHAP-XAI%20Explainability-ff69b4.svg)](https://shap.readthedocs.io/)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB%20Atlas-Cloud%20Database-47A248.svg?logo=mongodb&logoColor=white)](https://www.mongodb.com/atlas)
[![CAN Bus](https://img.shields.io/badge/CAN%20Bus-ISO%2011898%20%2F%20DBC-blueviolet.svg)](https://python-can.readthedocs.io/)
[![Architecture](https://img.shields.io/badge/Architecture-5--Node%20Microservices-informational.svg)](#system-architecture)
[![SIH 2026](https://img.shields.io/badge/Smart%20India%20Hackathon-2026-orange.svg)](https://www.sih.gov.in/)

---

## 📌 Executive Summary

Medium-Altitude Long-Endurance (MALE) Unmanned Aerial Vehicles (UAVs)—such as the **TAPAS-BH-201** class—perform mission-critical Intelligence, Surveillance, Target Acquisition, and Reconnaissance (ISTAR) sorties requiring uninterrupted powertrain reliability. In-flight piston engine failures present catastrophic operational and mission risks.

The **MALE UAV Aero Piston Engine Digital Twin Framework** provides a real-time, physics-informed, AI-powered health monitoring and predictive maintenance ecosystem. It models thermodynamic engine behavior, processes high-frequency engine sensor telemetry through standardized CAN bus protocols, runs four synchronized machine learning inference models, attributes root causes using Explainable AI (SHAP & Counterfactual Sensitivity), and streams live mission health metrics to Ground Control Station (GCS) dashboards while archiving complete mission trajectories to MongoDB Atlas.

---

## 📚 Canonical Documentation Index

All project documentation, benchmarks, security policies, and technical roadmaps are consolidated in the [`docs/`](docs/) directory:

- **[Security Architecture & Policy](docs/SECURITY.md)**: 5-layer Defense-in-Depth security framework, inter-service authentication, and model SHA-256 fingerprinting.
- **[Edge AI Benchmarking Report](docs/EDGE_AI_BENCHMARK.md)**: Model artifact sizes (KB), CPU single-core latency (ms), and Onboard vs. GCS split architecture.
- **[Federated Learning (FedAvg) PoC](docs/FEDERATED_LEARNING.md)**: Multi-UAV fleet parameter weight averaging and zero telemetry sharing privacy proof.
- **[Technical Documentation](docs/TECHNICAL_DOCUMENTATION.txt)** ([Word .docx](docs/TECHNICAL_DOCUMENTATION.docx)): Full microservices topology and model specifications.
- **[Deployment Roadmap](docs/DEPLOYMENT_ROADMAP.txt)** ([Word .docx](docs/DEPLOYMENT_ROADMAP.docx)): Phased enterprise defense transition plan.

---

```
                                  +---------------------------------------+
                                  |    MALE UAV Aero Piston Engine        |
                                  |    (Propulsion & Sensor Telemetry)    |
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |     CAN Telemetry Layer (DBC Codec)   |
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |   Physics-Informed Feature Engine     |
                                  |   (Thermodynamic Residuals & Lags)    |
                                  +-------------------+-------------------+
                                                      |
                    +---------------------------------+---------------------------------+
                    |                                 |                                 |
                    v                                 v                                 v
+-----------------------+         +-----------------------+         +-----------------------+
|  Anomaly Detection    |         | Degradation & Faults  |         |   RUL Prediction &    |
|  (Isolation Forest)   |         | (XGBoost Classifier)  |         | Uncertainty Bounds    |
+-----------+-----------+         +-----------+-----------+         +-----------+-----------+
            |                                 |                                 |
            +---------------------------------+---------------------------------+
                                              |
                                              v
                                  +---------------------------------------+
                                  |     Explainable AI (XAI) Engine       |
                                  |     (TreeSHAP & Counterfactuals)      |
                                  +-------------------+-------------------+
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |     Central API Gateway Service       |
                                  |    (WebSocket & REST Hub: Port 8000)  |
                                  +---------+-------------------+---------+
                                            |                   |
                        +-------------------+                   +-------------------+
                        v                                                           v
+-----------------------------------------------+           +-----------------------------------------------+
|      Ground Control Station (GCS) UI          |           |         MongoDB Atlas Cloud Database          |
|      (Real-Time WebSocket Stream)             |           |   (Mission Telemetry, Advisories, Replay)     |
+-----------------------------------------------+           +-----------------------------------------------+
```

---

## 📑 Table of Contents

- [Key Highlights & Capabilities](#-key-highlights--capabilities)
- [System Architecture](#-system-architecture)
- [Microservices Ecosystem](#-microservices-ecosystem)
- [Machine Learning Models & Inference Pipeline](#-machine-learning-models--inference-pipeline)
- [Explainable AI (XAI) & Diagnostic Advisory Layer](#-explainable-ai-xai--diagnostic-advisory-layer)
- [CAN Bus Protocol & Telemetry Adapter Layer](#-can-bus-protocol--telemetry-adapter-layer)
- [Physics-Informed Feature Engineering](#-physics-informed-feature-engineering)
- [Database Schema & MongoDB Atlas Integration](#-database-schema--mongodb-atlas-integration)
- [Repository File Structure](#-repository-file-structure)
- [Installation & Setup Guide](#-installation--setup-guide)
- [Running the Platform](#-running-the-platform)
- [API Gateway & WebSocket Specification](#-api-gateway--websocket-specification)
- [Synthetic Fault Injection & What-If Simulation](#-synthetic-fault-injection--what-if-simulation)
- [Verification & Automated Testing](#-verification--automated-testing)
- [License & Acknowledgments](#-license--acknowledgments)

---

## 🌟 Key Highlights & Capabilities

- ⚡ **5-Tier Microservices Architecture**: Decoupled, scalable microservices orchestrating telemetry streaming, ML inference, explainability, persistence, and API gateway operations.
- 🔬 **Physics-Informed Thermodynamics**: Calculates dynamic residuals between real-time sensor observations and expected physical values ($CHT_{\text{residual}}$, $EGT_{\text{residual}}$, $RPM_{\text{residual}}$, Fuel/Air ratios, Thermal efficiency).
- 🧠 **Multi-Model AI/ML Diagnostics**:
  1. **Anomaly Detection**: Unsupervised Isolation Forest isolating multivariate operating outliers.
  2. **Degradation Estimation**: XGBoost Regressor tracking wear progression from $0.0$ to $1.0$ (Health: $100\% \to 0\%$).
  3. **Multiclass Fault Classification**: XGBoost Classifier categorizing specific failure modes (Overheating, Lubrication Breakdown, Injector Degradation, Misfire, Sensor Bias).
  4. **RUL Estimation**: XGBoost Regressor predicting Remaining Useful Life in flight hours with dynamic degradation lifecycle anchoring, EMA smoothing, and $90\%$ confidence bounds ($P_{10} - P_{90}$).
- 🔍 **Transparent Explainable AI (XAI)**:
  - Additive TreeSHAP value decomposition for tree-based models.
  - Counterfactual sensitivity analysis and normalized Z-score distance metrics for Isolation Forest anomalies.
  - Human-interpretable engineering narratives and actionable maintenance advisories.
- 📡 **CAN 2.0B Hardware Protocol Compliance**: Complete DBC specification (`engine_can.dbc`) encoding/decoding raw sensor signals to/from standard CAN frames.
- ☁️ **Mission Telemetry & Fleet History in MongoDB Atlas**: Automatic frame-by-frame logging, mission summaries, advisory history, and full historical mission trajectory playback.
- 🛠️ **Synthetic Fault Injection Engine**: Real-time what-if scenario testing (e.g. inject $+30^\circ\text{C}$ CHT rise or $-2.0\,\text{bar}$ oil pressure drop) to validate model diagnostics live.

---

## 🏗️ System Architecture

The framework is organized into five distributed microservices running over high-speed HTTP and WebSockets:

```mermaid
flowchart TD
    subgraph SENSORS_CAN ["CAN Hardware & Simulation Layer"]
        CSV[("Flight Telemetry Dataset\n(100k+ Records)")] --> SIM["Telemetry & Simulation Service\n(Port 8001)"]
        SIM --> DBC["CAN Codec & DBC Spec\n(engine_can.dbc)"]
        DBC --> CAN_BUS["Virtual / Hardware CAN Bus\n(ISO 11898)"]
        CAN_BUS --> DECODE["CAN Telemetry Adapter"]
    end

    subgraph FEATURES ["Feature Engineering Layer"]
        DECODE --> FE["DigitalTwinFeatureEngine\n(120-Frame Rolling Buffer)"]
        FE --> FV1["13-Feat Anomaly Vector"]
        FE --> FV2["120-Feat Degradation Vector"]
        FE --> FV3["55-Feat Fault Vector"]
        FE --> FV4["60-Feat RUL Vector"]
    end

    subgraph ML_SERVICE ["AI/ML Inference Microservice (Port 8002)"]
        FV1 --> M1["Model 1: Isolation Forest\n(Anomaly Detection)"]
        FV2 --> M2["Model 2: XGBoost Regressor\n(Degradation % Score)"]
        FV3 --> M3["Model 3: XGBoost Classifier\n(Multiclass Fault)"]
        FV4 --> M4["Model 4: XGBoost Regressor\n(RUL & Uncertainty Filter)"]
    end

    subgraph XAI_SERVICE ["XAI & Advisory Microservice (Port 8003)"]
        M1 & M2 & M3 & M4 --> XAI["DigitalTwinXAIEngine"]
        XAI --> SHAP["Additive TreeSHAP"]
        XAI --> SENS["Counterfactual Perturbation"]
        XAI --> MAP["FeatureMapper (Engineering Names)"]
        XAI --> ADV["Advisory State Tracker (Anti-Spam)"]
    end

    subgraph MONGO_SERVICE ["MongoDB Atlas Persistence (Port 8004)"]
        LOGS[("mission_telemetry_logs")]
        SUMM[("mission_summaries")]
        ADVH[("advisory_history")]
        FLEET[("engine_fleet_metadata")]
    end

    subgraph GATEWAY ["Central API Gateway Service (Port 8000)"]
        GW["FastAPI Central Gateway"]
        WS["WebSocket Stream (/ws/telemetry)"]
        REST["REST Endpoints & Mission Replay"]
    end

    SIM --> GW
    GW <--> ML_SERVICE
    GW <--> XAI_SERVICE
    GW <--> MONGO_SERVICE
    GW --> WS
    GW --> REST

    WS --> GCS["Ground Control Station Dashboard"]
    REST --> GCS
    MONGO_SERVICE --- LOGS & SUMM & ADVH & FLEET
```

---

## 🌐 Microservices Ecosystem

| Microservice | Default Port | Primary Responsibilities | Health Endpoint |
| :--- | :---: | :--- | :--- |
| **API Gateway Service** | `8000` | Central routing, CORS management, WebSocket telemetry streaming (`/ws/telemetry`), orchestrating ML/XAI pipelines, and proxying MongoDB queries. | `GET /api/health` |
| **Telemetry & Simulation Service** | `8001` | Ingests mission telemetry, executes physics reference models, manages playback states (`RUNNING`, `PAUSED`, `SEEK`, `SPEED`), and handles fault injection. | `GET /health` |
| **AI/ML Inference Service** | `8002` | Executes all 4 frozen machine learning models simultaneously, returning consolidated health statuses, probabilities, degradation indices, and RUL. | `GET /health` |
| **XAI & Advisory Service** | `8003` | Generates local SHAP feature attributions, counterfactual anomaly recovery scores, sensor-level impact rankings, and natural language maintenance advisories. | `GET /health` |
| **MongoDB Persistence Service** | `8004` | Connects directly to MongoDB Atlas cluster, performs indexed batch persistence of mission frames, advisories, fault logs, and supplies mission replay data. | `GET /health` |

---

## 🧠 Machine Learning Models & Inference Pipeline

All machine learning models operate as **frozen inference engines** to ensure zero runtime drift and deterministic execution during flight monitoring.

| Model | Target Metric | Algorithm | Input Shape | Primary Output Parameters |
| :--- | :--- | :--- | :---: | :--- |
| **Model 1: Anomaly Detection** | Operational Outliers | **Isolation Forest** + `StandardScaler` | $13$ Features | `anomaly_score`, `is_anomaly` (bool), `decision_function` |
| **Model 2: Degradation Estimation** | Engine Wear Index | **XGBoost Regressor** | $120$ Features | `degradation_index` ($0.0 - 1.0$), `estimated_health_pct` ($0\% - 100\%$) |
| **Model 3: Fault Classification** | Specific Failure Mode | **Multiclass XGBoost Classifier** + `LabelEncoder` | $55$ Features | `predicted_fault`, `confidence`, `fault_probabilities` |
| **Model 4: RUL Prediction** | Remaining Useful Life | **XGBoost Regressor** + Dynamic Post-Processing | $60$ Features | `predicted_rul_hours`, `rul_lower_bound_p10`, `rul_upper_bound_p90`, `uncertainty_std_hours` |

### RUL Post-Processing & Uncertainty Quantification

To eliminate sensor noise and produce physically realistic, monotonically decreasing flight hours, the RUL inference engine incorporates a robust post-processing pipeline:

1. **Failure-State Dynamic Physical Anchoring**:
   - If degradation reaches failure threshold ($\ge 0.98$), RUL is clamped directly to $0.0\,\text{hours}$.
   - For intermediate health states, raw ML output is dynamically blended with physical lifecycle targets:
     $$\text{RUL}_{\text{target}} = \left(\frac{\text{Health}\%}{100}\right) \times 50.0\,\text{hrs}$$
     $$\text{RUL}_{\text{anchored}} = 0.3 \times \text{RUL}_{\text{raw}} + 0.7 \times \text{RUL}_{\text{target}}$$
2. **Exponential Moving Average (EMA) Filtering**:
   - Low-pass smoothing ($\alpha = 0.12$) removes high-frequency fluctuations caused by transient throttle bursts.
3. **Slew-Rate Limiting**:
   - Caps rate of change per tick ($+0.5\,\text{h}$ max climb, $-2.0\,\text{h}$ max descent) preventing discontinuous jumps.
4. **Sub-Ensemble Boosting Round Variance Estimation ($90\%$ CI)**:
   - Evaluates predictions across 10 checkpoint sub-ensembles along the boosting tree sequence to estimate prediction variance ($\sigma$).
   - Calculates $90\%$ Confidence Intervals:
     $$\text{P10} = \max\left(0, \text{RUL} - 1.645 \cdot \sigma\right), \quad \text{P90} = \text{RUL} + 1.645 \cdot \sigma$$

---

## 🔍 Explainable AI (XAI) & Diagnostic Advisory Layer

Black-box predictions are unacceptable in aviation. The XAI layer translates multidimensional feature spaces into actionable engineering insights for pilots and maintenance crews.

```
                           +-------------------------------------+
                           |    Feature Attributions per Model   |
                           +------------------+------------------+
                                              |
             +--------------------------------+--------------------------------+
             |                                |                                |
             v                                v                                v
+--------------------------+     +--------------------------+     +--------------------------+
|  Model 1: Anomaly        |     |  Model 2 & 3: Wear/Fault |     |  Model 4: RUL            |
|  Counterfactual Recovery |     |  Additive TreeSHAP       |     |  TreeSHAP + Filters      |
|  & Z-Score Distance      |     |  (Log-Odds Attribution)  |     |  (Lifecycle Context)     |
+------------+-------------+     +------------+-------------+     +------------+-------------+
             |                                |                                |
             +--------------------------------+--------------------------------+
                                              |
                                              v
                           +-------------------------------------+
                           |   Intelligent Feature Mapper        |
                           |   (Signal Grouping & Plain English) |
                           +------------------+------------------+
                                              |
                                              v
                           +-------------------------------------+
                           |   Operational Maintenance Advisory  |
                           |   (State-Tracked Anti-Spam Alerts)  |
                           +-------------------------------------+
```

### Explanation Techniques by Model

1. **Isolation Forest Counterfactual Sensitivity**:
   - Evaluates the score recovery when feature $i$ is returned to nominal mean baseline ($\Delta \text{score}_i = f(X_{\text{nominal\_i}}) - f(X)$).
   - Identifies which physical parameters are actively pulling the engine into an anomalous state.
2. **TreeSHAP for Multiclass Fault Classification**:
   - Computes exact Shapley values on tree log-odds for the diagnosed fault class $C_{\text{pred}}$, showing which sensor drifts caused the fault classification.
3. **Dual-Source Degradation Attribution**:
   - Identifies whether wear is driven by thermal stress (high CHT/EGT), lubrication breakdown (oil pressure/temp), or mechanical friction (vibration RMS).
4. **Intelligent Feature Mapper (`FeatureMapper`)**:
   - Aggregates rolling statistics, lag terms, and derivatives into their parent physical sensors (e.g. `cht_C_rollmean30`, `cht_C_diff10`, and `cht_residual` $\to$ **Cylinder Head Temperature (CHT)**).

---

## 📡 CAN Bus Protocol & Telemetry Adapter Layer

The platform includes an **ISO 11898 CAN 2.0B compliance layer** (`can_layer/`) defining bit-level signal packings in `can_layer/engine_can.dbc`.

### Standardized CAN Messages

| CAN ID (Hex) | Message Name | DLC (Bytes) | Transmitted Signals |
| :---: | :--- | :---: | :--- |
| `0x100` | `ENGINE_CORE_DYNAMICS` | 8 | Engine RPM, Throttle Position (%), Engine Load (%) |
| `0x101` | `ENGINE_THERMAL_STATUS` | 8 | Cylinder Head Temp (CHT), Exhaust Gas Temp (EGT), Oil Temp, Oil Pressure |
| `0x102` | `FUEL_AND_AIRFLOW` | 8 | Air Mass Flow Rate ($\text{kg/s}$), Fuel Flow Rate ($\text{kg/s}$) |
| `0x103` | `MECHANICAL_AND_ELECTRICAL` | 8 | Engine Torque ($\text{Nm}$), Power ($\text{W}$), Vibration RMS, Battery Voltage ($\text{V}$) |
| `0x104` | `ELECTRICAL_AND_IGNITION` | 8 | Alternator Current ($\text{A}$), Alternator Health, Injection Timing ($^\circ$) |
| `0x105` | `FLIGHT_ENVIRONMENT` | 8 | Altitude ($\text{m}$), Ambient Temp ($^\circ\text{C}$), Atmospheric Pressure ($\text{kPa}$), Air Density |

The `CANTelemetryAdapter` in `backend/can_adapter.py` acts as a bi-directional transceiver:
$$\text{Raw Telemetry} \xrightarrow{\text{Encode}} \text{CAN Frames} \xrightarrow{\text{Transmit}} \text{CAN Bus (Virtual/Hardware)} \xrightarrow{\text{Receive}} \text{CAN Frames} \xrightarrow{\text{Decode}} \text{Normalized Signals}$$

---

## ⚙️ Physics-Informed Feature Engineering

The `DigitalTwinFeatureEngine` maintains a rolling temporal window (120 frames) to compute physical residuals and thermodynamic correlations:

### 1. Thermodynamic Reference Calculations
- **Expected Cylinder Head Temp ($CHT_{\text{exp}}$)**: Baseline thermal response mapped to throttle, load, and ambient temperature.
- **Expected Exhaust Gas Temp ($EGT_{\text{exp}}$)**: Combustion heat profile baseline.
- **Physics Residuals**:
  $$\Delta CHT = CHT_{\text{measured}} - CHT_{\text{exp}}$$
  $$\Delta EGT = EGT_{\text{measured}} - EGT_{\text{exp}}$$
  $$\Delta RPM = RPM_{\text{measured}} - RPM_{\text{exp}}$$

### 2. Dimensionless Thermodynamic Ratios
- **Fuel-to-Air Ratio**: $\Phi = \frac{\dot{m}_{\text{fuel}}}{\dot{m}_{\text{air}} + \epsilon}$
- **Specific Energy Conversion**: $\eta_{\text{thermal}} = \frac{P_{\text{mech}}}{\dot{m}_{\text{fuel}} + \epsilon}$
- **Specific Torque Efficiency**: $\tau_{\text{rpm}} = \frac{\tau}{\text{RPM} + \epsilon}$

### 3. Dynamic Time-Series Lags & Moving Statistics
- **Differencing**: 1-step, 5-step, and 10-step delta gradients.
- **Rolling Windows**: 5, 15, and 30-frame rolling means and standard deviations.
- **RUL Multi-Lag Histories**: 1, 3, 6, 12-step lagged snapshots and historical trend slopes over elapsed hours.

---

## 🗄️ Database Schema & MongoDB Atlas Integration

The system persists telemetry and diagnostics in real time to **MongoDB Atlas** (`aero_digital_twin_db`) via `services/mongodb_service/`.

```
aero_digital_twin_db
 ├── mission_telemetry_logs    (Frame-by-frame sensor telemetry, residuals, ML predictions, XAI drivers)
 ├── mission_summaries         (Flight duration, peak thermal loads, min oil pressure, health trajectories)
 ├── advisory_history          (Logged alerts, severity levels, recommended maintenance actions)
 ├── fault_injection_logs      (Injected parameter overrides, detected fault classifications)
 └── engine_fleet_metadata     (Engine serial numbers, UAV tail numbers, total operating hours, airworthiness)
```

### Indexed Collections

1. **`mission_telemetry_logs`**:
   - Compound index on `(mission_id: 1, frame_index: 1)` enables instant sub-millisecond retrieval for **Mission Replay**.
   - Descending index on `(timestamp: -1)`.
2. **`mission_summaries`**:
   - Unique index on `(mission_id: 1)`.
3. **`advisory_history`**:
   - Indexed on `(timestamp: -1)` and `(mission_id: 1)`.
4. **`engine_fleet_metadata`**:
   - Unique index on `(engine_serial_number: 1)` storing airworthiness status and depot maintenance intervals.

---

## 📂 Repository File Structure

```text
SIH-26/
├── backend/                                # Core Engine Logic & Microservices Adapters
│   ├── __init__.py
│   ├── can_adapter.py                     # CAN Bus Hardware/Virtual Gateway Adapter
│   ├── config.py                          # Global File Paths, Defaults & Thresholds
│   ├── feature_engine.py                  # Physics Residuals & 120-Feature Rolling Engine
│   ├── model_loader.py                    # Unified 4-Model Manager & Temporal Filtering
│   ├── simulation_engine.py               # Flight Simulation & Replay Engine
│   └── verify_microservices.py            # End-to-End Microservices Test Suite
│
├── can_layer/                              # CAN Bus Hardware Interface Layer
│   ├── bus.py                             # python-can Bus Provider (Virtual / SocketCAN)
│   ├── can_codec.py                       # DBC Frame Encoder and Decoder
│   ├── can_pipeline.py                    # Standalone CAN Test & Replay Utility
│   ├── dbc.py                             # DBC Parser Loader
│   ├── engine_can.dbc                     # ISO 11898 CAN Message & Signal Definition
│   ├── sample_engine_sensor_input.csv     # Sample Telemetry for CAN Validation
│   ├── sensor_simulator.py                # Simulated ECU Sensor Transmitter
│   └── README.md                          # Detailed CAN Subsystem Documentation
│
├── data/                                   # Datasets & Flight Logs
│   ├── MALE_UAV_aero_piston_engine_final_100k.csv  # 100k Multi-Mission Flight Dataset
│   ├── demo_synthetic_flight_test.csv     # Out-of-Sample Mission 999 Test Set
│   └── degradation_data/                  # Engine Degradation Calibration Logs
│
├── explainability/                         # Explainable AI (XAI) Diagnostic Layer
│   ├── __init__.py
│   ├── anomaly_explainer.py               # Counterfactual & Z-Score Anomaly Analyzer
│   ├── confidence.py                      # Uncertainty & Confidence Metric Computations
│   ├── feature_mapper.py                  # Sensor Grouping & Technical Name Mapper
│   ├── shap_explainer.py                  # TreeSHAP for Fault, Degradation & RUL Models
│   ├── xai_engine.py                      # Central Multi-Model XAI Orchestrator
│   └── README.md                          # Comprehensive XAI Mathematical Reference
│
├── models/                                 # Trained & Frozen AI/ML Model Artifacts
│   ├── anomaly_detection/
│   │   ├── isolation_forest_model.pkl     # Isolation Forest Estimator
│   │   └── scaler.pkl                     # 13-Feature StandardScaler
│   ├── degradation_detection/
│   │   ├── xgb_degradation_model.json     # XGBoost Regressor (120 Features)
│   │   ├── feature_columns.json           # Expected Feature Column Ordering
│   │   └── README.md
│   ├── fault_detection/
│   │   ├── fault_detection_multiclass_xgb.json # Multiclass XGBoost Classifier
│   │   ├── fault_detection_label_encoder.pkl   # Fault Class LabelEncoder
│   │   └── fault_detection_multiclass_feature_cols.json
│   └── rul_prediction/
│       ├── xgboost_rul_model.json         # XGBoost RUL Regressor (60 Features)
│       └── xgboost_rul_features.txt       # RUL Feature Specification List
│
├── services/                               # 5-Tier Microservices Architecture
│   ├── api_gateway/
│   │   └── main.py                        # Central Gateway, WebSocket Proxy (Port 8000)
│   ├── telemetry_service/
│   │   └── main.py                        # Simulation & Telemetry Service (Port 8001)
│   ├── ml_inference_service/
│   │   └── main.py                        # AI/ML Inference Microservice (Port 8002)
│   ├── xai_service/
│   │   └── main.py                        # XAI & Maintenance Advisory Service (Port 8003)
│   ├── mongodb_service/
│   │   └── main.py                        # MongoDB Atlas Persistence Service (Port 8004)
│   └── run_all_services.py                # Automated Multi-Service Supervisor & Process Manager
│
├── .env.example                            # Template for MongoDB Atlas Credentials
├── .gitignore                              # Git Ignore Configuration
├── requirements.txt                        # Production Python Dependencies
└── README.md                               # Master Project Documentation
```

---

## 📥 Installation & Setup Guide

### 1. Prerequisites
- **Python**: Version `3.10` or higher (tested on `3.10` and `3.11`).
- **MongoDB Atlas**: An active MongoDB Atlas cluster URI (free tier M0 or higher).
- **Operating System**: Windows 10/11, Ubuntu 20.04+, or macOS.

### 2. Clone the Repository
```bash
git clone https://github.com/VIKASHL25/SIH-26.git
cd SIH-26
```

### 3. Create & Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Copy `.env.example` to `.env` and configure your MongoDB Atlas connection string:
```bash
# Windows (PowerShell)
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

Edit `.env`:
```ini
MONGO_URL=mongodb+srv://<username>:<password>@your-cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=aero_digital_twin_db
```

---

## 🚀 Running the Platform

### Single-Command Multi-Service Launcher (Recommended)
Launch all 5 microservices concurrently with automatic port conflict resolution:

```bash
python services/run_all_services.py
```

```text
================================================================================
  STARTING MALE UAV DIGITAL TWIN FULL MICROSERVICES ARCHITECTURE
================================================================================
[LAUNCH] Launching Telemetry & Simulation Service on Port 8001...
[LAUNCH] Launching AI/ML Inference Service on Port 8002...
[LAUNCH] Launching XAI & Advisory Service on Port 8003...
[LAUNCH] Launching MongoDB Atlas Persistence Service on Port 8004...
[LAUNCH] Launching API Gateway Service on Port 8000...
================================================================================
ALL 5 MICROSERVICES ONLINE AND READY!
API Gateway URL:      http://localhost:8000
WebSocket Stream:     ws://localhost:8000/ws/telemetry
MongoDB Replay API:   http://localhost:8000/api/db/mission/999/replay
Press Ctrl+C to terminate all microservices.
================================================================================
```

### Manual Individual Microservice Launch
To run services individually in dedicated terminal tabs:

```bash
# Terminal 1: Telemetry & Simulation Service
uvicorn services.telemetry_service.main:app --port 8001 --reload

# Terminal 2: AI/ML Inference Service
uvicorn services.ml_inference_service.main:app --port 8002 --reload

# Terminal 3: XAI & Advisory Service
uvicorn services.xai_service.main:app --port 8003 --reload

# Terminal 4: MongoDB Atlas Persistence Service
uvicorn services.mongodb_service.main:app --port 8004 --reload

# Terminal 5: API Gateway Service
uvicorn services.api_gateway.main:app --port 8000 --reload
```

---

## 📡 API Gateway & WebSocket Specification

The API Gateway runs on **Port 8000** and serves as the unified interface for the frontend Ground Control Station.

### Interactive API Documentation
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Key REST Endpoints

| Category | Method | Endpoint | Request Body | Description |
| :--- | :---: | :--- | :--- | :--- |
| **System** | `GET` | `/` | — | Microservice service directory & versions. |
| **Health** | `GET` | `/api/health` | — | Full cluster health check across all 5 nodes. |
| **Missions** | `GET` | `/api/missions` | — | List all available recorded mission IDs. |
| **Simulation** | `POST` | `/api/simulation/load_mission` | `{"mission_id": 999}` | Loads mission dataset and resets filters. |
| **Simulation** | `POST` | `/api/simulation/start` | — | Starts continuous real-time mission playback. |
| **Simulation** | `POST` | `/api/simulation/pause` | — | Pauses mission playback. |
| **Simulation** | `POST` | `/api/simulation/step` | — | Steps simulation by 1 frame and returns full diagnostics. |
| **Simulation** | `POST` | `/api/simulation/speed` | `{"speed": 2.0}` | Updates simulation speed multiplier ($0.1\times - 100\times$). |
| **Simulation** | `POST` | `/api/simulation/seek` | `{"frame_idx": 450}` | Jumps playback to specific mission frame. |
| **Fault Injection** | `POST` | `/api/simulation/inject_fault` | `{"overrides": {"cht_C": 40.0}}` | Injects synthetic parameter perturbations. |
| **Fault Injection** | `POST` | `/api/simulation/clear_faults` | — | Restores nominal sensor parameters. |
| **MongoDB** | `GET` | `/api/db/saved_missions` | — | Returns list of mission IDs logged in Atlas. |
| **MongoDB** | `GET` | `/api/db/mission/{id}/replay` | — | Fetches complete recorded mission trajectory. |
| **MongoDB** | `GET` | `/api/db/advisories` | `?mission_id=999` | Retrieves logged maintenance advisories. |
| **MongoDB** | `GET` | `/api/db/fleet_metadata` | — | Retrieves UAV tail numbers & flight hours. |

### WebSocket Real-Time Stream

- **URL**: `ws://localhost:8000/ws/telemetry`
- **Streaming Rate**: Dynamically governed by `playback_speed` (Default: $1\,\text{Hz}$).

#### WebSocket Frame Payload Schema
```json
{
  "timestamp_s": 1420,
  "frame_index": 142,
  "total_frames": 2500,
  "mission_id": 999,
  "mission_type": "ISR_Surveillance",
  "playback_state": "RUNNING",
  "playback_speed": 1.0,
  "health_status": "NOMINAL",
  "telemetry": {
    "rpm": 2340.0,
    "throttle_pct": 72.5,
    "load_pct": 68.0,
    "cht_C": 138.2,
    "egt_C": 674.5,
    "oil_temperature_C": 86.4,
    "oil_pressure_bar": 4.45,
    "vibration_rms": 0.16,
    "fuel_flow_kg_s": 0.0051,
    "air_mass_flow_kg_s": 0.082,
    "battery_voltage_V": 28.1,
    "alternator_current_A": 24.8,
    "altitude_m": 3200.0,
    "ambient_temp_C": 8.5
  },
  "physics_model": {
    "expected_rpm": 2340.0,
    "expected_cht_C": 137.0,
    "expected_egt_C": 672.0,
    "cht_residual_C": 1.2,
    "egt_residual_C": 2.5,
    "fuel_air_ratio": 0.0622
  },
  "anomaly_detection": {
    "is_anomaly": false,
    "anomaly_score": -0.142,
    "decision_function": 0.142
  },
  "degradation_estimation": {
    "degradation_index": 0.062,
    "estimated_health_pct": 93.8
  },
  "fault_classification": {
    "predicted_fault": "normal",
    "confidence": 0.9842,
    "fault_probabilities": {
      "normal": 0.9842,
      "overheating": 0.0081,
      "lubrication_degradation": 0.0042,
      "injector_degradation": 0.0021,
      "sensor_fault": 0.0014
    }
  },
  "rul_prediction": {
    "status": "PREDICTED",
    "predicted_rul_hours": 46.85,
    "raw_rul_hours": 47.10,
    "rul_lower_bound_p10": 43.12,
    "rul_upper_bound_p90": 50.58,
    "uncertainty_std_hours": 2.27,
    "confidence_level": "HIGH"
  },
  "xai": {
    "top_diagnostic_drivers": [
      {
        "sensor": "Cylinder Head Temperature (CHT)",
        "impact": "NOMINAL",
        "attribution_score": 0.012
      }
    ]
  },
  "advisories": [
    "Propulsion health is nominal. All thermodynamic parameters within green envelope."
  ]
}
```

---

## 🧪 Synthetic Fault Injection & What-If Simulation

The platform supports live synthetic fault injection to test how the digital twin responds to sudden component degradation:

```bash
# Inject Overheating Fault (+45 deg C CHT rise)
curl -X POST http://localhost:8000/api/simulation/inject_fault \
     -H "Content-Type: application/json" \
     -d '{"overrides": {"cht_C": 45.0}}'

# Inject Lubrication Loss (-2.5 bar Oil Pressure drop & +25 deg C Oil Temp rise)
curl -X POST http://localhost:8000/api/simulation/inject_fault \
     -H "Content-Type: application/json" \
     -d '{"overrides": {"oil_pressure_bar": -2.5, "oil_temperature_C": 25.0}}'

# Clear Fault Overrides
curl -X POST http://localhost:8000/api/simulation/clear_faults
```

---

## 🛡️ Verification & Automated Testing

An automated end-to-end verification script tests all 5 microservices, simulation streaming, fault injection, and MongoDB Atlas persistence:

```bash
# Ensure services are running, then execute:
python backend/verify_microservices.py
```

### Test Output
```text
=================================================================
STARTING FULL END-TO-END MICROSERVICES & MONGODB VERIFICATION
=================================================================
Test 1: Checking All 5 Microservices Health Endpoints...
[SUCCESS] Telemetry Service Online: HEALTHY
[SUCCESS] ML Inference Service Online: True
[SUCCESS] XAI Advisory Service Online: HEALTHY
[SUCCESS] MongoDB Atlas Service Online: True
[SUCCESS] API Gateway Service Online: HEALTHY
Test 2: Loading Out-of-Sample Demo Mission 999 via API Gateway...
[SUCCESS] Load Mission Response: Successfully loaded Mission 999
Test 3: Stepping simulation & logging frames to MongoDB Atlas...
[SUCCESS] 10 Steps executed cleanly with automatic MongoDB Atlas frame logging!
Test 4: Testing MongoDB Atlas Mission Replay API...
[SUCCESS] Mission Replay Data Retrieved: 10 frames persisted in MongoDB Atlas!
Test 5: Testing synthetic fault injection via Gateway...
[SUCCESS] Fault Injection Health Status: FAULT DETECTED (OVERHEATING)
[SUCCESS] Synthetic fault cleared successfully!
Test 6: Checking MongoDB Atlas Advisory History Retrieval...
[SUCCESS] Retrieved 10 advisories from MongoDB Atlas advisory_history collection!
=================================================================
ALL 5 MICROSERVICES & MONGODB ATLAS END-TO-END TESTS PASSED CLEANLY!
=================================================================
```

---

## 👥 Contributors & Acknowledgments

Developed for the **Smart India Hackathon (SIH 2026)** — Problem Statement **SIH-26**.

- **Team**: Aero Digital Twin Research & Development Team
- **Target Platform**: MALE UAV (Medium-Altitude Long-Endurance) Piston Aero Propulsion Systems (e.g., TAPAS-BH-201)
- **Tech Stack**: Python 3.10+, FastAPI, XGBoost, SHAP, scikit-learn, python-can, cantools, MongoDB Atlas, Motor, WebSockets

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
