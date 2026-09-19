"""
Live Aero-Piston Engine Continuous Physics Simulator
=====================================================
Simulates real-time thermodynamic, combustion, mechanical, and electrical ODEs
for a 4-cylinder MALE UAV aero-piston engine and transmits live telemetry
packets to UDP port 5005 (compatible with udp_can_bridge.py and the backend twin).

Features:
- Dynamic flight phase profile (Takeoff -> Climb -> Cruise -> Loiter -> Descent)
- Live ODE equations for 4 cylinder head temperatures (CHT1-4), EGT, oil pressure/temp
- Real-time interactive fault injection (Overheating, Injector Clogging, Oil Leak, Misfire)
- Transmits standardized 20-signal binary CAN telemetry frames over UDP 127.0.0.1:5005
"""

import socket
import struct
import time
import math
import random
import os
import sys
import threading

HOST = "127.0.0.1"
PORT = 5005
PACKET_FORMAT = ">20d"

class LiveEnginePhysicsPlant:
    def __init__(self):
        # State variables
        self.time_s = 0.0
        self.throttle_pct = 70.0
        self.rpm = 2300.0
        self.cht1 = 135.0
        self.cht2 = 134.5
        self.cht3 = 136.0
        self.cht4 = 135.2
        self.egt = 665.0
        self.oil_temp = 75.0
        self.oil_pressure = 4.2
        self.altitude_m = 1500.0
        self.ambient_temp_C = 20.0
        self.vibration_rms = 0.75
        self.battery_voltage = 28.0
        self.alternator_current = 40.0
        
        # Flight Profile Controller
        self.flight_phase = "CRUISE"
        self.climb_rate_mps = 0.0
        
        # Fault Injection Flags
        self.fault_mode = "NONE"
        self.fault_severity = 0.0
        self.lock = threading.Lock()
        
    def set_fault(self, mode: str, severity: float = 1.0):
        with self.lock:
            self.fault_mode = mode
            self.fault_severity = severity
            print(f"\n[ALERT] Fault Injected: {mode} (Severity: {severity:.1f})\n")

    def clear_faults(self):
        with self.lock:
            self.fault_mode = "NONE"
            self.fault_severity = 0.0
            print("\n[INFO] All faults cleared. Returning to nominal physics.\n")

    def step(self, dt: float = 1.0):
        with self.lock:
            self.time_s += dt
            t = self.time_s
            
            # 1. Dynamic Flight Phase Logic (Simulated Mission)
            if t < 30:
                self.flight_phase = "TAKEOFF_CLIMB"
                target_throttle = 95.0
                target_alt = 15.0 + t * 50.0
            elif t < 180:
                self.flight_phase = "CRUISE"
                target_throttle = 72.0 + 4.0 * math.sin(t * 0.05)
                target_alt = 1500.0 + 50.0 * math.sin(t * 0.02)
            elif t < 240:
                self.flight_phase = "LOITER"
                target_throttle = 55.0 + 3.0 * math.sin(t * 0.08)
                target_alt = 1200.0
            else:
                self.flight_phase = "DESCENT_APPROACH"
                target_throttle = 40.0
                target_alt = max(50.0, 1200.0 - (t - 240) * 15.0)

            # Smooth throttle transition
            self.throttle_pct += (target_throttle - self.throttle_pct) * 0.15
            self.altitude_m += (target_alt - self.altitude_m) * 0.1

            # 2. Atmospheric & Ambient Physics
            self.ambient_temp_C = 25.0 - (self.altitude_m / 1000.0) * 6.5
            p_ambient_kPa = 101.325 * ((1.0 - 0.0000225577 * self.altitude_m) ** 5.25588)
            t_kelvin = self.ambient_temp_C + 273.15
            air_density = (p_ambient_kPa * 1000.0) / (287.05 * max(200.0, t_kelvin))

            # 3. Engine Mechanical & Combustion Dynamics
            target_rpm = 1600.0 + 850.0 * (self.throttle_pct / 100.0) * (air_density / 1.225) ** 0.3
            self.rpm += (target_rpm - self.rpm) * 0.25 + random.gauss(0, 3.0)
            
            load_pct = min(100.0, (self.throttle_pct * 0.96) + (self.rpm / 2500.0) * 4.0)
            air_mass_flow = (self.rpm / 2500.0) * 0.085 * (air_density / 1.225)
            
            # Fuel-Air Mixture (Lambda)
            nominal_fuel_flow = air_mass_flow / 14.7
            fuel_flow = nominal_fuel_flow * (1.0 + 0.08 * (self.throttle_pct / 100.0))
            
            # Power and Torque
            power_W = (self.rpm * 2.0 * math.pi / 60.0) * (260.0 * (load_pct / 100.0) * (air_density / 1.225))
            torque_Nm = power_W / max(10.0, (self.rpm * 2.0 * math.pi / 60.0))

            # Lower Heating Value Combustion Heat Release (LHV = 44 MJ/kg, 32% thermal efficiency)
            q_comb = fuel_flow * 44e6 * 0.32

            # 4. Thermodynamic ODEs for 4 Cylinders (Euler Integration)
            # Cylinder 4 gets extra heat if Injector Clog or Misfire fault is active
            q_cyl1 = q_comb * 0.250
            q_cyl2 = q_comb * 0.252
            q_cyl3 = q_comb * 0.248
            q_cyl4 = q_comb * 0.250

            if self.fault_mode == "INJECTOR_CLOG":
                # Cylinder 4 leans out and overheats or suffers severe thermal imbalance
                q_cyl4 *= (1.0 + 0.35 * self.fault_severity)
                fuel_flow *= (1.0 - 0.12 * self.fault_severity)
            elif self.fault_mode == "OVERHEATING":
                # Thermal dissipation failure (cooling blockage)
                cooling_factor = max(0.2, 1.0 - 0.65 * self.fault_severity)
            else:
                cooling_factor = 1.0

            # ODE: mc * dCHT/dt = Q_comb - hA*(CHT - T_amb)
            hA = 180.0 * cooling_factor * (air_mass_flow / 0.08)
            mc = 1250.0  # Thermal mass (J/K)
            
            self.cht1 += ((q_cyl1 - hA * (self.cht1 - self.ambient_temp_C)) / mc) * dt
            self.cht2 += ((q_cyl2 - hA * (self.cht2 - self.ambient_temp_C)) / mc) * dt
            self.cht3 += ((q_cyl3 - hA * (self.cht3 - self.ambient_temp_C)) / mc) * dt
            self.cht4 += ((q_cyl4 - hA * (self.cht4 - self.ambient_temp_C)) / mc) * dt

            # 5. Exhaust Gas Dynamics (EGT ODE)
            target_egt = 450.0 + 260.0 * (load_pct / 100.0)
            if self.fault_mode == "OVERHEATING":
                target_egt += 90.0 * self.fault_severity
            elif self.fault_mode == "INJECTOR_CLOG":
                target_egt += 60.0 * self.fault_severity
                
            self.egt += ((target_egt - self.egt) / 4.0) * dt + random.gauss(0, 0.8)

            # 6. Lubrication & Oil System Dynamics
            if self.fault_mode == "LUBRICATION_BREAKDOWN":
                oil_viscosity_loss = 0.65 * self.fault_severity
                oil_temp_rise = 35.0 * self.fault_severity
            else:
                oil_viscosity_loss = 0.0
                oil_temp_rise = 0.0

            target_oil_temp = 65.0 + 20.0 * (self.rpm / 2500.0) + oil_temp_rise
            self.oil_temp += ((target_oil_temp - self.oil_temp) / 15.0) * dt

            nom_oil_p = 4.3 * (self.rpm / 2300.0) * (80.0 / max(40.0, self.oil_temp))
            self.oil_pressure = max(0.5, nom_oil_p * (1.0 - oil_viscosity_loss) + random.gauss(0, 0.02))

            # 7. Mechanical Vibration & Harmonics
            base_vib = 0.35 + 0.40 * (self.rpm / 2500.0)
            if self.fault_mode == "MISFIRE":
                vib_spike = 1.8 * self.fault_severity
            elif self.fault_mode == "VIBRATION_WEAR":
                vib_spike = 1.2 * self.fault_severity
            elif self.fault_mode == "INJECTOR_CLOG":
                vib_spike = 0.6 * self.fault_severity
            else:
                vib_spike = 0.0
                
            self.vibration_rms = base_vib + vib_spike + random.gauss(0, 0.015)

            # 8. Electrical System Dynamics
            self.battery_voltage = 28.0 + random.gauss(0, 0.03)
            self.alternator_current = 30.0 + 15.0 * (self.throttle_pct / 100.0)
            alternator_health = 1.0

            # 9. Pack 20-Signal Vector
            avg_cht = (self.cht1 + self.cht2 + self.cht3 + self.cht4) / 4.0
            injection_timing = 24.5 + 2.0 * (self.rpm / 2500.0)

            telemetry = [
                float(self.rpm),
                float(self.throttle_pct),
                float(load_pct),
                float(avg_cht),
                float(self.egt),
                float(self.oil_temp),
                float(self.oil_pressure),
                float(air_mass_flow),
                float(fuel_flow),
                float(torque_Nm),
                float(power_W),
                float(self.vibration_rms),
                float(self.battery_voltage),
                float(self.alternator_current),
                float(alternator_health),
                float(self.altitude_m),
                float(self.ambient_temp_C),
                float(p_ambient_kPa),
                float(injection_timing),
                float(air_density)
            ]
            
            return telemetry

