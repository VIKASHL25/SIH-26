import socket
import struct
import time
import os
import sys
import pandas as pd

HOST = "127.0.0.1"
PORT = 5005
PACKET_FORMAT = ">20d"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATH = os.path.join(ROOT, "data", "MALE_UAV_aero_piston_engine_final_100k.csv")

def main():
    print(f"=== TESTING UDP TELEMETRY SENDER ===")
    print(f"Target: {HOST}:{PORT}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    if os.path.exists(DATA_PATH):
        print(f"Loading telemetry from {DATA_PATH}...")
        df = pd.read_csv(DATA_PATH)
        m1 = df[df["mission_id"] == 1].copy()
    else:
        m1 = None

    print("Streaming packets to UDP port 5005 (Press Ctrl+C to stop)...\n")
    packet_idx = 0
    
    try:
        while True:
            if m1 is not None and len(m1) > 0:
                row = m1.iloc[packet_idx % len(m1)]
                signals = [
                    float(row.get("rpm", 2300.0)),
                    float(row.get("throttle_pct", 70.0)),
                    float(row.get("load_pct", 70.0)),
                    float(row.get("cht_C", 135.0)),
                    float(row.get("egt_C", 665.0)),
                    float(row.get("oil_temperature_C", 75.0)),
                    float(row.get("oil_pressure_bar", 4.2)),
                    float(row.get("air_mass_flow_kg_s", 0.065)),
                    float(row.get("fuel_flow_kg_s", 0.005)),
                    float(row.get("torque_Nm", 240.0)),
                    float(row.get("power_W", 60000.0)),
                    float(row.get("vibration_rms", 0.75)),
                    float(row.get("battery_voltage_V", 28.0)),
                    float(row.get("alternator_current_A", 40.0)),
                    float(row.get("alternator_health", 1.0)),
                    float(row.get("altitude_m", 1500.0)),
                    float(row.get("ambient_temp_C", 20.0)),
                    float(row.get("pressure_kPa", 85.0)),
                    float(row.get("injection_timing_deg", 25.0)),
                    float(row.get("air_density_kg_m3", 1.05)),
                ]
            else:
                signals = [
                    2300.0 + 100.0 * (packet_idx % 10),
                    70.0,
                    68.0,
                    135.0 + 2.0 * (packet_idx % 5),
                    660.0 + 5.0 * (packet_idx % 4),
                    75.0,
                    4.2,
                    0.065,
                    0.005,
                    240.0,
                    60000.0,
                    0.75,
                    28.0,
                    40.0,
                    1.0,
                    1500.0,
                    20.0,
                    85.0,
                    25.0,
                    1.05
                ]
                
            data = struct.pack(PACKET_FORMAT, *signals)
            sock.sendto(data, (HOST, PORT))
            
            print(f"[SENT PACKET {packet_idx+1:04d}] RPM={signals[0]:.1f} | CHT={signals[3]:.1f}°C | EGT={signals[4]:.1f}°C | OilP={signals[6]:.2f} bar")
            packet_idx += 1
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nSender stopped.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
