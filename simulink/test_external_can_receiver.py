import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.can_receiver import CANInputReceiver


CHANNEL = "ff15:7079:7468:6f6e:6465:6d6f:6d63:6173"


def main():
    receiver = CANInputReceiver(
        backend="udp_multicast",
        channel=CHANNEL,
    )

    try:
        print("=== EXTERNAL CAN RECEIVER TEST ===")
        print("Backend: udp_multicast")
        print(f"Channel: {CHANNEL}")
        print("Waiting for telemetry...\n")

        telemetry = receiver.receive_telemetry(timeout=10.0)

        print("Received telemetry:")
        for key, value in telemetry.items():
            print(f"  {key}: {value}")

        print(f"\nSignals received: {len(telemetry)}")

        if len(telemetry) != 20:
            raise RuntimeError(
                f"Expected 20 signals, got {len(telemetry)}"
            )

        print("\nPASS")
        print("External CAN receiver successfully received 20 signals.")

    finally:
        receiver.close()


if __name__ == "__main__":
    main()