"""
FIREWATCH - Drone Agent Model
Models individual UAV flight dynamics, sensor payloads, GPS georeferencing,
and closes the loop with the Drosophila neural brain controller.
"""

import math
import time
import numpy as np
from typing import Dict, Any, List, Optional
from .brain_interface import DrosophilaBioController
from .environment import AtmosphericEnvironment
from flybridge.core import FlybridgeNervousSystem

class FirewatchDrone:
    def __init__(
        self,
        drone_id: str,
        init_lat: float,
        init_lon: float,
        init_alt_m: float = 65.0,
        init_heading_deg: float = 0.0,
        battery_pct: float = 95.0,
        mission: str = "PATRULLA_SECTOR",
        weights: Dict[str, float] = None
    ):
        self.drone_id = drone_id
        self.lat = init_lat
        self.lon = init_lon
        self.alt_m = init_alt_m
        self.heading_deg = init_heading_deg
        self.speed_kmh = 28.0
        self.battery_pct = battery_pct
        self.mission = mission
        self.status = "OPERATIVO"  # OPERATIVO, INVESTIGANDO, VERIFICANDO, RETORNO
        
        # FLYBRIDGE: Sistema Nervioso Artificial en 5 capas
        self.nervous_system = FlybridgeNervousSystem(agent_id=drone_id)

        # Bio-inspired brain controller instance
        self.brain = DrosophilaBioController(agent_id=drone_id, weights=weights)
        
        # Flight trail (last 30 GPS points)
        self.trajectory: List[List[float]] = [[round(self.lat, 6), round(self.lon, 6)]]
        
        # Manual operator override
        self.manual_override: bool = False
        self.manual_target_heading: float = self.heading_deg
        self.manual_speed_kmh: float = 28.0

        # Current sensor telemetry
        self.latest_telemetry: Dict[str, Any] = {}

    def set_manual_command(self, heading_deg: Optional[float] = None, speed_kmh: Optional[float] = None, alt_delta_m: Optional[float] = None):
        """Activa y actualiza el control manual por parte del operador sin desconectar sensores."""
        self.manual_override = True
        if heading_deg is not None:
            self.manual_target_heading = heading_deg % 360.0
        if speed_kmh is not None:
            self.manual_speed_kmh = max(0.0, min(65.0, speed_kmh))
        if alt_delta_m is not None:
            self.alt_m = max(10.0, min(250.0, self.alt_m + alt_delta_m))

    def release_manual_control(self):
        """Retorna el mando al sistema nervioso autónomo FLYBRIDGE."""
        self.manual_override = False

    def update(self, env: AtmosphericEnvironment, dt: float = 0.5):
        # 1. Sample environment at drone's current 3D position
        env_sample = env.sample_at(self.lat, self.lon, self.alt_m)
        
        # 2. Step the biological brain controller
        bio_turn_rate, bio_speed, brain_spikes = self.brain.step(
            current_heading_deg=self.heading_deg,
            temperature_c=env_sample["temperature_c"],
            smoke_conc=env_sample["smoke_concentration"],
            wind_speed_kmh=env_sample["wind_speed_kmh"],
            wind_dir_deg=env_sample["wind_direction_deg"],
            dt=dt
        )

        # 3. Determine actual flight commands (Manual vs Autonomous)
        if self.manual_override:
            # Operator manual command tracking
            diff = (self.manual_target_heading - self.heading_deg + 180.0) % 360.0 - 180.0
            turn_rate = float(np.clip(diff * 4.0, -50.0, 50.0))
            speed = self.manual_speed_kmh
            self.status = "MANUAL"
            self.mission = "PILOTAJE_OPERADOR"
        else:
            turn_rate = bio_turn_rate
            speed = bio_speed
        
        # 3. Update attitude & kinematics
        self.heading_deg = (self.heading_deg + turn_rate * dt) % 360.0
        self.speed_kmh = speed
        
        # Speed in m/s
        speed_ms = (self.speed_kmh * 1000.0) / 3600.0
        dist_moved_m = speed_ms * dt
        
        # Convert distance to delta lat/lon
        heading_rad = math.radians(self.heading_deg)
        delta_lat = (dist_moved_m * math.cos(heading_rad)) / 111139.0
        delta_lon = (dist_moved_m * math.sin(heading_rad)) / (111139.0 * math.cos(math.radians(self.lat)))
        
        self.lat += delta_lat
        self.lon += delta_lon
        
        # Record trajectory point periodically
        if len(self.trajectory) == 0 or math.hypot(
            (self.lat - self.trajectory[-1][0]) * 111139.0,
            (self.lon - self.trajectory[-1][1]) * 111139.0
        ) > 20.0:
            self.trajectory.append([round(self.lat, 6), round(self.lon, 6)])
            if len(self.trajectory) > 50:
                self.trajectory.pop(0)

        # Battery consumption
        self.battery_pct = max(5.0, self.battery_pct - 0.005 * dt)
        
        # Mission status update based on brain behavior (only if not under manual operator override)
        if not self.manual_override:
            if brain_spikes["behavior_state"] == "UPWIND_SURGE":
                self.status = "INVESTIGANDO"
                self.mission = "RASTREO_PLUMA"
            elif brain_spikes["behavior_state"] == "CROSSWIND_CASTING":
                self.status = "VERIFICANDO"
                self.mission = "BUSQUEDA_TRANSVERSAL"
            else:
                self.status = "OPERATIVO"
                if not self.mission.startswith("FORMACION_") and not self.mission.startswith("RECONOCIMIENTO_"):
                    self.mission = "PATRULLA_SECTOR"

        # ── FLYBRIDGE: Ciclo del Sistema Nervioso Artificial ─────────────────
        nervous_eval = self.nervous_system.process(
            thermal_c=env_sample["temperature_c"],
            vegetation_rgb_index=0.88,
            smoke_conc=env_sample["smoke_concentration"],
            voc_ppm=env_sample["smoke_concentration"] * 45.0,
            alt_m=self.alt_m,
            speed_ms=(self.speed_kmh * 1000.0) / 3600.0,
            heading_deg=self.heading_deg,
            battery_pct=self.battery_pct,
            lat=self.lat,
            lon=self.lon,
            habitat_type="forest",
            ambient_temp_c=env.base_temp_c,
            humidity_pct=env_sample["humidity_pct"],
            wind_speed_kmh=env_sample["wind_speed_kmh"],
            wind_dir_deg=env_sample["wind_direction_deg"],
            season=env.season,
            hour_of_day=15.0
        )

        # Generate telemetry packet
        self.latest_telemetry = {
            "drone_id": self.drone_id,
            "latitude": round(self.lat, 6),
            "longitude": round(self.lon, 6),
            "altitude_m": round(self.alt_m, 1),
            "heading_deg": round(self.heading_deg, 1),
            "speed_kmh": round(self.speed_kmh, 1),
            "battery_pct": round(self.battery_pct, 1),
            "status": self.status,
            "mission": self.mission,
            "manual_override": self.manual_override,
            "temperature_c": env_sample["temperature_c"],
            "humidity_pct": env_sample["humidity_pct"],
            "smoke_concentration": env_sample["smoke_concentration"],
            "co2_ppm": env_sample.get("co2_ppm", 415.0),
            "wind": {
                "speed_kmh": env_sample["wind_speed_kmh"],
                "direction_deg": env_sample["wind_direction_deg"]
            },
            "brain": brain_spikes,
            "flybridge": {
                "internal_state": nervous_eval["internal_state"],
                "neural_state": nervous_eval["neural_state"],
                "environmental_state": nervous_eval["environmental_state"],
                "recommended_action": nervous_eval["recommended_action"],
                "context_justification": nervous_eval["memory_context"]["context_summary"],
                "integrated_salience": nervous_eval["integrated_packet"]["integrated_salience"],
                "active_event": nervous_eval["neural_event"]
            },
            "dist_to_hotspot_m": env_sample.get("dist_to_hotspot_m"),
            "trajectory": self.trajectory
        }
        return self.latest_telemetry

    def to_dict(self) -> Dict[str, Any]:
        return self.latest_telemetry