def interactive_cli(engine: LiveEnginePhysicsPlant):
    """Interactive command line for injecting faults on the fly during simulation."""
    print("\n" + "="*60)
    print("LIVE PHYSICS SIMULATION CONTROL COMMANDS:")
    print("  Type 'overheat'  -> Inject Cooling Failure (Overheating)")
    print("  Type 'injector'  -> Inject Cylinder 4 Clogged Injector")
    print("  Type 'oil'       -> Inject Lubrication Breakdown / Oil Leak")
    print("  Type 'misfire'   -> Inject Cylinder Misfire / Vibration")
    print("  Type 'normal'    -> Return to Normal Nominal Flight")
    print("="*60 + "\n")
    
    while True:
        try:
            cmd = input().strip().lower()
            if cmd == "overheat":
                engine.set_fault("OVERHEATING", severity=1.0)
            elif cmd == "injector":
                engine.set_fault("INJECTOR_CLOG", severity=1.0)
            elif cmd == "oil":
                engine.set_fault("LUBRICATION_BREAKDOWN", severity=1.0)
            elif cmd == "misfire":
                engine.set_fault("MISFIRE", severity=1.0)
            elif cmd == "normal":
                engine.clear_faults()
            elif cmd in ["exit", "quit"]:
                break
        except (EOFError, KeyboardInterrupt):
            break

