import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from can_layer.bus import create_bus
from can_layer.can_codec import encode_telemetry
from backend.can_receiver import CANInputReceiver


TEST_CHANNEL = "can_receiver_test"

TEST_TELEMETRY = {
    "rpm": 2317.25,
    "throttle_pct": 70.0,
    "load_pct": 55.0,
    "cht_C": 132.89,
    "egt_C": 665.45,
    "oil_temperature_C": 92.3,
    "oil_pressure_bar": 3.766,
    "air_mass_flow_kg_s": 0.0123,
    "fuel_flow_kg_s": 0.0012,
    "torque_Nm": 12.34,
    "power_W": 2828.0,
    "vibration_rms": 0.123,
    "battery_voltage_V": 24.5,
    "alternator_current_A": 8.2,
    "alternator_health": 0.98,
    "altitude_m": 1500.0,
    "ambient_temp_C": 25.0,
    "pressure_kPa": 84.5,
    "injection_timing_deg": 18.5,
    "air_density_kg_m3": 1.06,
}


def main():
    tx_bus = create_bus("virtual", TEST_CHANNEL)
    receiver = CANInputReceiver(
        backend="virtual",
        channel=TEST_CHANNEL,
    )

    try:
        frames = encode_telemetry(TEST_TELEMETRY)

        print("\n=== CAN RECEIVER TEST ===")
        print(f"Frames generated: {len(frames)}")

        for frame in frames:
            tx_bus.send(frame)

        decoded = receiver.receive_telemetry()

        print(f"Signals decoded:  {len(decoded)}")

        if len(decoded) != 20:
            raise AssertionError(
                f"Expected 20 signals, got {len(decoded)}"
            )

        print("PASS")
        print("All 20 telemetry signals received and decoded.")

    finally:
        receiver.close()
        tx_bus.shutdown()


if __name__ == "__main__":
    main()