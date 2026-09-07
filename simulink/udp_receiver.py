import socket
import struct


HOST = "127.0.0.1"
PORT = 5005

SIGNAL_NAMES = [
    "rpm",
    "throttle_pct",
    "load_pct",
    "cht_C",
    "egt_C",
    "oil_temperature_C",
    "oil_pressure_bar",
    "air_mass_flow_kg_s",
    "fuel_flow_kg_s",
    "torque_Nm",
    "power_W",
    "vibration_rms",
    "battery_voltage_V",
    "alternator_current_A",
    "alternator_health",
    "altitude_m",
    "ambient_temp_C",
    "pressure_kPa",
    "injection_timing_deg",
    "air_density_kg_m3",
]

PACKET_FORMAT = ">20d"
PACKET_SIZE = struct.calcsize(PACKET_FORMAT)


def create_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    return sock


def receive_telemetry(sock):
    """
    Receive and decode one 20-signal telemetry packet.
    """

    data, addr = sock.recvfrom(4096)

    if len(data) != PACKET_SIZE:
        raise ValueError(
            f"Invalid UDP packet size: {len(data)} bytes "
            f"(expected {PACKET_SIZE})"
        )

    values = struct.unpack(PACKET_FORMAT, data)

    telemetry = dict(zip(SIGNAL_NAMES, values))

    return telemetry, addr


if __name__ == "__main__":

    sock = create_receiver()

    print(f"Listening for UDP telemetry on {HOST}:{PORT}")
    print(f"Expected packet size: {PACKET_SIZE} bytes")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:

            telemetry, addr = receive_telemetry(sock)

            print(
                f"RPM={telemetry['rpm']:.2f} | "
                f"Throttle={telemetry['throttle_pct']:.2f}% | "
                f"Load={telemetry['load_pct']:.2f}% | "
                f"CHT={telemetry['cht_C']:.2f} C | "
                f"EGT={telemetry['egt_C']:.2f} C | "
                f"OilP={telemetry['oil_pressure_bar']:.3f} bar | "
                f"Vib={telemetry['vibration_rms']:.4f} g"
            )

    except KeyboardInterrupt:
        print("\nReceiver stopped.")

    finally:
        sock.close()