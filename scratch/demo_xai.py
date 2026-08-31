import sys
import os
import time

import textwrap

# Ensure workspace root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.simulation_engine import MissionSimulationEngine

def print_banner(title: str):
    print("\n" + "=" * 88)
    print(f"  {title.center(84)}")
    print("=" * 88)

def print_xai_card(payload: dict, frame_num: int):
    t = payload["telemetry"]
    xai = payload.get("xai", {})
    fault = payload["fault_classification"]
    anom = payload["anomaly_detection"]
    deg = payload["degradation_estimation"]
    rul = payload["rul_prediction"]

    CARD_WIDTH = 84

    print(f"\n+" + "-" * CARD_WIDTH + "+")
    header_left = f"TELEMETRY FRAME #{str(frame_num).ljust(4)} | Time: {str(payload['timestamp_s']) + 's':<6} | Status: {payload['health_status']}"
    print(f"| {header_left:<{CARD_WIDTH-2}} |")
    print(f"+" + "-" * CARD_WIDTH + "+")
    sensors_line = f"SENSORS: RPM: {t['rpm']:<6} | CHT: {str(t['cht_C']) + '°C':<8} | EGT: {str(t['egt_C']) + '°C':<8} | Oil Press: {str(t['oil_pressure_bar']) + ' bar':<10} | Vib: {str(t['vibration_rms']) + 'g':<6}"
    print(f"| {sensors_line:<{CARD_WIDTH-2}} |")
    print(f"+" + "-" * CARD_WIDTH + "+")
    
    anom_line = f"1. ANOMALY DETECTION    : Score {anom['anomaly_score']:<7} | Detected: {str(anom['is_anomaly']):<5} | Confidence: {xai.get('anomaly', {}).get('confidence_display', 'N/A'):<5} ({xai.get('anomaly', {}).get('confidence_type', 'N/A')})"
    print(f"| {anom_line:<{CARD_WIDTH-2}} |")
    
    deg_line = f"2. DEGRADATION ESTIMATE : Health: {str(deg['estimated_health_pct']) + '%':<6} | Index: {deg['degradation_index']:<7} | Source: {xai.get('degradation', {}).get('explanation_source', 'N/A'):<10}"
    print(f"| {deg_line:<{CARD_WIDTH-2}} |")
    
    fault_line = f"3. FAULT CLASSIFICATION : {fault['predicted_fault'].upper():<14} | Confidence: {str(round(fault['confidence']*100, 1)) + '%':<6}"
    print(f"| {fault_line:<{CARD_WIDTH-2}} |")
    
    if rul.get("status") == "COLLECTING_HISTORY":
        rul_text = f"WARM-UP ({rul.get('records_available', 0)}/{rul.get('records_required', 13)} frames collected)"
    else:
        rul_text = f"{rul['predicted_rul_hours']}h (P10: {rul['rul_lower_bound_p10']}h - P90: {rul['rul_upper_bound_p90']}h | Conf: {xai.get('rul', {}).get('confidence_display', 'N/A')})"
    rul_line = f"4. REMAINING USEFUL LIFE: {rul_text}"
    print(f"| {rul_line:<{CARD_WIDTH-2}} |")

    # XAI Diagnostic Drivers
    if xai:
        print(f"+" + "-" * CARD_WIDTH + "+")
        print(f"| >> EXPLAINABLE AI (XAI) TOP DIAGNOSTIC DRIVERS:".ljust(CARD_WIDTH - 1) + " |")
        
        target_exp = xai.get("fault") if fault["predicted_fault"] != "normal" else xai.get("anomaly")
        if target_exp and "top_contributors" in target_exp:
            for item in target_exp["top_contributors"][:3]:
                score_str = f"SHAP: {item.get('shap_value', item.get('importance', 0.0)):+0.3f}"
                driver_line = f"   * {item['display_name']:<38} | {score_str:<14} | {item['direction_text']}"
                print(f"| {driver_line:<{CARD_WIDTH-2}} |")

        print(f"|" + " " * CARD_WIDTH + "|")
        print(f"| >> ENGINEERING ASSESSMENT:".ljust(CARD_WIDTH - 1) + " |")
        interp = xai.get("engineering_interpretation", "")
        for line in textwrap.wrap(interp, width=CARD_WIDTH - 4):
            print(f"|   {line:<{CARD_WIDTH-4}} |")

        if xai.get("recommendations"):
            print(f"|" + " " * CARD_WIDTH + "|")
            print(f"| >> MAINTENANCE ADVISORY / ACTION:".ljust(CARD_WIDTH - 1) + " |")
            for rec in xai["recommendations"]:
                for line in textwrap.wrap(rec, width=CARD_WIDTH - 4):
                    print(f"|   {line:<{CARD_WIDTH-4}} |")

    print(f"+" + "-" * CARD_WIDTH + "+")

def run_interactive_demo():
    print_banner("AERO PISTON ENGINE DIGITAL TWIN - LIVE XAI DEMONSTRATION")
    print("Loading AI/ML models & flight telemetry dataset...")
    
    engine = MissionSimulationEngine()
    engine.initialize()
    engine.load_mission(1)
    
    print("Models and XAI TreeExplainers loaded successfully!\n")

    # Phase 1: Nominal Flight
    print_banner("PHASE 1: NOMINAL CRUISE FLIGHT (Frames 1 - 15)")
    print("Observing standard operational envelope and RUL history buffer warm-up...")
    for i in range(1, 16):
        payload = engine.step()
        if i in [1, 5, 13, 15]:
            print_xai_card(payload, i)
        time.sleep(0.02)

    # Phase 2: Synthetic Overheating Fault Injection
    print_banner("PHASE 2: SYNTHETIC OVERHEATING FAULT INJECTION")
    print("Injecting Thermal Distress: +45 deg C CHT, +65 deg C EGT, +0.25g Vibration...")
    engine.set_fault_injection({
        "cht_C": 45.0,
        "egt_C": 65.0,
        "vibration_rms": 0.25
    })

    for i in range(16, 22):
        payload = engine.step()
        if i in [16, 18, 21]:
            print_xai_card(payload, i)
        time.sleep(0.02)

    # Phase 3: Synthetic Lubrication Fault Injection
    print_banner("PHASE 3: SYNTHETIC LUBRICATION DEGRADATION FAULT")
    print("Injecting Oil System Fault: -2.8 bar Oil Pressure, +35 deg C Oil Temperature...")
    engine.set_fault_injection({
        "oil_pressure_bar": -2.8,
        "oil_temperature_C": 35.0,
        "vibration_rms": 0.20
    })

    for i in range(22, 27):
        payload = engine.step()
        if i in [22, 24, 26]:
            print_xai_card(payload, i)
        time.sleep(0.02)

    # Phase 4: Recovery / Cleared Faults
    print_banner("PHASE 4: CLEARING FAULTS -> RETURN TO NOMINAL CRUISE")
    engine.clear_fault_injection()
    for i in range(27, 30):
        payload = engine.step()
        if i == 29:
            print_xai_card(payload, i)
        time.sleep(0.02)

    print_banner("DEMONSTRATION COMPLETE - ALL 4 MODELS & XAI EXPLAINERS FULLY FUNCTIONAL")

if __name__ == "__main__":
    run_interactive_demo()
