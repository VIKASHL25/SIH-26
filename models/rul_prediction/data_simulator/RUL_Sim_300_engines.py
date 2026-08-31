import numpy as np
import pandas as pd

MASTER_SEED=42
NUM_ENGINES=300
MIN_LIFE_HOURS=20
MAX_LIFE_HOURS=1000
DT_MINUTES=10
DT=DT_MINUTES*60.0
rng=np.random.default_rng(MASTER_SEED)

T0=288.15
P0=101325.0
L=0.0065
g=9.80665
R=287.05

BASE_ENGINE={
    "displacement_m3":0.0020,
    "rpm_idle":1200.0,
    "rpm_rated":6000.0,
    "rpm_opt":4800.0,
    "eta_v_max":0.88,
    "afr_base":14.0,
    "lhv_j_per_kg":44e6,
    "eta_th_base":0.30,
    "eta_mech":0.88,
    "J":0.20,
    "oil_viscosity_ref":0.10,
    "T_oil_ref_K":363.15
}

def atmosphere(
    altitude_m,
    temperature_offset_C
):
    T_isa=T0-L*altitude_m
    T_actual=T_isa+temperature_offset_C
    pressure=P0*(T_isa/T0)**(g/(R*L))
    density=pressure/(R*T_actual)
    return T_actual,pressure,density

def mission_profile(
    t,
    total_time,
    mission_type
):
    progress=t/max(total_time,1.0)

    if mission_type=="normal":

        if progress<0.10:
            altitude=5000*progress/0.10
            throttle=0.72

        elif progress<0.80:
            altitude=5000
            throttle=0.65

        elif progress<0.86:
            altitude=5000
            x=(progress-0.80)/0.06
            throttle=0.65+0.20*np.sin(np.pi*x)

        else:
            x=(progress-0.86)/0.14
            altitude=5000*(1-x)
            throttle=0.58

        temperature_offset=10.0

    elif mission_type=="high_load":

        altitude=3500
        throttle=0.82+0.08*np.sin(
            2*np.pi*t/1800
        )
        temperature_offset=15.0

    elif mission_type=="hot_weather":

        altitude=4500
        throttle=0.70+0.04*np.sin(
            2*np.pi*t/2400
        )
        temperature_offset=35.0

    elif mission_type=="mixed":

        phase=(t%7200)/7200

        if phase<0.25:
            altitude=2000+6000*phase/0.25
            throttle=0.78

        elif phase<0.50:
            altitude=8000-2000*(phase-0.25)/0.25
            throttle=0.62

        elif phase<0.75:
            altitude=6000
            throttle=0.78

        else:
            altitude=6000-6000*(phase-0.75)/0.25
            throttle=0.60

        temperature_offset=25.0

    else:

        altitude=6500+500*np.sin(
            2*np.pi*t/3600
        )

        throttle=0.85+0.08*np.sin(
            2*np.pi*t/900
        )

        temperature_offset=40.0

    throttle=np.clip(
        throttle,
        0.20,
        0.95
    )

    return (
        altitude,
        throttle,
        temperature_offset
    )

