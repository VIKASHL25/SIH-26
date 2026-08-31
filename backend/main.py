import sys
import os
import json
import argparse
import uvicorn
import logging

# Ensure workspace root is in sys.path when invoked directly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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
    logger.info(f"Running Headless Simulation Demo for Mission {mission_id} ({steps} steps)...")
    engine = MissionSimulationEngine()

    try:
        engine.initialize()
        engine.load_mission(mission_id)

        print("\n" + "="*80)
        print(f"DIGITAL TWIN SIMULATION ENGINE DEMO - MISSION {mission_id}")
        print("="*80)

        for step_num in range(1, steps + 1):
            payload = engine.step()
            if payload is None:
                break

            rul = payload['rul_prediction']
            if rul.get('status') == "COLLECTING_HISTORY":
                rul_str = f"COLLECTING_HISTORY ({rul.get('records_available', 0)}/{rul.get('records_required', 13)} ticks)"
            else:
                rul_str = f"{rul['predicted_rul_hours']} hrs (P10: {rul['rul_lower_bound_p10']}h - P90: {rul['rul_upper_bound_p90']}h | +/-{rul['uncertainty_std_hours']}h | Conf: {rul['confidence_level']})"

            print(f"\n--- [TICK #{step_num}] Timestamp: {payload['timestamp_s']}s | Mission: {payload['mission_id']} ---")
            print(f"RPM: {payload['telemetry']['rpm']} | CHT: {payload['telemetry']['cht_C']} C | EGT: {payload['telemetry']['egt_C']} C | Oil Press: {payload['telemetry']['oil_pressure_bar']} bar")
            print(f"Physics CHT Residual: {payload['physics_model']['cht_residual']} C | Physics Residual C: {payload['physics_model']['physics_residual_C']} C")
            print(f"1. Anomaly Detection: Score {payload['anomaly_detection']['anomaly_score']} | Is Anomaly: {payload['anomaly_detection']['is_anomaly']} (Conf: {payload.get('xai', {}).get('anomaly', {}).get('confidence_display', 'N/A')})")
            print(f"2. Degradation Health: {payload['degradation_estimation']['estimated_health_pct']}% | Index: {payload['degradation_estimation']['degradation_index']} (Source: {payload.get('xai', {}).get('degradation', {}).get('explanation_source', 'N/A')})")
            print(f"3. Fault Classification: {payload['fault_classification']['predicted_fault'].upper()} (Confidence: {payload['fault_classification']['confidence']*100:.1f}%)")
            print(f"4. Remaining Useful Life (RUL): {rul_str}")
            if 'xai' in payload and payload['xai'].get('human_summary'):
                print(f"   >> [XAI Assessment]: {payload['xai']['engineering_interpretation']}")
            print(f"Advisories: {payload['advisories']}")

        print("\n" + "="*80)
        print("SIMULATION DEMO COMPLETED SUCCESSFULLY")
        print("="*80)
    finally:
        if hasattr(engine, "close"):
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
