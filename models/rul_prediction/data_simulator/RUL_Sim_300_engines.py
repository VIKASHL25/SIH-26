import os
import numpy as np
import pandas as pd

MASTER_SEED = 42
NUM_ENGINES = 150
MIN_LIFE_HOURS = 50.0
MAX_LIFE_HOURS = 350.0
DT_MINUTES = 10
DT = DT_MINUTES * 60.0
rng = np.random.default_rng(MASTER_SEED)

T0 = 288.15
P0 = 101325.0
L = 0.0065
g = 9.80665
R = 287.05

BASE_ENGINE = {
    "displacement_m3": 0.0020,
    "rpm_idle": 1200.0,
    "rpm_rated": 6000.0,
    "rpm_opt": 4800.0,
    "eta_v_max": 0.88,
    "afr_base": 14.0,
    "lhv_j_per_kg": 44e6,
    "eta_th_base": 0.30,
    "eta_mech": 0.88,
    "J": 0.20,
    "oil_viscosity_ref": 0.10,
    "T_oil_ref_K": 363.15,
}

def atmosphere(altitude_m, temperature_offset_C):
    T_isa = T0 - L * altitude_m
    T_actual = T_isa + temperature_offset_C
    pressure = P0 * (max(0.2, T_isa / T0)) ** (g / (R * L))
    density = pressure / (R * T_actual)
    return T_actual, pressure, density

def mission_profile(t, total_time, mission_type):
    progress = t / max(total_time, 1.0)

    if mission_type == "normal":
        if progress < 0.10:
            altitude = 5000.0 * progress / 0.10
            throttle = 0.72
        elif progress < 0.80:
            altitude = 5000.0
            throttle = 0.65
        elif progress < 0.86:
            altitude = 5000.0
            x = (progress - 0.80) / 0.06
            throttle = 0.65 + 0.20 * np.sin(np.pi * x)
        else:
            x = (progress - 0.86) / 0.14
            altitude = 5000.0 * (1.0 - x)
            throttle = 0.58
        temperature_offset = 10.0

    elif mission_type == "high_load":
        altitude = 3500.0
        throttle = 0.82 + 0.08 * np.sin(2 * np.pi * t / 1800.0)
        temperature_offset = 15.0

    elif mission_type == "hot_weather":
        altitude = 4500.0
        throttle = 0.70 + 0.04 * np.sin(2 * np.pi * t / 2400.0)
        temperature_offset = 35.0

    elif mission_type == "mixed":
        phase = (t % 7200.0) / 7200.0
        if phase < 0.25:
            altitude = 2000.0 + 6000.0 * phase / 0.25
            throttle = 0.78
        elif phase < 0.50:
            altitude = 8000.0 - 2000.0 * (phase - 0.25) / 0.25
            throttle = 0.62
        elif phase < 0.75:
            altitude = 6000.0
            throttle = 0.78
        else:
            altitude = 6000.0 - 6000.0 * (phase - 0.75) / 0.25
            throttle = 0.60
        temperature_offset = 25.0

    else:  # harsh
        altitude = 6500.0 + 500.0 * np.sin(2 * np.pi * t / 3600.0)
        throttle = 0.85 + 0.08 * np.sin(2 * np.pi * t / 900.0)
        temperature_offset = 40.0

    throttle = np.clip(throttle, 0.20, 0.95)
    return altitude, throttle, temperature_offset

FAULT_MODES = [
    "normal_wear",
    "injector_degradation",
    "lubrication_degradation",
    "overheating",
    "misfire",
    "vibration_wear"
]

