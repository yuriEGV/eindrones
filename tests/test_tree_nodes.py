"""
Tests unitarios y de integración para Nodos Arbóreos Ignífugos y NeuroFly Edge
Verifica:
1. Inferencia Sensorial Neuromórfica en el Borde:
   - Lóbulo Olfativo: Tasa de cambio dC/dt ante microplumas de gases.
   - Médula/Lámina Visual: Gradiente térmico convectivo multizona.
   - Filtro Neuromórfico de Falsos Positivos:
     * Rechazo de calentamiento solar diurno en copas.
     * Rechazo de gases de escape aislados.
     * Confirmación de combustión real con coincidencia quimio-térmica.
2. Empaquetado binario LoRaWAN / LoRa Mesh a 915 MHz (< 50 bytes):
   - Empaque binario exacto (32 bytes).
   - Desempaque y verificación de campos y CRC.
3. Infraestructura del Nodo Ignífugo:
   - Chasis UL94 V-0, membrana hidrofóbica PTFE, celda LiFePO4 + panel solar.
4. Gateway de Cuenca:
   - Retransmisión de paquetes por enlace satelital Starlink/4G.
"""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flybridge.tree_node import TreeNodeModel, BasinGateway, LoRaCompactPacket, NeuroFlyEdgeInference

def test_lora_compact_packet():
    print("--- 1. Probando Paquete LoRaWAN Compacto (< 50 bytes) ---")
    raw = LoRaCompactPacket.pack(
        node_id_int=3,
        timestamp=time.time(),
        lat=-33.4195,
        lon=-70.5835,
        ambient_temp_c=34.2,
        convective_grad_c=16.5,
        gas_dc_dt=4.8,
        co2_ppm=620.0,
        voc_ppb=85.0,
        wind_speed_kmh=27.5,
        wind_dir_deg=65.0,
        confidence_pct=94,
        alert_level=3,
        battery_pct=98
    )

    print(f"Tamaño del paquete binario LoRa: {len(raw)} bytes (límite estricto < 50 bytes)")
    assert len(raw) <= 50, f"Paquete excede 50 bytes: {len(raw)}"
    assert len(raw) == 32, f"Se esperaban 32 bytes exactos, se obtuvo {len(raw)}"

    unpacked = LoRaCompactPacket.unpack(raw)
    assert unpacked["node_id_int"] == 3
    assert abs(unpacked["lat"] - (-33.4195)) < 1e-4
    assert abs(unpacked["lon"] - (-70.5835)) < 1e-4
    assert abs(unpacked["ambient_temp_c"] - 34.2) < 0.2
    assert abs(unpacked["convective_grad_c"] - 16.5) < 0.2
    assert abs(unpacked["gas_dc_dt"] - 4.8) < 0.2
    assert unpacked["confidence_pct"] == 94
    assert unpacked["alert_level"] == 3
    assert unpacked["battery_pct"] == 98
    print("Hexadecimal:", raw.hex().upper())
    print("Desempaquetado OK:", unpacked)


