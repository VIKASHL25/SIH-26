# 🚀 MATLAB / Simulink Digital Twin Engine Integration Guide

This guide explains how to generate, simulate, and link the **MALE UAV Aero Piston Engine Simulink Model** (`AeroPistonEngine_DigitalTwin.slx`) directly with our live **Ground Control Station (GCS) Dashboard** and **AI/ML Microservices Ecosystem**.

> Current live-demo path: Simulink replays recorded mission CSV telemetry as
> a real-time source. Use `simulink/simulink_udp_poc.slx` and
> `simulink/run_mission.m`, not the legacy generated continuous plant described
> below. The current path is `CSV → Simulink → UDP 127.0.0.1:5005 → UDP→CAN
> bridge → CAN-FD multicast → CANInputReceiver → backend ML/XAI/RUL → API
> Gateway → WebSocket → dashboard`. It is not physical-engine telemetry.

## Current live replay procedure

1. Start `python simulink\udp_can_bridge.py`.
2. Start `python services\run_all_services.py`.
3. Start the frontend with `cd frontend; npm ci; npm run dev -- --host 127.0.0.1`.
4. Open `http://127.0.0.1:5173/`, select Mission `1`–`100`, and confirm the
   dashboard remains `PAUSED`.
5. Click `STREAM LIVE` to start the selected Simulink mission. Mission `999`
   is historical-only and is not a live Simulink selection.

Simulink uses a 1-second fixed step so each CSV row produces one simulation
sample and one UDP packet. Keep dashboard playback speed at `1x`. PAUSE
currently terminates MATLAB/Simulink rather than preserving exact simulation
time for resume.

---

## 📂 Available Simulink Files

| File | Purpose | Location |
| :--- | :--- | :--- |
| **`build_engine_simulink_model.m`** | Programmatically builds the complete `.slx` model with blocks, integrators & wiring. | [`scripts/build_engine_simulink_model.m`](../scripts/build_engine_simulink_model.m) |
| **`simulink_bridge.py`** | Live co-simulation bridge streaming Simulink states to API Gateway & GCS. | [`scripts/simulink_bridge.py`](../scripts/simulink_bridge.py) |
| **`engine_architecture_diagram.svg`** | Reference schematic block diagram showing all gates, switches & transfer functions. | [`docs/engine_architecture_diagram.svg`](engine_architecture_diagram.svg) |
| **`ENGINE_ARCHITECTURE.md`** | Comprehensive mathematical equations & state transfer specifications. | [`docs/ENGINE_ARCHITECTURE.md`](ENGINE_ARCHITECTURE.md) |

---

## 🛠️ Step 1: Generate the Simulink Model (`.slx`) in MATLAB

1. Open **MATLAB** (R2021a or newer recommended).
2. Set the current MATLAB folder to the repository root:
   ```matlab
   cd 'c:/Users/bhara/OneDrive/Desktop/SIH-26'
   ```
3. Run the automated generation script:
   ```matlab
   build_engine_simulink_model
   ```
4. MATLAB will instantly generate and open **`AeroPistonEngine_DigitalTwin.slx`** containing:
   - **Fuel & Air Intake Subsystem**: `ConstStoich`, `Saturation`, `Sum`, `FcnAirFuel`, `SwitchAirGate` ($u > 0.5$), `GainLambda`.
   - **Combustion Heat Core**: LHV heat release function with saturation bounds.
   - **4-Cylinder Thermal Head**: 4 parallel Continuous `Integrator` ($1/s$) blocks for $\text{CHT}_1, \text{CHT}_2, \text{CHT}_3, \text{CHT}_4$.
   - **Exhaust Gas Dynamics**: Wastegate threshold `Switch` ($u > 0.8$) and continuous `Integrator` ($1/s$ $\text{EGT}$).
   - **Lubrication & Oil Pressure**: Dynamic Viscosity/RPM pump model and oil thermal capacitance.
   - **To Workspace Sinks**: Signal ports (`out_cht1_out`, `out_egt_out`, `out_oil_pressure_out`, etc.).

---

## ⚡ Step 2: Run the Live Simulink-to-GCS Dashboard Bridge

You can stream the Simulink simulation outputs directly into the live Web Ground Control Station:

1. Ensure the microservices and frontend are running:
   ```bash
   # Terminal 1: Start 5 Microservices
   python services/run_all_services.py

   # Terminal 2: Start GCS Frontend Dashboard
   cd frontend && npm run dev
   ```

2. Run the Simulink Bridge:
   ```bash
   python scripts/simulink_bridge.py --duration 300 --step 0.25
   ```

3. Open **`http://localhost:5173/`** in your browser:
   - Watch the live telemetry gauges, sparklines, and 3D Engine Digital Twin react to the Simulink ODE solver in real time!
   - Observe AI/ML anomaly detection, degradation index, and TreeSHAP explainability dynamically evaluating the Simulink plant outputs.

---

## 🔬 Step 3: Injecting Synthetic Faults in Simulink

You can inject faults directly into the Simulink model workspace or via our API Gateway:

* **Overheating Fault**: Set `SwitchEgtGate` threshold to $1.2$ or scale fuel-air ratio $\Phi > 1.2$.
* **Lubrication Breakdown**: Scale `SatOilPressure` down to $1.5\,\text{bar}$.
* **Cylinder Imbalance**: Adjust `GainCht4Rate` from $1.03 \to 1.25$ to simulate a clogged fuel injector on Cylinder 4.
