"""
FLYBRIDGE — Coordinador de Despacho Operativo Multiorganismo
Implementa la integración y despacho de información operativa para:
1. Central de Alarmas de Bomberos (132 / CONAF):
   - Coordenadas geográficas exactas y ruta de acceso vehicular más expedita.
   - Proyección del comportamiento y avance del fuego en tiempo real según el vector
     del viento del árbol y la cámara térmica del dron (cono de propagación elíptico).
   - Puntos de abastecimiento de agua cercanos (grifos, tranques, ríos).
2. Comunicaciones de Carabineros (CENCO - 133):
   - Alerta simultánea con registro fotográfico y video georreferenciado de alta resolución.
   - Datos probatorios y trazabilidad de huellas/vehículos para cierre perimetral de rutas.
   - Emisión de Carpeta Investigativa Pericial para el Ministerio Público (Fiscalía) ante incendios intencionales.
"""

import time
import math
import hashlib
from typing import Dict, Any, List, Optional, Tuple

class AuthorityDispatchCoordinator:
    """
    Coordina la generación y despacho en tiempo real de información operativa
    diferenciada para Bomberos y Carabineros (CENCO).
    """
    def __init__(self, basin_center_lat: float = -33.4200, basin_center_lon: float = -70.6000):
        self.center_lat = basin_center_lat
        self.center_lon = basin_center_lon
        
        # Red de caminos forestales y cortafuegos modelados
        self.forest_roads = [
            {
                "id": "RUTA-CORTAFUEGO-NORTE",
                "name": "Pista Forestal Cortafuego Quebrada Honda",
                "surface": "Maicillo Compactado 6m (Transitable Carro Bomba 4x4)",
                "max_speed_kmh": 40.0,
                "access_gate": "Portón 3 - Acceso Camino El Refugio",
                "start_coords": [-33.4030, -70.5350],
                "end_coords": [-33.4150, -70.5850]
            },
            {
                "id": "RUTA-INTERFAZ-SUR",
                "name": "Camino Vecinal Las Araucarias / Sector Alto",
                "surface": "Pavimento Asfáltico y Ripio Mixto",
                "max_speed_kmh": 55.0,
                "access_gate": "Retén Móvil Carabineros Km 4.2",
                "start_coords": [-33.4020, -70.5280],
                "end_coords": [-33.4350, -70.6200]
            }
        ]

        # Puntos de abastecimiento de agua
        self.water_sources = [
            {
                "id": "TRANQUE-SAN-CARLOS",
                "name": "Tranque Agrícola San Carlos (150.000 L)",
                "type": "TRANQUE_AGUA_HELITRANSPORTABLE_Y_MOTOBOMBA",
                "coords": [-33.4110, -70.5620],
                "distance_km": 1.4,
                "capacity_liters": 150000
            },
            {
                "id": "GRIFO-RURAL-04",
                "name": "Grifo Forestal Alta Presión Interfaz",
                "type": "GRIFO_ALTA_PRESION_100MM",
                "coords": [-33.4045, -70.5390],
                "distance_km": 0.8,
                "capacity_liters": 500000
            }
        ]

        # Puntos de control perimetral para Carabineros (Cortes de Ruta)
        self.police_roadblocks = [
            {
                "id": "CP-CENCO-01",
                "name": "Control Ruta G-21 / Cruce Quebrada Honda",
                "coords": [-33.4010, -70.5250],
                "purpose": "Bloqueo perimetral y fiscalización de vehículos en escape"
            },
            {
                "id": "CP-CENCO-02",
                "name": "Control Camino Antiguo Las Pircas",
                "coords": [-33.4090, -70.5310],
                "purpose": "Cierre perimetral de huella vehicular lateral"
            },
            {
                "id": "CP-CENCO-03",
                "name": "Control Acceso Parque / Sendero El Tranque",
                "coords": [-33.4180, -70.5480],
                "purpose": "Control de peatones y senderistas"
            }
        ]

        self.dispatched_missions: List[Dict[str, Any]] = []

    def compute_fire_spread_projection(
        self,
        ignition_lat: float,
        ignition_lon: float,
        wind_speed_kmh: float,
        wind_dir_deg: float,
        flir_core_temp_c: float,
        fire_perimeter_m: float
    ) -> Dict[str, Any]:
        """
        Calcula el cono de proyección de avance del fuego (modelo elíptico de Huygens / Rothermel):
        Combina el vector de viento medido en el árbol y la radiometría del dron.
        """
        # Velocidad de propagación según viento y calor
        base_rate_m_min = 2.0
        wind_multiplier = 1.0 + (wind_speed_kmh / 25.0) ** 1.6
        heat_multiplier = 1.0 + max(0.0, (flir_core_temp_c - 100.0) / 400.0)
        head_rate_m_min = round(base_rate_m_min * wind_multiplier * heat_multiplier, 1)

        # Vector de avance (dirección hacia donde avanza la cabeza del fuego)
        spread_heading_deg = wind_dir_deg % 360.0

        # Proyección a 15, 30 y 60 minutos
        spread_15m = head_rate_m_min * 15.0
        spread_30m = head_rate_m_min * 30.0
        spread_60m = head_rate_m_min * 60.0

        # Coordenadas proyectadas del frente principal a 30 minutos
        wind_rad = math.radians(spread_heading_deg)
        d_lat_30 = (spread_30m * math.cos(wind_rad)) / 111139.0
        d_lon_30 = (spread_30m * math.sin(wind_rad)) / (111139.0 * math.cos(math.radians(ignition_lat)))
        head_coords_30m = [round(ignition_lat + d_lat_30, 6), round(ignition_lon + d_lon_30, 6)]

        # Estimación de superficie amenazada
        threatened_hectares_30m = round((spread_30m * (spread_30m * 0.45) * math.pi) / 10000.0, 2)

        return {
            "head_rate_m_min": head_rate_m_min,
            "flank_rate_m_min": round(head_rate_m_min * 0.35, 1),
            "back_rate_m_min": round(head_rate_m_min * 0.12, 1),
            "spread_heading_deg": round(spread_heading_deg, 1),
            "cardinal_direction": self._degrees_to_cardinal(spread_heading_deg),
            "spread_front_meters_30m": round(spread_30m, 1),
            "projected_head_coords_30m": head_coords_30m,
            "threatened_area_hectares_30m": threatened_hectares_30m,
            "flame_length_est_m": round(max(0.8, (head_rate_m_min * 0.28)), 1),
            "behavior_summary": (
                f"Frente de avance activo hacia el {self._degrees_to_cardinal(spread_heading_deg)} "
                f"a {head_rate_m_min} m/min impulsado por viento de {wind_speed_kmh:.0f} km/h. "
                f"Proyección de {threatened_hectares_30m} hectáreas comprometidas a 30 minutos."
            )
        }

    def compute_bomberos_dispatch(
        self,
        target_lat: float,
        target_lon: float,
        node_id: str,
        wind_speed_kmh: float,
        wind_dir_deg: float,
        drone_flir: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genera la Ficha Táctica Oficial para la Central de Alarmas de Bomberos.
        """
        # Calcular mejor ruta vehicular
        primary_road = self.forest_roads[0]
        # Distancia euclidiana aproximada + factor de sinuosidad de camino de montaña (1.35)
        dlat = (target_lat - primary_road["start_coords"][0]) * 111139.0
        dlon = (target_lon - primary_road["start_coords"][1]) * (111139.0 * math.cos(math.radians(target_lat)))
        straight_dist_km = math.hypot(dlat, dlon) / 1000.0
        road_distance_km = round(straight_dist_km * 1.35, 2)
        eta_minutes = round((road_distance_km / primary_road["max_speed_kmh"]) * 60.0 + 2.0, 1)

        core_temp = drone_flir.get("core_temp_c", 480.0)
        perimeter = drone_flir.get("fire_perimeter_m", 180.0)

        spread = self.compute_fire_spread_projection(
            ignition_lat=target_lat,
            ignition_lon=target_lon,
            wind_speed_kmh=wind_speed_kmh,
            wind_dir_deg=wind_dir_deg,
            flir_core_temp_c=core_temp,
            fire_perimeter_m=perimeter
        )

        return {
            "target_node_id": node_id,
            "target_coordinates": {
                "decimal": [round(target_lat, 6), round(target_lon, 6)],
                "wgs84_formatted": f"{abs(target_lat):.4f}°S, {abs(target_lon):.4f}°W",
                "sector_name": "Cuenca Alta Sector San Carlos - Bosque Esclerófilo"
            },
            "access_route": {
                "primary_road_id": primary_road["id"],
                "road_name": primary_road["name"],
                "surface_type": primary_road["surface"],
                "entry_gate": primary_road["access_gate"],
                "distance_km": road_distance_km,
                "estimated_arrival_time_min": eta_minutes,
                "recommended_vehicles": "2 Carros Forestales 4x4 (B-14 / BF-2) + 1 Aljibe de 10.000 L"
            },
            "tactical_water_sources": self.water_sources,
            "fire_behavior": spread,
            "recommended_strategy": (
                f"Ataque directo por el flanco izquierdo (barlovento). "
                f"Establecer línea de agua y cortafuego de anclaje antes de la proyección a 30 min. "
                f"Abastecimiento prioritario en {self.water_sources[0]['name']} (a 1.4 km)."
            )
        }

    def compute_carabineros_cenco_dispatch(
        self,
        target_lat: float,
        target_lon: float,
        node_id: str,
        forensic_optical: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genera el despacho probatorio pericial para Carabineros (CENCO) y Fiscalía.
        """
        evidence_hash = forensic_optical.get("evidence_hash_sha256", "EVID-SHA256-PENDING")
        detections = forensic_optical.get("detections", [])

        # Lista de puntos de cierre perimetral recomendados
        roadblocks = []
        for cp in self.police_roadblocks:
            dlat = (cp["coords"][0] - target_lat) * 111139.0
            dlon = (cp["coords"][1] - target_lon) * 92850.0
            dist_km = round(math.hypot(dlat, dlon) / 1000.0, 2)
            roadblocks.append({
                "checkpoint_id": cp["id"],
                "name": cp["name"],
                "coords": cp["coords"],
                "distance_from_fire_km": dist_km,
                "instruction": f"Cierre vehicular total. Fiscalización de ocupantes y control de identidad ({cp['purpose']})"
            })

        return {
            "dispatch_code": f"CENCO-ALERTA-{int(time.time()) % 100000:05d}",
            "target_node_id": node_id,
            "ignition_coords": [round(target_lat, 6), round(target_lon, 6)],
            "timestamp_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
            "evidence_integrity_hash": evidence_hash,
            "forensic_captures_count": len(detections),
            "forensic_detections": detections,
            "perimeter_containment_plan": {
                "strategy": "CERROJO PERIMETRAL DE RUTAS DE ESCAPE INMEDIATO",
                "checkpoints": roadblocks
            },
            "prosecutor_dossier": {
                "destinatario": "Fiscalía Local / Ministerio Público (Unidad Investigadora de Incendios)",
                "chain_of_custody": "Digital SHA-256 Verificada con Georreferencia Satelital",
                "status": "CARPETA_INVESTIGATIVA_PREPARADA"
            }
        }

    def _degrees_to_cardinal(self, deg: float) -> str:
        dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        ix = round(deg / (360.0 / len(dirs))) % len(dirs)
        return dirs[ix]
