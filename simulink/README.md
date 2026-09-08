# Simulink Integration — SIH 2026

## Current Architecture

```text
Recorded Mission CSV
        ↓
    Simulink
        ↓ UDP telemetry
UDP → CAN Bridge
        ↓ CAN-FD multicast
CANInputReceiver
        ↓
MissionSimulationEngine
        ↓
Digital Twin Feature Engine
        ↓
 ┌──────┬────────────┬─────────────┬─────┐
 ↓      ↓            ↓             ↓
Anomaly Degradation Fault         RUL
Detection Estimation Classification Prediction
 └──────┴────────────┴─────────────┴─────┘
                    ↓
                 XAI
                    ↓
             Health / Advisory
                    ↓
             Existing Backend
                    ↓
             API / WebSocket
                    ↓
                Frontend
```

Simulink currently **replays recorded engine telemetry as a real-time telemetry stream**. It does not represent a physical live engine.

---

## 1. What Has Been Implemented

### Simulink telemetry replay

Main model:

```text
simulink_udp_poc.slx
```

Mission 1 contains 1000 samples at 1-second intervals (`0 ... 999 s`).

The 20 raw telemetry signals sent by Simulink are:

1. `rpm`
2. `throttle_pct`
3. `load_pct`
4. `cht_C`
5. `egt_C`
6. `oil_temperature_C`
7. `oil_pressure_bar`
8. `air_mass_flow_kg_s`
9. `fuel_flow_kg_s`
10. `torque_Nm`
11. `power_W`
12. `vibration_rms`
13. `battery_voltage_V`
14. `alternator_current_A`
15. `alternator_health`
16. `altitude_m`
17. `ambient_temp_C`
18. `pressure_kPa`
19. `injection_timing_deg`
20. `air_density_kg_m3`

### UDP

Simulink sends:

```text
Address: 127.0.0.1
Port:    5005
Payload: 20 doubles = 160 bytes
```

### UDP → CAN bridge

File:

```text
simulink/udp_can_bridge.py
```

The bridge converts the UDP telemetry into CAN-FD multicast traffic using the existing CAN DBC/codec.

Current CAN backend:

```text
udp_multicast
```

Multicast channel:

```text
ff15:7079:7468:6f6e:6465:6d6f:6d63:6173
```

Port:

```text
43113
```

### Backend receiver

Added:

```text
backend/can_receiver.py
```

The existing:

```text
backend/can_adapter.py
```

was intentionally kept unchanged.

`can_adapter.py` continues to support the existing CSV → CAN loopback path.

`can_receiver.py` handles:

```text
Simulink → UDP → CAN → Backend
```

### Simulation engine

`MissionSimulationEngine` now supports:

```python
MissionSimulationEngine(input_mode="csv")
```

and:

```python
MissionSimulationEngine(input_mode="simulink")
```

The default CSV path remains available.

---

## 2. Important Timing Fix

The original dataset is sampled once per second.

Initially Simulink used:

```text
Fixed step = 0.1 s
```

This caused interpolation between CSV samples.

For example, the CSV contained independent 1-second samples, while the received stream became a smooth trajectory between them. This caused the Simulink sample and backend reference row to become mismatched.

### Fix

Simulink is now configured as:

```text
Solver: Fixed-step
Fixed-step size: 1 second
```

This provides:

```text
CSV row N
    ↕
Simulink sample N
    ↕
UDP packet N
    ↕
CAN frame N
    ↕
Backend frame N
```

Synchronization was successfully verified.

---

## 3. Telemetry Synchronization Verification

The first 10 Mission 1 frames were compared between received Simulink telemetry and the corresponding CSV reference rows.

```text
FRAME | RX RPM | REF RPM | RX CHT | REF CHT | RX EGT | REF EGT
--------------------------------------------------------------------------------
1 | 2317.0 | 2317.25 | 132.9 | 132.89 | 665.4 | 665.45
2 | 2304.0 | 2304.40 | 132.6 | 132.64 | 665.9 | 665.94
3 | 2310.0 | 2310.13 | 134.6 | 134.65 | 672.5 | 672.55
4 | 2318.0 | 2318.32 | 137.4 | 137.43 | 687.1 | 687.11
5 | 2301.0 | 2301.38 | 130.8 | 130.79 | 671.4 | 671.35
6 | 2299.0 | 2299.24 | 133.6 | 133.62 | 663.9 | 663.89
7 | 2330.0 | 2329.95 | 133.4 | 133.36 | 682.2 | 682.16
8 | 2316.0 | 2315.96 | 134.4 | 134.43 | 669.3 | 669.26
9 | 2300.0 | 2300.30 | 131.8 | 131.80 | 672.5 | 672.47
10 | 2304.0 | 2304.39 | 135.8 | 135.83 | 672.4 | 672.43
```

