import can


UDP_MULTICAST_CHANNEL = "ff15:7079:7468:6f6e:6465:6d6f:6d63:6173"
UDP_MULTICAST_PORT = 43113


def create_bus(backend="virtual", channel="engine_bus"):
    """
    Create the CAN transport used by the prototype.

    virtual:
        Cross-platform python-can VirtualBus.
        No CAN hardware required.

    udp_multicast:
        Inter-process CAN transport using UDP multicast.
        Uses CAN-FD because the project's CAN frames contain
        an additional integrity-checksum byte.

    socketcan:
        Linux SocketCAN interface such as can0.
    """

    if backend == "virtual":
        return can.Bus(
            interface="virtual",
            channel=channel,
            receive_own_messages=False,
        )

    if backend == "udp_multicast":
        return can.Bus(
            interface="udp_multicast",
            channel=channel or UDP_MULTICAST_CHANNEL,
            port=UDP_MULTICAST_PORT,
            receive_own_messages=False,
            fd=True,
        )

    if backend == "socketcan":
        return can.Bus(
            interface="socketcan",
            channel=channel,
        )

    raise ValueError(
        "backend must be 'virtual', 'udp_multicast', or 'socketcan'"
    )