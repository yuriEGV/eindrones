"""
Unit and integration test suite for interactive drone piloting, draggable nodes,
site survey presets, Return to Launch (RTL), hotspot extinction, and SUBTEL compliance.
Uses standard library unittest with Starlette / FastAPI TestClient.
"""

import unittest
from starlette.testclient import TestClient
from firewatch.server import app


class TestPilotAndNodes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_status_endpoint(self):
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("tree_nodes", data)
        self.assertEqual(len(data["tree_nodes"]), 10)
        self.assertIn("docking_station", data)
        self.assertIn("verifier_drone", data)
        self.assertIn("gateway", data)
        self.assertEqual(data["gateway"]["altitude_m"], 1120.0)

    def test_02_move_node_endpoint(self):
        target_node = "NODE-ARBOR-01"
        new_lat = -33.4110
        new_lon = -70.5710

        res = self.client.post("/api/node/move", json={
            "node_id": target_node,
            "lat": new_lat,
            "lon": new_lon
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        moved = next(n for n in data["tree_nodes"] if n["node_id"] == target_node)
        self.assertAlmostEqual(moved["lat"], new_lat, places=4)
        self.assertAlmostEqual(moved["lon"], new_lon, places=4)

    def test_03_preset_layout_endpoint(self):
        res1 = self.client.post("/api/node/preset", json={
            "preset_name": "ALTA_PENDIENTE_QUEBRADAS"
        })
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(len(res1.json()["tree_nodes"]), 10)

        res2 = self.client.post("/api/node/preset", json={
            "preset_name": "INTERFAZ_URBANO_FORESTAL"
        })
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(len(res2.json()["tree_nodes"]), 10)

    def test_04_pilot_commands_and_bio_dynamics(self):
        # 1. FORWARD
        res = self.client.post("/api/drone/pilot", json={"command": "FORWARD", "speed_factor": 1.0})
        self.assertEqual(res.status_code, 200)
        d = res.json()["drone"]
        self.assertEqual(d["status"], "MANUAL_PILOT")

        # 2. YAW_RIGHT -> Biomimetic turning saccade
        res = self.client.post("/api/drone/pilot", json={"command": "YAW_RIGHT"})
        self.assertEqual(res.status_code, 200)
        d = res.json()["drone"]
        self.assertEqual(d["bio_flight_state"], "SACCADE_TURN")

        # 3. HOVER -> Optomotor stabilization
        res = self.client.post("/api/drone/pilot", json={"command": "HOVER"})
        self.assertEqual(res.status_code, 200)
        d = res.json()["drone"]
        self.assertEqual(d["bio_flight_state"], "HOVER_PRECISION")
        self.assertEqual(d["speed_kmh"], 0.0)

        # 4. ALTITUDE_UP
        init_alt = d["altitude_m"]
        res = self.client.post("/api/drone/pilot", json={"command": "ALTITUDE_UP", "delta_alt_m": 10.0})
        self.assertEqual(res.status_code, 200)
        d = res.json()["drone"]
        self.assertEqual(d["altitude_m"], init_alt + 10.0)

        # 5. GIMBAL
        res = self.client.post("/api/drone/pilot", json={"command": "GIMBAL", "pitch": -45.0, "zoom": 15.0})
        self.assertEqual(res.status_code, 200)
        d = res.json()["drone"]
        self.assertEqual(d["gimbal_pitch_deg"], -45.0)
        self.assertEqual(d["zoom_optical"], 15.0)

    def test_05_drone_rtl(self):
        res = self.client.post("/api/drone/rtl")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["drone"]["status"], "RTL_RETURNING")
        self.assertEqual(data["drone"]["bio_flight_state"], "RTL_HOMING")

    def test_06_hotspot_clear_and_extinguish(self):
        # Trigger
        self.client.post("/api/node/trigger", json={"node_id": "NODE-ARBOR-03", "peak_temp_c": 75.0})
        status_after = self.client.get("/api/status").json()
        self.assertGreater(len(status_after["active_hotspots"]), 0)

        # Extinguish / clear
        res_clear = self.client.post("/api/hotspot/clear")
        self.assertEqual(res_clear.status_code, 200)
        cleared_data = res_clear.json()
        self.assertEqual(len(cleared_data["active_hotspots"]), 0)
        node3 = next(n for n in cleared_data["tree_nodes"] if n["node_id"] == "NODE-ARBOR-03")
        self.assertLess(node3["telemetry"]["sensor_temp_c"], 40.0)

    def test_07_subtel_compliance_endpoint(self):
        res = self.client.get("/api/subtel/compliance")
        self.assertEqual(res.status_code, 200)
        subtel = res.json()
        self.assertEqual(subtel["authority"], "SUBTEL Chile")
        self.assertEqual(subtel["regulation"], "Resolución Exenta N° 1.985 / 2017")
        self.assertEqual(subtel["frequency_band_mhz"], "915.0 - 928.0 MHz")
        self.assertEqual(subtel["max_eirp_w"], 1.0)
        self.assertEqual(subtel["node_tx_power_dbm"], 20.0)
        self.assertIn("Estrella Redundante", subtel["topology"])


if __name__ == "__main__":
    unittest.main()
