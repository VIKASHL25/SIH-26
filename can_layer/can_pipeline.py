import argparse
import time
from collections import OrderedDict

import pandas as pd

from .bus import create_bus
from .can_codec import decode_frame, encode_telemetry
from .sensor_simulator import SensorSimulator


def run(
    csv_path: str,
    output_path: str = "decoded_telemetry.csv",
    backend: str = "virtual",
    channel: str = "engine_bus",
    rate_hz: float = 0.0,
):
    """
    Full prototype:

    CSV
      -> Sensor Simulator
      -> CAN Encoder
      -> CAN Frames
      -> CAN Bus
      -> CAN Decoder + DBC
      -> Telemetry Packet
    """

    simulator = SensorSimulator(csv_path, rate_hz=rate_hz)

    # Two nodes share the same virtual CAN channel:
    # TX node publishes frames; RX node represents the telemetry gateway.
    tx_bus = create_bus(backend, channel)
    rx_bus = create_bus(backend, channel)

    outputs = []

    try:
        for packet in simulator.packets():
            frames = encode_telemetry(packet.values)

            # ---------------- CAN BUS ----------------
            # Sensor/ECU-side node publishes frames.
            for frame in frames:
                tx_bus.send(frame)

            # Telemetry gateway receives and decodes the frames.
            decoded = OrderedDict()
            deadline = time.monotonic() + 1.0

            while len(decoded) < len(frames):
                remaining = max(0.0, deadline - time.monotonic())
                frame = rx_bus.recv(timeout=remaining)

                if frame is None:
                    raise RuntimeError(
                        "Timed out waiting for CAN frames for "
                        f"stream row {packet.stream_row_id}"
                    )

                decoded_dict = decode_frame(frame)
                decoded.update(decoded_dict)

            telemetry_packet = {
                "stream_row_id": packet.stream_row_id,
                "mission_id": packet.mission_id,
                "timestamp_s": packet.timestamp_s,
                **decoded,
            }

            outputs.append(telemetry_packet)

            print(
                f"[CAN] row={packet.stream_row_id:04d} | "
                f"RPM={decoded.get('rpm', float('nan')):.1f} | "
                f"EGT={decoded.get('egt_C', float('nan')):.1f} | "
                f"CHT={decoded.get('cht_C', float('nan')):.1f} | "
                f"OilP={decoded.get('oil_pressure_bar', float('nan')):.2f}"
            )

    finally:
        tx_bus.shutdown()
        rx_bus.shutdown()

    result = pd.DataFrame(outputs)
    result.to_csv(output_path, index=False)

    print(f"\nDecoded telemetry saved to: {output_path}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="decoded_telemetry.csv")

    parser.add_argument(
        "--backend",
        choices=["virtual", "socketcan"],
        default="virtual",
        help="virtual is cross-platform; socketcan is for Linux CAN hardware",
    )

    parser.add_argument("--channel", default="engine_bus")

    parser.add_argument(
        "--rate-hz",
        type=float,
        default=0.0,
        help="0 = as fast as possible; 1 = approximately one packet/sec",
    )

    args = parser.parse_args()

    run(
        csv_path=args.input,
        output_path=args.output,
        backend=args.backend,
        channel=args.channel,
        rate_hz=args.rate_hz,
    )
