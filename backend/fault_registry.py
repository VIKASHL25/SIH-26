"""
Central fault registry for the Digital Twin diagnostic layer.

This registry does NOT perform ML classification.
It defines the engineering metadata used after the existing
fault classifier has produced a result.

Important:
- classifier_label is the label currently supported by the trained model.
- None means the current classifier has not been trained for that scenario.
"""

FAULT_REGISTRY = {
    "F01": {
        "name": "misfire",
        "classifier_label": "misfire",
        "subsystem": "Combustion",
        "signals": [
            "rpm",
            "egt_C",
            "cht_C",
            "fuel_flow_kg_s",
            "rpm_residual",
            "egt_residual",
        ],
        "severity_inputs": [
            "fault_confidence",
            "rpm_residual",
            "egt_residual",
            "degradation_index",
        ],
        "maintenance_advisory": (
            "Inspect spark plugs, ignition system, and combustion stability."
        ),
    },

    "F02": {
        "name": "injector_degradation",
        "classifier_label": "injector_degradation",
        "subsystem": "Combustion",
        "signals": [
            "fuel_flow_kg_s",
            "egt_C",
            "injection_timing_deg",
            "egt_residual",
        ],
        "severity_inputs": [
            "fault_confidence",
            "egt_residual",
            "injection_timing_deg",
            "degradation_index",
        ],
        "maintenance_advisory": (
            "Inspect fuel injection performance and service injectors if degradation persists."
        ),
    },

    "F03": {
        "name": "lubrication_degradation",
        "classifier_label": "lubrication_degradation",
        "subsystem": "Lubrication",
        "signals": [
            "oil_temperature_C",
            "oil_pressure_bar",
        ],
        "severity_inputs": [
            "fault_confidence",
            "oil_temperature_C",
            "oil_pressure_bar",
            "degradation_index",
        ],
        "maintenance_advisory": (
            "Inspect oil level, oil pump, filter, and lubrication system condition."
        ),
    },

    "F04": {
        "name": "cooling_degradation",
        "classifier_label": None,
        "subsystem": "Thermal",
        "signals": [
            "cht_C",
            "egt_C",
            "expected_cht_C",
            "expected_egt_C",
            "cht_residual",
            "egt_residual",
        ],
        "severity_inputs": [
            "cht_residual",
            "egt_residual",
            "degradation_index",
        ],
        "maintenance_advisory": (
            "Inspect the cooling system, airflow, cooling ducts, and thermal management."
        ),
    },

    "F05": {
        "name": "sensor_drift_bias",
        "classifier_label": "sensor_fault",
        "subsystem": "Sensor",
        "signals": [
            "cht_C",
            "egt_C",
            "rpm",
            "oil_temperature_C",
            "oil_pressure_bar",
            "vibration_rms",
        ],
        "severity_inputs": [
            "fault_confidence",
            "sensor_residual",
            "cross_sensor_consistency",
        ],
        "maintenance_advisory": (
            "Check sensor wiring, calibration, plausibility, and telemetry consistency."
        ),
    },

    "F06": {
        "name": "combustion_instability",
        "classifier_label": None,
        "subsystem": "Combustion",
        "signals": [
            "rpm",
            "egt_C",
            "cht_C",
            "fuel_flow_kg_s",
            "injection_timing_deg",
            "rpm_residual",
            "egt_residual",
        ],
        "severity_inputs": [
            "rpm_residual",
            "egt_residual",
            "degradation_index",
        ],
        "maintenance_advisory": (
            "Inspect combustion stability, fuel delivery, ignition, and injection timing."
        ),
    },

    "F07": {
        "name": "vibration_fault",
        "classifier_label": None,
        "subsystem": "Mechanical",
        "signals": [
            "vibration_rms",
            "rpm",
            "torque_Nm",
            "power_W",
        ],
        "severity_inputs": [
            "vibration_rms",
            "vibration_progression",
            "degradation_index",
        ],
        "maintenance_advisory": (
            "Inspect rotating components, mounts, bearings, and mechanical balance."
        ),
    },

    "F08": {
        "name": "overheating",
        "classifier_label": "overheating",
        "subsystem": "Thermal",
        "signals": [
            "cht_C",
            "egt_C",
            "oil_temperature_C",
            "expected_cht_C",
            "expected_egt_C",
            "cht_residual",
            "egt_residual",
        ],
        "severity_inputs": [
            "fault_confidence",
            "cht_residual",
            "egt_residual",
            "oil_temperature_C",
            "degradation_index",
        ],
        "maintenance_advisory": (
            "Inspect cooling performance and investigate the cause of the thermal excursion."
        ),
    },
}


CLASSIFIER_LABEL_TO_FAULT = {
    entry["classifier_label"]: fault_id
    for fault_id, entry in FAULT_REGISTRY.items()
    if entry["classifier_label"] is not None
}


def get_fault_definition(fault_id: str):
    """Return registry metadata for a fault scenario."""
    return FAULT_REGISTRY.get(fault_id)


def get_fault_id_from_classifier_label(label: str):
    """Map an existing XGBoost classifier label to the registered fault ID."""
    return CLASSIFIER_LABEL_TO_FAULT.get(label)