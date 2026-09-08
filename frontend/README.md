# MALE UAV Aero Piston Engine Digital Twin — Ground Control Station (GCS) Frontend

**Smart India Hackathon 2026 | DRDO Problem Statement 26054**  
*"AI-Enabled Real-Time Digital Twin System for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs"*

This frontend is a defence-grade Ground Control Station (GCS) web application built with **React + TypeScript + Vite + Tailwind CSS**, consuming the API Gateway REST and WebSocket interfaces.

For the verified live demo, Simulink replays recorded mission CSV telemetry at
one sample per second. The dashboard is not connected to a physical engine.
Live Simulink missions are `1`–`100`; Mission `999` is historical-only.

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
   - **Mission Simulation Controls**: Prepare a live Simulink mission (`1`–`100`), keep the dashboard paused until `STREAM LIVE` is clicked, pause/stop the current run, and select the playback speed. Keep speed at `1x` for synchronized Simulink streaming.
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

### Step 1: Start the UDP→CAN bridge and backend

MATLAB/Simulink must be installed and `matlab` must be available on `PATH`.
The bridge must be running before starting a live mission:

```powershell
# From the repository root
python simulink\udp_can_bridge.py
python services\run_all_services.py
```

The live path is `CSV → Simulink → UDP → UDP→CAN → CAN multicast →
CANInputReceiver → backend ML/XAI/RUL → API Gateway → WebSocket`.
Selecting a mission only prepares it and leaves the dashboard `PAUSED`; click
`STREAM LIVE` to start MATLAB/Simulink for the selected mission. PAUSE currently
terminates MATLAB/Simulink rather than preserving exact simulation time for a
later resume.

### Step 2: Install and Launch Frontend

```powershell
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

The GCS dashboard will be available at:
`http://127.0.0.1:5173/`

Vite is pre-configured to proxy `/api` calls to `http://localhost:8000` and `/ws` WebSocket traffic to `ws://localhost:8000`.

### Production build

```powershell
npm run build
```

The verified build uses the declared dependencies in `package-lock.json`; no
dependency version changes are required for the live integration.

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
