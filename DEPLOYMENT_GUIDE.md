# MALE UAV Aero Piston Engine Digital Twin — Deployment & Microservices Guide

This document provides complete instructions for deploying the **MALE UAV Aero Piston Engine Digital Twin** application, explaining the microservices architecture, how to run without MATLAB using **CSV Telemetry Replay Mode**, how to deploy with **Docker Compose**, and handoff instructions for running with **MATLAB / Simulink**.

---

## 🛠️ Architecture Overview

The system is designed as a distributed, decoupled 5-Microservice backend architecture with a React 3D WebGL Ground Control Station (GCS) Dashboard:

```
                  ┌────────────────────────────────────────┐
                  │   React 3D GCS Dashboard (Port 3000)   │
                  └───────────────────┬────────────────────┘
                                      │ REST API / WebSockets
                                      ▼
                  ┌────────────────────────────────────────┐
                  │       API Gateway (Port 8000)          │
                  └───────┬───────────┬───────────┬────────┘
                          │           │           │
          ┌───────────────┘           │           └──────────────┐
          ▼                           ▼                          ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│ Telemetry & Sim  │        │  ML Inference    │        │  XAI & Advisory  │
│ Service (8001)   │        │  Service (8002)  │        │  Service (8003)  │
└─────────┬────────┘        └──────────────────┘        └──────────────────┘
          │                                                       │
          └───────────────────────────┬───────────────────────────┘
                                      ▼
                            ┌──────────────────┐
                            │ MongoDB Atlas DB │
                            │ Service (8004)   │
                            └──────────────────┘
```

---

## 📊 MATLAB vs. CSV Telemetry Ingestion Modes

The system natively supports two input modes for stream ingestion, controlled by the `TELEMETRY_INPUT_MODE` environment variable:

### 1. CSV Telemetry Replay Mode (`TELEMETRY_INPUT_MODE=csv`) — **Default**
- **Requirements**: No MATLAB/Simulink required!
- **How it works**: Uses `CANTelemetryAdapter(backend="virtual")` to stream real aero piston engine flight telemetry datasets directly from CSV files through virtual CAN into the 4 AI/ML models, thermodynamic physics engine, XAI engine, and MongoDB Atlas persistence layer.
- **Ideal for**: Docker containers, cloud deployments, development on machines without MATLAB.

### 2. MATLAB / Simulink Live Replay Mode (`TELEMETRY_INPUT_MODE=simulink`)
- **Requirements**: MATLAB / Simulink installed with `matlab` added to system PATH.
- **How it works**: Spawns `simulink/run_mission.m`, streaming real-time CAN-FD telemetry frames over UDP multicast (`ff15:7079:7468:6f6e:6465:6d6f:6d63:6173`) into `CANInputReceiver`.
- **Ideal for**: Hardware-in-the-Loop (HIL) testing and local Simulink simulation on your friend's machine.

---

## 🐳 Docker Deployment (One-Command Launch)

You can launch the entire 6-container microservice stack (Frontend + 5 Microservices) with a single command:

### Prerequisites:
- Docker Desktop or Docker Engine installed (`docker --version`)
- Docker Compose installed (`docker-compose --version`)

### Step 1: Build & Start Containers
```bash
docker-compose up --build -d
```

### Step 2: Verify Running Containers
```bash
docker-compose ps
```
You should see all 6 services online and healthy:
- `uav_frontend_dashboard` (Port 3000)
- `uav_api_gateway` (Port 8000)
- `uav_telemetry_service` (Port 8001)
- `uav_ml_inference_service` (Port 8002)
- `uav_xai_service` (Port 8003)
- `uav_mongodb_service` (Port 8004)

### Step 3: Access GCS Dashboard
Open your browser and navigate to:
- **GCS 3D Dashboard**: [http://localhost:3000](http://localhost:3000)
- **API Gateway Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **API Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

### Step 4: Stop Containers
```bash
docker-compose down
```

---

## 💻 Local Development Launch (Without Docker)

If you prefer running services directly via Python:

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### Step 2: Start All 5 Microservices
```bash
python services/run_all_services.py
```

### Step 3: Start Frontend Dev Server
Open a new terminal window:
```bash
cd frontend
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🤝 Handoff Instructions for your Friend (MATLAB / Simulink Setup)

When your friend pulls this repository to run with **MATLAB / Simulink**:

1. **Ensure MATLAB is installed** and available in system PATH (`matlab -version`).
2. **Update `.env`**:
   Set:
   ```env
   TELEMETRY_INPUT_MODE=simulink
   ```
3. **Start the Microservices**:
   Run `python services/run_all_services.py` or `docker-compose up --build`.
4. **Trigger Simulink Replay**:
   When selecting a mission in the GCS Dashboard, `SimulinkController` will automatically launch MATLAB asynchronously (`simulink/run_mission.m`) and stream CAN telemetry over UDP multicast.

---

## 📜 Port & Environment Variable Reference

| Service | Port | Endpoint | Description |
|---|---|---|---|
| **Frontend** | `3000` | `/` | React + Three.js 3D Aero Piston Engine GCS Dashboard |
| **API Gateway** | `8000` | `/api/health` | Central REST Gateway & WebSocket Broadcaster |
| **Telemetry Service** | `8001` | `/health` | Mission playback, CAN virtual/UDP adapter & physics engine |
| **ML Inference Service** | `8002` | `/health` | Anomaly, Degradation, Fault Classification & RUL ML Models |
| **XAI Advisory Service** | `8003` | `/health` | SHAP attribution & Maintenance Advisory engine |
| **MongoDB Service** | `8004` | `/health` | Mission logs, telemetry summaries & fleet metadata persistence |

---
