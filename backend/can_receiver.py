from collections import OrderedDict
from typing import Dict

from can_layer.bus import create_bus
from can_layer.can_codec import db, decode_frame


class CANInputReceiver:
    """
    Receive telemetry produced by an external CAN source.

    Flow:
        External telemetry source
            -> CAN frames
            -> CANInputReceiver
            -> decode_frame()
            -> normalized telemetry dictionary

    This receiver does NOT transmit anything.
    The existing ML models and feature engine remain
    completely unaware of the CAN transport mechanism.
    """

    def __init__(
        self,
        backend: str = "virtual",
        channel: str = "engine_backend",
    ):
        self.backend = backend
        self.channel = channel

        # Receive-only CAN node.
        self.rx_bus = create_bus(backend, channel)

        # Determine the number of CAN messages used by the
        # current telemetry protocol automatically.
        self.expected_message_ids = {
            message.frame_id
            for message in db.messages
            if message.name in {
                "ENGINE_STATE",
                "THERMAL",
                "AIR_FUEL",
                "MECHANICAL",
                "ELECTRICAL",
                "ENVIRONMENT",
                "INJECTION",
                "AIR_DENSITY",
            }
        }

    def receive_telemetry(
        self,
        timeout: float = 1.0,
    ) -> Dict[str, float]:
        """
        Receive one complete telemetry sample.

        Frames are collected until one frame from every
        telemetry message type has been received.

        Returns:
            Dict containing normalized telemetry signals.
        """

        if not self.expected_message_ids:
            raise RuntimeError(
                "No telemetry CAN message definitions found."
            )

        decoded = OrderedDict()
        received_ids = set()

        while received_ids != self.expected_message_ids:
            frame = self.rx_bus.recv(timeout=timeout)

            if frame is None:
                missing = self.expected_message_ids - received_ids

                raise RuntimeError(
                    "Timed out waiting for CAN telemetry frame. "
                    f"Missing message IDs: "
                    f"{sorted(missing)}"
                )

            # Ignore unrelated CAN frames.
            if frame.arbitration_id not in self.expected_message_ids:
                continue

            decoded_values = decode_frame(frame)

            decoded.update(decoded_values)
            received_ids.add(frame.arbitration_id)

        return dict(decoded)

    def close(self):
        """Safely shut down the CAN receiver."""
        if self.rx_bus is not None:
            self.rx_bus.shutdown()
            self.rx_bus = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()