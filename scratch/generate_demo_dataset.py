import os
import sys
import numpy as np
import pandas as pd

def generate_demo_dataset(output_path: str = "data/demo_synthetic_flight_test.csv", num_frames: int = 1000):
    """
    Generates a realistic 1,000-frame out-of-sample MALE UAV flight dataset
    simulating an 8-hour ISR Mission with:
    1. Climb to High Altitude (0 - 4500m)
    2. Hot Weather Cruise (Ambient 38°C)
    3. Rapid Throttle Transitions (Combat Evasion & Recon Loiter)
    4. Progressive Oil Pressure Loss & Cooling Degradation
    """
    print(f"Generating out-of-sample demo flight dataset ({num_frames} frames)...")
    
    np.random.seed(42)
    time_steps = np.linspace(0, 3600 * 8, num_frames)  # 8-hour mission timeline
    
    # 1. Flight Trajectory & Environment
    altitude_m = np.concatenate([
        np.linspace(100, 4500, 200),            # Climb phase
        np.full(500, 4500.0) + np.sin(np.linspace(0, 10, 500)) * 50, # High Altitude Cruise
        np.linspace(4500, 200, 300)             # Descent & Recovery
    ])
    
    ambient_temp_C = 38.0 - (altitude_m / 1000.0) * 6.5 + np.random.normal(0, 0.5, num_frames)
    
    # 2. Engine Operating Parameters
    throttle_pct = np.concatenate([
        np.full(200, 85.0) + np.random.normal(0, 1.0, 200),  # High Throttle Climb
        np.full(300, 65.0) + np.random.normal(0, 1.5, 300),  # Cruise Loiter
        65.0 + 20.0 * np.sin(np.linspace(0, 20, 200)),       # Rapid Throttle Transitions
        np.linspace(65.0, 25.0, 300)                         # Idle Descent
    ])
    
    rpm = 1200.0 + throttle_pct * 22.0 + np.random.normal(0, 10.0, num_frames)
    load_pct = throttle_pct * 0.95 + np.random.normal(0, 1.0, num_frames)
    power_W = rpm * (throttle_pct / 100.0) * 45.0 + np.random.normal(0, 50.0, num_frames)
    torque_Nm = power_W / (2 * np.pi * rpm / 60.0 + 1e-5)
    
    # 3. Progressive Degradation Curve (Oil Leak & Cylinder Overheating after frame 600)
    oil_leak_factor = np.zeros(num_frames)
    oil_leak_factor[600:] = np.linspace(0.0, 2.2, 400) # Drops oil pressure by 2.2 bar
    
    cht_C = 120.0 + (load_pct * 0.4) + (ambient_temp_C * 0.5) + (oil_leak_factor * 18.0) + np.random.normal(0, 1.0, num_frames)
    egt_C = 650.0 + (load_pct * 1.2) + np.random.normal(0, 3.0, num_frames)
    oil_temperature_C = 75.0 + (cht_C * 0.25) + (oil_leak_factor * 12.0) + np.random.normal(0, 0.8, num_frames)
    oil_pressure_bar = np.clip(4.8 - (oil_leak_factor) + np.random.normal(0, 0.05, num_frames), 0.5, 6.0)
    fuel_flow_kg_s = 0.001 + (power_W / 1e5) * 0.003 + np.random.normal(0, 0.0001, num_frames)
    vibration_rms = 0.35 + (oil_leak_factor * 0.4) + np.random.normal(0, 0.02, num_frames)
    
    battery_voltage_V = 28.0 - (vibration_rms * 0.2) + np.random.normal(0, 0.1, num_frames)
    alternator_current_A = 35.0 + np.random.normal(0, 0.5, num_frames)
    injection_timing_deg = 15.0 + (rpm / 1000.0) * 2.0 + np.random.normal(0, 0.2, num_frames)
    
    df = pd.DataFrame({
        "timestamp_s": np.round(time_steps, 1),
        "engine_id": "MALE_UAV_ENGINE_DEMO_01",
        "mission_id": 999,  # Dedicated Demo Mission ID
        "mission_type": "Out_of_Sample_ISR_Endurance",
        "rpm": np.round(rpm, 1),
        "throttle_pct": np.round(throttle_pct, 1),
        "load_pct": np.round(load_pct, 1),
        "power_W": np.round(power_W, 1),
        "torque_Nm": np.round(torque_Nm, 1),
        "cht_C": np.round(cht_C, 1),
        "egt_C": np.round(egt_C, 1),
        "oil_temperature_C": np.round(oil_temperature_C, 1),
        "oil_pressure_bar": np.round(oil_pressure_bar, 2),
        "fuel_flow_kg_s": np.round(fuel_flow_kg_s, 5),
        "vibration_rms": np.round(vibration_rms, 4),
        "battery_voltage_V": np.round(battery_voltage_V, 2),
        "alternator_current_A": np.round(alternator_current_A, 2),
        "altitude_m": np.round(altitude_m, 1),
        "ambient_temp_C": np.round(ambient_temp_C, 1),
        "injection_timing_deg": np.round(injection_timing_deg, 1),
        "expected_rpm": np.round(rpm, 1),
        "expected_cht_C": np.round(120.0 + (load_pct * 0.4) + (ambient_temp_C * 0.5), 1),
        "expected_egt_C": np.round(650.0 + (load_pct * 1.2), 1),
        "physics_residual_C": np.round((cht_C - (120.0 + (load_pct * 0.4) + (ambient_temp_C * 0.5))), 2)
    })
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[SUCCESS] Demo flight dataset generated successfully: {output_path} ({len(df)} frames)")

if __name__ == "__main__":
    generate_demo_dataset()