Result:

```text
PASS
```

Small differences are due to CAN/DBC signal quantization.

---

## 4. Physics Reference Values

Only the 20 raw sensor signals are sent through Simulink/CAN.

The backend retains the corresponding Digital Twin reference values from the mission dataset:

```text
expected_rpm
expected_cht_C
expected_egt_C
physics_residual_C
```

These remain outside the raw CAN telemetry payload.

This allows the existing Feature Engine to continue generating its physics-informed features without modifying the ML models or CAN protocol.

---

## 5. ML Pipeline Verification

The Simulink-originated telemetry successfully reached the existing ML pipeline.

A successful test reached frame 15 and produced:

```text
Anomaly:
False

Degradation:
0.0

Estimated Health:
100.0%

Fault:
normal

Fault confidence:
100%

RUL:
PREDICTED

Predicted RUL:
42.13 hours

RUL confidence:
HIGH

90% confidence interval:
36.83 – 47.43 hours

Health:
NOMINAL

Advisories:
[]

XAI:
NOMINAL OPERATION
```

This confirms that the Simulink-originated telemetry reaches the existing Feature Engine, four ML models, XAI, health state, and advisory pipeline without modifying the trained models.

---

## 6. RUL Warm-up

The RUL model requires a historical window of:

```text
13 frames
```

Before sufficient history:

```text
status = COLLECTING_HISTORY
predicted_rul_hours = None
```

After sufficient history:

```text
status = PREDICTED
```

This is expected behavior.

Do not modify the RUL model because early frames return `None`.

---

## 7. Transient Anomalies

During Mission 1 testing, some frames temporarily triggered anomaly detection.

For example:

```text
Frame 7:
is_anomaly = True
```

XAI identified physics-residual features among the dominant contributors.

The anomaly subsequently returned to normal and the final tested state was:

```text
ANOMALY = False
FAULT = normal
HEALTH = NOMINAL
```

This represents a transient anomaly rather than an engine failure.

No anomaly threshold changes have been made.

---

## 8. Known scikit-learn Warning

The backend currently prints warnings such as:

```text
InconsistentVersionWarning:
Trying to unpickle estimator ExtraTreeRegressor
from version 1.9.0 when using version 1.6.1
```

Similar warnings occur for:

```text
IsolationForest
StandardScaler
```

### Current status

The models currently load and produce outputs.

This is a pre-existing model/environment compatibility issue.

### Do not change this during integration

Do not upgrade or downgrade scikit-learn unless deliberately tested.

Treat this as a separate cleanup/compatibility task after the integration is stable.

---

## 9. Known CAN Timeout

Possible error:

```text
RuntimeError:
Timed out waiting for CAN telemetry frame.

Missing message IDs:
[256, 257, 258, 259, 260, 261, 262, 263]
```

### Cause

The backend requested another telemetry frame after Simulink had stopped transmitting, or the backend was started too late.

### Fix

Keep the bridge running:

```powershell
python simulink\udp_can_bridge.py
```

Start Simulink:

```matlab
sim('simulink_udp_poc')
```

Then start the backend while Simulink is actively streaming.

For testing, use:

```text
Fixed step = 1 s
Stop Time  = 30–60 s
```

A timeout in this situation does not indicate a CAN protocol failure if the telemetry synchronization tests pass.

---

## 10. Important Files

```text
simulink/
├── simulink_udp_poc.slx
├── udp_can_bridge.py
├── udp_receiver.py
└── README.md
```

Backend integration:

```text
backend/can_receiver.py
backend/simulation_engine.py
```

Existing CAN layer:

```text
can_layer/
├── bus.py
├── can_codec.py
├── can_pipeline.py
├── dbc.py
└── engine_can.dbc
```

The existing CAN codec/DBC was not redesigned for this integration.

---

# 11. Current Status

## COMPLETED

