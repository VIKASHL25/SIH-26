import numpy as np
import pandas as pd
rng = np.random.default_rng(42)
# ============================================================
# 1. REPRESENTATIVE ENGINE PARAMETERS
# ============================================================
ENGINE = {
    "displacement_m3": 0.0020,     # 2.0 L representative engine
    "rpm_idle": 1200.0,
    "rpm_rated": 6000.0,
    "rpm_opt": 4800.0,
    "eta_v_max": 0.88,
    # Representative stoichiometric/operating AFR region
    "afr_base": 14.0,
    # Representative gasoline-like LHV
    "lhv_j_per_kg": 44e6,
    "eta_th_base": 0.30,
    "eta_mech": 0.88,
    # Rotational inertia
    "J": 0.20,
    # Normalized reference oil viscosity
    "oil_viscosity_ref": 0.10,
    # Reference oil temperature
    "T_oil_ref_K": 363.15,
}
# ============================================================
# 2. ATMOSPHERIC CONSTANTS
# ============================================================
T0 = 288.15       # Sea-level standard temperature [K]
P0 = 101325.0     # Sea-level standard pressure [Pa]
L = 0.0065        # Temperature lapse rate [K/m]
g = 9.80665        # Gravity [m/s²]
R = 287.05         # Specific gas constant for air [J/kg/K]
# ============================================================
# 3. SIMULATION PARAMETERS
# ============================================================
DT = 1.0           # timestep = 1 second
MAX_HOURS = 14
MAX_STEPS = int(MAX_HOURS * 3600 / DT)
# ============================================================
# 4. ATMOSPHERE MODEL
# ============================================================
def atmosphere(altitude_m, temp_offset_C):
    # ISA temperature
    T_isa = T0 - L * altitude_m
    # Weather-adjusted temperature
    T_actual = T_isa + temp_offset_C
    # Pressure
    P = P0 * (
        T_isa / T0
    ) ** (
        g / (R * L)
    )
    # Air density
    rho = P / (R * T_actual)
    return T_actual, P, rho
# ============================================================
# 5. UAV MISSION PROFILE
# ============================================================
def mission_profile(t, total_time):
    progress = t / total_time
    # -------------------------
    # CLIMB
    # -------------------------
    if progress < 0.10:
        altitude = 5000.0 * (
            progress / 0.10
        )
        throttle = 0.75
    # -------------------------
    # CRUISE
    # -------------------------
    elif progress < 0.80:
        altitude = 5000.0
        throttle = 0.68
    # -------------------------
    # RAPID THROTTLE TRANSITION
    # -------------------------
    elif progress < 0.86:
        altitude = 5000.0
        x = (
            progress - 0.80
        ) / 0.06
        throttle = (
            0.68
            + 0.25 * np.sin(np.pi * x)
        )
    # -------------------------
    # DESCENT
    # -------------------------
    else:
        x = (
            progress - 0.86
        ) / 0.14
        altitude = 5000.0 * (1.0 - x)
        throttle = 0.60
    # Hot-weather mission
    ambient_offset = 25.0
    return altitude, throttle, ambient_offset
