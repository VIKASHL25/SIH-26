from typing import Dict, List

import can

from .dbc import load_db

db = load_db()


# ---------------------------------------------------------------------------
# Application telemetry name <-> DBC signal name
# ---------------------------------------------------------------------------

SIGNAL_TO_DBC = {
    "rpm": "RPM",
    "throttle_pct": "Throttle",
    "load_pct": "Load",

    "cht_C": "CHT",
    "egt_C": "EGT",
    "oil_temperature_C": "OilTemperature",
    "oil_pressure_bar": "OilPressure",

    "air_mass_flow_kg_s": "AirMassFlow",
    "fuel_flow_kg_s": "FuelFlow",

    "torque_Nm": "Torque",
    "power_W": "Power",
    "vibration_rms": "Vibration",
    "injection_timing_deg": "InjectionTiming",

    "battery_voltage_V": "BatteryVoltage",
    "alternator_current_A": "AlternatorCurrent",
    "alternator_health": "AlternatorHealth",

    "altitude_m": "Altitude",
    "ambient_temp_C": "AmbientTemperature",
    "pressure_kPa": "Pressure",
    "air_density_kg_m3": "AirDensity",
}


DBC_TO_SIGNAL = {
    dbc_name: normalized_name
    for normalized_name, dbc_name in SIGNAL_TO_DBC.items()
}


# ---------------------------------------------------------------------------
# CAN message definitions
# ---------------------------------------------------------------------------

MESSAGE_SIGNALS = {
    "ENGINE_STATE": [
        "rpm",
        "throttle_pct",
        "load_pct",
    ],

    "THERMAL": [
        "cht_C",
        "egt_C",
        "oil_temperature_C",
        "oil_pressure_bar",
    ],

    "AIR_FUEL": [
        "air_mass_flow_kg_s",
        "fuel_flow_kg_s",
    ],

    "MECHANICAL": [
        "torque_Nm",
        "power_W",
        "vibration_rms",
    ],

    "ELECTRICAL": [
        "battery_voltage_V",
        "alternator_current_A",
        "alternator_health",
    ],

    "ENVIRONMENT": [
        "altitude_m",
        "ambient_temp_C",
        "pressure_kPa",
    ],
    
    "INJECTION": [
        "injection_timing_deg",
    ],

    "AIR_DENSITY": [
        "air_density_kg_m3",
    ],
}


def encode_telemetry(values: Dict[str, float]) -> List[can.Message]:
    """
    Convert normalized telemetry values into grouped CAN frames.

    The DBC determines:
      - CAN arbitration ID
      - signal bit position
      - signal size
      - scaling
      - offset
      - units
    """

    frames = []

    for message_name, normalized_signals in MESSAGE_SIGNALS.items():

        msg_def = db.get_message_by_name(message_name)

        signal_values = {}

        for normalized_name in normalized_signals:

            if normalized_name not in values:
                continue

            dbc_signal_name = SIGNAL_TO_DBC[normalized_name]

            signal_values[dbc_signal_name] = float(
                values[normalized_name]
            )

        # Do not transmit an empty frame.
        if not signal_values:
            continue

        payload = msg_def.encode(signal_values)

        frame = can.Message(
            arbitration_id=msg_def.frame_id,
            data=payload,
            is_extended_id=False,
        )

        frames.append(frame)

    return frames


def decode_frame(frame: can.Message) -> Dict[str, float]:
    """
    Decode one CAN frame into normalized telemetry values.

    Example:

        0x100 -> {
            "rpm": ...,
            "throttle_pct": ...,
            "load_pct": ...
        }
    """

    msg_def = db.get_message_by_frame_id(frame.arbitration_id)

    decoded = msg_def.decode(frame.data)

    telemetry = {}

    for dbc_signal_name, value in decoded.items():

        normalized_name = DBC_TO_SIGNAL.get(dbc_signal_name)

        if normalized_name is None:
            continue

        telemetry[normalized_name] = float(value)

    return telemetry