def simulate_engine(
    engine_id,
    lifetime_hours,
    mission_type,
    seed
):

    local_rng=np.random.default_rng(seed)

    engine=BASE_ENGINE.copy()

    # ========================================================
    # ENGINE-TO-ENGINE PHYSICAL VARIATION
    # ========================================================

    engine["displacement_m3"]*=(
        1+local_rng.normal(0,0.025)
    )

    engine["eta_v_max"]*=(
        1+local_rng.normal(0,0.025)
    )

    engine["eta_th_base"]*=(
        1+local_rng.normal(0,0.025)
    )

    engine["J"]*=(
        1+local_rng.normal(0,0.05)
    )

    engine["eta_mech"]*=(
        1+local_rng.normal(0,0.015)
    )

    # ========================================================
    # ENGINE HEALTH CHARACTERISTICS
    # ========================================================

    thermal_sensitivity=local_rng.uniform(
        0.88,
        1.15
    )

    mechanical_sensitivity=local_rng.uniform(
        0.88,
        1.15
    )

    lubrication_sensitivity=local_rng.uniform(
        0.88,
        1.15
    )

    vibration_sensitivity=local_rng.uniform(
        0.88,
        1.15
    )

    combustion_sensitivity=local_rng.uniform(
        0.90,
        1.12
    )

    cooling_efficiency=local_rng.uniform(
        0.90,
        1.10
    )

    # ========================================================
    # LATENT ENGINE WEAR CHARACTERISTIC
    # ========================================================

    # This represents manufacturing condition,
    # material variation and long-term wear tendency.

    wear_factor=local_rng.lognormal(
        mean=0.0,
        sigma=0.12
    )

    wear_factor=np.clip(
        wear_factor,
        0.70,
        1.35
    )

    # ========================================================
    # LIFETIME-DEPENDENT WEAR RATE
    # ========================================================

    # Shorter-life engines develop stronger degradation
    # signatures earlier than long-life engines.

    life_ratio=(
        MAX_LIFE_HOURS/
        max(lifetime_hours,1.0)
    )

    life_wear_factor=np.clip(
        life_ratio**0.28,
        0.90,
        1.80
    )

    effective_wear_rate=(
        wear_factor*
        life_wear_factor
    )

    # ========================================================
    # INITIAL STATES
    # ========================================================

    rpm=1200.0

    cht_K=390.0

    egt_K=800.0

    oil_temperature_K=350.0

    degradation=0.0

    vibration_phase=0.0

    total_time=(
        lifetime_hours*
        3600.0
    )

    steps=int(
        np.ceil(
            total_time/DT
        )
    )

    rows=[]

    # ========================================================
    # ENGINE SIMULATION LOOP
    # ========================================================

    for step in range(steps+1):

        t=min(
            step*DT,
            total_time
        )

        altitude,throttle,temperature_offset=(
            mission_profile(
                t,
                total_time,
                mission_type
            )
        )

        ambient_K,pressure_Pa,air_density=(
            atmosphere(
                altitude,
                temperature_offset
            )
        )

        # ====================================================
        # OPERATING CONDITIONS
        # ====================================================

        load=np.clip(
            throttle+
            0.025*np.sin(
                2*np.pi*t/1800
            )+
            local_rng.normal(
                0,
                0.008
            ),
            0.15,
            1.0
        )

        rpm_shape=(
            (rpm-engine["rpm_opt"])/
            2500.0
        )**2

        eta_v=(
            engine["eta_v_max"]
            -
            0.08*rpm_shape
            -
            0.04*(1-load)**2
        )

        eta_v=np.clip(
            eta_v,
            0.60,
            0.92
        )

        air_mass_flow=(
            air_density*
            engine["displacement_m3"]*
            rpm/
            120.0*
            eta_v
        )

        afr=np.clip(
            engine["afr_base"]-
            1.0*load+
            local_rng.normal(
                0,
                0.08
            ),
            12.0,
            14.5
        )

        fuel_flow=(
            air_mass_flow/
            afr
        )

        # ====================================================
        # CURRENT ENGINE DEGRADATION EFFECT
        # ====================================================

        eta_th=(
            engine["eta_th_base"]*
            (
                1.0-
                0.10*
                degradation*
                thermal_sensitivity
            )
        )

        eta_th=np.clip(
            eta_th,
            0.22,
            0.32
        )

        fuel_power=(
            fuel_flow*
            engine["lhv_j_per_kg"]
        )

        shaft_power=(
            fuel_power*
            eta_th*
            engine["eta_mech"]
        )

        omega=max(
            1.0,
            2*np.pi*rpm/60.0
        )

        engine_torque=(
            shaft_power/
            omega
        )

        propeller_torque=(
            0.0000010*
            rpm**2*
            (
                0.45+
                0.70*load
            )
        )

        friction_torque=(
            2.0+
            0.0018*rpm+
            0.8*
            degradation*
            mechanical_sensitivity
        )

        target_rpm=(
            1200.0+
            4700.0*
            throttle
        )

        target_rpm*=(
            1.0-
            0.04*
            degradation*
            mechanical_sensitivity
        )

        net_torque=(
            engine_torque-
            propeller_torque-
            friction_torque+
            0.02*
            (
                target_rpm-
                rpm
            )
        )

        domega=(
            net_torque/
            engine["J"]
        )

        omega+=(
            domega*
            DT
        )

        rpm=np.clip(
            omega*60/(2*np.pi),
            1100.0,
            engine["rpm_rated"]*1.01
        )

        omega=(
            2*np.pi*rpm/60.0
        )

        torque=(
            shaft_power/
            max(omega,1.0)
        )

        # ====================================================
        # EXHAUST GAS TEMPERATURE
        # ====================================================

        egt_equilibrium=(
            ambient_K+
            430.0*
            load+
            70.0*
            degradation*
            thermal_sensitivity*
            combustion_sensitivity
        )

        egt_equilibrium=np.clip(
            egt_equilibrium,
            650.0,
            1150.0
        )

        egt_tau=300.0

        egt_alpha=(
            1.0-
            np.exp(
                -DT/
                egt_tau
            )
        )

        egt_K+=(
            egt_alpha*
            (
                egt_equilibrium-
                egt_K
            )
        )

        egt_K=np.clip(
            egt_K,
            650.0,
            1200.0
        )

        # ====================================================
        # CYLINDER HEAD TEMPERATURE
        # ====================================================

        head_heat=(
            0.055*
            shaft_power*
            (
                1.0+
                0.8*
                degradation*
                thermal_sensitivity
            )
        )

        cooling_factor=(
            (
                0.40+
                0.000025*rpm+
                0.18*
                np.sqrt(
                    max(
                        air_density,
                        0.05
                    )
                )
            )*
            cooling_efficiency
        )

        cht_equilibrium=(
            ambient_K+
            head_heat/
            (
                600.0*
                cooling_factor
            )
        )

        cht_equilibrium=np.clip(
            cht_equilibrium,
            390.0,
            500.0
        )

        cht_tau=600.0

        cht_alpha=(
            1.0-
            np.exp(
                -DT/
                cht_tau
            )
        )

        cht_K+=(
            cht_alpha*
            (
                cht_equilibrium-
                cht_K
            )
        )

        cht_K=np.clip(
            cht_K,
            380.0,
            520.0
        )

        # ====================================================
        # OIL TEMPERATURE
        # ====================================================

        oil_heat=(
            0.018*
            shaft_power*
            (
                1.0+
                0.7*
                degradation*
                lubrication_sensitivity
            )
        )

        oil_equilibrium=(
            ambient_K+
            oil_heat/
            (
                70.0*
                (
                    0.8+
                    0.00003*rpm
                )
            )
        )

        oil_equilibrium=np.clip(
            oil_equilibrium,
            330.0,
            410.0
        )

        oil_tau=900.0

        oil_alpha=(
            1.0-
            np.exp(
                -DT/
                oil_tau
            )
        )

        oil_temperature_K+=(
            oil_alpha*
            (
                oil_equilibrium-
                oil_temperature_K
            )
        )

        oil_temperature_K=np.clip(
            oil_temperature_K,
            330.0,
            420.0
        )

        # ====================================================
        # OIL PRESSURE
        # ====================================================

        oil_viscosity=(
            engine["oil_viscosity_ref"]*
            np.exp(
                -0.012*
                (
                    oil_temperature_K-
                    engine["T_oil_ref_K"]
                )
            )
        )

        oil_viscosity=np.clip(
            oil_viscosity,
            0.025,
            0.20
        )

        oil_pressure=(
            0.0032*
            rpm*
            oil_viscosity+
            1.0-
            1.5*
            degradation*
            lubrication_sensitivity
        )

        oil_pressure=np.clip(
            oil_pressure,
            1.0,
            6.5
        )

        # ====================================================
        # VIBRATION
        # ====================================================

        rotational_frequency=(
            rpm/
            60.0
        )

        vibration_amplitude=(
            0.25+
            0.000018*rpm+
            1.6*
            (
                degradation**
                1.8
            )*
            vibration_sensitivity
        )

        vibration_phase+=(
            2*np.pi*
            rotational_frequency*
            DT
        )

        vibration_signal=(
            vibration_amplitude*
            np.sin(
                vibration_phase
            )+
            0.30*
            vibration_amplitude*
            np.sin(
                2*vibration_phase
            )+
            local_rng.normal(
                0,
                0.04
            )
        )

        vibration_rms=np.sqrt(
            0.5*
            vibration_amplitude**2+
            0.5*
            (
                0.30*
                vibration_amplitude
            )**2+
            0.04**2
        )

        # ====================================================
        # CONVERT TEMPERATURES
        # ====================================================

        cht_C=(
            cht_K-
            273.15
        )

        egt_C=(
            egt_K-
            273.15
        )

        oil_temperature_C=(
            oil_temperature_K-
            273.15
        )

        # ====================================================
        # STRESS CALCULATION
        # ====================================================

        thermal_stress=(
            0.5*
            np.clip(
                (
                    cht_C-
                    140.0
                )/
                80.0,
                0,
                2
            )
            +
            0.5*
            np.clip(
                (
                    egt_C-
                    650.0
                )/
                250.0,
                0,
                2
            )
        )

        load_stress=(
            load**2
        )

        rpm_stress=(
            rpm/
            engine["rpm_rated"]
        )**2

        vibration_stress=np.clip(
            vibration_rms/
            1.0,
            0,
            2
        )

        lubrication_stress=np.clip(
            (
                3.5-
                oil_pressure
            )/
            2.5,
            0,
            2
        )

        stress=(
            0.28*
            thermal_stress+
            0.22*
            load_stress+
            0.12*
            rpm_stress+
            0.20*
            vibration_stress+
            0.18*
            lubrication_stress
        )

        # ====================================================
        # IMPROVED DEGRADATION MODEL
        # ====================================================

        progress=(
            t/
            max(
                total_time,
                1.0
            )
        )

        # Base physical aging
        base_degradation=(
            progress**
            1.65
        )

        # Engine-specific wear behavior
        engine_wear=(
            effective_wear_rate*
            base_degradation
        )

        # Operating stress contribution
        stress_effect=(
            1.0+
            0.22*
            np.clip(
                stress,
                0,
                2
            )
        )

        target_degradation=(
            engine_wear*
            stress_effect
        )

        # Small stochastic degradation variation
        random_wear=local_rng.normal(
            0,
            0.0015
        )

        target_degradation+=(
            random_wear*
            np.sqrt(
                max(
                    progress,
                    0.001
                )
            )
        )

        target_degradation=np.clip(
            target_degradation,
            0,
            1
        )

        # Smooth degradation accumulation
        degradation+=(
            0.12*
            (
                target_degradation-
                degradation
            )
        )

        degradation=np.clip(
            degradation,
            0,
            1
        )

        # ====================================================
        # FORCE TRUE END-OF-LIFE STATE
        # ====================================================

        if step==steps:

            degradation=1.0

        health_index=(
            1.0-
            degradation
        )

        if step==steps:

            health_index=0.0

        # ====================================================
        # NUMERICAL CHECK
        # ====================================================

        values=[
            rpm,
            cht_K,
            egt_K,
            oil_temperature_K,
            oil_pressure,
            vibration_rms,
            degradation
        ]

        if not np.isfinite(
            values
        ).all():

            raise RuntimeError(
                f"Numerical instability in "
                f"{engine_id} at "
                f"{t/3600:.2f} hours"
            )

        # ====================================================
        # TELEMETRY OUTPUT
        # ====================================================

        rows.append({

            "engine_id":
                engine_id,

            "timestamp_hours":
                t/3600.0,

            "mission_type":
                mission_type,

            "altitude_m":
                altitude,

            "ambient_temp_C":
                ambient_K-
                273.15,

            "pressure_kPa":
                pressure_Pa/
                1000.0,

            "air_density_kg_m3":
                air_density,

            "throttle":
                throttle,

            "load":
                load,

            "rpm":
                rpm+
                local_rng.normal(
                    0,
                    4.0
                ),

            "air_mass_flow_kg_s":
                air_mass_flow+
                local_rng.normal(
                    0,
                    0.00001
                ),

            "fuel_flow_kg_s":
                fuel_flow+
                local_rng.normal(
                    0,
                    0.000005
                ),

            "torque_Nm":
                torque+
                local_rng.normal(
                    0,
                    0.05
                ),

            "power_W":
                shaft_power+
                local_rng.normal(
                    0,
                    5.0
                ),

            "cht_C":
                cht_C+
                local_rng.normal(
                    0,
                    0.4
                ),

            "egt_C":
                egt_C+
                local_rng.normal(
                    0,
                    1.2
                ),

            "oil_temperature_C":
                oil_temperature_C+
                local_rng.normal(
                    0,
                    0.25
                ),

            "oil_pressure_bar":
                oil_pressure+
                local_rng.normal(
                    0,
                    0.025
                ),

            "vibration_rms":
                vibration_rms+
                local_rng.normal(
                    0,
                    0.01
                ),

            "degradation":
                degradation,

            "health_index":
                health_index
        })

    # ========================================================
    # DATAFRAME
    # ========================================================

    result=pd.DataFrame(
        rows
    )

    failure_time=(
        result[
            "timestamp_hours"
        ].iloc[-1]
    )

    result[
        "rul_hours"
    ]=np.maximum(
        failure_time-
        result[
            "timestamp_hours"
        ],
        0.0
    )

    return result