# ============================================================
# 6. ENGINE SIMULATOR
# ============================================================
def simulate_engine(seed=42):
    local_rng = np.random.default_rng(seed)
    # --------------------------------------------------------
    # Engine-to-engine variation
    # --------------------------------------------------------
    nominal_life = local_rng.uniform(
        7.5,
        11.5
    ) * 3600
    alpha = local_rng.uniform(
        1.6,
        2.3
    )
    # --------------------------------------------------------
    # Initial engine states
    # --------------------------------------------------------
    rpm = 1200.0
    cht_K = 423.15
    egt_K = 923.15
    oil_T_K = 373.15
    degradation = 0.0
    vibration_phase = 0.0
    rows = []
    # ========================================================
    # MAIN TIME LOOP
    # ========================================================
    for i in range(MAX_STEPS):
        t = i * DT
        # ====================================================
        # MISSION
        # ====================================================
        altitude, throttle, temp_offset = (
            mission_profile(
                t,
                MAX_STEPS * DT
            )
        )
        # ====================================================
        # STEP 1 — ATMOSPHERE
        # ====================================================
        Ta_K, pressure_Pa, rho = atmosphere(
            altitude,
            temp_offset
        )
        # ====================================================
        # OPERATING LOAD
        # ====================================================
        load = np.clip(
            throttle
            + 0.025
            * np.sin(
                2 * np.pi * t / 180
            )
            + local_rng.normal(
                0,
                0.008
            ),
            0.10,
            1.0
        )
        # ====================================================
        # STEP 2 — ENGINE BREATHING
        # ====================================================
        rpm_shape = (
            (rpm - ENGINE["rpm_opt"])
            / 2500.0
        ) ** 2
        eta_v = (
            ENGINE["eta_v_max"]
            - 0.10 * rpm_shape
            - 0.05
            * (1.0 - load) ** 2
        )
        eta_v = np.clip(
            eta_v,
            0.55,
            0.92
        )
        # Four-stroke engine:
        #
        # m_dot_air =
        # rho * displacement * RPM/120 * volumetric_efficiency
        air_mass_flow = (
            rho
            * ENGINE["displacement_m3"]
            * rpm
            / 120.0
            * eta_v
        )
        # ====================================================
        # STEP 3 — FUEL / COMBUSTION
        # ====================================================
        afr = (
            ENGINE["afr_base"]
            - 1.2 * load
        )
        afr = np.clip(
            afr,
            11.5,
            15.0
        )
        # Fuel flow
        fuel_flow = (
            air_mass_flow / afr
        )
        # Thermal efficiency
        eta_th = (
            ENGINE["eta_th_base"]
            * (
                1.0
                - 0.10 * degradation
            )
            * (
                1.0
                - 0.08
                * (load - 0.7) ** 2
            )
        )
        eta_th = np.clip(
            eta_th,
            0.20,
            0.33
        )
        # Fuel chemical power
        fuel_power = (
            fuel_flow
            * ENGINE["lhv_j_per_kg"]
        )
        # Shaft power
        shaft_power = (
            fuel_power
            * eta_th
            * ENGINE["eta_mech"]
        )
        # ====================================================
        # STEP 4 — MECHANICAL MODEL
        # ====================================================
        omega = max(
            1.0,
            2 * np.pi * rpm / 60.0
        )
        # Engine torque
        engine_torque = (
            shaft_power / omega
        )
        # Propeller load torque
        prop_load_torque = (
            0.0000012
            * rpm ** 2
            * (
                0.45
                + 0.8 * load
            )
        )
        # Friction
        friction_torque = (
            2.0
            + 0.0025 * rpm
            + 0.8
            * degradation
            * (
                rpm
                / ENGINE["rpm_rated"]
            )
        )
        # Desired RPM
        rpm_target = (
            1200.0
            + 4700.0 * throttle
        )
        # Degradation slightly reduces target capability
        rpm_target *= (
            1.0
            - 0.04 * degradation
        )
        # Net torque
        net_torque = (
            engine_torque
            - prop_load_torque
            - friction_torque
            + 0.015
            * (
                rpm_target - rpm
            )
        )
        # Rotational dynamics
        #
        # J*dω/dt = T_engine - T_load
        domega = (
            net_torque
            / ENGINE["J"]
        )
        omega += (
            domega * DT
        )
        rpm = np.clip(
            omega
            * 60
            / (2 * np.pi),
            1000.0,
            ENGINE["rpm_rated"]
            * 1.02
        )
        omega = (
            2 * np.pi * rpm / 60
        )
        torque = (
            shaft_power
            / max(
                omega,
                1.0
            )
        )
        # ====================================================
        # STEP 5 — THERMAL MODEL
        # ====================================================
        # -------------------------
        # EGT
        # -------------------------
        egt_eq = (
            Ta_K
            + 430.0 * load
            + 90.0
            * (
                fuel_flow
                / max(
                    air_mass_flow,
                    1e-9
                )
                - 1 / 14.0
            )
            * 14.0
            + 100.0
            * degradation
        )
        egt_eq = np.clip(
            egt_eq,
            650.0,
            1250.0
        )
        # First-order thermal dynamics
        egt_tau = 20.0
        egt_K += (
            (
                egt_eq
                - egt_K
            )
            / egt_tau
            * DT
        )
        # -------------------------
        # CHT
        # -------------------------
        cooling_factor = (
            0.25
            + 0.00004 * rpm
            + 0.25
            * np.sqrt(
                max(
                    rho,
                    0.01
                )
            )
        )
        q_head = (
            0.10
            * shaft_power
            * (
                1.0
                + 0.8 * degradation
            )
        )
        q_cool = (
            55.0
            * cooling_factor
            * max(
                cht_K - Ta_K,
                0.0
            )
        )
        C_head = 250000.0
        dcht = (
            q_head
            - q_cool
        ) / C_head
        cht_K += (
            dcht * DT
        )
        # -------------------------
        # Oil temperature
        # -------------------------
        q_oil = (
            0.035
            * shaft_power
            * (
                1.0
                + 0.7 * degradation
            )
        )
        q_oil_cool = (
            45.0
            * max(
                oil_T_K - Ta_K,
                0.0
            )
            * (
                0.5
                + 0.00003 * rpm
            )
        )
        C_oil = 180000.0
        oil_T_K += (
            (
                q_oil
                - q_oil_cool
            )
            / C_oil
            * DT
        )
        # ====================================================
        # STEP 6 — LUBRICATION
        # ====================================================
        # Temperature-dependent oil viscosity
        oil_viscosity = (
            ENGINE["oil_viscosity_ref"]
            * np.exp(
                -0.018
                * (
                    oil_T_K
                    - ENGINE["T_oil_ref_K"]
                )
            )
        )
        # Oil pressure model
        oil_pressure = (
            0.00105
            * rpm
            * oil_viscosity
            - 0.00010
            * rpm
            - 2.0
            * degradation
        )
        oil_pressure = np.clip(
            oil_pressure,
            0.2,
            7.0
        )
        # ====================================================
        # STEP 7 — VIBRATION
        # ====================================================
        rotational_frequency = (
            rpm / 60.0
        )
        # Degradation increases vibration amplitude
        vibration_amplitude = (
            0.45
            + 0.000025
            * rpm
            + 2.2
            * degradation ** 1.7
        )
        vibration_phase += (
            2
            * np.pi
            * rotational_frequency
            * DT
        )
        # Time-domain vibration
        vibration_signal = (
            vibration_amplitude
            * np.sin(
                vibration_phase
            )
            + 0.35
            * vibration_amplitude
            * np.sin(
                2 * vibration_phase
            )
            + local_rng.normal(
                0,
                0.08
            )
        )
        # RMS approximation
        vibration_rms = np.sqrt(
            0.5
            * vibration_amplitude ** 2
            +
            0.5
            * (
                0.35
                * vibration_amplitude
            ) ** 2
            +
            0.08 ** 2
        )
        # ====================================================
        # STEP 8 — DEGRADATION
        # ====================================================
        cht_C = (
            cht_K - 273.15
        )
        egt_C = (
            egt_K - 273.15
        )
        oil_T_C = (
            oil_T_K - 273.15
        )
        # -------------------------
        # Thermal stress
        # -------------------------
        S_cht = np.clip(
            (
                cht_C - 150.0
            )
            / 80.0,
            0.0,
            2.0
        )
        S_egt = np.clip(
            (
                egt_C - 700.0
            )
            / 250.0,
            0.0,
            2.0
        )
        # -------------------------
        # Load stress
        # -------------------------
        S_load = (
            load ** 2
        )
        # -------------------------
        # RPM stress
        # -------------------------
        S_rpm = (
            rpm
            / ENGINE["rpm_rated"]
        ) ** 2
        # -------------------------
        # Vibration stress
        # -------------------------
        S_vibration = (
            vibration_rms
            / 1.0
        )
        # -------------------------
        # Combined stress
        # -------------------------
        stress = (
            0.25 * S_cht
            + 0.25 * S_egt
            + 0.25 * S_load
            + 0.15 * S_rpm
            + 0.10 * S_vibration
        )
        # ====================================================
        # DEGRADATION DYNAMICS
        # ====================================================
        # Base degradation trajectory
        x = np.clip(
            t
            / max(
                nominal_life,
                1.0
            ),
            0.0,
            1.0
        )
        nominal_rate = (
            alpha
            / max(
                nominal_life,
                1.0
            )
            * max(
                x,
                1e-6
            ) ** (
                alpha - 1
            )
        )
        # Operating stress modifies degradation rate
        stress_multiplier = (
            0.70
            + 0.55
            * np.clip(
                stress,
                0.0,
                2.0
            )
        )
        degradation += (
            nominal_rate
            * stress_multiplier
            * (
                1.0
                + 0.6 * degradation
            )
            * DT
        )
        degradation = min(
            degradation,
            1.0
        )
        # Health index
        health = (
            1.0
            - degradation
        )
        # ====================================================
        # STORE TELEMETRY
        # ====================================================
        rows.append({
            "timestamp_s": t,
            "engine_id":
                f"ENG_{seed:04d}",
            # Environment
            "altitude_m":
                altitude,
            "ambient_temp_C":
                Ta_K - 273.15,
            "pressure_kPa":
                pressure_Pa / 1000,
            "air_density_kg_m3":
                rho,
            # Operating state
            "throttle":
                throttle,
            "load":
                load,
            "rpm":
                rpm
                + local_rng.normal(
                    0,
                    5.0
                ),
            # Engine physics
            "air_mass_flow_kg_s":
                air_mass_flow,
            "fuel_flow_kg_s":
                fuel_flow
                + local_rng.normal(
                    0,
                    1e-5
                ),
            "torque_Nm":
                torque,
            "power_W":
                shaft_power,
            # Thermal sensors
            "cht_C":
                cht_C
                + local_rng.normal(
                    0,
                    0.5
                ),
            "egt_C":
                egt_C
                + local_rng.normal(
                    0,
                    1.5
                ),
            "oil_temperature_C":
                oil_T_C
                + local_rng.normal(
                    0,
                    0.3
                ),
            # Lubrication
            "oil_pressure_bar":
                oil_pressure
                + local_rng.normal(
                    0,
                    0.03
                ),
            # Vibration
            "vibration_rms":
                vibration_rms
                + local_rng.normal(
                    0,
                    0.015
                ),
            # Hidden simulator state
            "health_index":
                health,
            "degradation":
                degradation
        })
        # ====================================================
        # FAILURE CONDITION
        # ====================================================
        if degradation >= 1.0:
            break
    # ========================================================
    # CREATE DATAFRAME
    # ========================================================
    result = pd.DataFrame(rows)
    # ========================================================
    # ACTUAL FAILURE TIME
    # ========================================================
    failure_time_s = (
        result["timestamp_s"].iloc[-1]
    )
    # ========================================================
    # RUL LABEL
    # ========================================================
    result["rul_hours"] = (
        np.maximum(
            failure_time_s
            - result["timestamp_s"],
            0.0
        )
        / 3600.0
    )
    return result
# ============================================================
# 7. GENERATE ONE ENGINE
# ============================================================
df = simulate_engine(
    seed=42
)
# ============================================================
# 8. SAVE DATASET
# ============================================================
df.to_csv(
    "aero_piston_engine_simulation_v1_1.csv",
    index=False
)
print(
    "Rows:",
    len(df)
)
print(
    "Failure time:",
    df["timestamp_s"].iloc[-1] / 3600,
    "hours"
)
print(
    "Initial RUL:",
    df["rul_hours"].iloc[0],
    "hours"
)
print(
    df.head()
)
