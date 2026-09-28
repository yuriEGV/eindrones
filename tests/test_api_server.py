"""
Verify FastAPI endpoints for FLYBRIDGE v0.1:
Red de Nodos Arbóreos Ignífugos & Drone-in-a-Box en Cuartel de Autoridades
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from starlette.testclient import TestClient
from firewatch.server import app

def test_api():
    client = TestClient(app)
    
    # 1. Test /api/status
    res = client.get("/api/status")
    assert res.status_code == 200, f"Status failed: {res.status_code}"
    data = res.json()
    assert len(data["tree_nodes"]) == 10, f"Expected 10 tree nodes, got {len(data['tree_nodes'])}"
    assert data["gateway"]["id"] == "GW-CUENCA-SAN-CARLOS"
    assert data["verifier_drone"]["drone_id"] == "DRON-VERIFICADOR-01"
    print("GET /api/status OK -> 10 Nodos Arboreos, Gateway Starlink, Drone-in-a-Box activo")

    # 2. Test /api/node/trigger (Simular Ignición en Árbol)
    res_trig = client.post("/api/node/trigger", json={
        "node_id": "NODE-ARBOR-03",
        "peak_temp_c": 70.0
    })
    assert res_trig.status_code == 200
    print("POST /api/node/trigger OK -> Inyeccion en NODE-ARBOR-03 exitosa")

    # 3. Test /api/drone/launch (Despegue Emergencia desde Cuartel)
    res_launch = client.post("/api/drone/launch", json={
        "target_node_id": "NODE-ARBOR-03"
    })
    assert res_launch.status_code == 200
    print("POST /api/drone/launch OK -> Despegue <45s activado:", res_launch.json().get("facility_name"))

    # 4. Test /api/bomberos/route (Ficha Táctica y Ruta Vehicular)
    res_b = client.get("/api/bomberos/route")
    assert res_b.status_code == 200
    b_data = res_b.json()
    assert "access_route" in b_data
    assert "fire_behavior" in b_data
    print("GET /api/bomberos/route OK -> Camino:", b_data["access_route"]["road_name"], "| ETA:", b_data["access_route"]["estimated_arrival_time_min"], "min")

    # 5. Test /api/cenco/forensics (Evidencia Pericial y Cierre Rutas)
    res_c = client.get("/api/cenco/forensics")
    assert res_c.status_code == 200
    c_data = res_c.json()
    assert "perimeter_containment_plan" in c_data
    assert "evidence_integrity_hash" in c_data
    print("GET /api/cenco/forensics OK -> Codigo:", c_data["dispatch_code"], "| Hash:", c_data["evidence_integrity_hash"])

    # 6. Test /api/wind
    res_w = client.post("/api/wind", json={
        "speed_kmh": 32.0,
        "direction_deg": 70.0
    })
    assert res_w.status_code == 200
    print("POST /api/wind OK -> Viento actualizado a 32 km/h")

    # 7. Test /api/feedback
    res_fb = client.post("/api/feedback", json={
        "incident_id": "NODE-ARBOR-03",
        "verdict": "CONFIRMADO_INCENDIO",
        "operator_notes": "Test exitoso de validacion de Bomberos"
    })
    assert res_fb.status_code == 200
    print("POST /api/feedback OK ->", res_fb.json())

    # 8. Test /api/drone/return
    res_ret = client.post("/api/drone/return")
    assert res_ret.status_code == 200
    print("POST /api/drone/return OK -> Retorno a base:", res_ret.json().get("status"))

    # 9. Test root / (HTML Dashboard)
    res_html = client.get("/")
    assert res_html.status_code == 200
    assert "FLYBRIDGE" in res_html.text
    print("GET / (Dashboard UI) OK -> HTML servido con longitud:", len(res_html.text))

    print("\nTODOS LOS ENDPOINTS DE LA API FLYBRIDGE FUERON PROBADOS EXITOSAMENTE!")

if __name__ == "__main__":
    test_api()