def simulate_engine(engine_id, lifetime_hours, mission_type, fault_mode, seed):
    local_rng = np.random.default_rng(seed)
    engine = BASE_ENGINE.copy()

    # Physical variation
    engine["displacement_m3"] *= (1.0 + local_rng.normal(0, 0.025))
    engine["eta_v_max"] *= (1.0 + local_rng.normal(0, 0.025))
    engine["eta_th_base"] *= (1.0 + local_rng.normal(0, 0.025))
    engine["J"] *= (1.0 + local_rng.normal(0, 0.05))
    engine["eta_mech"] *= (1.0 + local_rng.normal(0, 0.015))

    # Base sensitivities
    thermal_sensitivity = local_rng.uniform(0.90, 1.10)
    mechanical_sensitivity = local_rng.uniform(0.90, 1.10)
    lubrication_sensitivity = local_rng.uniform(0.90, 1.10)
    vibration_sensitivity = local_rng.uniform(0.90, 1.10)
    combustion_sensitivity = local_rng.uniform(0.90, 1.10)
    cooling_efficiency = local_rng.uniform(0.90, 1.10)

    # Fault-mode specific amplification
    if fault_mode == "injector_degradation":
        combustion_sensitivity *= 1.45
        thermal_sensitivity *= 1.25
    elif fault_mode == "lubrication_degradation":
        lubrication_sensitivity *= 1.55
        mechanical_sensitivity *= 1.30
    elif fault_mode == "overheating":
        thermal_sensitivity *= 1.50
        cooling_efficiency *= 0.70
    elif fault_mode == "misfire":
        combustion_sensitivity *= 1.60
        vibration_sensitivity *= 1.35
    elif fault_mode == "vibration_wear":
        vibration_sensitivity *= 1.60
        mechanical_sensitivity *= 1.40

    wear_factor = np.clip(local_rng.lognormal(mean=0.0, sigma=0.12), 0.70, 1.35)
    life_ratio = MAX_LIFE_HOURS / max(lifetime_hours, 1.0)
    life_wear_factor = np.clip(life_ratio ** 0.28, 0.90, 1.80)
    effective_wear_rate = wear_factor * life_wear_factor

    # Initial states
    rpm = 1200.0
    cht_K = 390.0
    egt_K = 800.0
    oil_temperature_K = 350.0
    degradation = 0.0
    vibration_phase = 0.0

    total_time = lifetime_hours * 3600.0
    steps = int(np.ceil(total_time / DT))
    rows = []

    for step in range(steps + 1):
        t = min(step * DT, total_time)
        altitude, throttle, temperature_offset = mission_profile(t, total_time, mission_type)
        ambient_K, pressure_Pa, air_density = atmosphere(altitude, temperature_offset)

        load = np.clip(
            throttle + 0.025 * np.sin(2 * np.pi * t / 1800.0) + local_rng.normal(0, 0.008),
            0.15, 1.0
        )

        rpm_shape = ((rpm - engine["rpm_opt"]) / 2500.0) ** 2
        eta_v = np.clip(engine["eta_v_max"] - 0.08 * rpm_shape - 0.04 * (1.0 - load) ** 2, 0.60, 0.92)
        air_mass_flow = air_density * engine["displacement_m3"] * rpm / 120.0 * eta_v
        afr = np.clip(engine["afr_base"] - 1.0 * load + local_rng.normal(0, 0.08), 12.0, 14.5)
        fuel_flow = air_mass_flow / afr

        # Current degradation effect
        eta_th = np.clip(engine["eta_th_base"] * (1.0 - 0.10 * degradation * thermal_sensitivity), 0.22, 0.32)
        fuel_power = fuel_flow * engine["lhv_j_per_kg"]
        shaft_power = fuel_power * eta_th * engine["eta_mech"]

        omega = max(1.0, 2 * np.pi * rpm / 60.0)
        engine_torque = shaft_power / omega
        propeller_torque = 0.0000010 * rpm ** 2 * (0.45 + 0.70 * load)
        friction_torque = 2.0 + 0.0018 * rpm + 0.8 * degradation * mechanical_sensitivity
        target_rpm = (1200.0 + 4700.0 * throttle) * (1.0 - 0.04 * degradation * mechanical_sensitivity)
        net_torque = engine_torque - propeller_torque - friction_torque + 0.02 * (target_rpm - rpm)

        domega = net_torque / engine["J"]
        omega += domega * DT
        rpm = np.clip(omega * 60.0 / (2 * np.pi), 1100.0, engine["rpm_rated"] * 1.01)
        omega = 2 * np.pi * rpm / 60.0
        torque = shaft_power / max(omega, 1.0)

        # EGT
        egt_eq = np.clip(
            ambient_K + 430.0 * load + 70.0 * degradation * thermal_sensitivity * combustion_sensitivity,
            650.0, 1150.0
        )
        egt_alpha = 1.0 - np.exp(-DT / 300.0)
        egt_K = np.clip(egt_K + egt_alpha * (egt_eq - egt_K), 650.0, 1200.0)

        # CHT
        head_heat = 0.055 * shaft_power * (1.0 + 0.8 * degradation * thermal_sensitivity)
        cooling_factor = (0.40 + 0.000025 * rpm + 0.18 * np.sqrt(max(air_density, 0.05))) * cooling_efficiency
        cht_eq = np.clip(ambient_K + head_heat / (600.0 * cooling_factor), 390.0, 500.0)
        cht_alpha = 1.0 - np.exp(-DT / 600.0)
        cht_K = np.clip(cht_K + cht_alpha * (cht_eq - cht_K), 380.0, 520.0)

        # Oil temperature & pressure
        oil_heat = 0.018 * shaft_power * (1.0 + 0.7 * degradation * lubrication_sensitivity)
        oil_eq = np.clip(ambient_K + oil_heat / (70.0 * (0.8 + 0.00003 * rpm)), 330.0, 410.0)
        oil_alpha = 1.0 - np.exp(-DT / 900.0)
        oil_temperature_K = np.clip(oil_temperature_K + oil_alpha * (oil_eq - oil_temperature_K), 330.0, 420.0)

        oil_viscosity = np.clip(engine["oil_viscosity_ref"] * np.exp(-0.012 * (oil_temperature_K - engine["T_oil_ref_K"])), 0.025, 0.20)
        oil_pressure = np.clip(0.0032 * rpm * oil_viscosity + 1.0 - 1.5 * degradation * lubrication_sensitivity, 1.0, 6.5)

        # Vibration
        rot_freq = rpm / 60.0
        vib_amp = 0.25 + 0.000018 * rpm + 1.6 * (degradation ** 1.8) * vibration_sensitivity
        vibration_phase += 2 * np.pi * rot_freq * DT
        vibration_rms = np.sqrt(0.5 * vib_amp ** 2 + 0.5 * (0.30 * vib_amp) ** 2 + 0.04 ** 2)

        cht_C = cht_K - 273.15
        egt_C = egt_K - 273.15
        oil_temperature_C = oil_temperature_K - 273.15

        # Degradation progression
        progress_life = t / max(total_time, 1.0)
        thermal_stress = 0.5 * np.clip((cht_C - 140.0) / 80.0, 0, 2) + 0.5 * np.clip((egt_C - 650.0) / 250.0, 0, 2)
        stress = 0.28 * thermal_stress + 0.22 * (load ** 2) + 0.12 * ((rpm / engine["rpm_rated"]) ** 2) + 0.20 * np.clip(vibration_rms / 1.0, 0, 2) + 0.18 * np.clip((3.5 - oil_pressure) / 2.5, 0, 2)

        base_deg = progress_life ** 1.65
        engine_wear = effective_wear_rate * base_deg
        target_deg = np.clip(engine_wear * (1.0 + 0.22 * np.clip(stress, 0, 2)) + local_rng.normal(0, 0.0015) * np.sqrt(max(progress_life, 0.001)), 0.0, 1.0)
        degradation = np.clip(degradation + 0.12 * (target_deg - degradation), 0.0, 1.0)

        if step == steps:
            degradation = 1.0

        health_index = 1.0 - degradation

        rows.append({
            "engine_id": engine_id,
            "timestamp_hours": t / 3600.0,
            "mission_type": mission_type,
            "fault_mode": fault_mode,
            "altitude_m": float(altitude),
            "ambient_temp_C": float(ambient_K - 273.15),
            "pressure_kPa": float(pressure_Pa / 1000.0),
            "air_density_kg_m3": float(air_density),
            "throttle": float(throttle),
            "load": float(load),
            "rpm": float(rpm + local_rng.normal(0, 4.0)),
            "air_mass_flow_kg_s": float(air_mass_flow + local_rng.normal(0, 0.00001)),
            "fuel_flow_kg_s": float(fuel_flow + local_rng.normal(0, 0.000005)),
            "torque_Nm": float(torque + local_rng.normal(0, 0.05)),
            "power_W": float(shaft_power + local_rng.normal(0, 5.0)),
            "cht_C": float(cht_C + local_rng.normal(0, 0.4)),
            "egt_C": float(egt_C + local_rng.normal(0, 1.2)),
            "oil_temperature_C": float(oil_temperature_C + local_rng.normal(0, 0.25)),
            "oil_pressure_bar": float(oil_pressure + local_rng.normal(0, 0.025)),
            "vibration_rms": float(vibration_rms + local_rng.normal(0, 0.01)),
            "degradation": float(degradation),
            "health_index": float(health_index)
        })

    result = pd.DataFrame(rows)
    failure_time = result["timestamp_hours"].iloc[-1]
    result["rul_hours"] = np.maximum(failure_time - result["timestamp_hours"], 0.0)
    return result

