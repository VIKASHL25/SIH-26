import time
from dataclasses import dataclass
from typing import Iterator

import pandas as pd


@dataclass
class SensorPacket:
    stream_row_id: int
    mission_id: int
    timestamp_s: float
    values: dict


class SensorSimulator:
    """
    Replays a CSV as if sensor telemetry were arriving from an engine.

    The CSV is the source for this prototype. The evaluator/ground-truth file
    is deliberately NOT read by this component.
    """

    REQUIRED = [
        # Engine state
        "rpm",
        "throttle_pct",
        "load_pct",

        # Thermal
        "cht_C",
        "egt_C",
        "oil_temperature_C",
        "oil_pressure_bar",

        # Air / fuel
        "air_mass_flow_kg_s",
        "fuel_flow_kg_s",

        # Mechanical
        "torque_Nm",
        "power_W",
        "vibration_rms",
        "injection_timing_deg",

        # Electrical
        "battery_voltage_V",
        "alternator_current_A",
        "alternator_health",

        # Environment
        "altitude_m",
        "ambient_temp_C",
        "pressure_kPa",
        "air_density_kg_m3",
    ]

    def __init__(self, csv_path: str, rate_hz: float = 0.0):
        self.df = pd.read_csv(csv_path).sort_values(
            ["mission_id", "timestamp_s"]
        ).reset_index(drop=True)

        missing = [c for c in self.REQUIRED if c not in self.df.columns]
        if missing:
            raise ValueError(
                f"Input CSV is missing required sensor columns: {missing}"
            )

        self.rate_hz = rate_hz

    def packets(self) -> Iterator[SensorPacket]:
        delay = 1.0 / self.rate_hz if self.rate_hz > 0 else 0.0

        for row_index, row in self.df.iterrows():
            values = {
                c: float(row[c])
                for c in self.REQUIRED
                if pd.notna(row[c])
            }

            packet = SensorPacket(
                stream_row_id=(
                    int(row["stream_row_id"])
                    if "stream_row_id" in row.index
                    else int(row_index)
                ),
                mission_id=int(row["mission_id"]),
                timestamp_s=float(row["timestamp_s"]),
                values=values,
            )

            yield packet

            if delay:
                time.sleep(delay)
