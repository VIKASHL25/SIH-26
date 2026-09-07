import numpy as np
import pandas as pd

# ============================================================
# 1. SETTINGS
# ============================================================

np.random.seed(42)

ROWS_PER_MISSION = 1000

# 100 missions
MISSION_TYPES = (
    ["normal_isr"] * 20 +
    ["high_altitude"] * 15 +
    ["hot_weather"] * 15 +
    ["endurance"] * 10 +
    ["rapid_throttle"] * 10 +
    ["injector_degradation"] * 10 +
    ["lubrication_degradation"] * 8 +
    ["overheating"] * 5 +
    ["misfire"] * 4 +
    ["sensor_fault"] * 3
)

# ============================================================
# 2. REFERENCE ENGINE OPERATING POINTS
# ============================================================
# Prototype anchors based on publicly documented
# Lycoming O-235/O-290 operating information.

RPM_POINTS = np.array([2250, 2350, 2800])

LOAD_POINTS = np.array([0.65, 0.75, 1.00])

FUEL_FLOW_GPH_POINTS = np.array([
    5.8,     # 65%
    7.3,     # 75%
    10.7     # rated
])


# ============================================================
# 3. ATMOSPHERE MODEL
# ============================================================

def calculate_atmosphere(altitude_m, temperature_C):

    altitude_m = np.asarray(altitude_m)

    temperature_K = np.asarray(temperature_C) + 273.15

    # Standard atmosphere approximation
    temperature_standard = 288.15 - 0.0065 * altitude_m

    pressure_Pa = (
        101325 *
        np.maximum(
            temperature_standard / 288.15,
            0.35
        ) ** 5.25588
    )

    pressure_kPa = pressure_Pa / 1000

    air_density = (
        pressure_Pa /
        (287.05 * temperature_K)
    )

    return pressure_kPa, air_density


# ============================================================
# 4. GENERATE ONE MISSION
# ============================================================

