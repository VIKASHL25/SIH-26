import sys, os
sys.path.insert(0, os.path.abspath("."))
import pandas as pd
from backend.simulation_engine import MissionSimulationEngine

engine = MissionSimulationEngine()
engine.initialize()

print("--- TESTING MISSION 999 ---")
engine.load_mission(999)
for i in range(15):
    frame = engine.step()
    ad = frame.get("anomaly_detection", {})
    fc = frame.get("fault_classification", {})
    dg = frame.get("degradation_estimation", {})
    print(f"Frame {i:2d} | Health: {frame.get('health_status'):10s} | Anomaly: {str(ad.get('is_anomaly')):5s} | Score: {ad.get('anomaly_score', 0):+.4f} | Fault: {fc.get('predicted_fault'):15s} | HealthPct: {dg.get('estimated_health_pct')}%")