def test_neuromorphic_edge_inference():
    print("\n--- 2. Probando Inferencia NeuroFly Edge & Filtro Falsos Positivos ---")
    engine = NeuroFlyEdgeInference(node_id="NODE-TEST-01")

    # Caso A: Calentamiento solar normal (copa se calienta, dC/dt = 0, sin convección)
    solar_res = engine.process_sample(
        raw_co2_ppm=415.0,
        raw_voc_ppb=40.0,
        upper_canopy_temp_c=36.0,
        lower_sensor_temp_c=30.0,
        ambient_temp_c=30.0,
        wind_speed_kmh=15.0,
        wind_dir_deg=60.0,
        solar_radiation_wm2=850.0,
        dt_sec=2.0
    )
    print("Caso Solar -> Alerta:", solar_res["alert_level"], "Rechazo:", solar_res["neuromorphic_filter"]["rejection_reason"])
    assert solar_res["neuromorphic_filter"]["is_solar_heating_rejected"] is True
    assert solar_res["alert_level"] == 0

    # Caso B: Transitorio de gas aislado (escape de tractor sin calor convectivo)
    engine2 = NeuroFlyEdgeInference(node_id="NODE-TEST-02")
    engine2.process_sample(raw_co2_ppm=415.0, raw_voc_ppb=40.0, upper_canopy_temp_c=28.0, lower_sensor_temp_c=28.0, ambient_temp_c=28.0, wind_speed_kmh=10.0, wind_dir_deg=0.0)
    exhaust_res = engine2.process_sample(
        raw_co2_ppm=540.0,  # Salto de gas
        raw_voc_ppb=120.0,
        upper_canopy_temp_c=28.2,
        lower_sensor_temp_c=28.5,  # Sin calor ascendente
        ambient_temp_c=28.0,
        wind_speed_kmh=10.0,
        wind_dir_deg=0.0,
        solar_radiation_wm2=300.0,
        dt_sec=1.0
    )
    print("Caso Escape -> Alerta:", exhaust_res["alert_level"], "Rechazo:", exhaust_res["neuromorphic_filter"]["rejection_reason"])
    assert exhaust_res["neuromorphic_filter"]["is_exhaust_rejected"] is True
    assert exhaust_res["alert_level"] <= 1

    # Caso C: Combustión real (salto de gases + gradiente térmico convectivo ascendente)
    engine3 = NeuroFlyEdgeInference(node_id="NODE-TEST-03")
    engine3.process_sample(raw_co2_ppm=415.0, raw_voc_ppb=40.0, upper_canopy_temp_c=28.0, lower_sensor_temp_c=28.0, ambient_temp_c=28.0, wind_speed_kmh=25.0, wind_dir_deg=65.0)
    fire_res = engine3.process_sample(
        raw_co2_ppm=580.0,  # Gran salto de gas
        raw_voc_ppb=130.0,
        upper_canopy_temp_c=34.0,
        lower_sensor_temp_c=48.5,  # Fuerte gradiente convectivo desde la base
        ambient_temp_c=30.0,
        wind_speed_kmh=27.0,
        wind_dir_deg=65.0,
        solar_radiation_wm2=700.0,
        dt_sec=1.0
    )
    print("Caso Incendio Real -> Alerta:", fire_res["alert_level"], "Confianza:", fire_res["confidence_pct"], "% Evento:", fire_res["event_type"])
    assert fire_res["alert_level"] >= 2
    assert fire_res["confidence_pct"] >= 60
    assert fire_res["neuromorphic_filter"]["coincidence_verified"] is True


def test_tree_node_model_and_gateway():
    print("\n--- 3. Probando Nodo Arbóreo Físico & Gateway de Cuenca ---")
    node = TreeNodeModel(
        node_id="NODE-ARBOR-03",
        node_num=3,
        tree_species="Litre (Lithraea caustica)",
        lat=-33.4195,
        lon=-70.5835,
        altitude_m=720.0
    )
    assert "UL94 V-0" in node.hardware_profile["enclosure_spec"]
    assert "PTFE" in node.hardware_profile["gas_membrane"]
    assert "LiFePO4" in node.hardware_profile["battery_chemistry"]

    gateway = BasinGateway(
        gateway_id="GW-CUENCA-01",
        lat=-33.4070,
        lon=-70.5480,
        altitude_m=1120.0
    )

    # Actualizar nodo con ignición local
    out = node.update_environment_and_infer(
        ambient_temp_c=33.0,
        co2_ppm=580.0,
        voc_ppb=120.0,
        wind_speed_kmh=28.0,
        wind_dir_deg=65.0,
        local_heat_c=25.0,
        dt_sec=1.0
    )

    print("Salida Nodo:", out["node_id"], "Temp Sensor:", out["telemetry"]["sensor_temp_c"], "Alerta:", out["inference"]["alert_level"])
    assert out["lora_tx"]["packet_size_bytes"] == 32
    assert out["lora_tx"]["packet_hex"] is not None

    # Gateway relay
    relayed = gateway.relay_packet(node.latest_lora_packet_bytes, node.node_id)
    assert relayed["gateway_id"] == "GW-CUENCA-01"
    assert relayed["payload"]["node_id_int"] == 3
    print("Relay Gateway Satelital exitoso:", relayed["uplink_type"])

if __name__ == "__main__":
    test_lora_compact_packet()
    test_neuromorphic_edge_inference()
    test_tree_node_model_and_gateway()
    print("\nTODOS LOS TESTS DE NODOS ARBÓREOS Y LORA PASARON EXITOSAMENTE!")
