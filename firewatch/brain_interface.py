"""
FIREWATCH - Bio-Inspired Drosophila Brain Controller
Interfaces olfactory, thermal, and wind sensory pathways with Central Complex (CX)
and Descending Neurons (DN) steering dynamics.
"""

import math
import numpy as np
from typing import Dict, Any, Tuple

class DrosophilaBioController:
    """
    Biological neural controller derived from Drosophila connectome principles:
    - Chemosensory ORNs (smoke/CO2 detection)
    - Thermotaxis receptors (dTRPA1 channel activation on temperature rise)
    - Mechanosensory Johnston's Organ (wind speed and direction relative to heading)
    - Central Complex (CX) heading integration
    - Descending Neurons (DN) steering bias
    """
    def __init__(self, agent_id: str, weights: Dict[str, float] = None):
        self.agent_id = agent_id
        
        # Trainable synaptic weights & biological gains
        self.weights = {
            "orn_gain": 180.0,
            "trpa1_gain": 8.5,
            "upwind_turn_gain": 50.0,
            "surge_threshold": 0.08,
            "casting_period": 3.5
        }
        if weights:
            self.weights.update(weights)

        self.orn_gain = self.weights["orn_gain"]
        self.trpa1_gain = self.weights["trpa1_gain"]
        self.upwind_turn_gain = self.weights["upwind_turn_gain"]
        self.surge_threshold = self.weights["surge_threshold"]
        self.casting_period = self.weights["casting_period"]
        
        # State variables
        self.internal_heading_deg = 0.0
        self.casting_timer = 0.0
        self.casting_dir = 1.0  # +1 right, -1 left
        self.last_smoke_detected = 0.0
        self.last_thermal_detected = 0.0
        self.surge_mode = False
        
        # Simulated neural firing rates (Hz)
        self.orn_rate_hz = 15.0       # Olfactory receptor neurons baseline
        self.trpa1_rate_hz = 10.0     # Thermal receptor baseline
        self.johnston_rate_hz = 25.0  # Anemoreceptor baseline
        self.dn_left_rate_hz = 40.0   # Descending neuron L
        self.dn_right_rate_hz = 40.0  # Descending neuron R

    def step(
        self,
        current_heading_deg: float,
        temperature_c: float,
        smoke_conc: float,
        wind_speed_kmh: float,
        wind_dir_deg: float,
        dt: float = 0.5
    ) -> Tuple[float, float, Dict[str, Any]]:
        """
        Processes sensory input through the fly brain model and returns:
        (desired_turn_rate_deg_s, desired_speed_kmh, telemetry_spikes)
        """
        # 1. Olfactory transduction (smoke)
        self.orn_rate_hz = 15.0 + smoke_conc * self.orn_gain
        
        # 2. Thermotaxis transduction (dTRPA1 fires when temp > 35°C)
        temp_excess = max(0.0, temperature_c - 35.0)
        self.trpa1_rate_hz = 10.0 + min(200.0, temp_excess * self.trpa1_gain)
        
        # 3. Johnston's organ transduction (wind)
        rel_wind_angle = (wind_dir_deg - current_heading_deg + 180.0) % 360.0 - 180.0
        self.johnston_rate_hz = 20.0 + (wind_speed_kmh / 50.0) * 120.0
        
        # Total anomaly signal detected by bionic sensors
        anomaly_strength = smoke_conc * 0.6 + min(1.0, temp_excess / 15.0) * 0.4
        
        # 4. Behavioral state machine (Bio-plume tracing: Surge & Cast)
        upwind_heading_deg = (wind_dir_deg + 180.0) % 360.0

        if anomaly_strength > self.surge_threshold:
            # SURGE: Detected plume/heat! Orient UPWIND toward the fire source
            self.surge_mode = True
            self.last_smoke_detected = time_now = dt
            self.casting_timer = 0.0
            
            # Target heading is directly upwind with slight gradient adaptation
            target_heading = upwind_heading_deg
            angle_diff = (target_heading - current_heading_deg + 180.0) % 360.0 - 180.0
            
            # DN asymmetry drives proportional steering
            dn_bias = math.tanh(angle_diff / 45.0)
            self.dn_left_rate_hz = 40.0 + max(0.0, -dn_bias) * 70.0
            self.dn_right_rate_hz = 40.0 + max(0.0, dn_bias) * 70.0
            
            turn_rate = float(np.clip(dn_bias * self.upwind_turn_gain, -45.0, 45.0))
            forward_speed = 36.0  # High patrol speed towards source
            behavior_state = "UPWIND_SURGE"
            
        elif self.surge_mode:
            # CASTING: Just lost the scent/plume -> search zigzag crosswind
            self.casting_timer += dt
            if self.casting_timer > self.casting_period:
                self.casting_dir *= -1.0
                self.casting_timer = 0.0
                
            # Crosswind heading: upwind ± 90 degrees
            crosswind_heading = (upwind_heading_deg + self.casting_dir * 85.0) % 360.0
            angle_diff = (crosswind_heading - current_heading_deg + 180.0) % 360.0 - 180.0
            dn_bias = math.tanh(angle_diff / 30.0)
            
            self.dn_left_rate_hz = 40.0 + max(0.0, -dn_bias) * 50.0
            self.dn_right_rate_hz = 40.0 + max(0.0, dn_bias) * 50.0
            
            turn_rate = float(np.clip(dn_bias * 40.0, -35.0, 35.0))
            forward_speed = 22.0  # Moderate searching speed
            behavior_state = "CROSSWIND_CASTING"
            
            if self.casting_timer > 15.0:  # Timeout casting, resume normal patrol
                self.surge_mode = False
        else:
            # NORMAL PATROL: Crosswind sweeping path to maximize plume interception
            crosswind_target = (wind_dir_deg + 90.0) % 360.0
            angle_diff = (crosswind_target - current_heading_deg + 180.0) % 360.0 - 180.0
            dn_bias = math.tanh(angle_diff / 45.0)
            
            self.dn_left_rate_hz = 40.0 + max(0.0, -dn_bias) * 30.0
            self.dn_right_rate_hz = 40.0 + max(0.0, dn_bias) * 30.0
            turn_rate = float(np.clip(dn_bias * 30.0, -25.0, 25.0))
            forward_speed = 30.0
            behavior_state = "CROSSWIND_SWEEP"

        telemetry_spikes = {
            "orn_rate_hz": round(self.orn_rate_hz, 1),
            "trpa1_rate_hz": round(self.trpa1_rate_hz, 1),
            "johnston_rate_hz": round(self.johnston_rate_hz, 1),
            "dn_asymmetry": round((self.dn_left_rate_hz - self.dn_right_rate_hz) / 50.0, 2),
            "behavior_state": behavior_state,
            "anomaly_signal": round(anomaly_strength, 3)
        }

        return turn_rate, forward_speed, telemetry_spikes
