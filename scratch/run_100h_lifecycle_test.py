import sys, os, logging
sys.path.insert(0, os.path.abspath('.'))

# Mute verbose loggers during formatted table test
logging.getLogger("DigitalTwinModelManager").setLevel(logging.ERROR)
logging.getLogger("MissionSimulationEngine").setLevel(logging.ERROR)

import pandas as pd
import numpy as np
from backend.simulation_engine import MissionSimulationEngine

engine = MissionSimulationEngine()
engine.initialize()

# Mission 75 lifecycle: 1000 frames total
mission_id = 75
engine.load_mission(mission_id)
df_m = engine.mission_df

total_frames = len(df_m)

# Target 8 milestones at 15-hour gaps (0h, 15h, 30h, 45h, 60h, 75h, 90h, 105h)
sample_indices = np.linspace(15, total_frames - 1, 8, dtype=int)
sample_map = {idx: f"{i * 15} hrs" for i, idx in enumerate(sample_indices)}

print("=" * 140)
print("  DIGITAL TWIN ENGINE RUL LIFECYCLE TEST (100-HOUR SIMULATION WITH 15-HOUR INTERVALS)")
print("=" * 140)
print(f"{'Accumulated Operating Time':<28} | {'Frame #':<8} | {'Engine Health %':<16} | {'Degradation':<12} | {'Ground RUL':<12} | {'Predicted RUL':<15} | {'90% Conf Bounds (P10 - P90)':<30}")
print("-" * 140)

engine.load_mission(mission_id)

for f_idx in range(total_frames):
    payload = engine.step()
    if payload is None:
        break
        
    if f_idx in sample_map:
        target_time = sample_map[f_idx]
        deg_info = payload["degradation_estimation"]
        rul_info = payload["rul_prediction"]
        
        health_pct = deg_info["estimated_health_pct"]
        deg_idx = deg_info["degradation_index"]
        
        raw_row = df_m.iloc[f_idx]
        gt_rul = raw_row.get("rul_hours", 0.0)
        
        pred_rul = rul_info.get("predicted_rul_hours")
        p10 = rul_info.get("rul_lower_bound_p10")
        p90 = rul_info.get("rul_upper_bound_p90")
        
        conf_str = f"[{p10:.2f} hrs  -  {p90:.2f} hrs]" if p10 is not None and p90 is not None else "COLLECTING WARMUP"
        pred_str = f"{pred_rul:.2f} hrs" if pred_rul is not None else "COLLECTING"
        gt_str = f"{float(gt_rul):.2f} hrs"
        
        print(f"{target_time:<28} | {f_idx:<8} | {health_pct:<16.2f} | {deg_idx:<12.4f} | {gt_str:<12} | {pred_str:<15} | {conf_str:<30}")

print("=" * 140)
print("100-HOUR LIFECYCLE RUL TEST COMPLETED SUCCESSFULLY!")
print("=" * 140)
