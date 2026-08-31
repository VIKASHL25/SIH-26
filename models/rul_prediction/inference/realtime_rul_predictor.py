import os
import numpy as np
import pandas as pd
from collections import deque
from xgboost import XGBRegressor

BASE_DIR=os.path.dirname(os.path.abspath(__file__))
MODEL_FILE_PRIMARY=os.path.join(BASE_DIR,"..","xgboost_rul_model.json")
MODEL_FILE_ALT=os.path.join(BASE_DIR,"..","models","xgboost_rul_model.json")
MODEL_FILE=MODEL_FILE_PRIMARY if os.path.exists(MODEL_FILE_PRIMARY) else MODEL_FILE_ALT

class RealTimeRULPredictor:
    def __init__(self):
        print("====================================")
        print("REAL-TIME RUL PREDICTOR")
        print("====================================")
        self.model=XGBRegressor()
        self.model.load_model(MODEL_FILE)
        print("Model loaded successfully.")
        self.feature_names=self.model.get_booster().feature_names
        if self.feature_names is None:
            raise ValueError("Feature names were not found in the model.")
        print("Model features:",len(self.feature_names))
        if len(self.feature_names)!=131:
            raise ValueError(
                f"Expected 131 features, but model contains {len(self.feature_names)} features."
            )
        self.history_features=[
            "rpm",
            "cht_C",
            "egt_C",
            "oil_temperature_C",
            "oil_pressure_bar",
            "vibration_rms",
            "fuel_flow_kg_s",
            "power_W",
            "torque_Nm"
        ]
        self.base_features=[
            "altitude_m",
            "ambient_temp_C",
            "pressure_kPa",
            "air_density_kg_m3",
            "throttle",
            "load",
            "rpm",
            "air_mass_flow_kg_s",
            "fuel_flow_kg_s",
            "torque_Nm",
            "power_W",
            "cht_C",
            "egt_C",
            "oil_temperature_C",
            "oil_pressure_bar",
            "vibration_rms"
        ]
        self.lags=[1,3,6,12]
        self.windows=[3,6,12]
        self.trend_features=[
            "rpm",
            "cht_C",
            "egt_C",
            "oil_temperature_C",
            "oil_pressure_bar",
            "vibration_rms",
            "fuel_flow_kg_s",
            "power_W"
        ]
        self.difference_features=[
            "rpm",
            "cht_C",
            "egt_C",
            "oil_temperature_C",
            "oil_pressure_bar",
            "vibration_rms",
            "fuel_flow_kg_s",
            "power_W"
        ]
        self.history=deque(maxlen=13)
        self.previous_rul=None
        self.rul_history=deque(maxlen=5)
        self.smoothing_alpha=0.35
        print("Temporal RUL filter enabled.")
        print("Confidence estimation enabled.")
        print("Failure-aware correction enabled.")
        print("Real-time predictor ready.")
        print("====================================")

    def add_record(self,record):
        required_columns=[
            "timestamp_hours",
            "altitude_m",
            "ambient_temp_C",
            "pressure_kPa",
            "air_density_kg_m3",
            "throttle",
            "load",
            "rpm",
            "air_mass_flow_kg_s",
            "fuel_flow_kg_s",
            "torque_Nm",
            "power_W",
            "cht_C",
            "egt_C",
            "oil_temperature_C",
            "oil_pressure_bar",
            "vibration_rms"
        ]
        missing=[
            column for column in required_columns
            if column not in record
        ]
        if missing:
            raise ValueError(
                "Missing input columns: "+str(missing)
            )
        self.history.append(record.copy())

    def create_features(self):
        if len(self.history)<13:
            return None
        df=pd.DataFrame(list(self.history))
        features={}
        for feature in self.base_features:
            features[feature]=float(
                df.iloc[-1][feature]
            )
        for feature in self.history_features:
            for lag in self.lags:
                features[
                    f"{feature}_lag_{lag}"
                ]=float(
                    df.iloc[-1-lag][feature]
                )
        for feature in self.history_features:
            for window in self.windows:
                values=df[feature].iloc[-window:]
                features[
                    f"{feature}_mean_{window}"
                ]=float(
                    values.mean()
                )
        for feature in self.history_features:
            for window in self.windows:
                values=df[feature].iloc[-window:]
                std_value=values.std()
                features[
                    f"{feature}_std_{window}"
                ]=float(
                    std_value
                )
        for feature in self.trend_features:
            for window in [6,12]:
                current_value=float(
                    df.iloc[-1][feature]
                )
                previous_value=float(
                    df.iloc[-1-window][feature]
                )
                elapsed_hours=window*10/60
                features[
                    f"{feature}_slope_{window}"
                ]=(
                    current_value-previous_value
                )/elapsed_hours
        for feature in self.difference_features:
            current_value=float(
                df.iloc[-1][feature]
            )
            previous_value=float(
                df.iloc[-2][feature]
            )
            features[
                f"{feature}_delta"
            ]=(
                current_value-previous_value
            )
        features["timestamp_hours"]=float(
            df.iloc[-1]["timestamp_hours"]
        )
        X=pd.DataFrame([features])
        X=X.reindex(
            columns=self.feature_names
        )
        if X.shape[1]!=131:
            raise ValueError(
                f"Generated {X.shape[1]} features instead of 131."
            )
        if X.isna().any().any():
            missing_features=[
                column for column in X.columns
                if X[column].isna().any()
            ]
            raise ValueError(
                "NaN detected in features: "+
                str(missing_features)
            )
        if np.isinf(X.to_numpy()).any():
            raise ValueError(
                "Infinite value detected in generated features."
            )
        return X.astype(float)

    def apply_temporal_filter(self,raw_rul):
        raw_rul=max(
            0.0,
            float(raw_rul)
        )
        if self.previous_rul is None:
            filtered_rul=raw_rul
        else:
            filtered_rul=(
                self.smoothing_alpha*raw_rul+
                (1-self.smoothing_alpha)*self.previous_rul
            )
            maximum_upward_change=15.0
            if filtered_rul>self.previous_rul+maximum_upward_change:
                filtered_rul=(
                    self.previous_rul+
                    maximum_upward_change
                )
        filtered_rul=max(
            0.0,
            filtered_rul
        )
        self.previous_rul=filtered_rul
        self.rul_history.append(filtered_rul)
        return filtered_rul

    def apply_failure_correction(
        self,
        predicted_rul,
        record
    ):
        predicted_rul=max(
            0.0,
            float(predicted_rul)
        )
        degradation=record.get(
            "degradation",
            None
        )
        health_index=record.get(
            "health_index",
            None
        )
        if degradation is None or health_index is None:
            return predicted_rul
        degradation=float(
            degradation
        )
        health_index=float(
            health_index
        )
        degradation=np.clip(
            degradation,
            0.0,
            1.0
        )
        health_index=np.clip(
            health_index,
            0.0,
            1.0
        )
        # ============================================================
        # FINAL FAILURE
        # Only force zero when the engine is genuinely at failure.
        # This prevents 50-25 hours remaining from becoming zero.
        # ============================================================
        if (
            degradation>=0.9995 and
            health_index<=0.001
        ):
            return 0.0
        # ============================================================
        # VERY NEAR FAILURE
        # Gradually pull the prediction down instead of forcing zero.
        # ============================================================
        if (
            degradation>=0.995 and
            health_index<=0.005
        ):
            correction_strength=0.75
            corrected_rul=(
                predicted_rul*
                (1.0-correction_strength)
            )
            corrected_rul=min(
                corrected_rul,
                25.0
            )
            return max(
                corrected_rul,
                0.0
            )
        # ============================================================
        # CRITICAL REGION
        # Keep a non-zero estimate while approaching failure.
        # ============================================================
        if (
            degradation>=0.985 and
            health_index<=0.015
        ):
            correction_strength=0.40
            corrected_rul=(
                predicted_rul*
                (1.0-correction_strength)
            )
            corrected_rul=min(
                corrected_rul,
                45.0
            )
            return max(
                corrected_rul,
                0.0
            )
        # ============================================================
        # LATE WARNING REGION
        # Mild correction only.
        # ============================================================
        if (
            degradation>=0.97 and
            health_index<=0.03
        ):
            correction_strength=0.15
            corrected_rul=(
                predicted_rul*
                (1.0-correction_strength)
            )
            return max(
                corrected_rul,
                0.0
            )
        return predicted_rul

    def get_confidence(self):
        history_count=len(
            self.history
        )
        if history_count<13:
            return "LOW",0.0
        if len(self.rul_history)<3:
            return "LOW",35.0
        values=np.array(
            self.rul_history,
            dtype=float
        )
        mean_rul=float(
            np.mean(values)
        )
        std_rul=float(
            np.std(values)
        )
        if mean_rul<=1:
            return "HIGH",95.0
        relative_variation=(
            std_rul/
            max(mean_rul,1.0)
        )
        if history_count<30:
            base_confidence=50.0
        elif history_count<60:
            base_confidence=65.0
        elif history_count<120:
            base_confidence=75.0
        else:
            base_confidence=85.0
        if relative_variation<0.02:
            confidence=base_confidence+10.0
        elif relative_variation<0.05:
            confidence=base_confidence
        elif relative_variation<0.10:
            confidence=base_confidence-10.0
        else:
            confidence=base_confidence-20.0
        confidence=max(
            0.0,
            min(95.0,confidence)
        )
        if confidence>=80:
            level="HIGH"
        elif confidence>=60:
            level="MEDIUM"
        else:
            level="LOW"
        return level,confidence

    def get_health_status(self,rul):
        if rul>300:
            return "HEALTHY"
        elif rul>150:
            return "MONITOR"
        elif rul>50:
            return "WARNING"
        else:
            return "CRITICAL"

    def predict(self,record):
        self.add_record(record)
        X=self.create_features()
        if X is None:
            return {
                "status":"COLLECTING_HISTORY",
                "records_available":len(
                    self.history
                ),
                "records_required":13
            }
        raw_rul=float(
            self.model.predict(X)[0]
        )
        raw_rul=max(
            0.0,
            raw_rul
        )
        filtered_rul=self.apply_temporal_filter(
            raw_rul
        )
        final_rul=self.apply_failure_correction(
            filtered_rul,
            record
        )
        confidence_level,confidence_score=(
            self.get_confidence()
        )
        health_status=self.get_health_status(
            final_rul
        )
        return {
            "status":"PREDICTED",
            "timestamp_hours":float(
                record["timestamp_hours"]
            ),
            "raw_rul_hours":raw_rul,
            "filtered_rul_hours":filtered_rul,
            "rul_hours":final_rul,
            "health_status":health_status,
            "confidence":confidence_level,
            "confidence_score":confidence_score
        }

    def reset(self):
        self.history.clear()
        self.previous_rul=None
        self.rul_history.clear()
        print(
            "Engine history and RUL history cleared."
        )

