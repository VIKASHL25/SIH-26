import subprocess
import sys
import time
import os
import socket

# Force UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ports = [8000, 8001, 8002, 8003, 8004]

def kill_process_on_port(port: int):
    """Frees socket ports if occupied by leftover background processes on Windows."""
    try:
        result = subprocess.run(f'netstat -ano | findstr :{port}', shell=True, capture_output=True, text=True)
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if 'LISTENING' in line:
                    parts = line.split()
                    pid = parts[-1]
                    if pid != '0':
                        print(f"[CLEANUP] Clearing leftover process (PID {pid}) on Port {port}...")
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
    except Exception as e:
        print(f"Warning clearing port {port}: {e}")

# Pre-start port cleanup
for port in ports:
    kill_process_on_port(port)

services = [
    {"name": "Telemetry & Simulation Service", "cmd": [sys.executable, "services/telemetry_service/main.py"], "port": 8001},
    {"name": "AI/ML Inference Service", "cmd": [sys.executable, "services/ml_inference_service/main.py"], "port": 8002},
    {"name": "XAI & Advisory Service", "cmd": [sys.executable, "services/xai_service/main.py"], "port": 8003},
    {"name": "MongoDB Atlas Persistence Service", "cmd": [sys.executable, "services/mongodb_service/main.py"], "port": 8004},
    {"name": "API Gateway Service", "cmd": [sys.executable, "services/api_gateway/main.py"], "port": 8000},
]

processes = []

print("=" * 80)
print("  STARTING MALE UAV DIGITAL TWIN FULL MICROSERVICES ARCHITECTURE")
print("=" * 80)

try:
    for s in services:
        print(f"[LAUNCH] Launching {s['name']} on Port {s['port']}...", flush=True)
        p = subprocess.Popen(s["cmd"])
        processes.append((s["name"], p))
        time.sleep(2.5)  # Startup delay for model/DB connections

    print("=" * 80, flush=True)
    print("ALL 5 MICROSERVICES ONLINE AND READY!", flush=True)
    print("API Gateway URL: http://localhost:8000", flush=True)
    print("WebSocket Stream: ws://localhost:8000/ws/telemetry", flush=True)
    print("MongoDB Replay API: http://localhost:8000/api/db/mission/999/replay", flush=True)
    print("Press Ctrl+C to terminate all microservices.", flush=True)
    print("=" * 80, flush=True)

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nShutting down all microservices...")
    for name, p in processes:
        print(f"Stopping {name}...")
        p.terminate()
        p.wait()
    print("All microservices stopped cleanly.")
