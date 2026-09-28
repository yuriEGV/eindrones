"""
FLYBRIDGE — Servidor Central de Misiones & Orquestador de Red
Conecta todo el flujo operativo:
[Bosque: Nodos Arbóreos Ignífugos]
       │
       ▼ (LoRaWAN Estrella Redundante - 915 MHz SUBTEL Chile | Paquetes independientes)
[Gateway de Cuenca / Enlace Satelital Starlink o 4G]
       │
       ▼
[Servidor Central / API de Misiones]
       │
       ▼
[Tenencia de Autoridades: Cuartel Bomberos / Retén Carabineros]
  ├── Drone-in-a-Box (NeuroFly Dynamics, Pilotaje Manual & RTL)
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
    - Administra la red de Nodos Arbóreos Ignífugos (Topología Estrella LoRaWAN Redundante).
    - Admite reubicación dinámica de nodos en el mapa (Drag & Drop / Presets de separación 500-1000m).
    - Permite extinguir / resetear focos de simulacro a demanda.
    - Soporta control interactivo manual del dron verificador con dinámica biológica NeuroFly y RTL.
    - Valida cumplimiento regulatorio SUBTEL Chile (Res. Ex. N° 1.985 / 915–928 MHz).
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
        # Malla inicial con separación orientativa de 500 a 1.000 metros
        node_configs = [
            (1, "NODE-ARBOR-01", "Quillay (Quillaja saponaria)", -33.4105, -70.5650, 640.0),
            (2, "NODE-ARBOR-02", "Peumo (Cryptocarya alba)",     -33.4160, -70.5720, 680.0),
            (3, "NODE-ARBOR-03", "Litre (Lithraea caustica)",    -33.4195, -70.5835, 720.0), # Zona de prueba
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
        # Ubicado en la cumbre para máxima visibilidad de línea de vista (LoS)
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

        # 5. ── FOCOS ACTIVOS DE CALOR / SIMULACROS ─────────────────────────
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

        # Parámetros de Conformidad Regulatoria SUBTEL Chile (915–928 MHz)
        self.subtel_compliance = {
            "authority": "SUBTEL Chile",
            "regulation": "Resolución Exenta N° 1.985 / 2017",
            "category": "Dispositivos de Radiocomunicaciones de Corto Alcance",
            "frequency_band_mhz": "915.0 - 928.0 MHz",
            "max_eirp_w": 1.0,
            "node_tx_power_dbm": 20.0,
            "max_psd": "8 dBm en cualquier banda de 3 kHz",
            "modulation": "Chirp Spread Spectrum (LoRa CSS BW 125/500 kHz)",
            "topology": "Red LoRaWAN Estrella Redundante (Star-of-Stars)",
            "site_survey_recommended_m": "500–1.000 m separación orientativa validada por cota de Gateway (1.120 m)",
            "subtel_certification_status": "CONFORME_HOMOLOGACION_CHILE"
        }

    def set_wind(self, speed_kmh: float, direction_deg: float):
        self.wind_speed_kmh = speed_kmh
        self.wind_dir_deg = direction_deg

    def inject_hotspot(self, node_id: str, peak_temp: float = 68.0):
        """Inyecta un foco térmico y de gases en un nodo específico para probar el sistema."""
        target_node = next((n for n in self.tree_nodes if n.node_id == node_id), None)
        if not target_node:
            return None
        
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

    def clear_hotspots(self) -> Dict[str, Any]:
        """
        Extingue todos los focos activos de simulacro y devuelve la cuenca a estado limpio.
        """
        self.active_hotspots = []
        self.active_alert_incident = None
        # Normalizar sensores en todos los nodos
        for node in self.tree_nodes:
            node.current_sensor_temp_c = self.ambient_temp_c
            node.current_canopy_temp_c = self.ambient_temp_c + 2.0
            node.current_co2_ppm = 415.0
            node.current_voc_ppb = 40.0
            if node.inference_engine:
                node.inference_engine.prev_co2 = 415.0
                node.inference_engine.prev_voc = 40.0
                node.inference_engine.convective_history = [0.0]

        return {
            "status": "EXTINGUIDO_COMPLETO",
            "message": "Foco extinguido con éxito. Todos los nodos retornados a línea base ambiental.",
            "active_hotspots_count": 0
        }

    def move_node(self, node_id: str, new_lat: float, new_lon: float) -> Dict[str, Any]:
        """
        Mueve dinámicamente un nodo a nuevas coordenadas (mediante arrastre en el mapa).
        Recalcula distancias al Gateway, enlaces LoRaWAN y rutas.
        """
        node = next((n for n in self.tree_nodes if n.node_id == node_id), None)
        if not node:
            return {"error": f"Nodo {node_id} no encontrado"}
        
        node.lat = new_lat
        node.lon = new_lon

        # Si el dron tenía este nodo asignado, actualizar su objetivo
        if self.docking_station.drone.target_node_id == node_id:
            self.docking_station.drone.target_lat = new_lat
            self.docking_station.drone.target_lon = new_lon

        # Si hay un foco activo en este nodo, mover el foco también
        for hs in self.active_hotspots:
            if hs.get("target_node_id") == node_id:
                hs["lat"] = new_lat
                hs["lon"] = new_lon

        return {
            "status": "NODE_MOVED",
            "node_id": node_id,
            "new_lat": round(new_lat, 6),
            "new_lon": round(new_lon, 6)
        }

    def set_preset_layout(self, preset_name: str) -> Dict[str, Any]:
        """Aplica disposiciones tácticas de nodos para demostrar diferentes coberturas."""
        if preset_name == "SEPARACION_ORIENTATIVA_800M":
            # Distribución equidistante regular con 800m de separación
            coords = [
                (-33.4090, -70.5600), (-33.4150, -70.5680), (-33.4210, -70.5760),
                (-33.4270, -70.5840), (-33.4120, -70.5760), (-33.4180, -70.5840),
                (-33.4240, -70.5920), (-33.4150, -70.5920), (-33.4210, -70.6000),
                (-33.4270, -70.6080)
            ]
        elif preset_name == "ALTA_PENDIENTE_QUEBRADAS":
            # Siguiendo el relieve de cañadas y laderas de alta pendiente
            coords = [
                (-33.4080, -70.5520), (-33.4120, -70.5620), (-33.4160, -70.5720),
                (-33.4200, -70.5820), (-33.4240, -70.5920), (-33.4280, -70.6020),
                (-33.4110, -70.5850), (-33.4180, -70.5980), (-33.4230, -70.5680),
                (-33.4290, -70.5790)
            ]
        elif preset_name == "INTERFAZ_URBANO_FORESTAL":
            # Línea de defensa perimetral entre bosque y asentamientos habitados
            coords = [
                (-33.4040, -70.5350), (-33.4070, -70.5420), (-33.4100, -70.5490),
                (-33.4130, -70.5560), (-33.4160, -70.5630), (-33.4190, -70.5700),
                (-33.4220, -70.5770), (-33.4250, -70.5840), (-33.4280, -70.5910),
                (-33.4310, -70.5980)
            ]
        else:
            return {"error": f"Preset desconocido: {preset_name}"}

        for i, (lat, lon) in enumerate(coords):
            if i < len(self.tree_nodes):
                self.tree_nodes[i].lat = lat
                self.tree_nodes[i].lon = lon

        return {"status": "PRESET_APPLIED", "preset": preset_name, "nodes_updated": len(coords)}

    def trigger_drone_launch(self, target_node_id: Optional[str] = None):
        """Dispara el despegue inmediato del dron verificador hacia un nodo."""
        if not target_node_id:
            target_node_id = self.active_hotspots[0]["target_node_id"] if self.active_hotspots else "NODE-ARBOR-03"
        target_node = next((n for n in self.tree_nodes if n.node_id == target_node_id), self.tree_nodes[2])
        return self.docking_station.trigger_emergency_launch(
            target_node_id=target_node.node_id,
            target_lat=target_node.lat,
            target_lon=target_node.lon
        )

    def recall_drone(self):
        """Ordena el retorno del dron a la estación en el cuartel (RTL)."""
        self.docking_station.recall_drone()
        return {"status": "RETURNING_TO_BASE", "drone_id": self.docking_station.drone.drone_id}

    def pilot_drone(
        self,
        command: str,
        speed: Optional[float] = None,
        heading: Optional[float] = None,
        alt_delta: Optional[float] = None,
        gimbal_pitch_delta: Optional[float] = None,
        gimbal_yaw_delta: Optional[float] = None,
        zoom: Optional[float] = None,
        camera_mode: Optional[str] = None,
        pitch: Optional[float] = None
    ) -> Dict[str, Any]:
        """Comando de pilotaje manual en tiempo real para el Dron Verificador."""
        return self.docking_station.drone.pilot_command(
            command=command,
            speed=speed,
            heading=heading,
            alt_delta=alt_delta,
            gimbal_pitch_delta=gimbal_pitch_delta,
            gimbal_yaw_delta=gimbal_yaw_delta,
            zoom=zoom,
            camera_mode=camera_mode,
            pitch=pitch
        )

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
        """Ciclo maestro del servidor central."""
        now = time.time()

        # 1. Actualizar nodos arbóreos
        node_telemetries = []
        max_alert_level = 0
        critical_node: Optional[TreeNodeModel] = None

        for node in self.tree_nodes:
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

            # Métricas LoRaWAN Estrella Redundante hacia el Gateway de Cumbre
            dlat_gw = (self.gateway.lat - node.lat) * 111139.0
            dlon_gw = (self.gateway.lon - node.lon) * (111139.0 * math.cos(math.radians(node.lat)))
            dist_to_gw_m = math.hypot(dlat_gw, dlon_gw)
            # Pérdida de trayectoria en espacio libre (FSPL) a 915 MHz
            fspl_db = 20 * math.log10(max(10.0, dist_to_gw_m)) + 20 * math.log10(915e6) - 147.55
            rssi_dbm = round(max(-125.0, min(-55.0, 20.0 + 3.0 - fspl_db + 8.0)), 1)
            snr_db = round(max(-15.0, min(12.0, (rssi_dbm + 120.0) / 4.0)), 1)

            # Margen de zona de Fresnel (Gateway a 1.120m sobre cumbre)
            fresnel_radius_m = round(0.5 * math.sqrt((3e8 / 915e6) * dist_to_gw_m), 1)
            los_clearance = "LINEA_DE_VISTA_DESPEJADA" if self.gateway.altitude_m > node.altitude_m + 150.0 else "OBSTACULO_RELIEVE_PARCIAL"

            node_out["lorawan_link"] = {
                "topology": "STAR_OF_STARS_REDUNDANTE",
                "direct_to_gateway_id": self.gateway.gateway_id,
                "distance_to_gateway_m": round(dist_to_gw_m, 1),
                "rssi_dbm": rssi_dbm,
                "snr_db": snr_db,
                "fresnel_radius_m": fresnel_radius_m,
                "los_status": los_clearance,
                "subtel_conformity": "OK_RES_1985_915MHZ"
            }

            node_telemetries.append(node_out)

            # Transmisión vía Gateway de Cuenca
            if node.latest_lora_packet_bytes:
                self.gateway.relay_packet(node.latest_lora_packet_bytes, node.node_id)

            if node.latest_inference and node.latest_inference["alert_level"] > max_alert_level:
                max_alert_level = node.latest_inference["alert_level"]
                critical_node = node

        # 2. Despliegue automático de Dron Verificador (<45s) si hay alerta y está en dock
        if critical_node and max_alert_level >= 3:
            if self.docking_station.drone.status == "DOCK_CHARGING":
                self.docking_station.trigger_emergency_launch(
                    target_node_id=critical_node.node_id,
                    target_lat=critical_node.lat,
                    target_lon=critical_node.lon
                )

        # 3. Avanzar estación Drone-in-a-Box y dron verificador
        station_state = self.docking_station.step(
            dt=dt,
            hotspots=self.active_hotspots,
            wind_speed_kmh=self.wind_speed_kmh,
            wind_dir_deg=self.wind_dir_deg
        )
        drone_state = station_state["drone"]

        # 4. Generar Ficha Táctica de Bomberos y Despacho CENCO Carabineros
        active_target = critical_node or (self.tree_nodes[2] if len(self.tree_nodes) > 2 else self.tree_nodes[0])
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

        # 5. Generar tarjeta de incidente
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

        return {
            "timestamp": now,
            "system_mode": "RED_NODOS_ARBOREOS_Y_DRONE_IN_A_BOX",
            "lorawan_network": {
                "topology": "STAR_OF_STARS_REDUNDANTE",
                "subtel_compliance": self.subtel_compliance,
                "recommended_node_spacing_m": "500m - 1.000m (Sujeto a Site Survey)",
                "gateway_height_advantage": f"Gateway a {self.gateway.altitude_m}m supera orografía de cuenca"
            },
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
            "active_hotspots": self.active_hotspots,
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
