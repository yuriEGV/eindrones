"""
Verify hotspot detection, upwind surge, and incident card creation.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from firewatch.squadron_manager import SquadronManager

def test_hotspot_encounter():
    sm = SquadronManager()
    # Place FLY-02 in the convective smoke plume of ANOM-01
    hs = sm.env.hotspots[0]
    print(f"Hotspot ANOM-01 at: ({hs['lat']:.5f}, {hs['lon']:.5f}) with Peak Temp: {hs['peak_temp_c']}°C")
    
    # Place FLY-02 120 meters downwind
    sm.drones[1].lat = hs['lat'] - 0.0008
    sm.drones[1].lon = hs['lon'] - 0.0008
    sm.drones[1].heading_deg = 45.0
    
    for step in range(15):
        data = sm.step(dt=0.5)
        fly02 = data["drones"][1]
        risk = data["risk_analysis"]
        print(f"Step {step:02d} | FLY-02 Temp: {fly02['temperature_c']}°C | Smoke: {fly02['smoke_concentration']} "
              f"| Bio: {fly02['brain']['behavior_state']} | Risk: Level {risk['alert_level']} ({risk['risk_label']})")
        if risk["alert_level"] >= 3:
            print("\n*** LEVEL 3 ALARM TRIGGERED! ***")
            print("Primary Incident Card:", risk["primary_incident"])
            break

if __name__ == "__main__":
    test_hotspot_encounter()