def generate_mission(mission_id, mission_type):

    time = np.arange(
        ROWS_PER_MISSION,
        dtype=float
    )

    progress = time / (ROWS_PER_MISSION - 1)

    # --------------------------------------------------------
    # ENVIRONMENT + THROTTLE
    # --------------------------------------------------------

    if mission_type == "normal_isr":

        altitude = np.piecewise(
            time,
            [
                time < 200,
                (time >= 200) & (time < 850),
                time >= 850
            ],
            [
                lambda x: 50 + 50 * x,
                10000,
                lambda x: 10000 - 50 * (x - 850)
            ]
        )

        ambient_temp = (
            25 +
            1.5 * np.sin(time / 180)
        )

        throttle = np.piecewise(
            time,
            [
                time < 150,
                time < 300,
                time < 850,
                time >= 850
            ],
            [
                lambda x: 0.65 + 0.25 * x / 150,

                lambda x:
                0.90 -
                0.20 * (x - 150) / 150,

                0.70,

                lambda x:
                0.70 -
                0.35 * (x - 850) / 150
            ]
        )

    elif mission_type == "high_altitude":

        altitude = np.minimum(
            15000,
            15000 * progress
        )

        ambient_temp = (
            18 -
            0.006 * altitude +
            np.sin(time / 150)
        )

        throttle = (
            0.67 +
            0.05 * np.sin(time / 160)
        )

    elif mission_type == "hot_weather":

        altitude = (
            8000 +
            500 * np.sin(time / 200)
        )

        ambient_temp = (
            42 +
            2 * np.sin(time / 130)
        )

        throttle = (
            0.68 +
            0.08 * np.sin(time / 120)
        )

    elif mission_type == "endurance":

        altitude = (
            9000 +
            700 * np.sin(time / 250)
        )

        ambient_temp = (
            28 +
            1.5 * np.sin(time / 200)
        )

        throttle = (
            0.64 +
            0.04 * np.sin(time / 180)
        )

    elif mission_type == "rapid_throttle":

        altitude = (
            7000 +
            500 * np.sin(time / 180)
        )

        ambient_temp = (
            28 +
            2 * np.sin(time / 150)
        )

        # Rapid throttle transitions
        throttle = (
            0.55 +
            0.30 *
            (
                0.5 +
                0.5 * np.sin(time / 18)
            )
        )

    else:

        # Common environment for fault missions

        altitude = (
            8500 +
            500 * np.sin(time / 190)
        )

        ambient_temp = (
            30 +
            2 * np.sin(time / 160)
        )

        if mission_type == "injector_degradation":

            throttle = (
                0.68 +
                0.06 * np.sin(time / 120)
            )

            start = 100

        elif mission_type == "lubrication_degradation":

            throttle = (
                0.66 +
                0.05 * np.sin(time / 140)
            )

            start = 100

        elif mission_type == "overheating":

            throttle = (
                0.72 +
                0.06 * np.sin(time / 130)
            )

            ambient_temp = (
                40 +
                4 * progress +
                1.5 * np.sin(time / 120)
            )

            start = 150

        elif mission_type == "misfire":

            throttle = (
                0.68 +
                0.06 * np.sin(time / 110)
            )

            start = 250

        else:  # sensor_fault

            throttle = (
                0.67 +
                0.05 * np.sin(time / 140)
            )

            start = 300

    # --------------------------------------------------------
    # FAULT SEVERITY
    # --------------------------------------------------------

    if mission_type in [
        "injector_degradation",
        "lubrication_degradation",
        "overheating",
        "misfire",
        "sensor_fault"
    ]:

        severity = np.clip(
            (time - start) /
            (1000 - start),
            0,
            1
        )

        fault_type = np.where(
            severity > 0.05,
            mission_type,
            "normal"
        )

    else:

        severity = np.zeros(
            ROWS_PER_MISSION
        )

        fault_type = np.full(
            ROWS_PER_MISSION,
            "normal"
        )

    # --------------------------------------------------------
    # ENGINE LOAD
    # --------------------------------------------------------

    throttle = np.clip(
        throttle,
        0.25,
        0.95
    )

    load = np.clip(
        throttle +
        np.random.normal(
            0,
            0.015,
            ROWS_PER_MISSION
        ),
        0.25,
        1.0
    )

    # --------------------------------------------------------
    # ATMOSPHERE
    # --------------------------------------------------------

    pressure_kPa, air_density = (
        calculate_atmosphere(
            altitude,
            ambient_temp
        )
    )

    # ========================================================
    # 5. ENGINE PARAMETERS
    # ========================================================

    # --------------------------------------------------------
    # RPM
    # --------------------------------------------------------

    rpm = np.interp(
        np.clip(
            load,
            0.65,
            1.0
        ),
        LOAD_POINTS,
        RPM_POINTS
    )

    # Altitude effect
    rpm -= (
        0.0008 *
        np.maximum(
            altitude - 1500,
            0
        )
    )

    rpm += np.random.normal(
        0,
        7,
        ROWS_PER_MISSION
    )

    # Fault effects

    if mission_type == "injector_degradation":

        rpm += np.random.normal(
            0,
            3 + 18 * severity
        )

    if mission_type == "misfire":

        rpm += (
            35 *
            severity *
            np.sin(time / 5)
        )

        rpm += np.random.normal(
            0,
            4 + 12 * severity
        )

    # --------------------------------------------------------
    # FUEL FLOW
    # --------------------------------------------------------

    fuel_flow_gph = np.interp(
        np.clip(
            load,
            0.65,
            1.0
        ),
        LOAD_POINTS,
        FUEL_FLOW_GPH_POINTS
    )

    fuel_flow_gph *= (
        1 +
        0.03 *
        np.maximum(
            ambient_temp - 25,
            0
        ) / 20
    )

    if mission_type == "injector_degradation":

        fuel_flow_gph *= (
            1 +
            0.06 * severity
        )

    if mission_type == "misfire":

        fuel_flow_gph *= (
            1 +
            0.04 * severity
        )

    fuel_flow_gph += np.random.normal(
        0,
        0.06,
        ROWS_PER_MISSION
    )

    fuel_flow_gph = np.maximum(
        fuel_flow_gph,
        0.1
    )

    # Convert gallons/hour → kg/s
    # Prototype fuel density assumption
    fuel_density_kg_L = 0.72

    fuel_flow_kg_s = (
        fuel_flow_gph *
        3.785411784 *
        fuel_density_kg_L /
        3600
    )

    # --------------------------------------------------------
    # LOAD FRACTION
    # --------------------------------------------------------

    load_fraction = np.clip(
        (load - 0.65) / 0.35,
        0,
        1
    )

    # ========================================================
    # 6. TEMPERATURES
    # ========================================================

    # EGT
    # Model-derived synthetic value

    egt = (
        650 +
        140 * load_fraction +
        0.8 * (ambient_temp - 25) +
        0.002 * altitude
    )

    egt += np.random.normal(
        0,
        4,
        ROWS_PER_MISSION
    )

    # CHT
    # Model-derived and calibrated to remain reasonable
    # in healthy operating conditions.

    cht = (
        125 +
        55 * load_fraction +
        0.8 * (ambient_temp - 25) +
        0.0015 * altitude
    )

    cht += np.random.normal(
        0,
        1.4,
        ROWS_PER_MISSION
    )

    # Oil temperature

    oil_temperature = (
        70 +
        28 * load_fraction +
        0.45 * (ambient_temp - 25) +
        4 *
        (
            1 -
            np.exp(-time / 180)
        )
    )

    oil_temperature += np.random.normal(
        0,
        0.7,
        ROWS_PER_MISSION
    )

    # ========================================================
    # 7. FAULT EFFECTS
    # ========================================================

    if mission_type == "injector_degradation":

        egt += (
            45 * severity
        )

        egt += np.random.normal(
            0,
            3 + 10 * severity
        )

        cht += (
            18 * severity
        )

    elif mission_type == "lubrication_degradation":

        oil_temperature += (
            10 * severity
        )

        cht += (
            12 * severity
        )

    elif mission_type == "overheating":

        cht += (
            35 * severity
        )

        egt += (
            20 * severity
        )

        oil_temperature += (
            12 * severity
        )

    elif mission_type == "misfire":

        egt += (
            25 *
            severity *
            np.sin(time / 5)
        )

        egt += (
            10 * severity
        )

        cht += (
            8 * severity
        )

    # ========================================================
    # 8. OIL PRESSURE
    # ========================================================

    oil_pressure_psi = (
        25 +
        0.023 *
        np.maximum(
            rpm - 1000,
            0
        ) -
        0.08 *
        np.maximum(
            oil_temperature - 80,
            0
        )
    )

    if mission_type == "lubrication_degradation":

        oil_pressure_psi -= (
            18 * severity
        )

    oil_pressure_psi += np.random.normal(
        0,
        0.6,
        ROWS_PER_MISSION
    )

    oil_pressure_psi = np.clip(
        oil_pressure_psi,
        10,
        95
    )

    # Convert psi → bar

    oil_pressure_bar = (
        oil_pressure_psi *
        0.0689476
    )

    # ========================================================
    # 9. TORQUE + POWER
    # ========================================================

    # Prototype engine-output relationship.
    # It is NOT a manufacturer performance map.

    torque = (
        230 +
        120 * load_fraction
    )

    torque *= (
        rpm / 2350
    ) ** 0.15

    torque += np.random.normal(
        0,
        3,
        ROWS_PER_MISSION
    )

    if mission_type in [
        "lubrication_degradation",
        "overheating"
    ]:

        torque -= (
            18 * severity
        )

    power_W = (
        torque *
        2 *
        np.pi *
        rpm /
        60
    )

    power_W = np.maximum(
        power_W,
        0
    )

    # ========================================================
    # 10. AIR MASS FLOW
    # ========================================================

    # Representative displacement used only
    # for the prototype simulation.

    displacement_m3 = 0.00385

    volumetric_efficiency = np.clip(
        0.72 +
        0.10 * load_fraction,
        0.60,
        0.88
    )

    air_mass_flow = (
        air_density *
        displacement_m3 *
        (rpm / 60) *
        volumetric_efficiency /
        2
    )

    # ========================================================
    # 11. VIBRATION
    # ========================================================

    # Relative diagnostic index.
    # NOT a universal manufacturer limit.

    vibration = (
        0.7 +
        0.00045 *
        np.abs(
            rpm - 2250
        ) +
        0.15 *
        load_fraction
    )

    vibration += np.random.normal(
        0,
        0.06,
        ROWS_PER_MISSION
    )

    if mission_type == "injector_degradation":

        vibration += (
            1.4 * severity
        )

    elif mission_type == "lubrication_degradation":

        vibration += (
            0.9 * severity
        )

    elif mission_type == "misfire":

        vibration += (
            2 * severity +
            0.7 *
            severity *
            np.abs(
                np.sin(time / 5)
            )
        )

    elif mission_type == "overheating":

        vibration += (
            0.5 * severity
        )

    vibration = np.maximum(
        vibration,
        0.03
    )

    # ========================================================
    # 12. ELECTRICAL PARAMETERS
    # ========================================================

    battery_voltage = (
        28.0 +
        np.random.normal(
            0,
            0.10,
            ROWS_PER_MISSION
        )
    )

    alternator_current = (
        20 +
        30 * load +
        np.random.normal(
            0,
            1,
            ROWS_PER_MISSION
        )
    )

    alternator_health = np.ones(
        ROWS_PER_MISSION
    )

    # ========================================================
    # 13. INJECTION TIMING
    # ========================================================

    injection_timing = (
        25 +
        0.8 *
        (load_fraction - 0.5) +
        np.random.normal(
            0,
            0.12,
            ROWS_PER_MISSION
        )
    )

    if mission_type == "injector_degradation":

        injection_timing += (
            2.5 * severity
        )

    # ========================================================
    # 14. DIGITAL TWIN EXPECTED VALUES
    # ========================================================

    expected_rpm = np.interp(
        np.clip(
            load,
            0.65,
            1.0
        ),
        LOAD_POINTS,
        RPM_POINTS
    )

    expected_rpm -= (
        0.0008 *
        np.maximum(
            altitude - 1500,
            0
        )
    )

    expected_cht = (
        125 +
        55 * load_fraction +
        0.8 * (ambient_temp - 25) +
        0.0015 * altitude
    )

    expected_egt = (
        650 +
        140 * load_fraction +
        0.8 * (ambient_temp - 25) +
        0.002 * altitude
    )

    # ========================================================
    # 15. SENSOR FAULT
    # ========================================================

    reported_cht = cht.copy()

    if mission_type == "sensor_fault":

        reported_cht = (
            cht +
            25 *
            severity *
            np.sin(time / 12) +
            np.random.normal(
                0,
                1 + 4 * severity
            ) -
            80 * severity
        )

    # ========================================================
    # 16. PHYSICS RESIDUAL
    # ========================================================

    physics_residual = (
        reported_cht -
        expected_cht
    )

    # ========================================================
    # 17. HEALTH INDEX
    # ========================================================

    cht_penalty = np.maximum(
        (reported_cht - 204) / 56,
        0
    )

    oil_penalty = np.maximum(
        (60 - oil_pressure_psi) / 60,
        0
    )

    vibration_penalty = np.maximum(
        (vibration - 1.5) / 3,
        0
    )

    health_index = (
        100
        - 35 * cht_penalty
        - 30 * oil_penalty
        - 25 * vibration_penalty
        - 10 * severity
    )

    health_index = np.clip(
        health_index,
        0,
        100
    )

    # ========================================================
    # 18. RUL
    # ========================================================

    degradation = severity.copy()

    degradation_faults = [
        "injector_degradation",
        "lubrication_degradation",
        "overheating",
        "misfire",
        "sensor_fault"
    ]

    if mission_type in degradation_faults:

        rul_hours = (
            np.maximum(
                1000 - time,
                0
            ) / 3600
        )

        failure_flag = (
            severity >= 0.98
        ).astype(int)

    else:

        rul_hours = np.full(
            ROWS_PER_MISSION,
            np.nan
        )

        failure_flag = np.zeros(
            ROWS_PER_MISSION,
            dtype=int
        )

    # ========================================================
    # 19. CREATE DATAFRAME
    # ========================================================

    return pd.DataFrame({

        "timestamp_s":
            time.astype(int),

        "engine_id":
            "ENGINE_001",

        "mission_id":
            mission_id,

        "mission_type":
            mission_type,

        "altitude_m":
            np.round(
                altitude * 0.3048,
                2
            ),

        "ambient_temp_C":
            np.round(
                ambient_temp,
                2
            ),

        "pressure_kPa":
            np.round(
                pressure_kPa,
                3
            ),

        "air_density_kg_m3":
            np.round(
                air_density,
                5
            ),

        "throttle_pct":
            np.round(
                throttle * 100,
                2
            ),

        "load_pct":
            np.round(
                load * 100,
                2
            ),

        "rpm":
            np.round(
                rpm,
                2
            ),

        "air_mass_flow_kg_s":
            np.round(
                air_mass_flow,
                5
            ),

        "fuel_flow_kg_s":
            np.round(
                fuel_flow_kg_s,
                6
            ),

        "torque_Nm":
            np.round(
                torque,
                2
            ),

        "power_W":
            np.round(
                power_W,
                1
            ),

        "cht_C":
            np.round(
                reported_cht,
                2
            ),

        "egt_C":
            np.round(
                egt,
                2
            ),

        "oil_temperature_C":
            np.round(
                oil_temperature,
                2
            ),

        "oil_pressure_bar":
            np.round(
                oil_pressure_bar,
                3
            ),

        "vibration_rms":
            np.round(
                vibration,
                4
            ),

        "battery_voltage_V":
            np.round(
                battery_voltage,
                3
            ),

        "alternator_current_A":
            np.round(
                alternator_current,
                2
            ),

        "alternator_health":
            np.round(
                alternator_health,
                3
            ),

        "injection_timing_deg":
            np.round(
                injection_timing,
                3
            ),

        "expected_rpm":
            np.round(
                expected_rpm,
                2
            ),

        "expected_cht_C":
            np.round(
                expected_cht,
                2
            ),

        "expected_egt_C":
            np.round(
                expected_egt,
                2
            ),

        "physics_residual_C":
            np.round(
                physics_residual,
                2
            ),

        "health_index":
            np.round(
                health_index,
                2
            ),

        "fault_type":
            fault_type,

        "fault_severity":
            np.round(
                severity,
                4
            ),

        "degradation":
            np.round(
                degradation,
                4
            ),

        "failure_flag":
            failure_flag,

        "rul_hours":
            np.round(
                rul_hours,
                5
            )
    })


