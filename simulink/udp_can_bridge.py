import sys
import can
from pathlib import Path

# The bridge logs Unicode arrows; make it safe to launch from a default
# Windows PowerShell console using the system's non-UTF-8 code page.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from websockets import frames

# Allow imports from the repository root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from can_layer.can_codec import encode_telemetry, decode_frame
from can_layer.bus import create_bus

from udp_receiver import create_receiver, receive_telemetry


CAN_BACKEND = "udp_multicast"
CAN_CHANNEL = "ff15:7079:7468:6f6e:6465:6d6f:6d63:6173"


def telemetry_to_can(telemetry, tx_bus):
    """
    Send one UDP-derived telemetry dictionary through
    the existing CAN encoder and decoder.
    """

    frames = encode_telemetry(telemetry)

    for frame in frames:
        fd_frame = can.Message(
            arbitration_id=frame.arbitration_id,
            data=frame.data,
            is_extended_id=frame.is_extended_id,
            is_fd=True,
        )
        tx_bus.send(fd_frame)

    # The bridge's job is to publish CAN frames. Decode the same encoded
    # frames locally for logging instead of opening a second multicast
    # receive socket that can compete with the backend receiver on Windows.
    decoded = {}
    for frame in frames:
        decoded.update(decode_frame(frame))

    return decoded


def main():

    # UDP receiver
    udp_sock = create_receiver()

    # Existing CAN infrastructure
    tx_bus = create_bus(
        CAN_BACKEND,
        CAN_CHANNEL,
    )

    print("\n=== SIMULINK → UDP → CAN BRIDGE ===")
    print("UDP: 127.0.0.1:5005")
    print(f"CAN backend: {CAN_BACKEND}")
    print(f"CAN channel: {CAN_CHANNEL}")
    print("Waiting for Simulink telemetry...\n")

    packet_count = 0

    try:

        while True:

            # ------------------------------------------------
            # 1. Receive telemetry from Simulink
            # ------------------------------------------------

            telemetry, addr = receive_telemetry(
                udp_sock
            )

            packet_count += 1

            # ------------------------------------------------
            # 2. Send through existing CAN pipeline
            # ------------------------------------------------

            decoded = telemetry_to_can(
                telemetry,
                tx_bus,
            )

            # ------------------------------------------------
            # 3. Display result
            # ------------------------------------------------

            print(
                f"[PACKET {packet_count:04d}] "
                f"UDP→CAN | "
                f"RPM={telemetry['rpm']:.2f} → {decoded['rpm']:.2f} | "
                f"CHT={telemetry['cht_C']:.2f} → {decoded['cht_C']:.2f} | "
                f"EGT={telemetry['egt_C']:.2f} → {decoded['egt_C']:.2f} | "
                f"OilP={telemetry['oil_pressure_bar']:.3f} → "
                f"{decoded['oil_pressure_bar']:.2f}"
            )

    except KeyboardInterrupt:

        print("\nBridge stopped.")

    finally:

        udp_sock.close()
        tx_bus.shutdown()


if __name__ == "__main__":
    main()
