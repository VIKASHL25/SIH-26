"""
Deterministic diagnostic router.

Uses existing model outputs and engineered sensor relationships to:
- map faults to subsystems
- distinguish possible sensor issues from engine faults
- calculate transparent severity
- provide a unified diagnostic result

No new ML model is created here.
"""

from backend.fault_registry import (
    FAULT_REGISTRY,
    get_fault_id_from_classifier_label,
)


def _safe_float(value, default=0.0):
    """Convert a value to float without crashing on missing data."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalised_magnitude(value, scale):
    """Convert a residual/measurement into a 0-1 magnitude."""
    if scale <= 0:
        return 0.0
    return min(abs(_safe_float(value)) / scale, 1.0)


def _sensor_consistency(sample):
    """
    Estimate whether an abnormal CHT reading is supported by
    other engine/thermal signals.

    This is deliberately conservative:
    an isolated sensor abnormality should not automatically
    become an engine fault.
    """
    checks = 0
    supporting = 0

    cht_residual = _safe_float(sample.get("cht_residual"))
    if "cht_C" in sample and "expected_cht_C" in sample:
        checks += 1
        if abs(cht_residual) > 10:
            supporting += 1

    egt_residual = _safe_float(sample.get("egt_residual"))
    if "egt_C" in sample and "expected_egt_C" in sample:
        checks += 1
        if abs(egt_residual) > 10:
            supporting += 1

    rpm_residual = _safe_float(sample.get("rpm_residual"))
    if "rpm" in sample and "expected_rpm" in sample:
        checks += 1
        if abs(rpm_residual) > 100:
            supporting += 1

    if "oil_temperature_C" in sample:
        checks += 1
        if _safe_float(sample.get("oil_temperature_C")) > 110:
            supporting += 1

    if "oil_pressure_bar" in sample:
        checks += 1
        if _safe_float(sample.get("oil_pressure_bar")) < 2.0:
            supporting += 1

    if "vibration_rms" in sample:
        checks += 1
        if _safe_float(sample.get("vibration_rms")) > 0.5:
            supporting += 1

    if checks == 0:
        return 0.0

    return supporting / checks


def _is_possible_sensor_drift(sample, predicted_fault):
    """
    Detect an isolated sensor abnormality.

    This does NOT claim that sensor drift is proven.
    It only identifies a possible sensor issue when the
    abnormal reading lacks supporting engine evidence.
    """
    # A normal classifier output must also be allowed here.
    if predicted_fault not in {"normal", "overheating", "sensor_fault"}:
        return False

    cht_residual = abs(_safe_float(sample.get("cht_residual")))

    # CHT must actually be abnormal relative to its expected value.
    if cht_residual <= 10:
        return False

    consistency = _sensor_consistency(sample)

    # Low cross-sensor support -> possible sensor problem.
    return consistency < 0.34


def _thermal_event(sample):
    """
    Detect a multi-sensor thermal abnormality using existing
    Digital Twin residuals and telemetry.

    This is an engineering routing heuristic, not a new ML model
    and not a scientifically validated fault threshold.
    """
    cht_residual = abs(_safe_float(sample.get("cht_residual")))
    egt_residual = abs(_safe_float(sample.get("egt_residual")))

    thermal_residuals = 0

    if cht_residual > 10:
        thermal_residuals += 1

    if egt_residual > 10:
        thermal_residuals += 1

    if "oil_temperature_C" in sample:
        if _safe_float(sample.get("oil_temperature_C")) > 110:
            thermal_residuals += 1

    # Require multiple independent thermal indicators.
    return thermal_residuals >= 2


def _calculate_severity(
    fault_confidence,
    degradation_index=0.0,
    residuals=None,
):
    """
    Transparent severity estimate.

    This is an engineering heuristic, NOT a scientifically
    validated severity score.
    """
    residuals = residuals or []

    confidence = max(0.0, min(_safe_float(fault_confidence), 1.0))
    degradation = max(0.0, min(_safe_float(degradation_index), 1.0))

    residual_magnitude = 0.0

    if residuals:
        residual_magnitude = min(
            sum(_normalised_magnitude(value, 50.0) for value in residuals)
            / len(residuals),
            1.0,
        )

    score = (
        0.50 * confidence
        + 0.30 * degradation
        + 0.20 * residual_magnitude
    )

    if score >= 0.75:
        return "CRITICAL"
    if score >= 0.50:
        return "HIGH"
    if score >= 0.25:
        return "MEDIUM"

    return "LOW"


def build_diagnostic(
    sample,
    anomaly_result,
    fault_result,
    degradation_result=None,
):
    """
    Build the unified diagnostic result from existing outputs.

    Existing ML predictions are preserved; this layer adds
    engineering interpretation around them.
    """
    sample = sample or {}
    anomaly_result = anomaly_result or {}
    fault_result = fault_result or {}
    degradation_result = degradation_result or {}

    predicted_fault = str(
        fault_result.get("predicted_fault", "normal")
    )

    fault_confidence = _safe_float(
        fault_result.get("confidence")
    )

    degradation_index = _safe_float(
        degradation_result.get("degradation_index")
    )

    # ---------------------------------------------------------
    # 1. Existing classifier mapping
    # ---------------------------------------------------------
    fault_id = get_fault_id_from_classifier_label(predicted_fault)

    # ---------------------------------------------------------
    # 2. Sensor-vs-engine reasoning
    #
    # This is deliberately checked before accepting overheating.
    # An isolated CHT residual can therefore become F05 even when
    # the existing classifier says normal.
    # ---------------------------------------------------------
    possible_sensor_drift = _is_possible_sensor_drift(
        sample,
        predicted_fault,
    )

    if possible_sensor_drift:
        fault_id = "F05"
        fault_name = "possible_sensor_drift_bias"
        subsystem = "Sensor"
        explanation = (
            "The CHT reading is abnormal relative to the Digital Twin "
            "expectation, but supporting engine signals are largely normal. "
            "This is consistent with a possible sensor drift/bias rather "
            "than confirmed engine overheating."
        )
        advisory = FAULT_REGISTRY["F05"]["maintenance_advisory"]

    # ---------------------------------------------------------
    # 3. Multi-sensor thermal evidence
    #
    # Only route a normal classifier result to overheating when
    # multiple independent thermal indicators support the event.
    # ---------------------------------------------------------
    elif predicted_fault == "normal" and _thermal_event(sample):
        fault_id = "F08"
        definition = FAULT_REGISTRY["F08"]

        fault_name = definition["name"]
        subsystem = definition["subsystem"]
        advisory = definition["maintenance_advisory"]

        explanation = (
            "Multiple thermal indicators deviate from the Digital Twin "
            "baseline, including CHT/EGT and supporting temperature evidence. "
            "The existing classifier returned normal, so this is an "
            "engineering thermal-diagnosis route rather than a new ML class."
        )

    # ---------------------------------------------------------
    # 4. Existing classifier-supported fault
    # ---------------------------------------------------------
    elif fault_id and fault_id in FAULT_REGISTRY:
        definition = FAULT_REGISTRY[fault_id]

        fault_name = definition["name"]
        subsystem = definition["subsystem"]
        advisory = definition["maintenance_advisory"]

        explanation = (
            f"Existing fault classifier identified {fault_name} "
            f"with {fault_confidence:.1%} confidence. "
            f"The registered subsystem is {subsystem}."
        )

    # ---------------------------------------------------------
    # 5. Normal / unmapped classifier output
    # ---------------------------------------------------------
    else:
        fault_id = None
        fault_name = predicted_fault
        subsystem = None
        advisory = None

        if predicted_fault == "normal":
            explanation = (
                "No registered fault was identified by the existing "
                "classifier or the Digital Twin engineering routing rules."
            )
        else:
            explanation = (
                "The existing classifier produced a fault label "
                "that is not mapped to a registered engineering fault."
            )

    # ---------------------------------------------------------
    # 6. Severity
    # ---------------------------------------------------------
    residuals = [
        sample.get("cht_residual"),
        sample.get("egt_residual"),
        sample.get("rpm_residual"),
    ]

    severity = _calculate_severity(
        fault_confidence=fault_confidence,
        degradation_index=degradation_index,
        residuals=residuals,
    )

    # ---------------------------------------------------------
    # 7. Unified diagnostic payload
    # ---------------------------------------------------------
    return {
        "anomaly_detected": bool(
            anomaly_result.get("is_anomaly", False)
            or anomaly_result.get("anomaly_detected", False)
        ),
        "anomaly_score": anomaly_result.get("anomaly_score"),
        "fault_id": fault_id,
        "fault": fault_name,
        "subsystem": subsystem,
        "fault_confidence": fault_confidence,
        "severity": severity,
        "RUL": degradation_result.get(
            "predicted_rul_hours",
            degradation_result.get("RUL"),
        ),
        "time_to_critical": degradation_result.get(
            "time_to_critical"
        ),
        "contributing_features": (
            anomaly_result.get("contributing_features")
            or anomaly_result.get("feature_importance")
            or []
        ),
        "explanation": explanation,
        "maintenance_advisory": advisory,
        "possible_sensor_drift": possible_sensor_drift,
    }