if __name__=="__main__":
    predictor=RealTimeRULPredictor()
    print()
    print(
        "Waiting for engine telemetry..."
    )
    print()
    for i in range(100):
        timestamp=i*(10/60)
        degradation=min(
            1.0,
            timestamp/850.0
        )
        health_index=max(
            0.0,
            1.0-degradation
        )
        record={
            "timestamp_hours":timestamp,
            "altitude_m":4000.0,
            "ambient_temp_C":14.0,
            "pressure_kPa":61.64,
            "air_density_kg_m3":0.748,
            "throttle":0.65,
            "load":0.60,
            "rpm":4800.0,
            "air_mass_flow_kg_s":0.45,
            "fuel_flow_kg_s":0.025,
            "torque_Nm":55.0,
            "power_W":27646.0,
            "cht_C":140.0,
            "egt_C":650.0,
            "oil_temperature_C":85.0,
            "oil_pressure_bar":3.5,
            "vibration_rms":0.30,
            "degradation":degradation,
            "health_index":health_index
        }
        result=predictor.predict(
            record
        )
        print(
            f"Time: {timestamp:.2f} h | "
            f"Status: {result['status']}"
        )
        if result["status"]=="PREDICTED":
            print(
                f"Raw RUL: "
                f"{result['raw_rul_hours']:.2f} h | "
                f"Filtered RUL: "
                f"{result['filtered_rul_hours']:.2f} h | "
                f"Final RUL: "
                f"{result['rul_hours']:.2f} h | "
                f"Confidence: "
                f"{result['confidence']} "
                f"({result['confidence_score']:.1f}%) | "
                f"Health: "
                f"{result['health_status']}"
            )
        else:
            print(
                f"History: "
                f"{result['records_available']}/"
                f"{result['records_required']}"
            )
        print()