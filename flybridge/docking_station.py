"""
FLYBRIDGE — Estación Drone-in-a-Box en Tenencia de Autoridades & Dron Verificador
Implementa:
1. Base de Operaciones / Docking Station en Cuartel de Bomberos o Retén de Carabineros:
   - Protección contra robo o vandalismo dentro de un recinto oficial.
   - Conexión a red eléctrica 220V estable + UPS de respaldo y logística de guardia.
   - Despliegue automatizado con compuerta motorizada y despegue en menos de 45 segundos (<45 s).
2. Dron Verificador con Dinámica de Vuelo NeuroFly & Control Manual / RTL:
   - Controlador neuromórfico NeuroFly: reflejos optomotores de estabilización ante ráfagas,
     giros sacádicos biomiméticos y modulación de velocidad inspirada en Drosophila.
   - Modo de pilotaje manual con comandos interactivos (W/A/S/D, Altitud, Giro, Hover).
   - Retorno a Base autónomo (RTL / Return to Launch) con aterrizaje de precisión y cierre de compuerta.
   - Cámara en Primera Persona (FPV) con telemetría HUD táctica y control de Gimbal (Pitch / Yaw / Zoom).
   - Carga de pago especializada dual:
     a) Cámara Térmica Radiométrica (FLIR): Núcleo de temperatura (°C) y perímetro (m) para Bomberos.
     b) Cámara Óptica 4K con Zoom: Reconocimiento perimetral forense de senderos, huellas de vehículos
        y personas en fuga para Carabineros (CENCO) y Fiscalía.
"""

import time
import math
import random
import hashlib
from typing import Dict, Any, List, Optional, Tuple

class AuthorityFacility:
    """
    Instalación oficial de las autoridades que alberga la estación Drone-in-a-Box.
    """
    def __init__(
        self,
        facility_id: str = "BASE-AUTORIDAD-01",
        name: str = "14ª Compañía de Bomberos & Retén Móvil Carabineros San Carlos",
        agency: str = "BOMBEROS_CARABINEROS_CONAF",
        lat: float = -33.4020,
        lon: float = -70.5280,
        altitude_m: float = 680.0,
        power_grid: str = "RED_ELECTRICA_ESTABLE_CON_UPS_BACKUP",
        personnel_on_duty: int = 12
    ):
        self.facility_id = facility_id
        self.name = name
        self.agency = agency
        self.lat = lat
        self.lon = lon
        self.altitude_m = altitude_m
        self.power_grid = power_grid
        self.personnel_on_duty = personnel_on_duty
        self.security_status = "PROTEGIDO_RECINTO_OFICIAL_24_7"


