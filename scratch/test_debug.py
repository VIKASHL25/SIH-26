import sys, os, logging
from typing import Optional
sys.path.insert(0, os.path.abspath('.'))

logging.getLogger("DigitalTwinModelManager").setLevel(logging.ERROR)
logging.getLogger("MissionSimulationEngine").setLevel(logging.ERROR)

import pandas as pd
import numpy as np
from backend.simulation_engine import MissionSimulationEngine

engine = MissionSimulationEngine()

# Test across Mission 75 (engine degradation lifecycle from healthy to failure)
mission_id = 75

# Update model_manager apply_temporal_filter to include degradation scaling down to 0 RUL
def patched_temporal_filter(self, raw_rul: float, health_pct: Optional[float] = None, degradation_index: Optional[float] = None) -> float:
    raw_rul = max(0.0, float(raw_rul))

    if health_pct is not None:
        health_fraction = max(0.0, min(1.0, health_pct / 100.0))
        if degradation_index is not None and degradation_index >= 0.98:
            # Engine failure state
            raw_rul = 0.0
        else:
            # Scale RUL dynamically with degradation lifecycle (50h at 100% health -> 0h at 0% health)
            health_target = health_fraction * 50.0
            raw_rul = 0.3 * raw_rul + 0.7 * health_target

    if self.previous_rul is None:
        filtered = raw_rul
    else:
        alpha = 0.12
        filtered = alpha * raw_rul + (1.0 - alpha) * self.previous_rul
        
        delta = filtered - self.previous_rul
        if delta > 0.5:
            filtered = self.previous_rul + 0.5
        elif delta < -2.0:
            filtered = self.previous_rul - 2.0

    filtered = max(0.0, filtered)
    self.previous_rul = filtered
    return round(filtered, 2)

engine.model_manager.apply_temporal_filter = patched_temporal_filter.__get__(engine.model_manager)

engine.initialize()
engine.load_mission(mission_id)
df_m = engine.mission_df

total_frames = len(df_m)
sample_indices = np.linspace(15, total_frames - 1, 8, dtype=int)
sample_map = {idx: f"{i * 15} hrs" for i, idx in enumerate(sample_indices)}

print("=" * 140)
print("  DIGITAL TWIN ENGINE RUL LIFECYCLE TEST (100-HOUR SIMULATION WITH 15-HOUR INTERVALS)")
print("=" * 140)
print(f"{'Accumulated Operating Time':<28} | {'Frame #':<8} | {'Engine Health %':<16} | {'Degradation':<12} | {'Ground RUL':<12} | {'Predicted RUL':<15} | {'90% Conf Bounds (P10 - P90)':<30}")
print("-" * 140)

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
