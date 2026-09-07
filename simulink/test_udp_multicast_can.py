import sys
import can
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from can_layer.bus import create_bus
from can_layer.can_codec import encode_telemetry, decode_frame


CHANNEL = "ff15:7079:7468:6f6e:6465:6d6f:6d63:6173"
BACKEND = "udp_multicast"


TELEMETRY = {
    "rpm": 2317.25,
    "throttle_pct": 70.0,
    "load_pct": 70.75,
    "cht_C": 132.89,
    "egt_C": 665.45,
    "oil_temperature_C": 74.3,
    "oil_pressure_bar": 3.766,
    "air_mass_flow_kg_s": 0.06444,
    "fuel_flow_kg_s": 0.005013,
    "torque_Nm": 251.53,
    "power_W": 61036.1,
    "vibration_rms": 0.7529,
    "battery_voltage_V": 28.077,
    "alternator_current_A": 40.55,
    "alternator_health": 1.0,
    "altitude_m": 15.24,
    "ambient_temp_C": 25.0,
    "pressure_kPa": 100.726,
    "injection_timing_deg": 24.59,
    "air_density_kg_m3": 1.17692,
}


def main():
    tx_bus = create_bus(BACKEND, CHANNEL)
    rx_bus = create_bus(BACKEND, CHANNEL)

    try:
        frames = encode_telemetry(TELEMETRY)

        print("=== UDP MULTICAST CAN TEST ===")
        print(f"Backend: {BACKEND}")
        print(f"Channel: {CHANNEL}")
        print(f"Frames generated: {len(frames)}")

        decoded = {}

        for frame in frames:
            fd_frame = can.Message(
                arbitration_id=frame.arbitration_id,
                data=frame.data,
                is_extended_id=frame.is_extended_id,
                is_fd=True,
            )

            print(
                f"TX ID={hex(fd_frame.arbitration_id)} "
                f"DLC={fd_frame.dlc} "
                f"is_fd={fd_frame.is_fd}"
            )

            tx_bus.send(fd_frame)

            received = rx_bus.recv(timeout=2.0)

            if received is None:
                raise RuntimeError(
                    f"Timed out waiting for CAN frame "
                    f"{hex(fd_frame.arbitration_id)}"
                )

            print(
                f"RX ID={hex(received.arbitration_id)} "
                f"DLC={received.dlc} "
                f"is_fd={received.is_fd}"
            )

            decoded.update(decode_frame(received))

        print(f"\nSignals decoded:  {len(decoded)}")

        if len(decoded) != 20:
            raise RuntimeError(
                f"Expected 20 signals, got {len(decoded)}"
            )

        print("PASS")
        print("All 20 telemetry signals survived UDP multicast CAN.")

    finally:
        tx_bus.shutdown()
        rx_bus.shutdown()

if __name__ == "__main__":
    main()