# ============================================================
# 20. GENERATE ALL 100 MISSIONS
# ============================================================

all_missions = []

for mission_id, mission_type in enumerate(
    MISSION_TYPES,
    start=1
):

    print(
        f"Generating mission "
        f"{mission_id}/100: "
        f"{mission_type}"
    )

    mission_data = generate_mission(
        mission_id,
        mission_type
    )

    all_missions.append(
        mission_data
    )


# ============================================================
# 21. COMBINE DATA
# ============================================================

dataset = pd.concat(
    all_missions,
    ignore_index=True
)


# ============================================================
# 22. SAVE DATASET
# ============================================================

OUTPUT_FILE = (
    "MALE_UAV_aero_piston_engine_final_100k.csv"
)

dataset.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# 23. BASIC VALIDATION
# ============================================================

print("\n====================================")
print("DATASET GENERATED")
print("====================================")

print(
    "Rows:",
    len(dataset)
)

print(
    "Columns:",
    len(dataset.columns)
)

print("\nColumn names:")

for column in dataset.columns:
    print("-", column)

print("\nMission distribution:")

print(
    dataset["mission_type"]
    .value_counts()
)

print("\nFault distribution:")

print(
    dataset["fault_type"]
    .value_counts()
)

print("\nFirst 5 rows:")

print(
    dataset.head()
)

print("\nDataset saved as:")

print(
    OUTPUT_FILE
)