import sys, os
sys.path.insert(0, os.path.abspath("."))
from dotenv import load_dotenv
load_dotenv()

from backend.simulation_engine import MissionSimulationEngine

engine = MissionSimulationEngine(input_mode="csv")
engine.initialize()
engine.load_mission(999)

print("--- 3 NOMINAL TICKS ---")
for i in range(3):
    f = engine.step()
    print(f"Nominal Tick {i+1}: is_anomaly={f['anomaly_detection']['is_anomaly']}, score={f['anomaly_detection']['anomaly_score']}, health={f['health_status']}")

print("\n--- INJECTING +45°C CHT & +60°C EGT FAULT ---")
engine.set_fault_injection({"cht_C": 45.0, "egt_C": 60.0})

for i in range(8):
    f = engine.step()
    print(f"Fault Tick {i+1}: is_anomaly={f['anomaly_detection']['is_anomaly']}, score={f['anomaly_detection']['anomaly_score']}, health={f['health_status']}, cht={f['telemetry']['cht_C']}°C")

print("\n--- CLEARING OVERRIDES ---")
engine.clear_fault_injection()
for i in range(3):
    f = engine.step()
    print(f"Cleared Tick {i+1}: is_anomaly={f['anomaly_detection']['is_anomaly']}, score={f['anomaly_detection']['anomaly_score']}, health={f['health_status']}, cht={f['telemetry']['cht_C']}°C")
