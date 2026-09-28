"""
FLYBRIDGE — Servidor Central de Misiones & Orquestador de Red
Conecta todo el flujo operativo:
[Bosque: Nodos Arbóreos Ignífugos]
       │
       ▼ (LoRaWAN / LoRa Mesh 915 MHz)
[Gateway de Cuenca / Enlace Satelital o 4G]
       │
       ▼
[Servidor Central / API de Misiones]
       │
       ▼
[Tenencia de Autoridades: Cuartel Bomberos / Retén Carabineros]
  ├── Drone-in-a-Box (Despegue <45s)
  └── Panel en Tiempo Real (Bomberos & CENCO)
"""

import time
import math
import random
from typing import Dict, Any, List, Optional, Tuple

from .tree_node import TreeNodeModel, BasinGateway, LoRaCompactPacket
from .docking_station import DroneInABoxStation, AuthorityFacility
from .authority_dispatch import AuthorityDispatchCoordinator

class CentralMissionServer:
    """
    Servidor Central & API de Misiones:
    - Administra la red de Nodos Arbóreos Ignífugos en la cuenca.
    - Administra el Gateway de Cuenca con enlace satelital/4G.
    - Ejecuta la supervisión del Drone-in-a-Box en la Tenencia de Autoridades.
    - Emite los despachos operacionales hacia la Central de Alarmas de Bomberos y CENCO de Carabineros.
    """
    def __init__(
        self,
        center_lat: float = -33.4150,
        center_lon: float = -70.5750,
        base_temp_c: float = 33.5,
        base_humidity_pct: float = 19.0,
        wind_speed_kmh: float = 27.0,
        wind_dir_deg: float = 65.0
    ):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.ambient_temp_c = base_temp_c
        self.humidity_pct = base_humidity_pct
        self.wind_speed_kmh = wind_speed_kmh
        self.wind_dir_deg = wind_dir_deg
        self.solar_radiation_wm2 = 780.0

        # 1. ── RED DE NODOS ARBÓREOS IGNÍFUGOS DISTRIBUIDOS ──────────────────
        # Malla de 10 nodos arbóreos estratégicos en la cuenca forestal
        node_configs = [
            (1, "NODE-ARBOR-01", "Quillay (Quillaja saponaria)", -33.4105, -70.5650, 640.0),
            (2, "NODE-ARBOR-02", "Peumo (Cryptocarya alba)",     -33.4160, -70.5720, 680.0),
            (3, "NODE-ARBOR-03", "Litre (Lithraea caustica)",    -33.4195, -70.5835, 720.0), # Zona de prueba de foco
            (4, "NODE-ARBOR-04", "Boldo (Peumus boldus)",        -33.4240, -70.5780, 710.0),
            (5, "NODE-ARBOR-05", "Espino (Vachellia caven)",     -33.4080, -70.5540, 610.0),
            (6, "NODE-ARBOR-06", "Maitén (Maytenus boaria)",     -33.4130, -70.5890, 750.0),
            (7, "NODE-ARBOR-07", "Quillay Centenario",           -33.4280, -70.5690, 690.0),
            (8, "NODE-ARBOR-08", "Algarrobo (Prosopis chilensis)", -33.4210, -70.5590, 630.0),
            (9, "NODE-ARBOR-09", "Colliguay (Colliguaja odorifera)", -33.4155, -70.6010, 790.0),
            (10, "NODE-ARBOR-10", "Chagual (Puya chilensis)",    -33.4265, -70.5950, 810.0),
        ]

        self.tree_nodes: List[TreeNodeModel] = []
        for num, n_id, spec, lat, lon, alt in node_configs:
            node = TreeNodeModel(
                node_id=n_id,
                node_num=num,
                tree_species=spec,
                lat=lat,
                lon=lon,
                altitude_m=alt,
                battery_pct=random.uniform(94.0, 99.5)
            )
            self.tree_nodes.append(node)

        # 2. ── GATEWAY DE CUENCA / ENLACE SATELITAL O 4G ────────────────────
        self.gateway = BasinGateway(
            gateway_id="GW-CUENCA-SAN-CARLOS",
            name="Gateway Cerro Cumbre San Carlos",
            lat=-33.4070,
            lon=-70.5480,
            altitude_m=1120.0,
            uplink_type="STARLINK_SATELLITE_4G_BACKUP"
        )

        # 3. ── TENENCIA DE AUTORIDADES & ESTACIÓN DRONE-IN-A-BOX ─────────────
        self.facility = AuthorityFacility(
            facility_id="TENENCIA-BOMBEROS-CARABINEROS-01",
            name="Cuartel 14ª Cía Bomberos & Subcomisaría de Carabineros San Carlos",
            lat=-33.4020,
            lon=-70.5280,
            altitude_m=620.0
        )
        self.docking_station = DroneInABoxStation(
            station_id="DIB-TORRE-CUARTEL-01",
            facility=self.facility
        )

        # 4. ── COORDINADOR DE DESPACHO MULTIORGANISMO ───────────────────────
        self.dispatch_coordinator = AuthorityDispatchCoordinator(
            basin_center_lat=center_lat,
            basin_center_lon=center_lon
        )

        # 5. ── FOCOS ACTIVOS DE CALOR / INCENDIOS SIMULADOS ─────────────────
        # Inicialmente un foco activo en NODE-ARBOR-03
        self.active_hotspots: List[Dict[str, Any]] = [
            {
                "id": "FOCO-IGNICION-01",
                "target_node_id": "NODE-ARBOR-03",
                "lat": -33.4195,
                "lon": -70.5835,
                "peak_temp_c": 64.5,
                "co2_delta_ppm": 240.0,
                "voc_delta_ppb": 85.0,
                "radius_m": 42.0,
                "is_active": True,
                "start_time": time.time() - 120.0
            }
        ]

        # Despachos generados
        self.active_alert_incident: Optional[Dict[str, Any]] = None
        self.bomberos_dispatch_sheet: Optional[Dict[str, Any]] = None
        self.cenco_dispatch_sheet: Optional[Dict[str, Any]] = None
        self.operator_feedback_log: List[Dict[str, Any]] = []

    def set_wind(self, speed_kmh: float, direction_deg: float):
        self.wind_speed_kmh = speed_kmh
        self.wind_dir_deg = direction_deg

    def inject_hotspot(self, node_id: str, peak_temp: float = 68.0):
        """Inyecta un foco térmico y de gases en un nodo específico para probar el sistema."""
        target_node = next((n for n in self.tree_nodes if n.node_id == node_id), None)
        if not target_node:
            return None
        
        # Eliminar anteriores y fijar nuevo
        self.active_hotspots = [
            {
                "id": f"FOCO-{node_id}-{int(time.time()) % 1000}",
                "target_node_id": node_id,
                "lat": target_node.lat,
                "lon": target_node.lon,
                "peak_temp_c": peak_temp,
                "co2_delta_ppm": 280.0,
                "voc_delta_ppb": 110.0,
                "radius_m": 50.0,
                "is_active": True,
                "start_time": time.time()
            }
        ]
        return self.active_hotspots[0]

    def trigger_drone_launch(self, target_node_id: Optional[str] = None):
        """Dispara manualmente el despegue inmediato del dron verificador."""
        if not target_node_id:
            target_node_id = self.active_hotspots[0]["target_node_id"] if self.active_hotspots else "NODE-ARBOR-03"
        target_node = next((n for n in self.tree_nodes if n.node_id == target_node_id), self.tree_nodes[2])
        return self.docking_station.trigger_emergency_launch(
            target_node_id=target_node.node_id,
            target_lat=target_node.lat,
            target_lon=target_node.lon
        )

    def recall_drone(self):
        """Ordena el retorno del dron a la estación en el cuartel."""
        self.docking_station.recall_drone()
        return {"status": "RETURNING_TO_BASE", "drone_id": self.docking_station.drone.drone_id}

    def record_feedback(self, verdict: str, notes: str = ""):
        rec = {
            "timestamp": time.time(),
            "verdict": verdict,
            "notes": notes,
            "alert_incident_id": self.active_alert_incident.get("incident_id") if self.active_alert_incident else "INC-2026-N03",
            "weights_calibrated": True
        }
        self.operator_feedback_log.append(rec)
        return rec

    def step(self, dt: float = 0.5) -> Dict[str, Any]:
        """
        Ciclo maestro del servidor central:
        1. Actualiza nodos arbóreos e inferencia NeuroFly.
        2. Recibe paquetes LoRa a través del Gateway de Cuenca.
        3. Evalúa si se disparó alerta en algún nodo.
        4. Si hay alerta confirmada y el dron está en dock, despega en < 45s automáticamente.
        5. Actualiza simulación de vuelo del dron verificador y sus cargas de pago.
        6. Actualiza despachos en tiempo real para Bomberos y Carabineros CENCO.
        """
        now = time.time()

        # 1. Actualizar nodos arbóreos
        node_telemetries = []
        max_alert_level = 0
        critical_node: Optional[TreeNodeModel] = None

        for node in self.tree_nodes:
            # Calcular influencia de focos activos sobre este nodo
            local_heat = 0.0
            co2_add = 0.0
            voc_add = 0.0

            for hs in self.active_hotspots:
                if not hs.get("is_active"):
                    continue
                dlat = (hs["lat"] - node.lat) * 111139.0
                dlon = (hs["lon"] - node.lon) * 92850.0
                dist_m = math.hypot(dlat, dlon)

                if dist_m < hs["radius_m"] * 2.5:
                    decay = max(0.0, 1.0 - (dist_m / (hs["radius_m"] * 2.5)))
                    local_heat += (hs["peak_temp_c"] - self.ambient_temp_c) * decay
                    co2_add += hs["co2_delta_ppm"] * decay
                    voc_add += hs["voc_delta_ppb"] * decay

            node_out = node.update_environment_and_infer(
                ambient_temp_c=self.ambient_temp_c,
                co2_ppm=415.0 + co2_add,
                voc_ppb=45.0 + voc_add,
                wind_speed_kmh=self.wind_speed_kmh,
                wind_dir_deg=self.wind_dir_deg,
                local_heat_c=local_heat,
                solar_radiation_wm2=self.solar_radiation_wm2,
                dt_sec=dt
            )
            node_telemetries.append(node_out)

            # Transmisión vía Gateway de Cuenca
            if node.latest_lora_packet_bytes:
                self.gateway.relay_packet(node.latest_lora_packet_bytes, node.node_id)

            if node.latest_inference and node.latest_inference["alert_level"] > max_alert_level:
                max_alert_level = node.latest_inference["alert_level"]
                critical_node = node

        # 2. Despliegue automático de Dron Verificador (<45s) ante alerta crítica
        if critical_node and max_alert_level >= 3:
            if self.docking_station.drone.status == "DOCK_CHARGING":
                self.docking_station.trigger_emergency_launch(
                    target_node_id=critical_node.node_id,
                    target_lat=critical_node.lat,
                    target_lon=critical_node.lon
                )

        # 3. Avanzar estación Drone-in-a-Box y dron verificador
        station_state = self.docking_station.step(dt=dt, hotspots=self.active_hotspots)
        drone_state = station_state["drone"]

        # 4. Generar Ficha Táctica de Bomberos y Despacho CENCO Carabineros
        active_target = critical_node or self.tree_nodes[2]
        bomberos_data = self.dispatch_coordinator.compute_bomberos_dispatch(
            target_lat=active_target.lat,
            target_lon=active_target.lon,
            node_id=active_target.node_id,
            wind_speed_kmh=self.wind_speed_kmh,
            wind_dir_deg=self.wind_dir_deg,
            drone_flir=drone_state["thermal_flir"]
        )
        self.bomberos_dispatch_sheet = bomberos_data

        cenco_data = self.dispatch_coordinator.compute_carabineros_cenco_dispatch(
            target_lat=active_target.lat,
            target_lon=active_target.lon,
            node_id=active_target.node_id,
            forensic_optical=drone_state["optical_forensics_4k"]
        )
        self.cenco_dispatch_sheet = cenco_data

        # 5. Generar tarjeta de incidente XAI principal
        incident_card = None
        if max_alert_level >= 2 or drone_state["thermal_flir"].get("target_acquired"):
            incident_card = {
                "incident_id": f"INC-2026-{active_target.node_id}",
                "status": "INCENDIO CONFIRMADO POR DRON" if drone_state["thermal_flir"].get("target_acquired") else "ALERTA TEMPRANA EN NODO ARBÓREO",
                "alert_level": max(max_alert_level, 3 if drone_state["thermal_flir"].get("target_acquired") else 2),
                "origin_node_id": active_target.node_id,
                "species": active_target.tree_species,
                "coordinates": [round(active_target.lat, 6), round(active_target.lon, 6)],
                "detection_source": "Inferencia NeuroFly Edge en Nodo Arbóreo + Verificación Dron",
                "flir_peak_temp_c": drone_state["thermal_flir"].get("core_temp_c", active_target.current_sensor_temp_c),
                "fire_perimeter_m": drone_state["thermal_flir"].get("fire_perimeter_m", 120.0),
                "wind": {
                    "speed_kmh": self.wind_speed_kmh,
                    "direction_deg": self.wind_dir_deg,
                    "cardinal": self.dispatch_coordinator._degrees_to_cardinal(self.wind_dir_deg)
                },
                "verifier_drone": {
                    "status": drone_state["status"],
                    "takeoff_elapsed_s": drone_state["launch_elapsed_sec"],
                    "under_45s": drone_state["takeoff_under_45s"]
                },
                "recommended_action": "DESPACHO INMEDIATO CARROS BOMBA + CORTE PERIMETRAL CENCO"
            }
        self.active_alert_incident = incident_card

        # 6. Formar paquete consolidado de telemetría para WebSocket / REST
        return {
            "timestamp": now,
            "system_mode": "RED_NODOS_ARBOREOS_Y_DRONE_IN_A_BOX",
            "environment": {
                "ambient_temp_c": round(self.ambient_temp_c, 1),
                "humidity_pct": round(self.humidity_pct, 1),
                "wind": {
                    "speed_kmh": round(self.wind_speed_kmh, 1),
                    "direction_deg": round(self.wind_dir_deg, 1),
                    "cardinal": self.dispatch_coordinator._degrees_to_cardinal(self.wind_dir_deg)
                },
                "solar_radiation_wm2": round(self.solar_radiation_wm2, 1),
                "active_hotspots": self.active_hotspots
            },
            "tree_nodes": node_telemetries,
            "gateway": {
                "id": self.gateway.gateway_id,
                "name": self.gateway.name,
                "coords": [self.gateway.lat, self.gateway.lon],
                "altitude_m": self.gateway.altitude_m,
                "uplink": self.gateway.uplink_type,
                "packets_relayed": self.gateway.packets_relayed,
                "status": "ONLINE_SATELLITE_ACTIVE"
            },
            "docking_station": station_state,
            "verifier_drone": drone_state,
            "bomberos_dispatch": bomberos_data,
            "cenco_dispatch": cenco_data,
            "incident": incident_card,
            "operator_feedback_log": self.operator_feedback_log[-5:],
            "system_health": {
                "nodes_online": len(self.tree_nodes),
                "gateway_status": "OK",
                "docking_station_status": station_state["readiness"],
                "authority_facility": self.facility.name
            }
        }