# ============================================================
# GENERATE DATASET
# ============================================================

MISSION_TYPES=[
    "normal",
    "high_load",
    "hot_weather",
    "mixed",
    "harsh"
]

all_engines=[]

for i in range(
    NUM_ENGINES
):

    engine_id=(
        f"ENG_{i+1:04d}"
    )

    lifetime_hours=(
        rng.uniform(
            MIN_LIFE_HOURS,
            MAX_LIFE_HOURS
        )
    )

    mission_type=rng.choice(
        MISSION_TYPES
    )

    print(
        f"Generating {engine_id} | "
        f"Life={lifetime_hours:.1f} h | "
        f"Mission={mission_type}"
    )

    engine_df=simulate_engine(
        engine_id,
        lifetime_hours,
        mission_type,
        MASTER_SEED+i
    )

    all_engines.append(
        engine_df
    )

# ============================================================
# COMBINE
# ============================================================

dataset=pd.concat(
    all_engines,
    ignore_index=True
)

output_file=(
    "aero_piston_RUL_300_engines.csv"
)

dataset.to_csv(
    output_file,
    index=False
)

# ============================================================
# ENGINE SUMMARY
# ============================================================

engine_summary=(
    dataset
    .groupby("engine_id")
    .agg(
        lifetime_hours=(
            "timestamp_hours",
            "max"
        ),
        max_rul_hours=(
            "rul_hours",
            "max"
        ),
        rows=(
            "engine_id",
            "size"
        ),
        final_degradation=(
            "degradation",
            "last"
        )
    )
    .reset_index()
)

