import re
from typing import Dict, Any, Tuple, Optional, List

# Base sensor dictionary: sensor_key -> (Friendly Name, Unit, Sensor Group / Subsystem)
BASE_SENSOR_MAP: Dict[str, Tuple[str, str, str]] = {
    "cht_C": ("Cylinder Head Temperature (CHT)", "°C", "Thermal System"),
    "egt_C": ("Exhaust Gas Temperature (EGT)", "°C", "Combustion & Exhaust"),
    "oil_temperature_C": ("Engine Oil Temperature", "°C", "Lubrication System"),
    "oil_pressure_bar": ("Engine Oil Pressure", "bar", "Lubrication System"),
    "vibration_rms": ("Engine Vibration (RMS)", "g", "Mechanical / Vibration"),
    "fuel_flow_kg_s": ("Fuel Mass Flow Rate", "kg/s", "Fuel Delivery"),
    "air_mass_flow_kg_s": ("Air Mass Flow Rate", "kg/s", "Air Intake System"),
    "rpm": ("Engine Rotational Speed (RPM)", "RPM", "Powertrain / Speed"),
    "power_W": ("Engine Mechanical Power", "W", "Powertrain / Power"),
    "torque_Nm": ("Engine Torque", "Nm", "Powertrain / Torque"),
    "battery_voltage_V": ("Electrical Bus Voltage", "V", "Electrical System"),
    "alternator_current_A": ("Alternator Current Output", "A", "Electrical System"),
    "alternator_health": ("Alternator Health Index", "score", "Electrical System"),
    "injection_timing_deg": ("Fuel Injection Timing", "deg BTDC", "Ignition & Injection"),
    "cht_residual": ("CHT Physics Model Residual", "°C", "Thermal Physics Residual"),
    "egt_residual": ("EGT Physics Model Residual", "°C", "Combustion Physics Residual"),
    "rpm_residual": ("RPM Physics Model Residual", "RPM", "Mechanical Physics Residual"),
    "physics_residual_C": ("First-Principles Thermal Residual", "°C", "Physics Residual"),
    "altitude_m": ("Flight Altitude", "m", "Flight Envelope"),
    "ambient_temp_C": ("Ambient Temperature", "°C", "Environment"),
    "pressure_kPa": ("Ambient Barometric Pressure", "kPa", "Environment"),
    "air_density_kg_m3": ("Air Density", "kg/m³", "Environment"),
    "throttle_pct": ("Throttle Command", "%", "Flight Control"),
    "throttle": ("Throttle Command", "%", "Flight Control"),
    "load_pct": ("Engine Load", "%", "Flight Control"),
    "load": ("Engine Load", "%", "Flight Control"),
    "fuel_air_ratio": ("Fuel-to-Air Mass Ratio", "ratio", "Combustion Ratios"),
    "power_per_fuel": ("Specific Fuel Energy Conversion", "W/(kg/s)", "Efficiency Ratios"),
    "torque_per_rpm": ("Torque-to-RPM Ratio", "Nm/RPM", "Mechanical Ratios"),
    "power_per_air": ("Power-to-Air Ratio", "W/(kg/s)", "Efficiency Ratios"),
    "egt_rpm_ratio": ("EGT-to-RPM Ratio", "°C/RPM", "Thermodynamic Ratios"),
    "fuel_egt_ratio": ("Fuel-to-EGT Ratio", "kg/(s·°C)", "Thermodynamic Ratios"),
}

# Known compound physics ratios
PHYSICS_RATIOS = {
    "fuel_air_ratio": ("Fuel-Air Equivalence Ratio", "Combustion Chemistry"),
    "power_per_fuel": ("Power per Fuel Flow Efficiency", "Thermodynamic Efficiency"),
    "torque_per_rpm": ("Torque Delivery per RPM", "Mechanical Performance"),
    "power_per_air": ("Power per Air Mass Flow", "Aero Induction Efficiency"),
    "egt_rpm_ratio": ("Exhaust Heat per RPM Ratio", "Combustion Dynamics"),
    "fuel_egt_ratio": ("Fuel Consumption per EGT", "Fuel Economy"),
}

