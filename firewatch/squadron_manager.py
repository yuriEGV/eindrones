"""
FIREWATCH - Squadron Coordinator
Manages 5 autonomous bio-drones, multi-agent cooperation, and mission dispatch.
"""

import time
import math
import random
from pathlib import Path
from typing import Dict, Any, List, Optional
from .environment import AtmosphericEnvironment
from .drone_agent import FirewatchDrone
from .risk_engine import FirewatchRiskEngine

class SquadronManager:
    def __init__(self, center_lat: float = -33.4489, center_lon: float = -70.6693):
        self.env = AtmosphericEnvironment(center_lat=center_lat, center_lon=center_lon)
        self.risk_engine = FirewatchRiskEngine()
        
        # Instantiate 5 drones with staggered patrol positions
        offsets = [
            (-0.008, -0.006, 35.0, 92.0, "PATRULLA_NOROESTE"),
            ( 0.006,  0.009, 65.0, 88.0, "SEGUIMIENTO_ANOMALIA"),
            (-0.005,  0.012, 120.0, 95.0, "PATRULLA_SUR"),
            ( 0.003,  0.004, 75.0, 84.0, "VERIFICACION_COOPERATIVA"),
            ( 0.012, -0.007, 210.0, 91.0, "RETRANSMISION_ALTURA"),
        ]
        
        # Load trained weights if available
        trained_weights = None
        weights_file = Path(__file__).parent / "trained_brain.json"
        if weights_file.exists():
            try:
                import json
                with open(weights_file, "r", encoding="utf-8") as f:
                    wb = json.load(f)
                    trained_weights = wb.get("weights")
            except Exception:
                pass

        self.drones: List[FirewatchDrone] = []
        for i, (dlat, dlon, heading, bat, mission) in enumerate(offsets):
            d_id = f"FLY-0{i+1}"
            drone = FirewatchDrone(
                drone_id=d_id,
                init_lat=center_lat + dlat,
                init_lon=center_lon + dlon,
                init_alt_m=45.0 + i * 8.0,
                init_heading_deg=heading,
                battery_pct=bat,
                mission=mission,
                weights=trained_weights
            )
            self.drones.append(drone)

        # Swarm Coordination Modes:
        # "RECONOCIMIENTO_CO2" (Default), "SEGUIR_LIDER", "EXPLORACION_ALEATORIA", "MANUAL_LIDER"
        self.swarm_mode = "RECONOCIMIENTO_CO2"

        # Formation offsets relative to Leader (FLY-01) in Body-frame (dx=forward/back, dy=right/left)
        self.formation_offsets = {
            "FLY-02": {"dx": -35.0, "dy": -35.0, "alt_offset": 0.0, "role": "ALA_IZQUIERDA"},
            "FLY-03": {"dx": -35.0, "dy":  35.0, "alt_offset": 0.0, "role": "ALA_DERECHA"},
            "FLY-04": {"dx": -70.0, "dy": -60.0, "alt_offset": 5.0, "role": "FLANCO_EXTERIOR"},
            "FLY-05": {"dx": -90.0, "dy":   0.0, "alt_offset": 15.0, "role": "RETRANSMISION_ALTA"},
        }

        # Learning feedback history (Operator confirmed or false positive)
        self.feedback_log: List[Dict[str, Any]] = []

    def set_swarm_mode(self, mode: str):
        """Cambia la rutina operacional del escuadrón."""
        self.swarm_mode = mode
        fly01 = self.drones[0]
        if mode == "RECONOCIMIENTO_CO2":
            fly01.release_manual_control()
            fly01.mission = "RECONOCIMIENTO_CO2_BASE"
            for d in self.drones[1:]:
                d.release_manual_control()
                d.mission = "BARRIDO_PERIMETRAL"
        elif mode in ("SEGUIR_LIDER", "MANUAL_LIDER"):
            for d in self.drones[1:]:
                d.status = "FORMACIÓN"
                d.mission = f"SEGUIR_LIDER_FLY01"
        elif mode == "EXPLORACION_ALEATORIA":
            fly01.release_manual_control()
            for d in self.drones:
                d.release_manual_control()
                d.mission = "EXPLORACION_ALEATORIA"

    def command_leader(
        self,
        command: str,
        direction: Optional[str] = None,
        speed: Optional[float] = None,
        alt_delta: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Envía comandos de vuelo directamente al Dron Líder (FLY-01).
        Los seguidores adaptan su rumbo según el modo de enjambre activo.
        """
        fly01 = self.drones[0]
        self.swarm_mode = "MANUAL_LIDER"

        if command == "MOVE":
            cur_heading = fly01.heading_deg
            target_heading = cur_heading
            target_speed = speed if speed is not None else 32.0

            if direction == "FORWARD":
                target_heading = cur_heading
            elif direction == "BACKWARD":
                target_heading = (cur_heading + 180.0) % 360.0
            elif direction == "LEFT":
                target_heading = (cur_heading - 35.0) % 360.0
            elif direction == "RIGHT":
                target_heading = (cur_heading + 35.0) % 360.0
            elif direction == "NORTH":
                target_heading = 0.0
            elif direction == "SOUTH":
                target_heading = 180.0
            elif direction == "EAST":
                target_heading = 90.0
            elif direction == "WEST":
                target_heading = 270.0

            fly01.set_manual_command(heading_deg=target_heading, speed_kmh=target_speed)

        elif command == "HOVER" or command == "STOP":
            fly01.set_manual_command(speed_kmh=0.0)

        elif command == "ALTITUDE":
            delta = alt_delta if alt_delta is not None else 5.0
            fly01.set_manual_command(alt_delta_m=delta)

        elif command == "RELEASE_AUTONOMOUS":
            fly01.release_manual_control()
            self.swarm_mode = "RECONOCIMIENTO_CO2"

        return {
            "status": "command_applied",
            "swarm_mode": self.swarm_mode,
            "leader_id": "FLY-01",
            "leader_manual_override": fly01.manual_override,
            "leader_heading": fly01.manual_target_heading,
            "leader_speed": fly01.manual_speed_kmh
        }

    def step(self, dt: float = 0.5) -> Dict[str, Any]:
        """
        Steps all 5 drones, coordinates Leader-Follower swarm dynamics,
        gathers telemetry, and evaluates collective risk.
        """
        fly01 = self.drones[0]

        # ── Leader-Follower Swarm Formation Logic ─────────────────────────
        if self.swarm_mode in ("SEGUIR_LIDER", "MANUAL_LIDER"):
            # Compute follower slots based on FLY-01's current position and heading
            heading_rad = math.radians(fly01.heading_deg)
            cos_h = math.cos(heading_rad)
            sin_h = math.sin(heading_rad)

            for follower in self.drones[1:]:
                offset = self.formation_offsets.get(follower.drone_id, {"dx": -40.0, "dy": 0.0, "alt_offset": 0.0})
                dx = offset["dx"]
                dy = offset["dy"]

                # Target coordinates in meters from FLY-01
                target_north_m = dx * cos_h - dy * sin_h
                target_east_m  = dx * sin_h + dy * cos_h

                target_lat = fly01.lat + (target_north_m / 111139.0)
                target_lon = fly01.lon + (target_east_m / (111139.0 * math.cos(math.radians(fly01.lat))))

                # Steering follower towards formation slot
                dist_slot_m = math.hypot((target_lat - follower.lat) * 111139.0, (target_lon - follower.lon) * 92850.0)
                if dist_slot_m > 8.0:
                    diff_x = (target_lon - follower.lon)
                    diff_y = (target_lat - follower.lat)
                    target_deg = math.degrees(math.atan2(diff_x, diff_y)) % 360.0
                    
                    # Intercept heading
                    follower.heading_deg = (follower.heading_deg + 0.25 * ((target_deg - follower.heading_deg + 180) % 360 - 180)) % 360
                    # Catch-up speed
                    follower.speed_kmh = max(24.0, min(50.0, fly01.speed_kmh + dist_slot_m * 0.4))
                else:
                    # Match leader heading & speed
                    follower.heading_deg = fly01.heading_deg
                    follower.speed_kmh = fly01.speed_kmh

                follower.mission = f"FORMACION_V_{offset.get('role', 'SEGUIDOR')}"

        elif self.swarm_mode == "EXPLORACION_ALEATORIA":
            # Bio-inspired random foraging (Lévy flight / random walk)
            for d in self.drones:
                if not d.manual_override:
                    if random.random() < 0.15:
                        d.heading_deg = (d.heading_deg + random.uniform(-40.0, 40.0)) % 360.0
                        d.speed_kmh = random.uniform(22.0, 36.0)
                    # Boundary containment within ~1.8 km of center
                    dlat = (d.lat - self.env.center_lat) * 111139.0
                    dlon = (d.lon - self.env.center_lon) * 92850.0
                    if math.hypot(dlat, dlon) > 1800.0:
                        # Turn back towards base center
                        target_center = math.degrees(math.atan2(-dlon, -dlat)) % 360.0
                        d.heading_deg = (d.heading_deg + 0.2 * ((target_center - d.heading_deg + 180) % 360 - 180)) % 360.0
                    d.mission = "EXPLORACION_ALEATORIA"

        elif self.swarm_mode == "RECONOCIMIENTO_CO2":
            # Default initial mode upon boot:
            # Drones sample ambient CO2 to check if there is an active wildfire nearby.
            for d in self.drones:
                if not d.manual_override:
                    co2 = d.latest_telemetry.get("co2_ppm", 415.0) if d.latest_telemetry else 415.0
                    if co2 > 520.0:
                        d.status = "INVESTIGANDO"
                        d.mission = f"PLUMA_CO2_DETECTADA_{round(co2)}PPM"
                    else:
                        if d.drone_id == "FLY-01":
                            d.mission = "RECONOCIMIENTO_CO2_LIDER"
                        else:
                            d.mission = "MUESTREO_CO2_AMBIENTAL"

        telemetries = []
        for drone in self.drones:
            t = drone.update(self.env, dt=dt)
            telemetries.append(t)

        # Evaluate risk across squadron
        env_summary = self.env.get_summary()
        risk_evaluation = self.risk_engine.evaluate(telemetries, env_summary)

        # Cooperative behavior: If FLY-02 finds high anomaly, command FLY-04 to converge
        fly02 = self.drones[1]
        fly04 = self.drones[3]
        if fly02.latest_telemetry.get("temperature_c", 0) > 46.0:
            fly04.mission = "VERIFICACION_CONJUNTA_FLY02"
            # Steer FLY-04 towards FLY-02's coordinate
            dx = (fly02.lon - fly04.lon)
            dy = (fly02.lat - fly04.lat)
            target_deg = math.degrees(math.atan2(dx, dy)) % 360.0
            fly04.heading_deg = (fly04.heading_deg + 0.15 * ((target_deg - fly04.heading_deg + 180) % 360 - 180)) % 360

        formation_links = []
        if self.swarm_mode in ("SEGUIR_LIDER", "MANUAL_LIDER"):
            for follower in self.drones[1:]:
                role = self.formation_offsets.get(follower.drone_id, {}).get("role", "SEGUIDOR")
                formation_links.append({
                    "leader": "FLY-01",
                    "follower": follower.drone_id,
                    "role": role,
                    "leader_coords": [round(fly01.lat, 6), round(fly01.lon, 6)],
                    "follower_coords": [round(follower.lat, 6), round(follower.lon, 6)]
                })

        return {
            "timestamp": time.time(),
            "drones": telemetries,
            "environment": env_summary,
            "risk_analysis": risk_evaluation,
            "system_status": "SISTEMA OK" if all(d.battery_pct > 15.0 for d in self.drones) else "ALERTA BATERIA",
            "swarm_mode": self.swarm_mode,
            "leader_id": "FLY-01",
            "leader_manual": fly01.manual_override,
            "formation_links": formation_links
        }

    def record_operator_feedback(self, incident_id: str, verdict: str, operator_notes: str = ""):
        """
        Human-in-the-Loop learning loop.
        Operator classifies incident as: 'CONFIRMADO_INCENDIO' or 'FALSO_POSITIVO'
        """
        record = {
            "incident_id": incident_id,
            "timestamp": time.time(),
            "verdict": verdict,
            "notes": operator_notes,
            "training_datum_saved": True
        }
        self.feedback_log.append(record)
        return record
