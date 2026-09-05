"""
Script: generate_demo_dataset.py
Generates a comprehensive 5-phase Out-of-Sample Demo Flight Mission #999 dataset
for live GCS Ground Control Station demonstration.

Phases:
1. Startup & Nominal Takeoff / Climb (Frames 0 - 100)
2. High Altitude ISR Cruise & Loiter (Frames 101 - 200)
3. Thermal Stress & Lubrication Degradation (Frames 201 - 300)
4. Fuel Injector Clog & Misfire Fluctuations (Frames 301 - 400)
5. Emergency Throttle Back & Safe Landing Recovery (Frames 401 - 500)
"""

import os
import sys
import numpy as np
import pandas as pd

# Path definitions
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "demo_synthetic_flight_test.csv")

def generate_demo_dataset():
    np.random.seed(42)
    num_frames = 500
    timestamps = np.linspace(0, 1500, num_frames)

    # Initialize telemetry arrays
    rpm = np.zeros(num_frames)
    throttle_pct = np.zeros(num_frames)
    load_pct = np.zeros(num_frames)
    altitude_m = np.zeros(num_frames)
    ambient_temp_C = np.zeros(num_frames)
    cht_C = np.zeros(num_frames)
    egt_C = np.zeros(num_frames)
    oil_temperature_C = np.zeros(num_frames)
    oil_pressure_bar = np.zeros(num_frames)
    vibration_rms = np.zeros(num_frames)
    fuel_flow_kg_s = np.zeros(num_frames)
    battery_voltage_V = np.zeros(num_frames)
    alternator_current_A = np.zeros(num_frames)

    for i in range(num_frames):
        t = i / float(num_frames)
        noise = np.random.normal(0, 0.02)

        # -------------------------------------------------------------
        # PHASE 1: Startup & Nominal Takeoff / Climb (0 - 100 frames)
        # -------------------------------------------------------------
        if i <= 100:
            progress = i / 100.0
            throttle_pct[i] = 45.0 + 30.0 * progress + noise * 2.0
            rpm[i] = 1800.0 + 550.0 * progress + np.random.normal(0, 10.0)
            load_pct[i] = 40.0 + 35.0 * progress
            altitude_m[i] = 100.0 + 1400.0 * progress
            ambient_temp_C[i] = 25.0 - 5.0 * progress
            cht_C[i] = 95.0 + 37.0 * progress + np.random.normal(0, 0.5)
            egt_C[i] = 550.0 + 110.0 * progress + np.random.normal(0, 2.0)
            oil_temperature_C[i] = 65.0 + 20.0 * progress + np.random.normal(0, 0.3)
            oil_pressure_bar[i] = 4.5 + np.random.normal(0, 0.05)
            vibration_rms[i] = 0.12 + 0.04 * progress + np.random.normal(0, 0.005)
            fuel_flow_kg_s[i] = 0.0035 + 0.0017 * progress
            battery_voltage_V[i] = 28.1 + np.random.normal(0, 0.05)
            alternator_current_A[i] = 25.0 + np.random.normal(0, 0.5)

        # -------------------------------------------------------------
        # PHASE 2: High Altitude Cruise & Loiter (101 - 200 frames)
        # -------------------------------------------------------------
        elif i <= 200:
            progress = (i - 100) / 100.0
            throttle_pct[i] = 75.0 + noise * 1.5
            rpm[i] = 2350.0 + np.random.normal(0, 12.0)
            load_pct[i] = 75.0
            altitude_m[i] = 1500.0 + 3700.0 * progress
            ambient_temp_C[i] = 20.0 - 38.0 * progress  # Drops down to -18°C
            cht_C[i] = 132.0 + 6.0 * progress + np.random.normal(0, 0.6)
            egt_C[i] = 660.0 + 25.0 * progress + np.random.normal(0, 2.5)
            oil_temperature_C[i] = 85.0 + 3.0 * progress + np.random.normal(0, 0.3)
            oil_pressure_bar[i] = 4.5 - 0.2 * progress + np.random.normal(0, 0.04)
            vibration_rms[i] = 0.16 + np.random.normal(0, 0.008)
            fuel_flow_kg_s[i] = 0.0052 + np.random.normal(0, 0.0001)
            battery_voltage_V[i] = 28.0 + np.random.normal(0, 0.05)
            alternator_current_A[i] = 26.0 + np.random.normal(0, 0.5)

        # -------------------------------------------------------------
        # PHASE 3: Thermal Stress & Lubrication Degradation (201 - 300 frames)
        # -------------------------------------------------------------
        elif i <= 300:
            progress = (i - 200) / 100.0
            throttle_pct[i] = 75.0 + noise * 1.5
            rpm[i] = 2350.0 - 50.0 * progress + np.random.normal(0, 15.0)
            load_pct[i] = 75.0 + 5.0 * progress
            altitude_m[i] = 5200.0
            ambient_temp_C[i] = -18.0
            # Lubrication Loss & Thermal Overheating Ramp
            oil_pressure_bar[i] = 4.3 - 2.5 * progress + np.random.normal(0, 0.05) # Drops to 1.8 bar
            oil_temperature_C[i] = 88.0 + 34.0 * progress + np.random.normal(0, 0.4) # Rises to 122°C
            cht_C[i] = 138.0 + 40.0 * progress + np.random.normal(0, 0.8)             # Rises to 178°C
            egt_C[i] = 685.0 + 75.0 * progress + np.random.normal(0, 3.0)             # Rises to 760°C
            vibration_rms[i] = 0.18 + 0.10 * progress + np.random.normal(0, 0.01)     # Rises to 0.28g
            fuel_flow_kg_s[i] = 0.0052 + np.random.normal(0, 0.0001)
            battery_voltage_V[i] = 27.8 + np.random.normal(0, 0.08)
            alternator_current_A[i] = 28.0 + np.random.normal(0, 0.8)

        # -------------------------------------------------------------
        # PHASE 4: Fuel Injector Clog & Misfire Fluctuations (301 - 400 frames)
        # -------------------------------------------------------------
        elif i <= 400:
            progress = (i - 300) / 100.0
            throttle_pct[i] = 75.0 + noise * 2.0
            # Misfire fluctuations in RPM & Vibration
            misfire_fluct = np.sin(i * 0.4) * 120.0
            rpm[i] = 2300.0 - 250.0 * progress + misfire_fluct + np.random.normal(0, 25.0)
            load_pct[i] = 80.0
            altitude_m[i] = 5200.0
            ambient_temp_C[i] = -18.0
            oil_pressure_bar[i] = 1.8 + np.random.normal(0, 0.05)
            oil_temperature_C[i] = 122.0 + np.random.normal(0, 0.5)
            cht_C[i] = 178.0 + np.random.normal(0, 1.0)
            # Fuel flow restriction & EGT spike
            fuel_flow_kg_s[i] = 0.0052 - 0.0024 * progress + np.random.normal(0, 0.0001) # Drops to 0.0028 kg/s
            egt_C[i] = 760.0 + 50.0 * progress + np.random.normal(0, 4.0)               # Spikes to 810°C
            # Severe misfire vibration
            vibration_rms[i] = 0.28 + 0.20 * progress + abs(misfire_fluct / 500.0) + np.random.normal(0, 0.02) # Spikes to 0.48g
            battery_voltage_V[i] = 27.5 + np.random.normal(0, 0.1)
            alternator_current_A[i] = 32.0 + np.random.normal(0, 1.0)

        # -------------------------------------------------------------
        # PHASE 5: Emergency Throttle Back & Safe Recovery (401 - 500 frames)
        # -------------------------------------------------------------
        else:
            progress = (i - 400) / 100.0
            throttle_pct[i] = 75.0 - 40.0 * progress + noise * 1.0
            rpm[i] = 2050.0 - 400.0 * progress + np.random.normal(0, 15.0)
            load_pct[i] = 80.0 - 45.0 * progress
            altitude_m[i] = 5200.0 - 4900.0 * progress
            ambient_temp_C[i] = -18.0 + 43.0 * progress  # Warms up to +25°C
            cht_C[i] = 178.0 - 63.0 * progress + np.random.normal(0, 0.6)            # Cools to 115°C
            egt_C[i] = 810.0 - 250.0 * progress + np.random.normal(0, 3.0)           # Cools to 560°C
            oil_pressure_bar[i] = 1.8 + 2.0 * progress + np.random.normal(0, 0.05)   # Recovers to 3.8 bar
            oil_temperature_C[i] = 122.0 - 42.0 * progress + np.random.normal(0, 0.4) # Cools to 80°C
            vibration_rms[i] = 0.48 - 0.34 * progress + np.random.normal(0, 0.01)    # Calms to 0.14g
            fuel_flow_kg_s[i] = 0.0028 + 0.0007 * (1.0 - progress)
            battery_voltage_V[i] = 28.0 + np.random.normal(0, 0.04)
            alternator_current_A[i] = 24.0 + np.random.normal(0, 0.5)

    # Derived physics reference values
    power_W = (throttle_pct / 100.0) * 85000.0
    torque_Nm = power_W / np.maximum(100.0, (rpm * 2.0 * np.pi / 60.0))
    air_mass_flow_kg_s = (rpm / 2500.0) * 0.12
    p_kPa = np.maximum(40.0, 101.325 * ((1.0 - 2.25577e-5 * altitude_m) ** 5.25588))
    air_density_kg_m3 = p_kPa * 1000.0 / (287.05 * (ambient_temp_C + 273.15))

    expected_rpm = np.round(rpm * 0.99, 1)
    expected_cht_C = np.round(cht_C * 0.96, 1)
    expected_egt_C = np.round(egt_C * 0.97, 1)
    physics_residual_C = np.round(cht_C - expected_cht_C, 2)

    df_demo = pd.DataFrame({
        "timestamp_s": np.round(timestamps, 1),
        "engine_id": "MALE_UAV_ENGINE_DEMO_01",
        "mission_id": 999,
        "mission_type": "Out_of_Sample_ISR_Endurance",
        "altitude_m": np.round(altitude_m, 1),
        "ambient_temp_C": np.round(ambient_temp_C, 1),
        "pressure_kPa": np.round(p_kPa, 3),
        "air_density_kg_m3": np.round(air_density_kg_m3, 4),
        "throttle_pct": np.round(throttle_pct, 1),
        "load_pct": np.round(load_pct, 1),
        "rpm": np.round(rpm, 1),
        "air_mass_flow_kg_s": np.round(air_mass_flow_kg_s, 4),
        "fuel_flow_kg_s": np.round(fuel_flow_kg_s, 5),
        "torque_Nm": np.round(torque_Nm, 1),
        "power_W": np.round(power_W, 1),
        "cht_C": np.round(cht_C, 1),
        "egt_C": np.round(egt_C, 1),
        "oil_temperature_C": np.round(oil_temperature_C, 1),
        "oil_pressure_bar": np.round(oil_pressure_bar, 2),
        "vibration_rms": np.round(vibration_rms, 4),
        "battery_voltage_V": np.round(battery_voltage_V, 2),
        "alternator_current_A": np.round(alternator_current_A, 2),
        "alternator_health": 1.0,
        "injection_timing_deg": 21.0,
        "expected_rpm": expected_rpm,
        "expected_cht_C": expected_cht_C,
        "expected_egt_C": expected_egt_C,
        "physics_residual_C": physics_residual_C
    })

    os.makedirs(DATA_DIR, exist_ok=True)
    df_demo.to_csv(OUTPUT_PATH, index=False)
    print(f"Successfully generated Demo Mission #999 dataset with {len(df_demo)} frames to: {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_demo_dataset()
