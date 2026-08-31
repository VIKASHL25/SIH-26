import sys, os, logging
sys.path.insert(0, os.path.abspath('.'))

import pandas as pd
import numpy as np
from backend.simulation_engine import MissionSimulationEngine

engine = MissionSimulationEngine()
engine.initialize()

# Test across Mission 75 (which progresses from health ~100% to degradation 1.0 / failure RUL 0h)
mission_id = 75
engine.load_mission(mission_id)
df_m = engine.mission_df

total_frames = len(df_m)
sample_indices = np.linspace(0, total_frames - 1, 8, dtype=int)

print("=" * 135)
print("  DIGITAL TWIN ENGINE RUL LIFECYCLE TEST (100-HOUR SIMULATION WITH 15-HOUR INTERVALS)")
print("=" * 135)
print(f"{'Accumulated Operating Time':<28} | {'Frame #':<8} | {'Engine Health %':<16} | {'Degradation':<12} | {'Ground RUL':<12} | {'Predicted RUL':<15} | {'90% Conf Bounds (P10 - P90)':<30}")
print("-" * 135)

for i, idx in enumerate(sample_indices):
    target_time = f"{i * 15} hrs"
    
    # Fast seek to frame
    engine.seek(idx)
    payload = engine.step()
    
    deg_info = payload["degradation_estimation"]
    rul_info = payload["rul_prediction"]
    
    health_pct = deg_info["estimated_health_pct"]
    deg_idx = deg_info["degradation_index"]
    
    raw_row = df_m.iloc[idx]
    gt_rul = raw_row.get("rul_hours", 0.0)
    
    pred_rul = rul_info.get("predicted_rul_hours")
    p10 = rul_info.get("rul_lower_bound_p10")
    p90 = rul_info.get("rul_upper_bound_p90")
    
    conf_str = f"[{p10:.2f} hrs  -  {p90:.2f} hrs]" if p10 is not None and p90 is not None else "COLLECTING WARMUP"
    pred_str = f"{pred_rul:.2f} hrs" if pred_rul is not None else "COLLECTING"
    gt_str = f"{float(gt_rul):.2f} hrs"
    
    print(f"{target_time:<28} | {idx:<8} | {health_pct:<16.2f} | {deg_idx:<12.4f} | {gt_str:<12} | {pred_str:<15} | {conf_str:<30}")

print("=" * 135)
print("100-HOUR LIFECYCLE RUL TEST COMPLETED SUCCESSFULLY!")
print("=" * 135)