class VerifierDroneAgent:
    """
    Dron Verificador de Respuesta Rápida impulsado por el modelo de vuelo NeuroFly.
    - Despega en <45s desde el Docking Station del Cuartel.
    - Vuela de forma autónoma o pilotada manualmente por operador.
    - Incorpora reflejos neuromórficos: Optomotor Reflex (estabilización de deriva),
      Saccadic Turning (giros biológicos rápidos) y Haltere Damping (inercia fluida).
    - Carga de pago dual: FLIR Térmica Radiométrica + Óptica 4K con Zoom 30x y control Gimbal.
    """
    def __init__(
        self,
        drone_id: str = "VERIFIER-01",
        model: str = "NeuroFly Apex-6 Heavy Response",
        home_lat: float = -33.4020,
        home_lon: float = -70.5280,
        home_alt_m: float = 680.0
    ):
        self.drone_id = drone_id
        self.model = model
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.home_alt_m = home_alt_m

        # Estado cinemático
        self.lat = home_lat
        self.lon = home_lon
        self.alt_m = home_alt_m
        self.heading_deg = 0.0
        self.speed_kmh = 0.0
        self.battery_pct = 100.0

        # Estado dinámico NeuroFly
        self.roll_deg = 0.0
        self.pitch_deg = 0.0
        self.yaw_rate_deg_s = 0.0
        self.bio_flight_state = "REST_DOCK"  # REST_DOCK, SACCADE_TURN, OPTOMOTOR_STABILIZE, CRUISE_BIOMIMETIC, HOVER_PRECISION, RTL_HOMING
        self.target_heading_deg = 0.0
        self.target_speed_kmh = 0.0

        # Misión y navegación
        self.status = "DOCK_CHARGING"  # DOCK_CHARGING, PRE_FLIGHT, TAKING_OFF, TRANSIT_OUT, RECON_ORBIT, MANUAL_PILOT, RETURNING, LANDING
        self.target_node_id: Optional[str] = None
        self.target_lat: Optional[float] = None
        self.target_lon: Optional[float] = None
        self.target_alt_m = 75.0  # Altitud de reconocimiento sobre el dosel

        self.launch_start_time: Optional[float] = None
        self.time_to_takeoff_sec: float = 0.0
        self.flight_seconds: float = 0.0

        # Gimbal y FPV
        self.gimbal_pitch_deg = -35.0  # -90 (nadir) a +15 (horizonte)
        self.gimbal_yaw_deg = 0.0     # -180 a +180 relativo a dron
        self.optical_zoom_level = 1.0  # 1.0x a 30.0x
        self.camera_mode = "OPTICAL_4K"  # "OPTICAL_4K" o "FLIR_THERMAL"

        # Telemetría de sensores de carga útil
        self.latest_thermal_flir: Dict[str, Any] = {}
        self.latest_forensic_optical: Dict[str, Any] = {}
        self.flight_trajectory: List[List[float]] = [[home_lat, home_lon]]

    def dispatch_to_target(self, target_node_id: str, target_lat: float, target_lon: float):
        """Orden de despegue y ruta directa precalculada hacia el árbol."""
        self.target_node_id = target_node_id
        self.target_lat = target_lat
        self.target_lon = target_lon
        self.status = "PRE_FLIGHT"
        self.bio_flight_state = "PRE_FLIGHT"
        self.launch_start_time = time.time()
        self.time_to_takeoff_sec = 0.0
        self.flight_trajectory = [[self.lat, self.lon]]

    def return_to_launch(self):
        """Inicia el retorno autónomo a la estación base (RTL / Return to Launch)."""
        self.status = "RTL_RETURNING"
        self.bio_flight_state = "RTL_HOMING"
        self.target_speed_kmh = 72.0

    def pilot_command(
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
        """
        Control manual en tiempo real desde la cabina de pilotaje por el operador.
        Aplica suavizado neuromórfico (NeuroFly) para un comportamiento de vuelo natural.
        """
        # Si el dron está en dock, forzar despegue primero si se le ordena mover
        if self.status in ("DOCK_CHARGING", "LANDING") and command in ("MOVE", "FORWARD", "TAKEOFF"):
            self.status = "TAKING_OFF"
            self.time_to_takeoff_sec = 35.0
            self.alt_m = self.home_alt_m + 30.0

        if command == "RTL":
            self.return_to_launch()
            return {"status": "RTL_TRIGGERED", "drone_status": self.status}

        self.status = "MANUAL_PILOT"
        self.bio_flight_state = "MANUAL_PILOT"

        if command in ("MOVE", "FORWARD"):
            target_spd = speed if speed is not None else 65.0
            self.target_speed_kmh = target_spd
            self.bio_flight_state = "CRUISE_BIOMIMETIC"
            # Advance position in heading direction
            rad = math.radians(self.heading_deg)
            self.lat += math.cos(rad) * 0.0003
            self.lon += math.sin(rad) * 0.0003
            self.flight_trajectory.append([round(self.lat, 6), round(self.lon, 6)])

        elif command == "BACKWARD":
            target_spd = speed if speed is not None else 35.0
            self.target_speed_kmh = target_spd
            self.bio_flight_state = "CRUISE_BIOMIMETIC"
            rad = math.radians(self.heading_deg)
            self.lat -= math.cos(rad) * 0.0002
            self.lon -= math.sin(rad) * 0.0002
            self.flight_trajectory.append([round(self.lat, 6), round(self.lon, 6)])

        elif command == "YAW_LEFT":
            self.target_heading_deg = (self.heading_deg - 15.0) % 360.0
            self.heading_deg = self.target_heading_deg
            self.bio_flight_state = "SACCADE_TURN"

        elif command == "YAW_RIGHT":
            self.target_heading_deg = (self.heading_deg + 15.0) % 360.0
            self.heading_deg = self.target_heading_deg
            self.bio_flight_state = "SACCADE_TURN"

        elif command == "ROTATE":
            if heading is not None:
                self.target_heading_deg = heading % 360.0
                self.heading_deg = self.target_heading_deg
                self.bio_flight_state = "SACCADE_TURN"

        elif command in ("HOVER", "STOP"):
            self.target_speed_kmh = 0.0
            self.speed_kmh = 0.0
            self.bio_flight_state = "HOVER_PRECISION"

        elif command in ("ALTITUDE", "ALTITUDE_UP", "ALTITUDE_DOWN"):
            if alt_delta is not None:
                delta = alt_delta
            elif command == "ALTITUDE_UP":
                delta = 5.0
            elif command == "ALTITUDE_DOWN":
                delta = -5.0
            else:
                delta = 5.0
            self.alt_m = max(self.home_alt_m + 5.0, min(self.home_alt_m + 300.0, self.alt_m + delta))

        elif command == "ORBIT":
            self.status = "RECON_ORBIT"
            self.bio_flight_state = "CRUISE_BIOMIMETIC"
            self.target_speed_kmh = 28.0

        # Ajuste directo o relativo de Gimbal & Cámara
        if pitch is not None:
            self.gimbal_pitch_deg = max(-90.0, min(15.0, pitch))
        elif gimbal_pitch_delta is not None:
            self.gimbal_pitch_deg = max(-90.0, min(15.0, self.gimbal_pitch_deg + gimbal_pitch_delta))

        if gimbal_yaw_delta is not None:
            self.gimbal_yaw_deg = (self.gimbal_yaw_deg + gimbal_yaw_delta + 180.0) % 360.0 - 180.0
        if zoom is not None:
            self.optical_zoom_level = max(1.0, min(30.0, zoom))
        if camera_mode in ("OPTICAL_4K", "FLIR_THERMAL"):
            self.camera_mode = camera_mode

        return {
            "status": "COMMAND_APPLIED",
            "drone_id": self.drone_id,
            "flight_status": self.status,
            "bio_flight_state": self.bio_flight_state,
            "heading": round(self.heading_deg, 1),
            "speed_kmh": round(self.speed_kmh, 1),
            "alt_m": round(self.alt_m, 1),
            "gimbal_pitch_deg": round(self.gimbal_pitch_deg, 1),
            "gimbal_yaw_deg": round(self.gimbal_yaw_deg, 1),
            "zoom_optical": round(self.optical_zoom_level, 1),
            "camera_mode": self.camera_mode,
            "gimbal": {
                "pitch": round(self.gimbal_pitch_deg, 1),
                "yaw": round(self.gimbal_yaw_deg, 1),
                "zoom": round(self.optical_zoom_level, 1),
                "mode": self.camera_mode
            }
        }

    def step_simulation(
        self,
        dt: float = 0.5,
        fire_hotspots: Optional[List[Dict[str, Any]]] = None,
        wind_speed_kmh: float = 27.0,
        wind_dir_deg: float = 65.0
    ) -> Dict[str, Any]:
        """Avanza la simulación física, aerodinámica y de cargas de pago del dron."""
        now = time.time()

        # ── Control Motor Neuromórfico NeuroFly ────────────────────────────────
        # Simulación de reflejos optomotores de Drosophila:
        # Corrige deriva inducida por viento cruzado y produce giros sacádicos suaves.
        heading_error = (self.target_heading_deg - self.heading_deg + 180.0) % 360.0 - 180.0
        if abs(heading_error) > 2.0:
            # Giro sacádico con amortiguación
            turn_rate = max(-180.0, min(180.0, heading_error * 3.5))
            self.heading_deg = (self.heading_deg + turn_rate * dt) % 360.0
            self.roll_deg = -turn_rate * 0.15  # Inclinación lateral en viraje
            self.bio_flight_state = "SACCADE_TURN"
        else:
            self.roll_deg *= 0.8  # Restablece nivel alar
            if self.speed_kmh > 15.0:
                self.bio_flight_state = "CRUISE_BIOMIMETIC"

        # Aceleración suave inspirada en insectos
        speed_error = self.target_speed_kmh - self.speed_kmh
        self.speed_kmh += speed_error * (0.35 * dt * 5.0)

        # Inclinación de cabeceo (pitch) proporcional a aceleración longitudinal
        self.pitch_deg = max(-25.0, min(25.0, (self.speed_kmh / 80.0) * -20.0))

        # ── Máquina de Estados de Vuelo ───────────────────────────────────────
        if self.status == "DOCK_CHARGING":
            self.battery_pct = min(100.0, self.battery_pct + 0.15 * dt)
            self.speed_kmh = 0.0
            self.target_speed_kmh = 0.0
            self.bio_flight_state = "REST_DOCK"

        elif self.status == "PRE_FLIGHT":
            self.time_to_takeoff_sec += dt
            if self.time_to_takeoff_sec >= 14.0:
                self.status = "TAKING_OFF"
                self.bio_flight_state = "TAKEOFF_SPOOL"

        elif self.status == "TAKING_OFF":
            self.time_to_takeoff_sec += dt
            self.alt_m += 6.5 * dt
            if self.time_to_takeoff_sec >= 32.0 or self.alt_m >= self.home_alt_m + 50.0:
                # Despegue verificado en < 45 segundos!
                self.status = "TRANSIT_OUT"
                self.target_speed_kmh = 75.0

        elif self.status == "TRANSIT_OUT":
            self.flight_seconds += dt
            self.battery_pct = max(5.0, self.battery_pct - 0.015 * dt)
            self.target_speed_kmh = 76.0

            # Navegación hacia el árbol
            if self.target_lat is not None and self.target_lon is not None:
                dlat = (self.target_lat - self.lat) * 111139.0
                dlon = (self.target_lon - self.lon) * (111139.0 * math.cos(math.radians(self.lat)))
                dist_m = math.hypot(dlat, dlon)
                self.target_heading_deg = math.degrees(math.atan2(dlon, dlat)) % 360.0
                
                # Desplazamiento
                step_dist_m = (self.speed_kmh / 3.6) * dt
                if dist_m <= step_dist_m * 1.5:
                    self.lat = self.target_lat
                    self.lon = self.target_lon
                    self.status = "RECON_ORBIT"
                    self.target_speed_kmh = 24.0
                else:
                    move_frac = step_dist_m / dist_m
                    self.lat += (self.target_lat - self.lat) * move_frac
                    self.lon += (self.target_lon - self.lon) * move_frac

            self.flight_trajectory.append([round(self.lat, 6), round(self.lon, 6)])
            if len(self.flight_trajectory) > 250:
                self.flight_trajectory.pop(0)

        elif self.status == "RECON_ORBIT":
            self.flight_seconds += dt
            self.battery_pct = max(5.0, self.battery_pct - 0.012 * dt)
            self.target_speed_kmh = 24.0

            # Órbita perimetral circular de reconocimiento (radio 95m)
            orbit_angle = (self.flight_seconds * 0.42) % (2 * math.pi)
            if self.target_lat and self.target_lon:
                r_lat = (95.0 / 111139.0) * math.cos(orbit_angle)
                r_lon = (95.0 / (111139.0 * math.cos(math.radians(self.lat)))) * math.sin(orbit_angle)
                self.lat = self.target_lat + r_lat
                self.lon = self.target_lon + r_lon
                self.target_heading_deg = (math.degrees(orbit_angle) + 90.0) % 360.0

            self.flight_trajectory.append([round(self.lat, 6), round(self.lon, 6)])

        elif self.status == "MANUAL_PILOT":
            # Desplazamiento en la dirección del heading actual
            self.flight_seconds += dt
            self.battery_pct = max(5.0, self.battery_pct - 0.014 * dt)
            
            if self.speed_kmh > 1.0:
                step_dist_m = (self.speed_kmh / 3.6) * dt
                heading_rad = math.radians(self.heading_deg)
                dlat_deg = (step_dist_m * math.cos(heading_rad)) / 111139.0
                dlon_deg = (step_dist_m * math.sin(heading_rad)) / (111139.0 * math.cos(math.radians(self.lat)))
                self.lat += dlat_deg
                self.lon += dlon_deg

            self.flight_trajectory.append([round(self.lat, 6), round(self.lon, 6)])
            if len(self.flight_trajectory) > 250:
                self.flight_trajectory.pop(0)

        elif self.status == "RETURNING":
            self.flight_seconds += dt
            self.battery_pct = max(5.0, self.battery_pct - 0.015 * dt)
            self.target_speed_kmh = 72.0
            
            dlat = (self.home_lat - self.lat) * 111139.0
            dlon = (self.home_lon - self.lon) * (111139.0 * math.cos(math.radians(self.lat)))
            dist_m = math.hypot(dlat, dlon)
            if dist_m < 15.0:
                self.status = "LANDING"
                self.target_speed_kmh = 0.0
            else:
                self.target_heading_deg = math.degrees(math.atan2(dlon, dlat)) % 360.0
                step_dist_m = (self.speed_kmh / 3.6) * dt
                move_frac = step_dist_m / dist_m
                self.lat += (self.home_lat - self.lat) * move_frac
                self.lon += (self.home_lon - self.lon) * move_frac

            self.flight_trajectory.append([round(self.lat, 6), round(self.lon, 6)])

        elif self.status == "LANDING":
            self.alt_m = max(self.home_alt_m, self.alt_m - 4.5 * dt)
            self.speed_kmh = 0.0
            self.target_speed_kmh = 0.0
            if self.alt_m <= self.home_alt_m + 0.5:
                self.status = "DOCK_CHARGING"
                self.bio_flight_state = "REST_DOCK"

        # Simular lectura de cargas de pago (FLIR + Óptica 4K)
        self._sample_payloads(fire_hotspots)

        total_launch_s = round(self.time_to_takeoff_sec, 1)

        # Telemetría FPV HUD enriquecida
        fpv_hud = {
            "pitch_deg": round(self.pitch_deg, 1),
            "roll_deg": round(self.roll_deg, 1),
            "yaw_deg": round(self.heading_deg, 1),
            "altitude_agl_m": round(max(0.0, self.alt_m - self.home_alt_m), 1),
            "altitude_msl_m": round(self.alt_m, 1),
            "groundspeed_kmh": round(self.speed_kmh, 1),
            "airspeed_kmh": round(max(0.0, self.speed_kmh + random.uniform(-1.5, 1.5)), 1),
            "battery_pct": round(self.battery_pct, 1),
            "gimbal_pitch_deg": round(self.gimbal_pitch_deg, 1),
            "gimbal_yaw_deg": round(self.gimbal_yaw_deg, 1),
            "optical_zoom_level": round(self.optical_zoom_level, 1),
            "camera_mode": self.camera_mode,
            "bio_flight_state": self.bio_flight_state,
            "wind_cross_correction_deg": round((wind_dir_deg - self.heading_deg + 180) % 360 - 180, 1)
        }

        return {
            "drone_id": self.drone_id,
            "status": self.status,
            "bio_flight_state": self.bio_flight_state,
            "latitude": round(self.lat, 6),
            "longitude": round(self.lon, 6),
            "altitude_m": round(self.alt_m, 1),
            "heading_deg": round(self.heading_deg, 1),
            "speed_kmh": round(self.speed_kmh, 1),
            "battery_pct": round(self.battery_pct, 1),
            "flight_seconds": round(self.flight_seconds, 1),
            "launch_elapsed_sec": total_launch_s,
            "takeoff_under_45s": total_launch_s <= 45.0,
            "target_node": self.target_node_id,
            "trajectory": self.flight_trajectory[-60:],
            "gimbal_pitch_deg": round(self.gimbal_pitch_deg, 1),
            "gimbal_yaw_deg": round(self.gimbal_yaw_deg, 1),
            "zoom_optical": round(self.optical_zoom_level, 1),
            "thermal_flir": self.latest_thermal_flir,
            "optical_forensics_4k": self.latest_forensic_optical,
            "fpv_hud": fpv_hud
        }

    def _sample_payloads(self, hotspots: Optional[List[Dict[str, Any]]]):
        """Procesa las mediciones de la cámara FLIR y la óptica 4K con Zoom."""
        nearest_hs = None
        min_dist_m = float("inf")
        if hotspots:
            for hs in hotspots:
                if not hs.get("is_active", True):
                    continue
                dlat = (hs["lat"] - self.lat) * 111139.0
                dlon = (hs["lon"] - self.lon) * (111139.0 * math.cos(math.radians(self.lat)))
                dist = math.hypot(dlat, dlon)
                if dist < min_dist_m:
                    min_dist_m = dist
                    nearest_hs = hs

        in_proximity = (min_dist_m < 320.0 and nearest_hs is not None)

        if in_proximity and nearest_hs:
            # Lectura radiométrica FLIR real sobre el núcleo
            peak_temp = nearest_hs.get("peak_temp_c", 62.0) + 420.0
            perimeter_m = round(math.pi * 2 * nearest_hs.get("radius_m", 45.0), 1)
            spread_velocity_m_min = 3.8
            fire_intensity_kw_m = 1850.0

            self.latest_thermal_flir = {
                "sensor": "FLIR Boson 640 Radiometric IR",
                "target_acquired": True,
                "core_temp_c": round(peak_temp, 1),
                "fire_perimeter_m": perimeter_m,
                "spread_velocity_m_min": spread_velocity_m_min,
                "fireline_intensity_kw_m": fire_intensity_kw_m,
                "hotspot_coords": [round(nearest_hs["lat"], 6), round(nearest_hs["lon"], 6)],
                "thermal_status": "FRENTE_ACTIVO_CONFIRMADO"
            }

            evidence_hash = hashlib.sha256(
                f"{self.lat}:{self.lon}:{time.time()}:FORENSIC_CAPTURE".encode()
            ).hexdigest()[:16].upper()

            self.latest_forensic_optical = {
                "sensor": "Sony 4K HDR Exmor R con Zoom Óptico 30x",
                "zoom_factor": f"{self.optical_zoom_level:.1f}x",
                "timestamp_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                "evidence_hash_sha256": evidence_hash,
                "detections": [
                    {
                        "type": "VEHICULO_SOSPECHOSO",
                        "confidence": 0.94,
                        "description": "Camioneta Pickup 4x4 blanca estacionada en huella cortafuego no autorizada",
                        "distance_from_ignition_m": 120.0,
                        "coords": [round(nearest_hs["lat"] - 0.0011, 6), round(nearest_hs["lon"] - 0.0008, 6)],
                        "heading": "Hacia Camino Principal Sector Alto"
                    },
                    {
                        "type": "HUELLA_NEUMATICO_FRESCA",
                        "confidence": 0.88,
                        "description": "Rodado de tracción reciente sobre cubierta de tierra y pastizal seco",
                        "distance_from_ignition_m": 85.0,
                        "coords": [round(nearest_hs["lat"] - 0.0007, 6), round(nearest_hs["lon"] - 0.0005, 6)]
                    },
                    {
                        "type": "INDIVIDUO_EN_FUGA",
                        "confidence": 0.82,
                        "description": "Silueta humana desplazándose a paso rápido hacia sendero quebrada sur",
                        "distance_from_ignition_m": 165.0,
                        "coords": [round(nearest_hs["lat"] - 0.0015, 6), round(nearest_hs["lon"] + 0.0003, 6)]
                    }
                ],
                "evidential_record_status": "DISPONIBLE_PARA_CENCO_Y_MINISTERIO_PUBLICO"
            }

        else:
            self.latest_thermal_flir = {
                "sensor": "FLIR Boson 640 Radiometric IR",
                "target_acquired": False,
                "core_temp_c": 28.4,
                "fire_perimeter_m": 0.0,
                "spread_velocity_m_min": 0.0,
                "thermal_status": "ESCANEANDO_BARLOVENTO"
            }
            self.latest_forensic_optical = {
                "sensor": "Sony 4K HDR Exmor R con Zoom Óptico 30x",
                "zoom_factor": f"{self.optical_zoom_level:.1f}x",
                "detections": [],
                "evidential_record_status": "STANDBY_PATRULLA"
            }


class DroneInABoxStation:
    """
    Docking Station automatizada montada en el techo o torre del recinto de la Autoridad.
    - Apertura motorizada de compuertas meteorológicas herméticas.
    - Despliegue en < 45 segundos.
    - Soporte de pilotaje manual y RTL.
    """
    def __init__(
        self,
        station_id: str = "DIB-STATION-CUARTEL-01",
        facility: Optional[AuthorityFacility] = None
    ):
        self.station_id = station_id
        self.facility = facility or AuthorityFacility()
        self.hatch_status = "CLOSED"  # CLOSED, OPENING, OPEN, CLOSING
        self.hatch_open_pct = 0.0
        self.power_grid_connected = True
        self.ups_charge_pct = 100.0
        self.weather_protection = "IP67_CLIMATE_SEALED"
        
        # Dron asignado a la bahía
        self.drone = VerifierDroneAgent(
            drone_id="DRON-VERIFICADOR-01",
            home_lat=self.facility.lat,
            home_lon=self.facility.lon,
            home_alt_m=self.facility.altitude_m
        )

    def trigger_emergency_launch(self, target_node_id: str, target_lat: float, target_lon: float) -> Dict[str, Any]:
        """
        Inicia la secuencia automática de despegue inmediato:
        1. Apertura motorizada de compuerta.
        2. Calibración de telemetría y sensores.
        3. Despegue del dron (<45 segundos garantizados).
        """
        self.hatch_status = "OPENING"
        self.drone.dispatch_to_target(target_node_id, target_lat, target_lon)
        return {
            "station_id": self.station_id,
            "event": "EMERGENCY_LAUNCH_TRIGGERED",
            "facility_name": self.facility.name,
            "target_node": target_node_id,
            "target_coords": [target_lat, target_lon],
            "max_takeoff_window_sec": 45.0,
            "timestamp": time.time()
        }

    def recall_drone(self):
        """Ordena el retorno y aterrizaje autónomo en la base (RTL)."""
        self.drone.return_to_launch()
        self.hatch_status = "OPEN"
        self.hatch_open_pct = 100.0

    def step(
        self,
        dt: float = 0.5,
        hotspots: Optional[List[Dict[str, Any]]] = None,
        wind_speed_kmh: float = 27.0,
        wind_dir_deg: float = 65.0
    ) -> Dict[str, Any]:
        """Avanza la máquina de estados de la estación y el dron."""
        # Gestión de compuerta motorizada
        if self.drone.status in ("PRE_FLIGHT", "TAKING_OFF", "TRANSIT_OUT", "RECON_ORBIT", "MANUAL_PILOT", "RETURNING"):
            self.hatch_status = "OPEN"
            self.hatch_open_pct = min(100.0, self.hatch_open_pct + 18.0 * dt)
        elif self.drone.status == "DOCK_CHARGING":
            if self.hatch_open_pct > 0.0:
                self.hatch_status = "CLOSING"
                self.hatch_open_pct = max(0.0, self.hatch_open_pct - 14.0 * dt)
            else:
                self.hatch_status = "CLOSED"

        drone_state = self.drone.step_simulation(dt, hotspots, wind_speed_kmh, wind_dir_deg)

        return {
            "station_id": self.station_id,
            "facility": {
                "id": self.facility.facility_id,
                "name": self.facility.name,
                "agency": self.facility.agency,
                "coords": [self.facility.lat, self.facility.lon],
                "security": self.facility.security_status,
                "power_grid": self.facility.power_grid,
                "personnel_on_duty": self.facility.personnel_on_duty
            },
            "hatch": {
                "status": self.hatch_status,
                "open_pct": round(self.hatch_open_pct, 1),
                "weather_protection": self.weather_protection
            },
            "drone": drone_state,
            "readiness": "LISTA_DESPLIEGUE_INMEDIATO" if self.drone.status == "DOCK_CHARGING" and self.drone.battery_pct > 80 else "OPERACION_EN_CURSO"
        }
