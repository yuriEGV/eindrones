"""
FIREWATCH - PX4 Autopilot MAVLink Hardware Bridge
Bridges the Drosophila biological brain controller with PX4 Autopilot firmware
via MAVLink v2 protocol (compatible with Pixhawk 6C, Cube Orange, and PX4 SITL).
"""

import time
import math
from typing import Dict, Any, Optional
from .brain_interface import DrosophilaBioController

class PX4BioDroneBridge:
    """
    Bridge connecting Drosophila Bio-Brain with PX4 Autopilot.
    Handles:
    - MAVLink telemetry reception (GLOBAL_POSITION_INT, ATTITUDE, SYS_STATUS, WIND_COV)
    - Offboard mode setpoint generation (SET_POSITION_TARGET_LOCAL_NED)
    - Bio-inspired steering execution via Descending Neurons (DN)
    - Autonomous fail-safe monitoring
    """

    def __init__(
        self,
        drone_id: str = "FLY-01",
        connection_url: str = "udpin:127.0.0.1:14540", # Default PX4 SITL port
        baud_rate: int = 921600,
        weights: Optional[Dict[str, float]] = None
    ):
        self.drone_id = drone_id
        self.connection_url = connection_url
        self.baud_rate = baud_rate
        
        # Load bio-controller with trained weights
        self.brain = DrosophilaBioController(agent_id=drone_id, weights=weights)
        
        # Vehicle state from PX4 telemetry
        self.lat: float = 0.0
        self.lon: float = 0.0
        self.alt_rel_m: float = 0.0
        self.heading_deg: float = 0.0
        self.groundspeed_ms: float = 0.0
        self.battery_pct: float = 100.0
        self.is_armed: bool = False
        self.flight_mode: str = "UNKNOWN"
        
        # Environmental estimations from PX4 EKF2
        self.estimated_wind_speed_kmh: float = 20.0
        self.estimated_wind_dir_deg: float = 65.0
        
        # Connection handle (pymavlink mavutil if installed)
        self.master = None
        self.is_connected = False

    def connect(self):
        """
        Attempts MAVLink connection to PX4 Autopilot.
        Supports SITL (UDP) and Physical Hardware (UART/USB like /dev/ttyACM0 or COM3).
        """
        try:
            from pymavlink import mavutil
            print(f"[{self.drone_id}] Conectando a PX4 en {self.connection_url}...")
            self.master = mavutil.mavlink_connection(self.connection_url, baud=self.baud_rate)
            self.master.wait_heartbeat(timeout=3.0)
            self.is_connected = True
            print(f"[{self.drone_id}] ✅ Heartbeat recibido de PX4 (System ID: {self.master.target_system})")
            return True
        except ImportError:
            print(f"[{self.drone_id}] ⚠️ pymavlink no está instalado localmente. Operando en MODO SIMULADOR MAVLink.")
            self.is_connected = False
            return False
        except Exception as e:
            print(f"[{self.drone_id}] ⚠️ No se detectó PX4 en {self.connection_url}: {e}")
            self.is_connected = False
            return False

    def update_telemetry_from_mavlink(self):
        """
        Parses incoming MAVLink messages from PX4 uORB topics.
        """
        if not self.master:
            return

        while True:
            msg = self.master.recv_match(blocking=False)
            if not msg:
                break
            
            mtype = msg.get_type()
            if mtype == "GLOBAL_POSITION_INT":
                self.lat = msg.lat / 1e7
                self.lon = msg.lon / 1e7
                self.alt_rel_m = msg.relative_alt / 1000.0
                self.heading_deg = msg.hdg / 100.0 if msg.hdg != 65535 else self.heading_deg
                self.groundspeed_ms = math.hypot(msg.vx, msg.vy) / 100.0
            elif mtype == "SYS_STATUS":
                self.battery_pct = float(msg.battery_remaining)
            elif mtype == "WIND_COV":
                # PX4 EKF2 wind speed estimation
                self.estimated_wind_speed_kmh = math.hypot(msg.wind_x, msg.wind_y) * 3.6
                self.estimated_wind_dir_deg = math.degrees(math.atan2(msg.wind_y, msg.wind_x)) % 360.0

    def compute_bio_setpoint(
        self,
        smoke_conc: float,
        temperature_c: float,
        dt: float = 0.2
    ) -> Dict[str, Any]:
        """
        Runs Drosophila brain step and formats MAVLink OFFBOARD velocity setpoint.
        """
        turn_rate, forward_speed_kmh, spikes = self.brain.step(
            current_heading_deg=self.heading_deg,
            temperature_c=temperature_c,
            smoke_conc=smoke_conc,
            wind_speed_kmh=self.estimated_wind_speed_kmh,
            wind_dir_deg=self.estimated_wind_dir_deg,
            dt=dt
        )

        forward_speed_ms = (forward_speed_kmh * 1000.0) / 3600.0
        heading_rad = math.radians(self.heading_deg)

        # Body-to-NED velocity translation
        vx_ned = forward_speed_ms * math.cos(heading_rad)
        vy_ned = forward_speed_ms * math.sin(heading_rad)
        vz_ned = 0.0  # Maintain altitude

        setpoint = {
            "vx": vx_ned,
            "vy": vy_ned,
            "vz": vz_ned,
            "yaw_rate_rad_s": math.radians(turn_rate),
            "bio_state": spikes["behavior_state"],
            "spikes": spikes
        }

        # If connected to real PX4, send MAVLink message: SET_POSITION_TARGET_LOCAL_NED
        if self.is_connected and self.master:
            self._send_px4_velocity_setpoint(vx_ned, vy_ned, vz_ned, math.radians(turn_rate))

        return setpoint

    def _send_px4_velocity_setpoint(self, vx: float, vy: float, vz: float, yaw_rate: float):
        """
        Sends MAVLink SET_POSITION_TARGET_LOCAL_NED message to PX4.
        Bitmask 0b0000101111000111 ignores position and acceleration,
        controlling strictly velocities + yaw rate.
        """
        from pymavlink import mavutil
        type_mask = (
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_X_IGNORE |
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_Y_IGNORE |
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_Z_IGNORE |
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_AX_IGNORE |
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_AY_IGNORE |
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_AZ_IGNORE |
            mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_IGNORE
        )

        time_boot_ms = int(time.time() * 1000) & 0xFFFFFFFF
        self.master.mav.set_position_target_local_ned_send(
            time_boot_ms,
            self.master.target_system,
            self.master.target_component,
            mavutil.mavlink.MAV_FRAME_LOCAL_NED,
            type_mask,
            0, 0, 0,       # Position (ignored)
            vx, vy, vz,    # Velocity in m/s
            0, 0, 0,       # Acceleration (ignored)
            0,             # Yaw (ignored)
            yaw_rate       # Yaw rate in rad/s
        )

    def trigger_px4_rtl(self):
        """Emergency Return-to-Launch fail-safe trigger"""
        if self.is_connected and self.master:
            from pymavlink import mavutil
            self.master.mav.command_long_send(
                self.master.target_system,
                self.master.target_component,
                mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
                0, 0, 0, 0, 0, 0, 0, 0
            )
            print(f"[{self.drone_id}] 🚨 COMANDO RTL ENVIADO A PX4")
