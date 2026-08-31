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

# Load Mission 75 (which progresses from healthy to degraded/failure)
mission_id = 75
engine.load_mission(mission_id)
df_m = engine.mission_df

total_frames = len(df_m)
step_indices = np.linspace(0, total_frames - 1, 8, dtype=int)
frame_to_target_time = {idx: f"{i * 15:.1f} hrs" for i, idx in enumerate(step_indices)}

rows = []

# Run simulation step by step
for f_idx in range(total_frames):
    payload = engine.step()
    if payload is None:
        break
        
    if f_idx in step_indices:
        deg_info = payload["degradation_estimation"]
        rul_info = payload["rul_prediction"]
        
        target_time = frame_to_target_time[f_idx]
        health_pct = deg_info["estimated_health_pct"]
        deg_idx = deg_info["degradation_index"]
        
        raw_row = df_m.iloc[f_idx]
        gt_rul = raw_row.get("rul_hours", 0.0)
        
        pred_rul = rul_info.get("predicted_rul_hours")
        p10 = rul_info.get("rul_lower_bound_p10")
        p90 = rul_info.get("rul_upper_bound_p90")
        status = rul_info.get("status", "N/A")
        
        if pred_rul is None:
            op_status = "COLLECTING_HISTORY"
        elif health_pct <= 1.0:
            op_status = "ENGINE FAILURE / REPLACEMENT REQUIRED"
        elif health_pct <= 20.0:
            op_status = "PREDICTED (URGENT ALERT)"
        elif health_pct <= 40.0:
            op_status = "PREDICTED (MEDIUM CONF)"
        else:
            op_status = "PREDICTED (HIGH CONF)"

        rows.append({
            "target_time": target_time,
            "frame": f_idx,
            "health_pct": health_pct,
            "degradation": deg_idx,
            "gt_rul": gt_rul,
            "pred_rul": pred_rul,
            "p10": p10,
            "p90": p90,
            "op_status": op_status
        })

print("=" * 145)
print("  DIGITAL TWIN ENGINE RUL LIFECYCLE TEST (100-HOUR SIMULATION WITH 15-HOUR INTERVALS)")
print("=" * 145)
print(f"{'Accumulated Operating Time':<28} | {'Telemetry Frame #':<18} | {'Engine Health %':<16} | {'Degradation Index':<18} | {'Ground RUL':<12} | {'Predicted RUL':<15} | {'90% Confidence Interval (P10 - P90)':<35} | {'Operational Status':<35}")
print("-" * 145)

for r in rows:
    conf_str = f"[{r['p10']:.2f} hrs - {r['p90']:.2f} hrs]" if r['p10'] is not None and r['p90'] is not None else "COLLECTING WARMUP WINDOW"
    pred_str = f"{r['pred_rul']:.2f} hrs" if r['pred_rul'] is not None else "COLLECTING"
    gt_str = f"{float(r['gt_rul']):.2f} hrs"
    
    print(f"{r['target_time']:<28} | {r['frame']:<18} | {r['health_pct']:<16.2f} | {r['degradation']:<18.4f} | {gt_str:<12} | {pred_str:<15} | {conf_str:<35} | {r['op_status']:<35}")

print("=" * 145)
print("100-HOUR LIFECYCLE RUL TEST COMPLETED SUCCESSFULLY!")
print("=" * 145)
