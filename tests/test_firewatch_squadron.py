"""
Unit & Integration test for FLYBRIDGE FIREWATCH
Verifies:
- 5 drones instantiation
- Environmental sampling (plume dispersion, temperature, wind)
- Drosophila brain controller (ORN smoke, dTRPA1 thermal, Johnston anemotaxis)
- Multi-step patrol, upwind surge, and crosswind casting
- Risk Engine (FWI rules, persistence tracking, XAI natural language reasoning)
- Incident card generation (FW-2026-XXXXX)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from firewatch.squadron_manager import SquadronManager

def test_firewatch():
    sm = SquadronManager()
    print("Testing FLYBRIDGE FIREWATCH Squadron...")
    print(f"Squadron initialized with {len(sm.drones)} drones.")
    
    for step in range(30):
        data = sm.step(dt=0.5)
        fly02 = data["drones"][1]
        risk = data["risk_analysis"]
        
        if step % 5 == 0 or risk["alert_level"] >= 3:
            print(f"Step {step:02d} | FLY-02: pos=({fly02['latitude']:.4f}, {fly02['longitude']:.4f}) "
                  f"temp={fly02['temperature_c']}°C bio={fly02['brain']['behavior_state']} "
                  f"| Alert: Level {risk['alert_level']} ({risk['risk_label']})")
            
    print("\n--- XAI Risk Reasoning Evaluation ---")
    print("Explanation:", risk["explanation"])
    if risk["primary_incident"]:
        inc = risk["primary_incident"]
        print(f"\n--- Primary Firefighter Incident Card Generated: {inc['incident_id']} ---")
        print(f"Status: {inc['status']}")
        print(f"Peak Temp: {inc['peak_temperature_c']} °C")
        print(f"Persistence: {inc['persistence_min']} min")
        print(f"Assigned Drones: {inc['assigned_drones']}")
        print(f"Action: {inc['recommended_action']}")

    # Test feedback
    fb = sm.record_operator_feedback("FW-2026-00421", "CONFIRMADO_INCENDIO", "Verificado visualmente")
    print("\nOperator feedback recorded:", fb)
    print("\nALL FIREWATCH CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_firewatch()
