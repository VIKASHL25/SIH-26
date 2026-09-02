# MALE UAV Aero Piston Engine Digital Twin — Ground Control Station (GCS) Frontend

**Smart India Hackathon 2026 | DRDO Problem Statement 26054**  
*"AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs"*

This frontend is a defence-grade Ground Control Station (GCS) web application built with **React 18 + TypeScript + Vite + Tailwind CSS**, consuming the 5-microservice FastAPI backend architecture.

---

## Key Features

1. **Live Mission Dashboard (`/`)**
   - **Top Status Bar**: Live UTC/mission clocks, frame counter, active mission selector, WebSocket live stream indicator with auto-reconnect, and color-coded health badge (`NOMINAL` / `WARNING` / `CRITICAL FAULT`).
   - **Real-Time Sensor Telemetry Matrix (12 Channels)**: RPM, Cylinder Head Temperature (CHT), Exhaust Gas Temperature (EGT), Oil Pressure & Temperature, Fuel Flow, Vibration RMS, Battery Bus Voltage, Alternator Current, Altitude, Ambient Temp, and Throttle Position. Each gauge features configurable nominal/warning/critical bands and rolling mini sparklines.
   - **Physics-Informed Digital Twin Tracking**: Multi-series rolling chart comparing measured CHT, EGT, and RPM against expected thermodynamic baseline curves, alongside real-time residual deltas.
   - **4 AI/ML Predictive Health Models**:
     - *Degradation Estimation (XGBoost Regressor)*: Real-time engine health index (0–100%) and degradation index.
     - *Remaining Useful Life (XGBoost Regressor)*: Predicted operational hours with P10–P90 90% confidence bounds and uncertainty intervals.
     - *Anomaly Detection (Isolation Forest)*: Continuous multi-sensor deviation envelope monitoring and decision function tracking.
     - *Fault Classification (Multiclass XGBoost)*: Real-time classification (`normal`, `overheating`, `lubrication_degradation`, `injector_degradation`, `sensor_fault`) with confidence percentages and horizontal probability distribution bars.
   - **Explainable AI (XAI) & SHAP Diagnostic Drivers**: Ranked horizontal impact bars showing sensor attributions, directional influence, natural-language engineering assessment, and autonomous maintenance actions.
   - **Real-Time Advisory Feed**: Deduplicated, severity-colored alert feed with filter controls.
   - **Mission Simulation Controls**: Load mission dataset (e.g. Mission #999 Out-of-Sample Demo), Play, Pause, Step 1 frame, Speed selector (0.25x–10x), and Timeline Scrubber.
   - **Synthetic Fault Injection & "What-If" Analysis**: Quick presets (Thermal Overheating, Lubrication Loss, Vibration Spike, Lean Mixture) and custom parameter delta injection with active override badges and one-click clear.

2. **Mission Replay & Post-Flight Analysis (`/replay`)**
   - Load recorded flight trajectories directly from MongoDB Atlas (`/api/db/saved_missions` and `/api/db/mission/{id}/replay`).
   - Scrubbable mission timeline with play, pause, rewind, and speed controls.
   - Post-flight mission summary KPIs (Total duration, Peak CHT, Peak EGT, Min Oil Pressure, Health Delta, Total Anomalies Detected).
   - Synchronized snapshot gauges and trajectory profile chart with scrub cursor.
   - Mission advisory history table with severity, health indices, and recommended depot actions.

3. **Fleet & Depot Maintenance Overview (`/fleet`)**
   - Fleet propulsion asset table from MongoDB Atlas (`/api/db/fleet_metadata`) tracking tail numbers (`TAPAS-BH-201`), operating hours, mission counts, health indices, overhaul dates, and airworthiness status.
   - 5-microservice live health monitoring strip (API Gateway, Telemetry Service, AI/ML Inference, XAI Advisory, MongoDB Atlas) with ping latency indicators.
   - **Edge AI Benchmark Card** (`/api/analytics/edge_benchmark`): Onboard edge flight computer vs GCS latency split, confirming sub-100ms real-time SLA compliance (57.7ms total).
   - **Fleet Federated Learning Card** (`/api/analytics/federated_learning`): FedAvg fleet aggregation metrics, defense-grade zero telemetry egress, and 99.7% accuracy retention.

4. **Scenario & Environmental Simulator (`/scenario`)**
   - Simulate engine thermodynamic behavior under extreme operational conditions:
     - High Altitude ISR loiter (reduced cooling density, manifold stress)
     - Desert / Hot Weather operation (compressed cooling margins)
     - Rapid Tactical Throttle Maneuvers (thermal transients)
   - Interactive sliders for altitude (0–6000m), ambient temperature (-30°C to +55°C), and duration steps.

---

## Quick Start Guide

### Step 1: Start the Backend Microservices
Ensure the backend Python virtual environment is activated and launch all 5 microservices:

```powershell
# From the repository root (C:\Users\harsh\Desktop\SIH-26)
python services/run_all_services.py
```

This starts:
- Port 8000: API Gateway Service (`http://localhost:8000`)
- Port 8001: Telemetry & Simulation Service
- Port 8002: AI/ML Inference Service
- Port 8003: XAI & Advisory Service
- Port 8004: MongoDB Atlas Persistence Service

### Step 2: Install and Launch Frontend

```powershell
cd frontend
npm install
npm run dev
```

The GCS dashboard will be available at:
`http://localhost:5173`

Vite is pre-configured to proxy `/api` calls to `http://localhost:8000` and `/ws` WebSocket traffic to `ws://localhost:8000`.

---

## Build for Production

```powershell
cd frontend
npm run build
```

This compiles TypeScript and generates the production bundle in `dist/`. You can preview the production build using:

```powershell
npm run preview
```
