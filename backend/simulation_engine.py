import os
import time
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

from backend.config import DATASET_100K_PATH
from backend.model_loader import DigitalTwinModelManager
from backend.feature_engine import DigitalTwinFeatureEngine
from backend.can_adapter import CANTelemetryAdapter
from explainability.xai_engine import DigitalTwinXAIEngine

logger = logging.getLogger("MissionSimulationEngine")

class MissionSimulationEngine:
    """
    Core Simulation & Mission Replay Engine for Aero Piston Engine Digital Twin.
    
    Integrates:
    1. Historical flight telemetry streaming & mission replay.
    2. Dynamic parameter overrides & synthetic fault injection.
    3. Unified 4-Model real-time AI/ML inference execution.
    4. Mission health monitoring & advisory generation with alert level state tracking (anti-spam).
    5. Explainable AI (XAI) multi-model diagnostic and attribution engine.
    """
    REALTIME_INPUT_COLUMNS = [
        "timestamp_s",
        "engine_id",
        "mission_id",
        "mission_type",

        # Environment / operating conditions
        "altitude_m",
        "ambient_temp_C",
        "pressure_kPa",
        "air_density_kg_m3",
        "throttle_pct",
        "load_pct",

        # Engine telemetry
        "rpm",
        "air_mass_flow_kg_s",
        "fuel_flow_kg_s",
        "torque_Nm",
        "power_W",
        "cht_C",
        "egt_C",
        "oil_temperature_C",
        "oil_pressure_bar",
        "vibration_rms",

        # Electrical / injection
        "battery_voltage_V",
        "alternator_current_A",
        "alternator_health",
        "injection_timing_deg",

        # Digital Twin physics reference values
        "expected_rpm",
        "expected_cht_C",
        "expected_egt_C",
        "physics_residual_C",
    ]

    def __init__(self, dataset_path: str = str(DATASET_100K_PATH)):
        self.dataset_path = dataset_path
        self.df_raw: Optional[pd.DataFrame] = None
        self.active_mission_id: Optional[int] = None
        self.mission_df: Optional[pd.DataFrame] = None
        self.current_frame_idx: int = 0

        # Simulation State
        self.state: str = "STOPPED"  # STOPPED, RUNNING, PAUSED
        self.speed: float = 1.0       # Replay speed multiplier
        self.anomaly_threshold: float = 0.0

        # Alert State Tracking per Mission (Anti-Spam)
        self.last_alert_levels: Dict[str, Any] = {}

        # Model Manager, Feature Engine, & XAI Engine
        self.model_manager = DigitalTwinModelManager()
        self.feature_engine = DigitalTwinFeatureEngine()
        self.xai_engine = DigitalTwinXAIEngine()

        # CAN Adapter
        self.can_adapter = CANTelemetryAdapter(
            backend="virtual",
            channel="engine_backend",
        )

        # Fault Injection Overrides & Vibration Baseline Buffer
        self.fault_overrides: Dict[str, float] = {}
        self.env_overrides: Dict[str, float] = {}
        self.vibration_history: List[float] = []

    def initialize(self):
        """Loads dataset, models, and XAI explainers."""
        logger.info("Initializing Mission Simulation Engine...")
        
        # Load Models
        self.model_manager.load_all_models()
        self.xai_engine.initialize(self.model_manager)

        # Load Dataset
        logger.info(f"Loading dataset from: {self.dataset_path}")
        self.df_raw = pd.read_csv(self.dataset_path)
        logger.info(f"Dataset loaded: {len(self.df_raw)} rows across {self.df_raw['mission_id'].nunique()} missions.")

        # Default to first mission
        available_missions = self.get_available_missions()
        if available_missions:
            self.load_mission(available_missions[0])

    def get_available_missions(self) -> List[int]:
        """Returns list of unique mission IDs in the dataset."""
        missions = []
        if self.df_raw is not None and "mission_id" in self.df_raw.columns:
            missions = sorted(self.df_raw["mission_id"].unique().tolist())
        demo_path = os.path.join(os.path.dirname(self.dataset_path), "demo_synthetic_flight_test.csv")
        if os.path.exists(demo_path) and 999 not in missions:
            missions.append(999)
        return sorted(missions)

    def load_mission(self, mission_id: int):
        """Loads a specific mission dataset for replay."""
        demo_path = os.path.join(os.path.dirname(self.dataset_path), "demo_synthetic_flight_test.csv")
        if mission_id == 999 and os.path.exists(demo_path):
            demo_df = pd.read_csv(demo_path)
            self.active_mission_id = 999
            self.mission_df = demo_df.sort_values("timestamp_s").reset_index(drop=True)
            self.current_frame_idx = 0
            self.feature_engine.reset()
            self.model_manager.reset_state()
            self.last_alert_levels = {}
            self.state = "PAUSED"
            logger.info(f"Loaded Out-of-Sample Demo Mission 999 ({len(self.mission_df)} frames). Alert levels reset.")
            return

        if self.df_raw is None:
            raise ValueError("Dataset not loaded.")
        
        filtered = self.df_raw[self.df_raw["mission_id"] == mission_id].copy()
        if filtered.empty:
            raise ValueError(f"Mission ID {mission_id} not found in dataset.")

        self.active_mission_id = mission_id
        self.mission_df = filtered.sort_values("timestamp_s").reset_index(drop=True)
        self.current_frame_idx = 0
        self.feature_engine.reset()
        self.model_manager.reset_state()
        self.last_alert_levels = {}
        self.state = "PAUSED"
        logger.info(f"Loaded Mission {mission_id} ({len(self.mission_df)} frames). Alert levels reset.")

    def set_state(self, state: str):
        """Sets simulation playback state (RUNNING, PAUSED, STOPPED)."""
        valid_states = ["RUNNING", "PAUSED", "STOPPED"]
        if state.upper() not in valid_states:
            raise ValueError(f"Invalid state {state}. Must be one of {valid_states}")
        self.state = state.upper()
        logger.info(f"Simulation state changed to: {self.state}")

    def set_speed(self, speed: float):
        """Sets playback speed multiplier (e.g. 0.5, 1.0, 5.0, 10.0)."""
        self.speed = max(0.1, min(100.0, float(speed)))
        logger.info(f"Simulation replay speed set to: {self.speed}x")

    def seek(self, frame_idx: int):
        """Seeks to a specific frame index in the active mission."""
        if self.mission_df is None:
            return
        self.current_frame_idx = max(0, min(len(self.mission_df) - 1, frame_idx))

    def set_fault_injection(self, overrides: Dict[str, float]):
        """
        Injects synthetic parameter overrides for what-if scenarios.
        Example: {"cht_C": +30.0, "oil_pressure_bar": -2.0, "vibration_rms": +0.2}
        """
        self.fault_overrides = overrides
        logger.info(f"Active fault overrides updated: {self.fault_overrides}")

    def clear_fault_injection(self):
        """Clears all fault overrides."""
        self.fault_overrides.clear()
        logger.info("Fault overrides cleared.")

    def close(self):
        """Release simulation resources."""
        if self.can_adapter is not None:
            self.can_adapter.close()
            self.can_adapter = None

    def step(self, advance: bool = True) -> Optional[Dict[str, Any]]:
        """Advances simulation by 1 tick (if advance=True) and evaluates all 4 models."""
        if self.mission_df is None or self.mission_df.empty:
            return None

        if self.current_frame_idx >= len(self.mission_df):
            self.current_frame_idx = 0

        # Get raw telemetry row
        source_row = self.mission_df.iloc[self.current_frame_idx]
        raw_row = {
            col: source_row[col]
            for col in self.REALTIME_INPUT_COLUMNS
            if col in source_row.index
        }

        # Apply synthetic overrides if active
        for param, delta_or_val in self.fault_overrides.items():
            if param in raw_row:
                raw_row[param] = float(raw_row[param]) + delta_or_val

        # Preserve backend metadata outside the CAN telemetry payload.
        metadata = {
            "timestamp_s": raw_row.get("timestamp_s"),
            "engine_id": raw_row.get("engine_id"),
            "mission_id": raw_row.get("mission_id"),
            "mission_type": raw_row.get("mission_type"),
        }

        # Extract only normalized telemetry signals handled by the CAN layer.
        can_telemetry = {
            key: float(value)
            for key, value in raw_row.items()
            if key in self.can_adapter.SUPPORTED_SIGNALS
        }

        # CSV -> CAN -> RX -> decoded telemetry
        decoded_telemetry = self.can_adapter.transmit_and_receive(can_telemetry)

        # Reconstruct the backend sample.
        raw_row = {
            **metadata,
            **decoded_telemetry,
        }

        # Preserve Digital Twin reference values used by the feature engine.
        for key in (
            "expected_rpm",
            "expected_cht_C",
            "expected_egt_C",
            "physics_residual_C",
        ):
            if key in self.mission_df.columns:
                raw_row[key] = source_row[key]

        # Advance frame index for next step only if advance is True
        if advance:
            self.current_frame_idx += 1

        # Process decoded CAN telemetry through the existing ML pipeline.
        fv = self.feature_engine.generate_all_feature_vectors(
            raw_row,
            self.model_manager
        )
        buffer_len = len(self.feature_engine.buffer)

        # Run inference across all 4 models (handles fv["rul"] being None)
        predictions = self.model_manager.predict_all(
            fv,
            anomaly_threshold=self.anomaly_threshold,
            buffer_len=buffer_len
        )

        # Ensure RUL payload has COLLECTING_HISTORY structure if feature vector was None
        if fv["rul"] is None:
            predictions["rul_prediction"] = {
                "status": "COLLECTING_HISTORY",
                "predicted_rul_hours": None,
                "records_available": buffer_len,
                "records_required": 13
            }

        # Generate Maintenance Advisory with State Tracking (anti-spam)
        advisories = self._generate_maintenance_advisories(predictions, fv["clean_sample"])

        # Generate Explainable AI (XAI) multi-model explanations
        xai_payload = self.xai_engine.explain(fv, predictions, self.model_manager)

        # Construct Consolidated Digital Twin Frame Payload
        payload = {
            "timestamp_s": int(raw_row.get("timestamp_s", self.current_frame_idx)),
            "frame_index": self.current_frame_idx,
            "total_frames": len(self.mission_df),
            "mission_id": self.active_mission_id,
            "mission_type": raw_row.get("mission_type", "ISR_Mission"),
            "playback_state": self.state,
            "playback_speed": self.speed,
            
            # Telemetry Sensors
            "telemetry": {
                "rpm": round(float(fv["clean_sample"]["rpm"]), 1),
                "throttle_pct": round(float(fv["clean_sample"]["throttle_pct"]), 1),
                "load_pct": round(float(fv["clean_sample"]["load_pct"]), 1),
                "power_W": round(float(fv["clean_sample"]["power_W"]), 1),
                "torque_Nm": round(float(fv["clean_sample"]["torque_Nm"]), 1),
                "cht_C": round(float(fv["clean_sample"]["cht_C"]), 1),
                "egt_C": round(float(fv["clean_sample"]["egt_C"]), 1),
                "oil_temperature_C": round(float(fv["clean_sample"]["oil_temperature_C"]), 1),
                "oil_pressure_bar": round(float(fv["clean_sample"]["oil_pressure_bar"]), 2),
                "fuel_flow_kg_s": round(float(fv["clean_sample"]["fuel_flow_kg_s"]), 4),
                "vibration_rms": round(float(fv["clean_sample"]["vibration_rms"]), 4),
                "battery_voltage_V": round(float(fv["clean_sample"]["battery_voltage_V"]), 2),
                "alternator_current_A": round(float(fv["clean_sample"]["alternator_current_A"]), 2),
                "altitude_m": round(float(fv["clean_sample"]["altitude_m"]), 1),
                "ambient_temp_C": round(float(fv["clean_sample"]["ambient_temp_C"]), 1),
                "injection_timing_deg": round(float(fv["clean_sample"]["injection_timing_deg"]), 1),
            },

            # Physics & Residual Model Indicators
            "physics_model": {
                "expected_rpm": round(float(fv["clean_sample"].get("expected_rpm", fv["clean_sample"]["rpm"])), 1),
                "expected_cht_C": round(float(fv["clean_sample"].get("expected_cht_C", fv["clean_sample"]["cht_C"])), 1),
                "expected_egt_C": round(float(fv["clean_sample"].get("expected_egt_C", fv["clean_sample"]["egt_C"])), 1),
                "cht_residual": round(float(fv["clean_sample"]["cht_residual"]), 2),
                "egt_residual": round(float(fv["clean_sample"]["egt_residual"]), 2),
                "rpm_residual": round(float(fv["clean_sample"]["rpm_residual"]), 2),
                "physics_residual_C": round(float(fv["clean_sample"]["physics_residual_C"]), 2),
            },

            # Consolidated ML Model Outputs
            "health_status": predictions["status"],
            "anomaly_detection": predictions["anomaly_detection"],
            "degradation_estimation": predictions["degradation_estimation"],
            "fault_classification": predictions["fault_classification"],
            "rul_prediction": predictions["rul_prediction"],
            "model_metadata": predictions.get("metadata", {}),
            "advisories": advisories,
            "xai": xai_payload
        }

        return payload

    def get_current_frame(self) -> Optional[Dict[str, Any]]:
        """Returns the current telemetry frame evaluated across models without advancing the frame index."""
        return self.step(advance=False)

    def _generate_maintenance_advisories(self, predictions: dict, clean_sample: dict) -> List[str]:
        """
        Generates maintenance advisories, firing alerts only on state level changes to eliminate tick-by-tick spam.
        """
        advisories = []
        
        fault = predictions["fault_classification"]["predicted_fault"]
        confidence = predictions["fault_classification"]["confidence"]
        rul_pred = predictions["rul_prediction"]
        rul_hours = rul_pred.get("predicted_rul_hours")
        is_anomaly = predictions["anomaly_detection"]["is_anomaly"]
        health_pct = predictions["degradation_estimation"]["estimated_health_pct"]

        # 1. ANOMALY Alert State
        anomaly_state = is_anomaly
        if anomaly_state != self.last_alert_levels.get("ANOMALY"):
            if anomaly_state:
                msg = "CRITICAL: Operating parameters deviate significantly from normal baseline envelope."
                advisories.append(msg)
                logger.warning(msg)
            self.last_alert_levels["ANOMALY"] = anomaly_state

        # 2. FAULT Alert State
        fault_state = fault
        if fault_state != self.last_alert_levels.get("FAULT"):
            if fault == "overheating":
                msg = f"WARNING: Cylinder/Exhaust Overheating trend detected ({confidence*100:.1f}% confidence). Inspect cooling duct & mixture ratio."
                advisories.append(msg)
                logger.warning(msg)
            elif fault == "lubrication_degradation":
                msg = f"WARNING: Oil Pressure / Temperature abnormality detected ({confidence*100:.1f}% confidence). Check oil pump and filter."
                advisories.append(msg)
                logger.warning(msg)
            elif fault == "injector_degradation":
                msg = f"WARNING: Fuel Injection anomaly detected ({confidence*100:.1f}% confidence). Service fuel injectors."
                advisories.append(msg)
                logger.warning(msg)
            elif fault == "misfire":
                msg = f"WARNING: Engine misfire condition detected ({confidence*100:.1f}% confidence). Inspect spark plugs & ignition system."
                advisories.append(msg)
                logger.warning(msg)
            elif fault == "sensor_fault":
                msg = f"NOTICE: Sensor telemetry drift detected. Calibrate engine sensors."
                advisories.append(msg)
                logger.info(msg)
            self.last_alert_levels["FAULT"] = fault_state

        # 3. DEGRADATION Alert State (Defense Standards: NORMAL >= 60%, MODERATE 35-60%, CRITICAL < 35%)
        if health_pct < 35.0:
            deg_state = "CRITICAL"
        elif health_pct < 60.0:
            deg_state = "MODERATE"
        else:
            deg_state = "NORMAL"

        if deg_state != self.last_alert_levels.get("DEGRADATION"):
            if deg_state == "MODERATE":
                msg = f"ADVISORY: Engine degradation elevated (Health Index: {health_pct:.1f}%). Schedule depot maintenance post-mission."
                advisories.append(msg)
                logger.info(msg)
            elif deg_state == "CRITICAL":
                msg = f"ALERT: Critical engine degradation (Health Index: {health_pct:.1f}%). Initiate Return-to-Base (RTB)."
                advisories.append(msg)
                logger.warning(msg)
            self.last_alert_levels["DEGRADATION"] = deg_state

        # 4. RUL LOW Alert State (< 10.0 hours remaining)
        rul_state = "LOW" if (rul_hours is not None and rul_hours < 10.0) else "OK"
        if rul_state != self.last_alert_levels.get("RUL_LOW"):
            if rul_state == "LOW":
                msg = f"URGENT: Low RUL remaining ({rul_hours:.1f} hours). Plan engine replacement before next mission."
                advisories.append(msg)
                logger.warning(msg)
            self.last_alert_levels["RUL_LOW"] = rul_state

        # 5. VIBRATION ROLLING BASELINE Alert State (Mean +/- 3*Std)
        vib_val = clean_sample.get("vibration_rms", 0.0)
        self.vibration_history.append(vib_val)
        if len(self.vibration_history) > 30:
            self.vibration_history.pop(0)

        if len(self.vibration_history) >= 10:
            vib_mean = float(np.mean(self.vibration_history[:-1]))
            vib_std = float(np.std(self.vibration_history[:-1]))
            is_vib_anomaly = (vib_val > vib_mean + 3.0 * max(0.1, vib_std)) or (vib_val > 2.8)
        else:
            is_vib_anomaly = vib_val > 2.8

        vib_state = is_vib_anomaly
        if vib_state != self.last_alert_levels.get("VIBRATION_ANOMALY"):
            if vib_state:
                msg = "WARNING: Abnormal vibration pattern detected (Combustion Instability / Mechanical Fluctuation). Inspect cylinder balancing & crankshaft mounts."
                advisories.append(msg)
                logger.warning(msg)
            self.last_alert_levels["VIBRATION_ANOMALY"] = vib_state

        # 6. CARBON COKING / INJECTOR BUILDUP Alert State
        cht_val = clean_sample.get("cht_C", 0.0)
        ff_val = clean_sample.get("fuel_flow_kg_s", 0.0)
        egt_val = clean_sample.get("egt_C", 0.0)
        is_coking = (cht_val > 145.0 and ff_val < 0.0055 and egt_val > 670.0)
        coking_state = is_coking
        if coking_state != self.last_alert_levels.get("CARBON_COKING"):
            if coking_state:
                msg = "ADVISORY: Potential carbon coking / buildup detected on fuel injector tips & exhaust valves. Recommend thermal flush."
                advisories.append(msg)
                logger.info(msg)
            self.last_alert_levels["CARBON_COKING"] = coking_state

        # Nominal State trigger when no active alert state exists
        has_active_alerts = any([
            self.last_alert_levels.get("ANOMALY"),
            self.last_alert_levels.get("FAULT", "normal") != "normal",
            self.last_alert_levels.get("DEGRADATION") in ["ELEVATED", "CRITICAL"],
            self.last_alert_levels.get("RUL_LOW") == "LOW",
            self.last_alert_levels.get("VIBRATION_ANOMALY")
        ])

        if not advisories and not has_active_alerts:
            if self.last_alert_levels.get("SYSTEM_STATE") != "NOMINAL":
                advisories.append("NOMINAL: Engine operating within normal parameters. All sub-systems operational.")
                self.last_alert_levels["SYSTEM_STATE"] = "NOMINAL"
        elif advisories:
            self.last_alert_levels["SYSTEM_STATE"] = "ALERT"

        return advisories

    def simulate_scenario(
        self,
        scenario_name: str = "high_altitude",
        altitude_m: Optional[float] = None,
        ambient_temp_C: Optional[float] = None,
        throttle_profile: Optional[List[float]] = None,
        duration_steps: int = 30
    ) -> Dict[str, Any]:
        """
        Forward predictive simulator projecting hypothetical flight scenarios
        across physics models, feature engineering, and the 4 AI models.
        """
        # Define Scenario Presets
        presets = {
            "high_altitude": {
                "altitude_m": 5500.0,
                "ambient_temp_C": -15.0,
                "throttle_pct": 85.0,
                "description": "High Altitude Operations (5,500m ASL, -15°C Ambient) — Reduced air density & MAP."
            },
            "endurance_mission": {
                "altitude_m": 3000.0,
                "ambient_temp_C": 15.0,
                "throttle_pct": 65.0,
                "description": "Endurance Flight (Long Duration Cruise) — Steady-state thermal load & degradation progression."
            },
            "hot_weather": {
                "altitude_m": 500.0,
                "ambient_temp_C": 45.0,
                "throttle_pct": 75.0,
                "description": "Hot Weather Operation (+45°C Ambient) — High thermal stress on CHT & EGT cooling bounds."
            },
            "rapid_throttle_transitions": {
                "altitude_m": 1500.0,
                "ambient_temp_C": 20.0,
                "throttle_pct": 70.0,
                "description": "Rapid Throttle Transitions — Dynamic power cycling (30% to 95% throttle)."
            }
        }

        scenario_key = scenario_name.lower().replace("-", "_")
        if "rapid" in scenario_key or "throttle" in scenario_key:
            scenario_key = "rapid_throttle_transitions"
        elif "alt" in scenario_key:
            scenario_key = "high_altitude"
        elif "hot" in scenario_key or "desert" in scenario_key:
            scenario_key = "hot_weather"
        elif "endurance" in scenario_key:
            scenario_key = "endurance_mission"

        preset = presets.get(scenario_key, presets["high_altitude"])
        target_alt = altitude_m if altitude_m is not None else preset["altitude_m"]
        target_temp = ambient_temp_C if ambient_temp_C is not None else preset["ambient_temp_C"]
        
        if throttle_profile is None or len(throttle_profile) == 0:
            if scenario_key == "rapid_throttle_transitions":
                profile = [30.0 if (i % 6 < 3) else 95.0 for i in range(duration_steps)]
            else:
                profile = [preset["throttle_pct"]] * duration_steps
        else:
            profile = throttle_profile

        duration_steps = min(200, max(5, len(profile)))

        # Temporary engine state for simulation — reuse preloaded model manager
        sim_feature_engine = DigitalTwinFeatureEngine()
        if hasattr(self, "model_manager") and self.model_manager is not None and getattr(self.model_manager, "_is_loaded", False):
            sim_model_manager = self.model_manager
        else:
            sim_model_manager = DigitalTwinModelManager()
            sim_model_manager.load_all_models()

        trajectory = []

        for step_idx in range(duration_steps):
            th_val = profile[min(step_idx, len(profile) - 1)]
            
            # Physics-informed telemetry projection based on environmental parameters
            p_kPa = max(40.0, 101.325 * ((1.0 - 2.25577e-5 * target_alt) ** 5.25588))
            rho_kg_m3 = p_kPa * 1000.0 / (287.05 * (target_temp + 273.15))
            
            rpm = 1200.0 + th_val * 16.5 + (0.01 * target_alt)
            power_W = (th_val / 100.0) * 85000.0 * (rho_kg_m3 / 1.225)
            torque_Nm = power_W / max(100.0, (rpm * 2.0 * np.pi / 60.0))
            
            cht_base = 70.0 + (th_val * 0.8) + (target_temp * 0.6)
            egt_base = 400.0 + (th_val * 3.5) + (target_temp * 0.4)
            oil_temp_base = 50.0 + (th_val * 0.4) + (target_temp * 0.3)
            oil_press_base = max(1.5, 4.2 - (oil_temp_base - 70.0) * 0.02)
            vib_base = 1.2 + (rpm / 3000.0) * 0.5

            if scenario_key == "hot_weather":
                cht_base += 20.0
                egt_base += 30.0

            raw_sample = {
                "timestamp_s": step_idx * 1.0,
                "engine_id": 99,
                "mission_id": 888,
                "mission_type": f"scenario_{scenario_name}",
                "altitude_m": target_alt,
                "ambient_temp_C": target_temp,
                "pressure_kPa": p_kPa,
                "air_density_kg_m3": rho_kg_m3,
                "throttle_pct": th_val,
                "load_pct": min(100.0, th_val * 0.95),
                "rpm": rpm,
                "air_mass_flow_kg_s": (rpm / 2500.0) * 0.12 * (rho_kg_m3 / 1.225),
                "fuel_flow_kg_s": (power_W / 85000.0) * 0.007,
                "torque_Nm": torque_Nm,
                "power_W": power_W,
                "cht_C": cht_base,
                "egt_C": egt_base,
                "oil_temperature_C": oil_temp_base,
                "oil_pressure_bar": oil_press_base,
                "vibration_rms": vib_base,
                "battery_voltage_V": 28.0,
                "alternator_current_A": 40.0,
                "alternator_health": 1.0,
                "injection_timing_deg": 25.0,
                "expected_rpm": rpm * 0.99,
                "expected_cht_C": cht_base * 0.98,
                "expected_egt_C": egt_base * 0.98,
            }

            fv = sim_feature_engine.generate_all_feature_vectors(raw_sample, sim_model_manager)
            preds = sim_model_manager.predict_all(fv, buffer_len=len(sim_feature_engine.buffer))

            trajectory.append({
                "step": step_idx + 1,
                "timestamp_s": step_idx,
                "telemetry": {
                    "rpm": round(rpm, 1),
                    "throttle_pct": round(th_val, 1),
                    "cht_C": round(cht_base, 1),
                    "egt_C": round(egt_base, 1),
                    "oil_pressure_bar": round(oil_press_base, 2),
                    "vibration_rms": round(vib_base, 3),
                    "altitude_m": round(target_alt, 1),
                    "ambient_temp_C": round(target_temp, 1)
                },
                "health_status": preds["status"],
                "predicted_health_pct": preds["degradation_estimation"]["estimated_health_pct"],
                "predicted_fault": preds["fault_classification"]["predicted_fault"],
                "predicted_rul_hours": preds["rul_prediction"].get("predicted_rul_hours")
            })

        peak_cht = max([t["telemetry"]["cht_C"] for t in trajectory]) if trajectory else 0.0
        peak_egt = max([t["telemetry"]["egt_C"] for t in trajectory]) if trajectory else 0.0
        min_oil_p = min([t["telemetry"]["oil_pressure_bar"] for t in trajectory]) if trajectory else 0.0
        final_health = trajectory[-1]["predicted_health_pct"] if trajectory else 100.0

        return {
            "scenario_name": scenario_name,
            "description": preset.get("description", "Custom hypothetical mission profile simulation."),
            "environmental_inputs": {
                "altitude_m": target_alt,
                "ambient_temp_C": target_temp,
                "duration_steps": duration_steps
            },
            "total_steps": duration_steps,
            "projected_trajectory": trajectory,
            "summary": {
                "peak_cht": round(peak_cht, 1),
                "peak_egt": round(peak_egt, 1),
                "min_oil_pressure_bar": round(min_oil_p, 2),
                "final_health": round(final_health, 1),
                "cooling_margin_status": "DEGRADED_MARGIN" if peak_cht > 155.0 else "ACCEPTABLE"
            }
        }

