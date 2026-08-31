import time
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

from backend.config import DATASET_100K_PATH
from backend.model_loader import DigitalTwinModelManager
from backend.feature_engine import DigitalTwinFeatureEngine

logger = logging.getLogger("MissionSimulationEngine")

class MissionSimulationEngine:
    """
    Core Simulation & Mission Replay Engine for Aero Piston Engine Digital Twin.
    
    Integrates:
    1. Historical flight telemetry streaming & mission replay.
    2. Dynamic parameter overrides & synthetic fault injection.
    3. Unified 4-Model real-time AI/ML inference execution.
    4. Mission health monitoring & advisory generation.
    """

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

        # Model Manager & Feature Engine
        self.model_manager = DigitalTwinModelManager()
        self.feature_engine = DigitalTwinFeatureEngine()

        # Fault Injection Overrides
        self.fault_overrides: Dict[str, float] = {}
        self.env_overrides: Dict[str, float] = {}

    def initialize(self):
        """Loads dataset and models."""
        logger.info("Initializing Mission Simulation Engine...")
        
        # Load Models
        self.model_manager.load_all_models()

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
        if self.df_raw is not None and "mission_id" in self.df_raw.columns:
            return sorted(self.df_raw["mission_id"].unique().tolist())
        return []

    def load_mission(self, mission_id: int):
        """Loads a specific mission dataset for replay."""
        if self.df_raw is None:
            raise ValueError("Dataset not loaded.")
        
        filtered = self.df_raw[self.df_raw["mission_id"] == mission_id].copy()
        if filtered.empty:
            raise ValueError(f"Mission ID {mission_id} not found in dataset.")

        self.active_mission_id = mission_id
        self.mission_df = filtered.sort_values("timestamp_s").reset_index(drop=True)
        self.current_frame_idx = 0
        self.feature_engine.reset()
        self.state = "PAUSED"
        logger.info(f"Loaded Mission {mission_id} ({len(self.mission_df)} frames).")

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

    def step(self) -> Optional[Dict[str, Any]]:
        """Advances simulation by 1 tick and evaluates all 4 models."""
        if self.mission_df is None or self.mission_df.empty:
            return None

        if self.current_frame_idx >= len(self.mission_df):
            self.current_frame_idx = 0

        # Get raw telemetry row
        raw_row = self.mission_df.iloc[self.current_frame_idx].to_dict()

        # Apply synthetic overrides if active
        for param, delta_or_val in self.fault_overrides.items():
            if param in raw_row:
                raw_row[param] = float(raw_row[param]) + delta_or_val

        # Advance frame index for next step
        self.current_frame_idx += 1

        # Process through feature engine & generate model feature vectors
        fv = self.feature_engine.generate_all_feature_vectors(raw_row, self.model_manager)

        # Run inference across all 4 models
        predictions = self.model_manager.predict_all(fv, anomaly_threshold=self.anomaly_threshold)

        # Generate Maintenance Advisory
        advisories = self._generate_maintenance_advisories(predictions, fv["clean_sample"])

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
            "advisories": advisories
        }

        return payload

    def _generate_maintenance_advisories(self, predictions: dict, clean_sample: dict) -> List[str]:
        advisories = []
        
        fault = predictions["fault_classification"]["predicted_fault"]
        confidence = predictions["fault_classification"]["confidence"]
        rul_hours = predictions["rul_prediction"]["predicted_rul_hours"]
        is_anomaly = predictions["anomaly_detection"]["is_anomaly"]
        health_pct = predictions["degradation_estimation"]["estimated_health_pct"]

        if is_anomaly:
            advisories.append("CRITICAL: Operating parameters deviate significantly from normal baseline envelope.")

        if fault == "overheating":
            advisories.append(f"WARNING: Cylinder/Exhaust Overheating trend detected ({confidence*100:.1f}% confidence). Inspect cooling duct & mixture ratio.")
        elif fault == "lubrication_degradation":
            advisories.append(f"WARNING: Oil Pressure / Temperature abnormality detected ({confidence*100:.1f}% confidence). Check oil pump and filter.")
        elif fault == "injector_degradation":
            advisories.append(f"WARNING: Fuel Injection anomaly detected ({confidence*100:.1f}% confidence). Service fuel injectors.")
        elif fault == "misfire":
            advisories.append(f"WARNING: Engine misfire condition detected ({confidence*100:.1f}% confidence). Inspect spark plugs & ignition system.")
        elif fault == "sensor_fault":
            advisories.append(f"NOTICE: Sensor telemetry drift detected. Calibrate engine sensors.")

        if health_pct < 70.0:
            advisories.append(f"ALERT: Engine degradation level elevated (Health Index: {health_pct}%). Schedule depot maintenance.")

        if rul_hours < 25.0:
            advisories.append(f"URGENT: Low RUL remaining ({rul_hours} hours). Plan engine swap before next endurance mission.")

        if not advisories:
            advisories.append("NOMINAL: Engine operating within normal parameters. All sub-systems operational.")

        return advisories