# ============================================================
# FINAL REPORT
# ============================================================

print(
    "\n===================================="
)

print(
    "DATASET GENERATED"
)

print(
    "===================================="
)

print(
    f"Number of engines: "
    f"{dataset['engine_id'].nunique()}"
)

print(
    f"Total rows: "
    f"{len(dataset):,}"
)

print(
    f"Minimum actual lifetime: "
    f"{engine_summary['lifetime_hours'].min():.2f} h"
)

print(
    f"Maximum actual lifetime: "
    f"{engine_summary['lifetime_hours'].max():.2f} h"
)

print(
    f"Minimum RUL: "
    f"{dataset['rul_hours'].min():.2f} h"
)

print(
    f"Maximum RUL: "
    f"{dataset['rul_hours'].max():.2f} h"
)

print(
    f"NaN values: "
    f"{dataset.isna().sum().sum()}"
)

print(
    f"Infinite values: "
    f"{np.isinf(
        dataset.select_dtypes(
            include=np.number
        )
    ).sum().sum()}"
)

print(
    "\nEngine lifetime statistics:"
)

print(
    engine_summary[
        "lifetime_hours"
    ].describe()
)

print(
    "\nFirst 5 rows:"
)

print(
    dataset.head()
)

print(
    f"\nSaved to: "
    f"{output_file}"
)