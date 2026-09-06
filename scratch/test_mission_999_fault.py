import sys, os
sys.path.insert(0, os.path.abspath("."))
import pandas as pd
from backend.simulation_engine import MissionSimulationEngine

engine = MissionSimulationEngine()
engine.initialize()

print("--- TESTING MISSION 999 NOMINAL ---")
engine.load_mission(999)
for i in range(3):
    frame = engine.step()
    ad = frame.get("anomaly_detection", {})
    fc = frame.get("fault_classification", {})
    print(f"Nominal Frame {i} -> Health: {frame.get('health_status')}, Anomaly: {ad.get('is_anomaly')}, Score: {ad.get('anomaly_score')}")

print("\n--- INJECTING OVERHEATING FAULT ---")
engine.inject_fault({"cht_C": 45.0})
for i in range(3):
    frame = engine.step()
    ad = frame.get("anomaly_detection", {})
    fc = frame.get("fault_classification", {})
    print(f"Fault Frame {i} -> Health: {frame.get('health_status')}, Anomaly: {ad.get('is_anomaly')}, Score: {ad.get('anomaly_score')}, Fault: {fc.get('predicted_fault')}")

print("\n--- CLEARING FAULT ---")
engine.clear_faults()
for i in range(3):
    frame = engine.step()
    ad = frame.get("anomaly_detection", {})
    fc = frame.get("fault_classification", {})
    print(f"Recovered Frame {i} -> Health: {frame.get('health_status')}, Anomaly: {ad.get('is_anomaly')}, Score: {ad.get('anomaly_score')}")
