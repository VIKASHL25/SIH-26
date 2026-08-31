# SIH 2026 — CAN Telemetry Layer

## Overview

The CAN telemetry layer provides the communication boundary between the
engine telemetry source and the Digital Twin backend.

It converts normalized engine telemetry into CAN frames using a DBC
specification, transmits the frames over a CAN bus, and decodes the received
frames back into normalized telemetry.

The backend interacts with the CAN layer through:

    backend/can_adapter.py

The ML models and feature engine do not need to know how CAN bytes are packed.

---

## Integrated System Pipeline

The current prototype uses the following end-to-end architecture:

    CSV Dataset
         |
         v
    MissionSimulationEngine
         |
         v
    CANTelemetryAdapter
         |
         v
    CAN Encoder + DBC
         |
         v
    Virtual CAN Bus
         |
         v
    CAN Decoder + DBC
         |
         v
    Normalized Telemetry
         |
         v
    DigitalTwinFeatureEngine
         |
         +--> Anomaly Detection
         +--> Degradation Detection
         +--> Fault Classification
         +--> RUL Estimation
         |
         v
    Digital Twin Backend / FastAPI

The CAN layer therefore sits between the telemetry source and the existing
Digital Twin / ML pipeline.

---

## Directory Structure

The CAN subsystem is contained in:

    can_layer/

    can_layer/
    ├── __init__.py
    ├── bus.py
    ├── can_codec.py
    ├── can_pipeline.py
    ├── dbc.py
    ├── engine_can.dbc
    ├── sensor_simulator.py
    ├── sample_engine_sensor_input.csv
    └── README.md

### Components

`bus.py`
: Creates the configured CAN bus backend.

`can_codec.py`
: Encodes normalized telemetry into CAN frames and decodes CAN frames back
  into normalized telemetry.

`dbc.py`
: Loads the DBC specification used by the CAN codec.

`engine_can.dbc`
: Defines CAN message IDs, signals, bit positions, scaling factors, offsets,
  and units for the prototype.

`sensor_simulator.py`
: Replays CSV telemetry as simulated engine sensor packets.

`can_pipeline.py`
: Provides a standalone CAN-layer test/replay utility.

`sample_engine_sensor_input.csv`
: Small sample dataset used for CAN-layer testing.

`backend/can_adapter.py`
: Integration boundary between the CAN subsystem and the Digital Twin
  backend.

---

## CAN Bus Backend

The default implementation uses `python-can`'s `VirtualBus`.

This allows the complete prototype to run without physical CAN hardware.

Advantages:

- Works on Linux and Windows.
- No physical CAN interface is required.
- No Linux `vcan0` setup is required.
- Suitable for development, integration testing, and demonstration.

Linux SocketCAN is also supported through:

    --backend socketcan

For example, with a real CAN interface:

    can0

The rest of the backend does not need to change when switching between the
virtual and SocketCAN backends.

---

## DBC Specification

The `.dbc` file is NOT a CAN packet.

It is the database/description that defines how telemetry signals are
represented inside CAN frames.

The current prototype uses the following CAN messages:

    0x100  ENGINE_STATE
           rpm
           throttle_pct
           load_pct

    0x101  THERMAL
           cht_C
           egt_C
           oil_temperature_C
           oil_pressure_bar

    0x102  AIR_FUEL
           air_mass_flow_kg_s
           fuel_flow_kg_s

    0x103  MECHANICAL
           torque_Nm
           power_W
           vibration_rms

    0x104  ELECTRICAL
           battery_voltage_V
           alternator_current_A
           alternator_health

    0x105  ENVIRONMENT
           altitude_m
           ambient_temp_C
           pressure_kPa

    0x106  INJECTION
           injection_timing_deg

    0x107  AIR_DENSITY
           air_density_kg_m3

There are currently:

    8 CAN frames
    20 telemetry signals

The CAN IDs, signal layouts, and scaling factors are prototype definitions.

If an official ECU/FADEC/CAN specification becomes available, the DBC should
be updated to match the real specification.

The rest of the software should continue using the normalized telemetry names.

---

## Normalized Telemetry Contract

The CAN layer uses normalized application-level signal names.

Example:

    {
        "rpm": 2317.25,
        "throttle_pct": 70.0,
        "load_pct": 70.75,

        "cht_C": 132.89,
        "egt_C": 665.45,
        "oil_temperature_C": 74.3,
        "oil_pressure_bar": 3.766,

        "air_mass_flow_kg_s": 0.06444,
        "fuel_flow_kg_s": 0.005013,

        "torque_Nm": 251.53,
        "power_W": 61036.1,
        "vibration_rms": 0.7529,

        "injection_timing_deg": 24.59,

        "battery_voltage_V": 28.077,
        "alternator_current_A": 40.55,
        "alternator_health": 1.0,

        "altitude_m": 15.24,
        "ambient_temp_C": 25.0,
        "pressure_kPa": 100.726,
        "air_density_kg_m3": 1.17692
    }

These normalized names are the interface exposed to the backend.

The backend does not need to handle raw CAN payload bytes.

---

## Backend Integration

The backend integration is implemented by:

    backend/can_adapter.py

The adapter performs:

    normalized telemetry
          |
          v
    encode_telemetry()
          |
          v
    CAN frames
          |
          v
    CAN bus
          |
          v
    received CAN frames
          |
          v
    decode_frame()
          |
          v
    normalized telemetry

The adapter uses two CAN nodes for the prototype:

    TX node
    simulated engine / ECU

    RX node
    backend telemetry gateway

