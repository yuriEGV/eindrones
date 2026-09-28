"""
FIREWATCH - Atmospheric & Thermal Environment Model
Simulates weather conditions (wind vector, ambient temperature, relative humidity),
vegetation fuel index, and 3D convective heat/smoke dispersion plumes.
"""

import math
import time
import numpy as np
from typing import Dict, Any, List, Tuple

class AtmosphericEnvironment:
    def __init__(
        self,
        center_lat: float = -33.4489,
        center_lon: float = -70.6693,
        season: str = "summer",
        base_temp_c: float = 34.2,
        base_humidity_pct: float = 18.5,
        wind_speed_kmh: float = 28.0,
        wind_dir_deg: float = 65.0,  # Wind blowing towards 65° (NE)
        vegetation_dryness: float = 0.88,  # 0.0 (green) to 1.0 (extremely dry)
    ):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.season = season
        self.base_temp_c = base_temp_c
        self.base_humidity_pct = base_humidity_pct
        self.wind_speed_kmh = wind_speed_kmh
        self.wind_dir_deg = wind_dir_deg
        self.vegetation_dryness = vegetation_dryness

        # Active thermal hotspots: list of dicts with lat, lon, intensity_c, radius_m, start_time
        self.hotspots: List[Dict[str, Any]] = [
            {
                "id": "ANOM-01",
                "lat": center_lat + 0.0110,
                "lon": center_lon + 0.0150,
                "peak_temp_c": 56.4,
                "smoke_intensity": 0.92,
                "radius_m": 85.0,
                "start_time": time.time() - 360,  # Active for 6 minutes
                "confirmed": False,
                "status": "active"
            }
        ]

    def set_wind(self, speed_kmh: float, dir_deg: float):
        self.wind_speed_kmh = speed_kmh
        self.wind_dir_deg = dir_deg

    def add_hotspot(self, lat: float, lon: float, peak_temp: float = 60.0, radius_m: float = 50.0):
        hid = f"ANOM-{len(self.hotspots)+1:02d}"
        self.hotspots.append({
            "id": hid,
            "lat": lat,
            "lon": lon,
            "peak_temp_c": peak_temp,
            "smoke_intensity": 0.85,
            "radius_m": radius_m,
            "start_time": time.time(),
            "confirmed": False,
            "status": "active"
        })
        return hid

    def sample_at(self, lat: float, lon: float, altitude_m: float = 45.0) -> Dict[str, Any]:
        """
        Calculates local ambient temperature, smoke particulate density,
        and wind at any geographical point (lat, lon, alt).
        Accounts for convective plume downwind dispersion.
        """
        temp_c = self.base_temp_c
        smoke_conc = 0.0
        nearest_hotspot = None
        min_dist_m = float("inf")

        # Wind direction in radians (direction wind travels TOWARDS)
        wind_rad = math.radians(self.wind_dir_deg)

        # 1 deg latitude ≈ 111,139 meters; 1 deg longitude ≈ 111,139 * cos(lat)
        m_per_lat = 111139.0
        m_per_lon = 111139.0 * math.cos(math.radians(lat))

        for hs in self.hotspots:
            if hs.get("status") != "active":
                continue
            dx = (lon - hs["lon"]) * m_per_lon
            dy = (lat - hs["lat"]) * m_per_lat
            dist_ground = math.hypot(dx, dy)

            if dist_ground < min_dist_m:
                min_dist_m = dist_ground
                nearest_hotspot = hs

            # Convective plume calculation:
            # Distance along wind direction and crosswind distance
            downwind_dist = (dx * math.sin(wind_rad) + dy * math.cos(wind_rad))
            crosswind_dist = abs(-dx * math.cos(wind_rad) + dy * math.sin(wind_rad))

            # Ground thermal radiation (spherical falloff)
            rad_falloff = math.exp(-0.5 * (dist_ground / hs["radius_m"]) ** 2)
            temp_c += (hs["peak_temp_c"] - self.base_temp_c) * rad_falloff

            # Atmospheric smoke plume (Gaussian downwind cone)
            if downwind_dist >= -10.0:  # slightly upwind diffusion
                sigma_y = max(15.0, 0.18 * downwind_dist)
                plume_decay = 1.0 / (1.0 + 0.005 * downwind_dist)
                lateral_disp = math.exp(-0.5 * (crosswind_dist / sigma_y) ** 2)
                smoke_conc += hs["smoke_intensity"] * plume_decay * lateral_disp

        # Small micro-fluctuations
        temp_c += np.random.normal(0, 0.15)
        smoke_conc = float(np.clip(smoke_conc, 0.0, 1.0))
        humidity = max(10.0, self.base_humidity_pct - (temp_c - self.base_temp_c) * 0.4)

        # Atmospheric CO2 calculation (ppm):
        # Baseline ~415 ppm. Rises significantly in the presence of combustion/smoke and thermal radiation
        co2_ppm = round(415.0 + smoke_conc * 850.0 + max(0.0, temp_c - self.base_temp_c) * 12.0 + float(np.random.normal(0, 1.5)), 1)

        return {
            "temperature_c": round(float(temp_c), 2),
            "humidity_pct": round(float(humidity), 1),
            "smoke_concentration": round(smoke_conc, 3),
            "co2_ppm": co2_ppm,
            "wind_speed_kmh": round(self.wind_speed_kmh, 1),
            "wind_direction_deg": round(self.wind_dir_deg, 1),
            "dist_to_hotspot_m": round(min_dist_m, 1) if nearest_hotspot else None,
            "active_hotspot_id": nearest_hotspot["id"] if (nearest_hotspot and min_dist_m < 350.0) else None
        }

    def get_summary(self) -> Dict[str, Any]:
        return {
            "center": {"lat": self.center_lat, "lon": self.center_lon},
            "season": self.season,
            "base_temp_c": self.base_temp_c,
            "base_humidity_pct": self.base_humidity_pct,
            "wind": {"speed_kmh": self.wind_speed_kmh, "direction_deg": self.wind_dir_deg},
            "vegetation_dryness": self.vegetation_dryness,
            "active_hotspots": self.hotspots
        }
