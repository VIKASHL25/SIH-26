import can

from can.interfaces.udp_multicast import UdpMulticastBus


CHANNEL = "ff15:7079:7468:6f6e:6465:6d6f:6d63:6173"
PORT = 43113


def main():
    tx = UdpMulticastBus(
        channel=CHANNEL,
        port=PORT,
        receive_own_messages=False,
        fd=True,
    )

    rx = UdpMulticastBus(
        channel=CHANNEL,
        port=PORT,
        receive_own_messages=False,
        fd=True,
    )

    try:
        message = can.Message(
            arbitration_id=0x100,
            data=b"123456789",
            is_extended_id=False,
            is_fd=True,
        )

        print("=== RAW CAN-FD MULTICAST TEST ===")
        print(f"TX data length: {len(message.data)}")
        print(f"TX DLC:         {message.dlc}")
        print(f"TX is_fd:       {message.is_fd}")

        tx.send(message)

        received = rx.recv(timeout=2.0)

        if received is None:
            raise RuntimeError("No CAN-FD message received.")

        print("\nRX:")
        print(f"RX data length: {len(received.data)}")
        print(f"RX DLC:         {received.dlc}")
        print(f"RX is_fd:       {received.is_fd}")
        print(f"RX data:        {received.data}")

        if len(received.data) != 9:
            raise RuntimeError("Received data length is not 9.")

        if not received.is_fd:
            raise RuntimeError("Received message is not CAN-FD.")

        print("\nPASS")
        print("9-byte CAN-FD frame survived UDP multicast.")

    finally:
        tx.shutdown()
        rx.shutdown()


if __name__ == "__main__":
    main()