def main():
    print("==========================================================")
    print("LIVE UAV AERO-PISTON ENGINE CONTINUOUS ODE PHYSICS ENGINE")
    print("==========================================================")
    print(f"Target UDP Destination: {HOST}:{PORT}")
    print("Streaming live generated physics to udp_can_bridge.py...\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    engine = LiveEnginePhysicsPlant()

    # Start CLI listener in background thread for live fault injections
    cli_thread = threading.Thread(target=interactive_cli, args=(engine,), daemon=True)
    cli_thread.start()

    packet_count = 0
    try:
        while True:
            signals = engine.step(dt=1.0)
            data = struct.pack(PACKET_FORMAT, *signals)
            sock.sendto(data, (HOST, PORT))
            packet_count += 1

            mode_str = f"[{engine.fault_mode}]" if engine.fault_mode != "NONE" else "[NOMINAL]"
            print(
                f"[SIM #{packet_count:04d} {mode_str}] Phase: {engine.flight_phase:15} | "
                f"RPM: {signals[0]:.0f} | CHT: {signals[3]:.1f}°C | EGT: {signals[4]:.1f}°C | "
                f"OilP: {signals[6]:.2f} bar | Vib: {signals[11]:.2f}g | Alt: {signals[15]:.0f}m"
            )
            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\nLive Physics Simulation stopped.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