class FeatureMapper:
    """
    Intelligent Feature Name Parser and Engineering-to-Sensor Mapper.
    Translates raw engineered feature strings into human-friendly sensor names,
    mathematical operations, and aggregated sensor subsystem groups.
    """

    def __init__(self, custom_sensor_map: Optional[Dict[str, Tuple[str, str, str]]] = None):
        self.sensor_map = dict(BASE_SENSOR_MAP)
        if custom_sensor_map:
            self.sensor_map.update(custom_sensor_map)

    def parse_feature(self, feature_name: str) -> Dict[str, Any]:
        """
        Parses an engineered feature name into structured metadata.
        Returns:
            - display_name: Short human-readable name
            - base_sensor: Underlying physical signal key
            - sensor_group: High-level subsystem category
            - operation: Engineered transformation type (raw, rollmean, slope, diff, std, lag, delta, ratio)
            - window_or_lag: Numeric window size or lag offset if applicable
            - unit: Engineering physical unit
            - natural_description: Explanatory phrase
        """
        feat = feature_name.strip()

        # Check direct sensor match
        if feat in self.sensor_map:
            friendly_name, unit, group = self.sensor_map[feat]
            return {
                "raw_name": feat,
                "display_name": friendly_name,
                "base_sensor": feat,
                "sensor_group": group,
                "operation": "raw_telemetry",
                "window_or_lag": None,
                "unit": unit,
                "natural_description": f"{friendly_name} current instantaneous measurement"
            }

        # Check ratio match
        if feat in PHYSICS_RATIOS:
            friendly_name, group = PHYSICS_RATIOS[feat]
            return {
                "raw_name": feat,
                "display_name": friendly_name,
                "base_sensor": feat,
                "sensor_group": group,
                "operation": "physics_ratio",
                "window_or_lag": None,
                "unit": "ratio",
                "natural_description": f"{friendly_name} computed thermodynamic ratio"
            }

        # Parse patterns via regex decomposition
        # Sort sensor keys by length descending to match longest prefixes first (e.g. oil_temperature_C before oil_pressure_bar)
        sorted_sensors = sorted(self.sensor_map.keys(), key=len, reverse=True)

        matched_base = None
        matched_friendly = None
        matched_unit = ""
        matched_group = "Engine Subsystem"

        for base in sorted_sensors:
            if feat.startswith(base):
                matched_base = base
                matched_friendly, matched_unit, matched_group = self.sensor_map[base]
                break

        if not matched_base:
            # Fallback if prefix not directly found
            tokens = feat.split("_")
            matched_base = tokens[0]
            matched_friendly = feat.replace("_", " ").title()
            matched_unit = ""
            matched_group = "Engine Parameter"

        suffix = feat[len(matched_base):].lstrip("_")

        # 1. Slope pattern (e.g. slope_6, slope, slope_12)
        slope_match = re.match(r"^slope(?:_(\d+))?$", suffix)
        if slope_match:
            window = slope_match.group(1)
            win_str = f" over {window} samples" if window else " trend"
            return {
                "raw_name": feat,
                "display_name": f"{matched_friendly} Trend",
                "base_sensor": matched_base,
                "sensor_group": matched_group,
                "operation": "slope",
                "window_or_lag": int(window) if window else None,
                "unit": f"{matched_unit}/s" if matched_unit else "rate",
                "natural_description": f"Rate of change / trend in {matched_friendly}{win_str}"
            }

        # 2. Diff pattern (e.g. diff1, diff5, diff10)
        diff_match = re.match(r"^diff(\d+)$", suffix)
        if diff_match:
            lag = diff_match.group(1)
            return {
                "raw_name": feat,
                "display_name": f"{matched_friendly} Change (Δ{lag})",
                "base_sensor": matched_base,
                "sensor_group": matched_group,
                "operation": "diff",
                "window_or_lag": int(lag),
                "unit": matched_unit,
                "natural_description": f"Change in {matched_friendly} over last {lag} sample(s)"
            }

        # 3. Rolling Mean pattern (e.g. rollmean5, rollmean15, roll_mean, mean_3, mean_6)
        rollmean_match = re.match(r"^(?:roll_?mean|mean)(?:_?(\d+))?$", suffix)
        if rollmean_match:
            window = rollmean_match.group(1)
            win_str = f" over last {window} samples" if window else " (recent average)"
            return {
                "raw_name": feat,
                "display_name": f"{matched_friendly} Recent Average",
                "base_sensor": matched_base,
                "sensor_group": matched_group,
                "operation": "rolling_mean",
                "window_or_lag": int(window) if window else None,
                "unit": matched_unit,
                "natural_description": f"Moving average of {matched_friendly}{win_str}"
            }

        # 4. Rolling Standard Deviation pattern (e.g. rollstd5, roll_std, std_3, std_6)
        rollstd_match = re.match(r"^(?:roll_?std|std)(?:_?(\d+))?$", suffix)
        if rollstd_match:
            window = rollstd_match.group(1)
            win_str = f" over last {window} samples" if window else " (recent window)"
            return {
                "raw_name": feat,
                "display_name": f"{matched_friendly} Variability / Fluctuation",
                "base_sensor": matched_base,
                "sensor_group": matched_group,
                "operation": "rolling_std",
                "window_or_lag": int(window) if window else None,
                "unit": matched_unit,
                "natural_description": f"Fluctuation / standard deviation in {matched_friendly}{win_str}"
            }

        # 5. Lag pattern (e.g. lag_1, lag_3, lag12)
        lag_match = re.match(r"^lag_?(\d+)$", suffix)
        if lag_match:
            lag = lag_match.group(1)
            return {
                "raw_name": feat,
                "display_name": f"{matched_friendly} (Lag -{lag})",
                "base_sensor": matched_base,
                "sensor_group": matched_group,
                "operation": "lag",
                "window_or_lag": int(lag),
                "unit": matched_unit,
                "natural_description": f"Historical {matched_friendly} value from {lag} sample(s) ago"
            }

        # 6. Delta / Diff1 pattern
        if suffix in ["delta", "diff"]:
            return {
                "raw_name": feat,
                "display_name": f"{matched_friendly} Instantaneous Change",
                "base_sensor": matched_base,
                "sensor_group": matched_group,
                "operation": "delta",
                "window_or_lag": 1,
                "unit": matched_unit,
                "natural_description": f"Step-to-step delta in {matched_friendly}"
            }

        # Default fallback
        display_name = f"{matched_friendly} ({suffix.replace('_', ' ')})" if suffix else matched_friendly
        return {
            "raw_name": feat,
            "display_name": display_name,
            "base_sensor": matched_base,
            "sensor_group": matched_group,
            "operation": suffix or "raw_feature",
            "window_or_lag": None,
            "unit": matched_unit,
            "natural_description": f"Engineered feature '{feat}' derived from {matched_friendly}"
        }

    def group_contributions_by_sensor(self, contributors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggregates individual engineered feature contributions (e.g. egt_C_slope_6, egt_C_rollmean15)
        into high-level physical sensor groups.
        """
        groups: Dict[str, Dict[str, Any]] = {}

        for item in contributors:
            feat_name = item.get("feature", "")
            parsed = self.parse_feature(feat_name)
            base_sensor = parsed["base_sensor"]
            friendly_name = self.sensor_map.get(base_sensor, (parsed["display_name"], "", "General"))[0]
            subsystem = parsed["sensor_group"]
            importance = float(item.get("importance", abs(item.get("shap_value", item.get("contribution_score", 0.0)))))
            direction = item.get("direction", "neutral")

            if base_sensor not in groups:
                groups[base_sensor] = {
                    "sensor_id": base_sensor,
                    "sensor_name": friendly_name,
                    "subsystem": subsystem,
                    "total_importance": 0.0,
                    "dominant_direction": direction,
                    "supporting_features": [],
                    "features_count": 0
                }

            groups[base_sensor]["total_importance"] += importance
            groups[base_sensor]["features_count"] += 1
            groups[base_sensor]["supporting_features"].append({
                "feature": feat_name,
                "display_name": parsed["display_name"],
                "value": item.get("value"),
                "importance": round(importance, 4),
                "direction": direction,
                "description": parsed["natural_description"]
            })

        # Format and sort aggregated groups by total importance descending
        aggregated = list(groups.values())
        aggregated.sort(key=lambda g: g["total_importance"], reverse=True)

        for g in aggregated:
            g["total_importance"] = round(g["total_importance"], 4)
            # Classify overall contribution magnitude level
            if g["total_importance"] > 0.15:
                g["contribution_level"] = "HIGH"
            elif g["total_importance"] > 0.05:
                g["contribution_level"] = "MEDIUM"
            else:
                g["contribution_level"] = "LOW"

        return aggregated