```text
[✓] Mission 1 CSV loaded
[✓] Simulink telemetry replay
[✓] UDP transmission
[✓] UDP → CAN bridge
[✓] CAN-FD multicast
[✓] CAN receiver
[✓] 20/20 telemetry signals recovered
[✓] Telemetry/reference synchronization
[✓] Existing Feature Engine
[✓] Anomaly detection
[✓] Degradation estimation
[✓] Fault classification
[✓] RUL prediction
[✓] XAI
[✓] Health state
[✓] Maintenance advisory pipeline
```

---

# 12. Current Live Integration Status

The backend-to-frontend integration is complete. The older exploratory notes
below are retained only as implementation history; the acceptance results in
the final section are the authoritative current status.

## Verified Backend → Frontend Path

Verify the existing frontend with:

```text
Simulink
 ↓
UDP
 ↓
CAN
 ↓
Backend
 ↓
Existing API / WebSocket
 ↓
Existing Frontend Dashboard
```

The existing dashboard now works with:

```python
input_mode="simulink"
```

No frontend redesign is required for this integration.

Verify that the dashboard displays:

```text
RPM
CHT
EGT
Oil Pressure
Vibration
Health
Anomaly
Degradation
Fault
RUL
XAI / Advisory
```

---

## Historical validation notes

### 1. Timing / synchronization

Verify:

```text
Simulink timestamp
≈
Backend timestamp
≈
Frontend displayed frame
```

Check for buffering, dropped frames, or unnecessary latency.

### 2. Full Mission 1 replay

Run all:

```text
1000 frames
```

of Mission 1.

Verify backend stability for the complete mission.

### 3. Missions 1–100

The live selector supports:

```text
Mission 1
Mission 2
...
Mission 100
```

while keeping the same telemetry interface.

### 4. Final demo configuration

Current demo configuration:

- Simulink Stop Time: 1000 seconds / 1000 samples
- playback speed: 1x
- mission selection: 1–100 for live mode; 999 historical-only
- startup: selecting prepares and pauses; STREAM LIVE starts Simulink
- UDP endpoint: 127.0.0.1:5005
- pause behavior: terminates MATLAB/Simulink rather than preserving exact time

---

# 13. What NOT to Change

Unless a test proves it necessary, do not modify:

```text
ML models
Feature Engine
XAI engine
CAN codec
DBC definitions
API architecture
WebSocket architecture
Frontend architecture
RUL logic
Anomaly thresholds
Degradation model
Fault model
```

The current objective is integration, not redesign.

---

# 14. Recommended Startup Sequence

### Terminal 1 — UDP → CAN bridge

```powershell
python simulink\udp_can_bridge.py
```

Leave it running.

### MATLAB / Simulink

```matlab
% Normally started by the API after STREAM LIVE:
% run_mission(25, 1000)
```

Recommended test configuration:

```text
Fixed-step = 1 second
Stop Time  = 30–60 seconds
```

### Terminal 2 — backend

For a basic test:

```powershell
python -c "from backend.simulation_engine import MissionSimulationEngine; e=MissionSimulationEngine(input_mode='simulink'); e.initialize(); r=e.step(); print(r); e.close()"
```

For RUL testing, allow at least 13 frames to accumulate.

---

# 15. Last Verified Checkpoint

Last successful full inference test:

```text
FRAME: 15
ANOMALY: False
DEGRADATION: 0.0
HEALTH: 100.0%
FAULT: normal
RUL: 42.13 hours
RUL CONFIDENCE: HIGH
HEALTH STATE: NOMINAL
ADVISORIES: []
XAI: NOMINAL OPERATION
```

Current verified pipeline:

```text
SIMULINK → UDP → CAN → BACKEND → ML → XAI
```

---

# 16. Current Acceptance Result

The working Simulink/CAN/ML pipeline is complete and should be preserved.

```text
FULL LIVE DIGITAL TWIN ACCEPTANCE TEST: PASS
```

The verified sequence is recorded in the root README acceptance table.

---

# Integration Milestone

```text
                    STATUS

Simulink replay       ✓
UDP transport         ✓
CAN transport         ✓
Backend receiver      ✓
Synchronization       ✓
Feature Engine        ✓
Anomaly Detection     ✓
Degradation           ✓
Fault Classification  ✓
RUL                   ✓
XAI                   ✓
Advisory              ✓
Frontend              ✓
Mission 25 live       ✓
Mission 25 → 100      ✓
Final timing          ✓
```

The core Simulink-to-AI integration is working.