Both nodes share the same CAN channel.

The ML pipeline only receives the decoded normalized telemetry.

---

## Digital Twin Integration

`MissionSimulationEngine` integrates the CAN adapter before feature generation.

The current processing path is:

    Mission CSV row
          |
          v
    telemetry selection
          |
          v
    CANTelemetryAdapter
          |
          v
    CAN encode
          |
          v
    Virtual CAN bus
          |
          v
    CAN decode
          |
          v
    decoded telemetry
          |
          v
    DigitalTwinFeatureEngine
          |
          v
    Model Manager
          |
          +--> Anomaly Detection
          +--> Degradation Detection
          +--> Fault Classification
          +--> RUL Prediction

Digital Twin reference values such as:

    expected_rpm
    expected_cht_C
    expected_egt_C
    physics_residual_C

are not treated as ordinary CAN sensor signals.

They remain backend / Digital Twin values and are preserved separately for
the feature engine.

---

## Installation

From the project root:

    python -m venv .venv

### Linux

    source .venv/bin/activate

### Windows PowerShell

    .venv\Scripts\activate

Install all project dependencies:

    pip install -r requirements.txt

The project-wide requirements include the CAN and Digital Twin dependencies.

---

## CAN-Layer Test

The CAN subsystem can be tested independently from the Digital Twin backend.

From the project root:

    python -m can_layer.can_pipeline \
        --input can_layer/sample_engine_sensor_input.csv

The pipeline performs:

    CSV
     -> Sensor Simulator
     -> CAN Encoder
     -> CAN Frames
     -> CAN Bus
     -> CAN Decoder
     -> decoded telemetry

The command produces:

    decoded_telemetry.csv

`decoded_telemetry.csv` is a generated test artifact and is not part of the
source code.

For approximately one packet per second:

    python -m can_layer.can_pipeline \
        --input can_layer/sample_engine_sensor_input.csv \
        --rate-hz 1

---

## CAN Round-Trip Validation

The CAN codec should preserve all supported telemetry signals within the
precision defined by the DBC scaling factors.

The integration test validates:

    Source telemetry
          |
          v
    CAN encode
          |
          v
    CAN transmission
          |
          v
    CAN reception
          |
          v
    CAN decode
          |
          v
    Round-trip comparison

The current prototype has been validated with:

    8/8 CAN frames generated
    20/20 telemetry signals decoded
    CAN BUS ROUND-TRIP: PASS

Small numerical differences are expected where the DBC intentionally uses
quantized signal scales.

For example, a signal with a scale of `0.01` cannot preserve more than two
decimal places through the CAN representation.

---

## Backend Integration Test

The complete backend can be executed using:

    python -m backend.main run --mission 1 --steps 15

This validates the complete path:

    Mission Dataset
        -> CAN Adapter
        -> CAN Bus
        -> Feature Engine
        -> Anomaly Model
        -> Degradation Model
        -> Fault Model
        -> RUL Model
        -> Advisory Generation

The RUL model requires historical records before producing a prediction.

During the initial ticks the backend reports:

    COLLECTING_HISTORY

Once sufficient history is available, the RUL prediction becomes active.

---

## Standalone CAN vs Backend Integration

There are two supported testing levels.

### 1. CAN-only test

Use:

    python -m can_layer.can_pipeline \
        --input can_layer/sample_engine_sensor_input.csv

This tests only the CAN subsystem.

### 2. Full Digital Twin test

Use:

    python -m backend.main run --mission 1 --steps 15

This tests the CAN subsystem together with the Digital Twin backend and
all four ML models.

The second test is the primary integration test for the project.

---

## Hardware Deployment Path

### Current prototype

    CSV Dataset
        |
    Sensor Simulator
        |
    Virtual CAN
        |
    CAN Decoder
        |
    CANTelemetryAdapter
        |
    Digital Twin Backend
        |
    ML Models

### Future hardware deployment

    Real Sensors / ECU / FADEC
              |
             CAN
              |
        CAN Interface
              |
          SocketCAN
              |
         CAN Decoder
              |
      CANTelemetryAdapter
              |
       Digital Twin Backend
              |
          ML Models

The goal is that the feature engine and ML models remain independent of the
underlying CAN transport.

---

## Design Principles

### 1. CAN and ML are separated

The ML models should never need to know about:

- CAN arbitration IDs
- CAN payload bytes
- DBC bit positions
- CAN signal scaling
- CAN bus implementation

### 2. One telemetry stream feeds all models

The architecture uses:

    CAN Decoder
         |
    Normalized Telemetry
         |
    +----+----+----+
    |    |    |    |
    v    v    v    v
   Anomaly Fault Degradation RUL

There should not be four independent CAN integrations.

### 3. DBC is the source of CAN encoding rules

The codec should not manually duplicate CAN bit layouts or scaling logic.

Those definitions belong in:

    engine_can.dbc

### 4. Transport can change independently

The prototype uses:

    VirtualBus

A future deployment can use:

    SocketCAN

without requiring changes to the Digital Twin feature engine or ML models.

---

## Prototype Status

Current integrated CAN telemetry prototype:

    CAN frames:              8
    Telemetry signals:       20
    CAN round-trip:          PASS
    Backend integration:     PASS
    Four-model pipeline:     PASS
    RUL history handling:    PASS

The CAN layer is currently intended as a software prototype.

The DBC definitions should be replaced with the official aircraft engine
CAN specification when one becomes available.