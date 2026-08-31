from pathlib import Path
import sys
from collections import OrderedDict
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CAN_LAYER_ROOT = PROJECT_ROOT / "can_layer"

if str(CAN_LAYER_ROOT) not in sys.path:
    sys.path.insert(0, str(CAN_LAYER_ROOT))

from can_layer.bus import create_bus
from can_layer.can_codec import encode_telemetry, decode_frame


class CANTelemetryAdapter:
    """
    Bridges normalized engine telemetry and the CAN layer.

    Flow:
        normalized telemetry
            -> CAN frames
            -> CAN bus
            -> decoded telemetry

    The ML models and feature engine remain completely
    unaware of the CAN protocol.
    """
    SUPPORTED_SIGNALS = {
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
        "injection_timing_deg",

        "battery_voltage_V",
        "alternator_current_A",
        "alternator_health",

        "altitude_m",
        "ambient_temp_C",
        "pressure_kPa",
        "air_density_kg_m3",
    }

    def __init__(
        self,
        backend: str = "virtual",
        channel: str = "engine_backend",
    ):
        self.backend = backend
        self.channel = channel

        # Two CAN nodes:
        # TX = simulated engine/ECU
        # RX = backend telemetry gateway
        self.tx_bus = create_bus(backend, channel)
        self.rx_bus = create_bus(backend, channel)

    def transmit_and_receive(
        self,
        telemetry: Dict[str, float],
        timeout: float = 1.0,
    ) -> Dict[str, float]:
        """
        Encode telemetry into CAN frames, transmit them,
        receive them, and decode them back into normalized
        telemetry.

        Returns:
            Dict containing decoded telemetry signals.
        """

        frames = encode_telemetry(telemetry)

        if not frames:
            raise RuntimeError("No CAN frames generated from telemetry.")

        # ---------------- TRANSMIT ----------------

        for frame in frames:
            self.tx_bus.send(frame)

        # ---------------- RECEIVE ----------------

        decoded = OrderedDict()

        for _ in frames:
            frame = self.rx_bus.recv(timeout=timeout)

            if frame is None:
                raise RuntimeError(
                    "Timed out waiting for CAN telemetry frame."
                )

            decoded_values = decode_frame(frame)
            decoded.update(decoded_values)

        return dict(decoded)

    def close(self):
        """Safely shut down both CAN bus nodes."""
        if self.tx_bus is not None:
            self.tx_bus.shutdown()
            self.tx_bus = None

        if self.rx_bus is not None:
            self.rx_bus.shutdown()
            self.rx_bus = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()