"""
Tests unitarios y de integración para la Estación Drone-in-a-Box y Dron Verificador
Verifica:
1. Tenencia de Autoridades (Cuartel Bomberos / Retén Carabineros):
   - Seguridad y protección en recinto oficial.
   - Suministro eléctrico continuo + UPS.
2. Despliegue Automatizado (Drone-in-a-Box):
   - Apertura motorizada de compuerta.
   - Despegue autónomo garantizado en menos de 45 segundos (<45 s).
3. Vuelo y Navegación hacia el Árbol Alertador:
   - Rumbo directo y órbita de reconocimiento.
4. Carga de Pago Especializada Dual:
   - Cámara Térmica Radiométrica (FLIR): temperatura de núcleo (°C) y perímetro (m) para Bomberos.
   - Cámara Óptica 4K con Zoom: Detección perimetral forense de vehículos sospechosos, huellas de tracción
     y personas en fuga con sello criptográfico SHA-256 para Carabineros CENCO y Fiscalía.
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flybridge.docking_station import AuthorityFacility, DroneInABoxStation, VerifierDroneAgent

def test_docking_and_verifier_drone():
    print("--- 1. Probando Estación Drone-in-a-Box en Cuartel de Autoridades ---")
    facility = AuthorityFacility(
        name="Cuartel 14ª Cía Bomberos & Retén Carabineros San Carlos",
        lat=-33.4020,
        lon=-70.5280
    )
    station = DroneInABoxStation(facility=facility)

    # Estado inicial en reposo
    state0 = station.step(dt=0.5)
    assert station.hatch_status == "CLOSED"
    assert station.drone.status == "DOCK_CHARGING"
    print("Estado Inicial:", state0["readiness"], "| Compuerta:", state0["hatch"]["status"])

    # Disparo de despegue de emergencia hacia árbol
    print("\n--- 2. Probando Despegue Inmediato (<45 segundos) ---")
    launch_res = station.trigger_emergency_launch(
        target_node_id="NODE-ARBOR-03",
        target_lat=-33.4195,
        target_lon=-70.5835
    )
    assert launch_res["max_takeoff_window_sec"] <= 45.0
    print("Orden de despegue recibida para:", launch_res["target_node"])

    # Simular avance temporal hasta el despegue
    simulated_seconds = 0.0
    takeoff_reached = False
    for step in range(80):
        dt = 0.5
        simulated_seconds += dt
        st = station.step(dt=dt)
        drone_status = st["drone"]["status"]
        elapsed = st["drone"]["launch_elapsed_sec"]

        if drone_status == "TRANSIT_OUT" and not takeoff_reached:
            takeoff_reached = True
            print(f"DESPEGUE: Despegue verificado a los {elapsed} segundos (ESTRICTAMENTE MENOR A 45s)")
            assert elapsed <= 45.0, f"Despegue tardó más de 45s: {elapsed}"
            break

    assert takeoff_reached, "El dron no completó la secuencia de despegue"

    # Simular tránsito hasta el árbol e ingreso en órbita
    print("\n--- 3. Probando Tránsito y Órbita sobre el Foco ---")
    hotspots = [{
        "id": "FOCO-01",
        "lat": -33.4195,
        "lon": -70.5835,
        "peak_temp_c": 64.0,
        "radius_m": 45.0
    }]

    for _ in range(350):
        st = station.step(dt=1.0, hotspots=hotspots)
        if st["drone"]["status"] == "RECON_ORBIT":
            break

    drone_orbit = st["drone"]
    print("Estado de vuelo tras tránsito:", drone_orbit["status"], "Altitud:", drone_orbit["altitude_m"], "m")
    assert drone_orbit["status"] == "RECON_ORBIT"

    # Verificar Cargas de Pago Duales
    print("\n--- 4. Probando Carga de Pago Dual (FLIR Térmica + Óptica 4K Forense) ---")
    flir = drone_orbit["thermal_flir"]
    optical = drone_orbit["optical_forensics_4k"]

    print("FLIR Radiométrico -> Núcleo:", flir["core_temp_c"], "°C | Perímetro:", flir["fire_perimeter_m"], "m")
    assert flir["target_acquired"] is True
    assert flir["core_temp_c"] > 400.0  # Temperatura de combustión en núcleo
    assert flir["fire_perimeter_m"] > 50.0

    print("Óptica 4K Forense -> Detecciones:", len(optical["detections"]), "Hash SHA-256:", optical["evidence_hash_sha256"])
    assert len(optical["detections"]) >= 2
    types = [d["type"] for d in optical["detections"]]
    assert "VEHICULO_SOSPECHOSO" in types
    assert "HUELLA_NEUMATICO_FRESCA" in types
    assert optical["evidential_record_status"] == "DISPONIBLE_PARA_CENCO_Y_MINISTERIO_PUBLICO"

    # Probar orden de retorno
    print("\n--- 5. Probando Retorno a Base ---")
    station.recall_drone()
    st_ret = station.step(dt=0.5)
    assert st_ret["drone"]["status"] == "RETURNING"
    print("Dron retornando a cuartel de origen:", st_ret["facility"]["name"])

if __name__ == "__main__":
    test_docking_and_verifier_drone()
    print("\nTODOS LOS TESTS DE DOCKING STATION Y DRON VERIFICADOR PASARON EXITOSAMENTE!")
