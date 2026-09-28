"""
FIREWATCH - Single Drone Brain Trainer (FLY-01 Pilot Training)
Trains a single bio-drone agent to master plume tracking, thermal ascent,
and wind navigation through reinforcement and associative synaptic tuning.
"""

import math
import time
import json
import random
import sys
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Fix Windows console UTF-8 encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from .environment import AtmosphericEnvironment
from .drone_agent import FirewatchDrone

class SingleDroneTrainer:
    def __init__(self, output_weights_path: str = "firewatch/trained_brain.json"):
        self.output_weights_path = Path(output_weights_path)
        self.history: List[Dict[str, Any]] = []

    def run_training(self, num_episodes: int = 10, max_steps: int = 150) -> Dict[str, Any]:
        print(f"\n==================================================")
        print(f"🚀 INICIANDO ENTRENAMIENTO DE FLY-01 (DRON PILOTO)")
        print(f"==================================================")
        print(f"Episodios a ejecutar: {num_episodes} | Pasos máx/episodio: {max_steps}\n")

        # Trainable parameters (synaptic weights & sensor gains)
        # Starting with baseline parameters
        best_weights = {
            "orn_gain": 180.0,         # Olfactory gain (smoke sensitivity)
            "trpa1_gain": 8.5,         # Thermal gain (heat gradient sensitivity)
            "upwind_turn_gain": 50.0,  # Steering responsiveness towards upwind
            "surge_threshold": 0.08,   # Activation threshold for surge mode
            "casting_period": 3.5      # Zigzag search period in seconds
        }
        
        best_avg_reward = -float("inf")
        episode_rewards = []
        success_count = 0

        for ep in range(1, num_episodes + 1):
            center_lat = -33.4489
            center_lon = -70.6693
            
            # --- 3-PHASE CURRICULUM LEARNING ---
            wind_speed = random.uniform(20.0, 35.0)
            wind_dir = random.uniform(30.0, 90.0) # Viento predominante NE (vuela hacia NE)
            wind_rad = math.radians(wind_dir)

            if ep <= 8:
                phase_name = "FASE 1: RASTREO DIRECTO (DOWNWIND)"
                # Spawn downwind: along the wind vector from fire
                dist_m = random.uniform(150.0, 260.0)
                fire_lat = center_lat
                fire_lon = center_lon
                drone_lat = fire_lat + (dist_m * math.cos(wind_rad)) / 111139.0
                drone_lon = fire_lon + (dist_m * math.sin(wind_rad)) / (111139.0 * math.cos(math.radians(center_lat)))
            elif ep <= 16:
                phase_name = "FASE 2: BORDE DE PLUMA & CASTING"
                dist_m = random.uniform(250.0, 420.0)
                fire_lat = center_lat
                fire_lon = center_lon
                # Lateral crosswind displacement
                cross_m = random.choice([-1, 1]) * random.uniform(40.0, 90.0)
                dx = dist_m * math.sin(wind_rad) - cross_m * math.cos(wind_rad)
                dy = dist_m * math.cos(wind_rad) + cross_m * math.sin(wind_rad)
                drone_lat = fire_lat + dy / 111139.0
                drone_lon = fire_lon + dx / (111139.0 * math.cos(math.radians(center_lat)))
            else:
                phase_name = "FASE 3: BARRIDO DE CUADRANTE COMPLETO"
                dist_m = random.uniform(350.0, 650.0)
                angle = random.uniform(0, 2 * math.pi)
                fire_lat = center_lat
                fire_lon = center_lon
                drone_lat = fire_lat + (dist_m * math.cos(angle)) / 111139.0
                drone_lon = fire_lon + (dist_m * math.sin(angle)) / (111139.0 * math.cos(math.radians(center_lat)))

            env = AtmosphericEnvironment(
                center_lat=center_lat,
                center_lon=center_lon,
                wind_speed_kmh=wind_speed,
                wind_dir_deg=wind_dir,
                base_temp_c=32.0,
                base_humidity_pct=20.0
            )
            env.hotspots = [{
                "id": "FIRE-TARGET",
                "lat": fire_lat,
                "lon": fire_lon,
                "peak_temp_c": 58.0,
                "smoke_intensity": 0.95,
                "radius_m": 70.0,
                "start_time": time.time(),
                "confirmed": False,
                "status": "active"
            }]

            # Candidate weights with exploration perturbation
            candidate_weights = {
                "orn_gain": float(max(50.0, best_weights["orn_gain"] + np.random.normal(0, 10.0))),
                "trpa1_gain": float(max(3.0, best_weights["trpa1_gain"] + np.random.normal(0, 1.0))),
                "upwind_turn_gain": float(max(25.0, min(80.0, best_weights["upwind_turn_gain"] + np.random.normal(0, 3.5)))),
                "surge_threshold": float(max(0.04, min(0.18, best_weights["surge_threshold"] + np.random.normal(0, 0.015)))),
                "casting_period": float(max(1.5, min(6.0, best_weights["casting_period"] + np.random.normal(0, 0.4))))
            }

            # Spawn FLY-01 with candidate weights
            drone = FirewatchDrone(
                drone_id="FLY-01",
                init_lat=drone_lat,
                init_lon=drone_lon,
                init_alt_m=45.0,
                init_heading_deg=random.uniform(0, 360),
                mission="ENTRENAMIENTO_SOLITARIO",
                weights=candidate_weights
            )

            total_reward = 0.0
            found_fire = False
            prev_dist = math.hypot(
                (drone_lat - fire_lat) * 111139.0,
                (drone_lon - fire_lon) * 111139.0
            )
            initial_dist = prev_dist

            # Simulation loop
            for step in range(max_steps):
                telemetry = drone.update(env, dt=0.5)
                cur_dist = math.hypot(
                    (drone.lat - fire_lat) * 111139.0,
                    (drone.lon - fire_lon) * 111139.0
                )

                # Reward computation
                delta_d = prev_dist - cur_dist
                step_reward = delta_d * 2.0 - 0.15  # Time cost

                if telemetry.get("smoke_concentration", 0) > 0.10:
                    step_reward += 0.8
                if telemetry.get("temperature_c", 0) > 42.0:
                    step_reward += 1.5

                total_reward += step_reward
                prev_dist = cur_dist

                # Fire core reached condition (< 45 meters)
                if cur_dist < 45.0:
                    found_fire = True
                    total_reward += 300.0  # Big reward
                    success_count += 1
                    break

            episode_rewards.append(total_reward)
            
            # Policy improvement if this episode beat past average
            if total_reward > best_avg_reward:
                best_avg_reward = total_reward
                best_weights = {k: round(v, 2) for k, v in candidate_weights.items()}

            status_str = "🎯 FOCO ALCANZADO" if found_fire else "❌ NO ALCANZADO"
            print(f"Ep {ep:02d}/{num_episodes:02d} [{phase_name[:12]}] | {status_str} | "
                  f"Dist: {cur_dist:.1f}m (Inicio: {initial_dist:.1f}m) | "
                  f"Pasos: {step+1:03d} | R: {total_reward:+.1f}")

        success_rate = (success_count / num_episodes) * 100.0
        print(f"\n--------------------------------------------------")
        print(f"✅ ENTRENAMIENTO FINALIZADO")
        print(f"Tasa de éxito de localización: {success_rate:.1f}% ({success_count}/{num_episodes})")
        print(f"Pesos sinápticos óptimos calibrados:")
        print(json.dumps(best_weights, indent=2))
        print(f"--------------------------------------------------\n")

        # Save trained weights
        with open(self.output_weights_path, "w", encoding="utf-8") as f:
            json.dump({
                "model": "Drosophila_Connectome_Firewatch_v1",
                "drone_target": "FLY-01",
                "training_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "num_episodes": num_episodes,
                "success_rate_pct": success_rate,
                "weights": best_weights
            }, f, indent=2)
        print(f"Pesos guardados en: {self.output_weights_path}")

        return {
            "success_rate": success_rate,
            "best_weights": best_weights,
            "episode_rewards": episode_rewards
        }

if __name__ == "__main__":
    trainer = SingleDroneTrainer()
    trainer.run_training(num_episodes=25, max_steps=120)