def main():
    print("====================================")
    print("GENERATING PHYSICAL RUL TRAJECTORIES")
    print(f"Engines: {NUM_ENGINES}, Lifetime: {MIN_LIFE_HOURS}-{MAX_LIFE_HOURS}h")
    print("====================================")

    MISSION_TYPES = ["normal", "high_load", "hot_weather", "mixed", "harsh"]
    all_engines = []

    for i in range(NUM_ENGINES):
        engine_id = f"ENG_{i+1:04d}"
        lifetime_hours = float(rng.uniform(MIN_LIFE_HOURS, MAX_LIFE_HOURS))
        mission_type = MISSION_TYPES[i % len(MISSION_TYPES)]
        fault_mode = FAULT_MODES[i % len(FAULT_MODES)]

        if (i + 1) % 20 == 0 or i == 0:
            print(f"Generating {engine_id} | Life={lifetime_hours:.1f}h | Mission={mission_type} | Fault={fault_mode}")

        engine_df = simulate_engine(engine_id, lifetime_hours, mission_type, fault_mode, MASTER_SEED + i)
        all_engines.append(engine_df)

    dataset = pd.concat(all_engines, ignore_index=True)

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    output_file = os.path.join(data_dir, "aero_piston_RUL_300_engines.csv")

    dataset.to_csv(output_file, index=False)
    print(f"Saved {len(dataset):,} rows across {dataset['engine_id'].nunique()} engines to: {output_file}")

if __name__ == "__main__":
    main()