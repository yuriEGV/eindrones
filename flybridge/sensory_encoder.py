"""
FLYBRIDGE — Capa 1: Recepción de Estímulos (Sensory Encoder)
Transduce y codifica señales físicas del dron y su entorno en representaciones
neuronales biológicas (ojos, antenas, termorreceptores, propiocepción, sentido espacial y entorno).
"""

import time
import math
from typing import Dict, Any, Optional

class SensoryEncoder:
    """
    Codifica estímulos sensoriales crudos en magnitudes biológicamente interpretables.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.prev_temp: Optional[float] = None
        self.prev_time: Optional[float] = None

    def encode(
        self,
        # Ojos
        thermal_c: float,
        vegetation_rgb_index: float = 0.85, # 0.0 (verde húmedo) a 1.0 (paja/árido seco)
        # Antenas
        smoke_conc: float = 0.0,
        voc_ppm: float = 0.0,
        # Propiocepción
        alt_m: float = 45.0,
        speed_ms: float = 7.7,
        heading_deg: float = 0.0,
        battery_pct: float = 90.0,
        # Sentido espacial
        lat: float = -33.4489,
        lon: float = -70.6693,
        habitat_type: str = "forest", # forest, scrubland, urban, desert
        # Entorno meteorológico
        ambient_temp_c: float = 32.0,
        humidity_pct: float = 18.0,
        wind_speed_kmh: float = 28.0,
        wind_dir_deg: float = 65.0,
        season: str = "summer",
        hour_of_day: float = 14.5
    ) -> Dict[str, Any]:
        current_time = time.time()
        
        # Cálculo de gradiente temporal de temperatura (dT/dt)
        dt_sec = (current_time - self.prev_time) if self.prev_time else 1.0
        dt_sec = max(0.1, dt_sec)
        
        if self.prev_temp is not None:
            temp_rate_c_s = (thermal_c - self.prev_temp) / dt_sec
        else:
            temp_rate_c_s = 0.0
            
        self.prev_temp = thermal_c
        self.prev_time = current_time

        # Normalizaciones perceptuales (0.0 a 1.0)
        thermal_salience = float(min(1.0, max(0.0, (thermal_c - 30.0) / 40.0)))
        smoke_salience = float(min(1.0, max(0.0, smoke_conc)))
        dryness_salience = float(min(1.0, max(0.0, vegetation_rgb_index)))
        wind_salience = float(min(1.0, max(0.0, wind_speed_kmh / 50.0)))
        humidity_deficit = float(min(1.0, max(0.0, (40.0 - humidity_pct) / 30.0)))

        return {
            "agent_id": self.agent_id,
            "timestamp": current_time,
            "eyes": {
                "thermal_surface_c": round(thermal_c, 2),
                "thermal_salience": round(thermal_salience, 3),
                "vegetation_dryness": round(dryness_salience, 3),
                "rgb_classification": "dry_biomass" if dryness_salience > 0.6 else "healthy_canopy"
            },
            "antennae": {
                "smoke_concentration": round(smoke_salience, 3),
                "voc_ppm": round(voc_ppm, 2),
                "pyrolysis_gas_detected": smoke_salience > 0.05
            },
            "thermoreceptors": {
                "measured_temp_c": round(thermal_c, 2),
                "temp_rate_of_change_c_s": round(temp_rate_c_s, 3),
                "thermal_gradient_elevated": (thermal_c - ambient_temp_c) > 6.0
            },
            "proprioception": {
                "altitude_m": round(alt_m, 1),
                "speed_ms": round(speed_ms, 2),
                "heading_deg": round(heading_deg, 1),
                "battery_pct": round(battery_pct, 1)
            },
            "spatial_sense": {
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "habitat_type": habitat_type
            },
            "environment": {
                "ambient_temp_c": round(ambient_temp_c, 2),
                "humidity_pct": round(humidity_pct, 1),
                "humidity_deficit": round(humidity_deficit, 3),
                "wind_speed_kmh": round(wind_speed_kmh, 1),
                "wind_dir_deg": round(wind_dir_deg, 1),
                "wind_salience": round(wind_salience, 3),
                "season": season,
                "hour_of_day": round(hour_of_day, 1)
            }
        }
