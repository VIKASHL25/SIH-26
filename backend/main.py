import sys
import json
import argparse
import uvicorn
import logging

from backend.config import DEFAULT_HOST, DEFAULT_PORT
from backend.simulation_engine import MissionSimulationEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DigitalTwinMain")

def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    """Starts the FastAPI WebServer & WebSocket endpoint."""
    logger.info(f"Starting Digital Twin Backend Server on http://{host}:{port}")
    uvicorn.run("backend.api:app", host=host, port=port, reload=False)

def run_cli_simulation(mission_id: int = 1, steps: int = 30):
    """Runs a headless simulation step demo printing state outputs."""

    logger.info(
        f"Running Headless Simulation Demo for Mission "
        f"{mission_id} ({steps} steps)..."
    )

    engine = MissionSimulationEngine()

    try:
        engine.initialize()
        engine.load_mission(mission_id)

        print("\n" + "=" * 80)
        print(
            f"DIGITAL TWIN SIMULATION ENGINE DEMO - "
            f"MISSION {mission_id}"
        )
        print("=" * 80)

        for step_num in range(1, steps + 1):

            payload = engine.step()

            if payload is None:
                break

            rul = payload["rul_prediction"]

            if rul.get("status") == "COLLECTING_HISTORY":
                rul_str = (
                    f"COLLECTING_HISTORY "
                    f"({rul.get('records_available', 0)}/"
                    f"{rul.get('records_required', 13)} ticks)"
                )
            else:
                rul_str = (
                    f"{rul['predicted_rul_hours']} hrs "
                    f"(P10: {rul['rul_lower_bound_p10']}h – "
                    f"P90: {rul['rul_upper_bound_p90']}h | "
                    f"±{rul['uncertainty_std_hours']}h | "
                    f"Conf: {rul['confidence_level']})"
                )

            print(
                f"\n--- [TICK #{step_num}] "
                f"Timestamp: {payload['timestamp_s']}s | "
                f"Mission: {payload['mission_id']} ---"
            )

            print(
                f"RPM: {payload['telemetry']['rpm']} | "
                f"CHT: {payload['telemetry']['cht_C']}°C | "
                f"EGT: {payload['telemetry']['egt_C']}°C | "
                f"Oil Press: "
                f"{payload['telemetry']['oil_pressure_bar']} bar"
            )

            print(
                f"Physics CHT Residual: "
                f"{payload['physics_model']['cht_residual']}°C | "
                f"Physics Residual C: "
                f"{payload['physics_model']['physics_residual_C']}°C"
            )

            print(
                f"1. Anomaly Detection Score: "
                f"{payload['anomaly_detection']['anomaly_score']} "
                f"(Anomaly: "
                f"{payload['anomaly_detection']['is_anomaly']})"
            )

            print(
                f"2. Degradation Health Index: "
                f"{payload['degradation_estimation']['estimated_health_pct']}% "
                f"(Degradation: "
                f"{payload['degradation_estimation']['degradation_index']})"
            )

            print(
                f"3. Fault Classification: "
                f"{payload['fault_classification']['predicted_fault']} "
                f"(Confidence: "
                f"{payload['fault_classification']['confidence'] * 100:.1f}%)"
            )

            print(
                f"4. Remaining Useful Life (RUL): {rul_str}"
            )

            print(f"Advisories: {payload['advisories']}")

        print("\n" + "=" * 80)
        print("SIMULATION DEMO COMPLETED SUCCESSFULLY")
        print("=" * 80)

    finally:
        engine.close()

def main():
    parser = argparse.ArgumentParser(description="MALE UAV Aero Piston Engine Digital Twin Backend CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Server command
    server_parser = subparsers.add_parser("server", help="Launch FastAPI REST & WebSocket server")
    server_parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Host IP address")
    server_parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port number")

    # Run CLI command
    run_parser = subparsers.add_parser("run", help="Run headless simulation replay demo in terminal")
    run_parser.add_argument("--mission", type=int, default=1, help="Mission ID to simulate")
    run_parser.add_argument("--steps", type=int, default=30, help="Number of telemetry steps to simulate")

    args = parser.parse_args()

    if args.command == "server" or args.command is None:
        host = getattr(args, "host", DEFAULT_HOST)
        port = getattr(args, "port", DEFAULT_PORT)
        run_server(host, port)
    elif args.command == "run":
        run_cli_simulation(args.mission, args.steps)

if __name__ == "__main__":
    main()
