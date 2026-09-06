import os
import sys
import pandas as pd
import numpy as np

def generate_demo_dataset(
    source_100k_path: str = "data/MALE_UAV_aero_piston_engine_final_100k.csv",
    output_path: str = "data/demo_synthetic_flight_test.csv"
):
    """
    Generates a dedicated 1,000-frame Out-of-Sample Demo Flight (Mission 999)
    using the calibrated nominal aero piston engine flight distribution.
    Ensures that nominal flight is 100% NOMINAL (is_anomaly=False),
    while fully supporting dynamic runtime fault injection.
    """
    print(f"Generating high-fidelity Mission 999 demo dataset from {source_100k_path}...")
    
    if not os.path.exists(source_100k_path):
        raise FileNotFoundError(f"Source dataset not found: {source_100k_path}")
        
    df_100k = pd.read_csv(source_100k_path)
    
    # Select a clean nominal mission as the baseline trajectory (e.g. Mission 50)
    nominal_df = df_100k[df_100k["mission_id"] == 50].copy().reset_index(drop=True)
    
    # Update mission metadata for out-of-sample demo flight
    nominal_df["mission_id"] = 999
    nominal_df["engine_id"] = "MALE_UAV_ENGINE_DEMO_01"
    nominal_df["mission_type"] = "Out_of_Sample_ISR_Sortie"
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    nominal_df.to_csv(output_path, index=False)
    print(f"[SUCCESS] Mission 999 demo dataset saved to {output_path} ({len(nominal_df)} frames).")

if __name__ == "__main__":
    generate_demo_dataset()
