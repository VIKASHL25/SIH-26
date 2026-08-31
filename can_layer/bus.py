import can


def create_bus(backend="virtual", channel="engine_bus"):
    """
    Create the CAN transport used by the prototype.

    virtual:
        Cross-platform python-can VirtualBus.
        No CAN hardware required.

    socketcan:
        Linux SocketCAN interface such as can0.
        Used later if real CAN hardware is available.
    """

    if backend == "virtual":
        return can.Bus(
            interface="virtual",
            channel=channel,
            receive_own_messages=False,
        )

    if backend == "socketcan":
        return can.Bus(
            interface="socketcan",
            channel=channel,
        )

    raise ValueError(
        "backend must be 'virtual' or 'socketcan'"
    )
