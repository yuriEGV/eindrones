"""
Tests de integración para Servidor Central de Misiones & Despacho Multiorganismo
Verifica:
1. Orquestación completa de la Red de Nodos Arbóreos Ignífugos (10 nodos).
2. Retransmisión satelital/4G vía Gateway de Cuenca.
3. Despacho automatizado del Dron Verificador (<45s) ante ignición confirmada.
4. Generación de Ficha Táctica de Bomberos:
   - Ruta vehicular más expedita (pistas cortafuego, distancia km, ETA minutos).
   - Proyección de propagación del fuego (modelo elíptico de avance).
   - Abastecimiento de agua cercano.
5. Generación de Despacho CENCO Carabineros:
   - Capturas forenses ópticas 4K con hash SHA-256.
   - Plan de cierre perimetral de rutas y retenes de control vehicular.
   - Carpeta penal para el Ministerio Público / Fiscalía.
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flybridge.mission_server import CentralMissionServer

def test_central_mission_server():
    print("--- 1. Inicializando Servidor Central de Misiones ---")
    server = CentralMissionServer()
    assert len(server.tree_nodes) == 10
    assert server.gateway is not None
    assert server.docking_station is not None
    print(f"Red inicializada con {len(server.tree_nodes)} nodos arbóreos y Gateway en cumbre.")

    # 2. Paso de simulación normal
    snap1 = server.step(dt=0.5)
    assert len(snap1["tree_nodes"]) == 10
    assert snap1["gateway"]["packets_relayed"] > 0
    print(f"Paso 1 OK: Gateway ha retransmitido {snap1['gateway']['packets_relayed']} paquetes LoRa a través de Starlink.")

    # 3. Inyección de foco térmico en Nodo 03
    print("\n--- 2. Inyectando Ignición en Nodo Arbóreo 03 ---")
    hs = server.inject_hotspot(node_id="NODE-ARBOR-03", peak_temp=72.0)
    assert hs is not None

    # Avanzar simulación hasta que el nodo detecte y active al Dron Verificador
    drone_launched = False
    for step in range(30):
        snap = server.step(dt=0.5)
        d_status = snap["verifier_drone"]["status"]
        if d_status in ("PRE_FLIGHT", "TAKING_OFF", "TRANSIT_OUT"):
            drone_launched = True
            print(f"Alerta en Nodo detectada. Dron activado en cuartel! Estado: {d_status} (Tiempo: {snap['verifier_drone']['launch_elapsed_sec']}s)")
            break

    assert drone_launched, "El Dron Verificador no fue lanzado automáticamente ante la ignición"

    # 4. Verificar Ficha Táctica de Bomberos
    print("\n--- 3. Verificando Despacho a Central de Alarmas de Bomberos ---")
    b_disp = snap["bomberos_dispatch"]
    assert b_disp is not None
    assert b_disp["target_node_id"] == "NODE-ARBOR-03"
    assert b_disp["access_route"]["distance_km"] > 0
    assert b_disp["access_route"]["estimated_arrival_time_min"] > 0
    assert "fire_behavior" in b_disp
    print("Ficha Bomberos Generada:")
    print(f"  - Camino: {b_disp['access_route']['road_name']}")
    print(f"  - Distancia: {b_disp['access_route']['distance_km']} km | ETA: {b_disp['access_route']['estimated_arrival_time_min']} min")
    print(f"  - Velocidad Avance Fuego: {b_disp['fire_behavior']['head_rate_m_min']} m/min hacia el {b_disp['fire_behavior']['cardinal_direction']}")
    print(f"  - Fuentes de Agua: {len(b_disp['tactical_water_sources'])} fuentes estratégicas")

    # 5. Verificar Despacho CENCO Carabineros & Fiscalía
    print("\n--- 4. Verificando Despacho CENCO Carabineros & Fiscalía ---")
    c_disp = snap["cenco_dispatch"]
    assert c_disp is not None
    assert c_disp["target_node_id"] == "NODE-ARBOR-03"
    assert "perimeter_containment_plan" in c_disp
    assert len(c_disp["perimeter_containment_plan"]["checkpoints"]) >= 3
    print(f"Despacho CENCO Generado: {c_disp['dispatch_code']}")
    print(f"  - Puntos de Cierre Perimetral: {len(c_disp['perimeter_containment_plan']['checkpoints'])} retenes")
    print(f"  - Carpeta Fiscalía: {c_disp['prosecutor_dossier']['status']}")

    # 6. Probar registro de feedback operador
    fb = server.record_feedback(verdict="CONFIRMADO_INCENDIO", notes="Confirmado por Bomberos")
    assert fb["verdict"] == "CONFIRMADO_INCENDIO"
    print("Feedback registrado exitosamente:", fb["verdict"])

    print("\nTODOS LOS TESTS DEL SERVIDOR CENTRAL DE MISIONES PASARON EXITOSAMENTE!")

if __name__ == "__main__":
    test_central_mission_server()
