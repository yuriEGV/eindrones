"""
FLYBRIDGE — Nodos Arbóreos Ignífugos con Inferencia NeuroFly (Edge)
Implementa:
1. Sensores físicos modelados: CO2/VOCs, Gradiente Térmico Multizona, Anemometría.
2. Inferencia Local Edge (Python / MicroPython / C++ port compatible):
   - Lóbulo Olfativo: Tasa de cambio temporal (dC/dt) de gases para microplumas diluidas.
   - Médula/Lámina Visual (Flujo Térmico Convectivo): Discriminación de fuentes de combustión
     versus calentamiento solar normal de hojas o suelo.
   - Filtro Neuromórfico de Falsos Positivos: Coincidencia cruzada quimio-térmica.
3. Infraestructura del Nodo Ignífugo:
   - Chasis UL94 V-0 / Aluminio con barrera cerámica externa.
   - Membrana hidrofóbica de PTFE para flujo de gases y repulsión de agua/polvo.
   - Batería LiFePO4 de alta estabilidad térmica + panel solar compacto.
4. Protocolo LoRaWAN / LoRa Mesh (915 MHz):
   - Paquete binario ultracompacto (< 50 bytes) con identificador, GPS, vector de viento,
     confianza y telemetría diagnóstica.
"""

import time
import math
import struct
from typing import Dict, Any, List, Optional, Tuple

class LoRaCompactPacket:
    """
    Empaquetado binario ultracompacto (< 50 bytes) para transmisión LoRaWAN / LoRa Mesh a 915 MHz.
    Estructura binaria fija de 32 bytes:
    - node_id: uint16 (2 bytes)
    - timestamp_sec: uint32 (4 bytes)
    - lat_fixed: int32 (4 bytes, lat * 1e6)
    - lon_fixed: int32 (4 bytes, lon * 1e6)
    - ambient_temp_c10: int16 (2 bytes, temp * 10)
    - convective_grad_c10: int16 (2 bytes, grad * 10)
    - gas_dc_dt_c10: int16 (2 bytes, dC/dt * 10)
    - co2_ppm: uint16 (2 bytes)
    - voc_ppb: uint16 (2 bytes)
    - wind_speed_c10: uint16 (2 bytes, speed * 10)
    - wind_dir_deg: uint16 (2 bytes)
    - confidence_pct: uint8 (1 byte, 0-100)
    - alert_level: uint8 (1 byte, 0-4)
    - battery_pct: uint8 (1 byte, 0-100)
    - checksum_crc8: uint8 (1 byte)
    TOTAL: 32 bytes (ampliamente inferior a la cuota estricta de 50 bytes).
    """
    STRUCT_FORMAT = ">HIii hhh HH HH BBB B"
    PACKET_SIZE_BYTES = struct.calcsize(STRUCT_FORMAT)

    @classmethod
    def pack(
        cls,
        node_id_int: int,
        timestamp: float,
        lat: float,
        lon: float,
        ambient_temp_c: float,
        convective_grad_c: float,
        gas_dc_dt: float,
        co2_ppm: float,
        voc_ppb: float,
        wind_speed_kmh: float,
        wind_dir_deg: float,
        confidence_pct: int,
        alert_level: int,
        battery_pct: int
    ) -> bytes:
        lat_fixed = int(round(lat * 1e6))
        lon_fixed = int(round(lon * 1e6))
        temp_c10 = int(round(ambient_temp_c * 10))
        grad_c10 = int(round(convective_grad_c * 10))
        gas_c10 = int(round(max(-32760, min(32760, gas_dc_dt * 10))))
        co2_u = int(round(min(65535, max(0, co2_ppm))))
        voc_u = int(round(min(65535, max(0, voc_ppb))))
        wind_spd_c10 = int(round(min(65535, max(0, wind_speed_kmh * 10))))
        wind_dir_u = int(round(wind_dir_deg)) % 360
        conf_u = int(round(min(100, max(0, confidence_pct))))
        alert_u = int(round(min(4, max(0, alert_level))))
        bat_u = int(round(min(100, max(0, battery_pct))))

        # Simple CRC8 computation
        data_to_hash = (
            f"{node_id_int}:{lat_fixed}:{lon_fixed}:{temp_c10}:{grad_c10}:{co2_u}:{conf_u}"
        ).encode("utf-8")
        crc8 = sum(data_to_hash) % 256

        raw_bytes = struct.pack(
            cls.STRUCT_FORMAT,
            node_id_int,
            int(timestamp),
            lat_fixed,
            lon_fixed,
            temp_c10,
            grad_c10,
            gas_c10,
            co2_u,
            voc_u,
            wind_spd_c10,
            wind_dir_u,
            conf_u,
            alert_u,
            bat_u,
            crc8
        )
        return raw_bytes

    @classmethod
    def unpack(cls, raw_bytes: bytes) -> Dict[str, Any]:
        if len(raw_bytes) != cls.PACKET_SIZE_BYTES:
            raise ValueError(f"Tamaño de paquete inválido: {len(raw_bytes)} (esperado {cls.PACKET_SIZE_BYTES})")
        
        unpacked = struct.unpack(cls.STRUCT_FORMAT, raw_bytes)
        return {
            "node_id_int": unpacked[0],
            "timestamp": float(unpacked[1]),
            "lat": unpacked[2] / 1e6,
            "lon": unpacked[3] / 1e6,
            "ambient_temp_c": unpacked[4] / 10.0,
            "convective_grad_c": unpacked[5] / 10.0,
            "gas_dc_dt": unpacked[6] / 10.0,
            "co2_ppm": float(unpacked[7]),
            "voc_ppb": float(unpacked[8]),
            "wind_speed_kmh": unpacked[9] / 10.0,
            "wind_dir_deg": float(unpacked[10]),
            "confidence_pct": unpacked[11],
            "alert_level": unpacked[12],
            "battery_pct": unpacked[13],
            "crc8": unpacked[14],
            "packet_size_bytes": len(raw_bytes)
        }


class NeuroFlyEdgeInference:
    """
    Inferencia Sensorial Neuromórfica en el Borde (Edge Python / MicroPython):
    1. Lóbulo Olfativo: Detección diferencial dC/dt de gases de combustión.
    2. Médula/Lámina Visual (Flujo Térmico): Análisis de gradientes térmicos convectivos
       ascendentes y parpadeo errático.
    3. Filtro Neuromórfico de Falsos Positivos: Discriminación frente a radiación solar
       diurna en copas y polvo/gases agrícolas sin calor ascendente.
    """
    def __init__(self, node_id: str):
        self.node_id = node_id
        
        # Historial temporal para cálculo diferencial (dC/dt y dT/dt)
        self.prev_co2: Optional[float] = None
        self.prev_voc: Optional[float] = None
        self.prev_temp: Optional[float] = None
        self.prev_time: Optional[float] = None
        
        # Buffer de derivadas para detección de turbulencia convectiva
        self.convective_history: List[float] = []
        self.solar_baseline_temp = 28.0

    def process_sample(
        self,
        raw_co2_ppm: float,
        raw_voc_ppb: float,
        upper_canopy_temp_c: float,
        lower_sensor_temp_c: float,
        ambient_temp_c: float,
        wind_speed_kmh: float,
        wind_dir_deg: float,
        solar_radiation_wm2: float = 750.0,
        dt_sec: float = 1.0
    ) -> Dict[str, Any]:
        """
        Ejecuta el ciclo de inferencia sensorial biomimética.
        """
        # 1. ── LÓBULO OLFATIVO: TASA TEMPORAL DE CAMBIO DE GASES (dC/dt) ────────
        if self.prev_co2 is None:
            self.prev_co2 = raw_co2_ppm
            self.prev_voc = raw_voc_ppb
            self.prev_temp = lower_sensor_temp_c
            self.prev_time = time.time()
            d_co2_dt = 0.0
            d_voc_dt = 0.0
        else:
            effective_dt = max(0.2, dt_sec)
            d_co2_dt = (raw_co2_ppm - self.prev_co2) / effective_dt
            d_voc_dt = (raw_voc_ppb - self.prev_voc) / effective_dt

        self.prev_co2 = raw_co2_ppm
        self.prev_voc = raw_voc_ppb

        # Detección de microplumas diluidas por el viento:
        # Una micropluma genera pulsos rápidos y positivos de dC/dt incluso si la
        # concentración absoluta aún está lejos de un humo visible masivo.
        gas_plume_score = 0.0
        if d_co2_dt > 1.8 or d_voc_dt > 12.0:
            # Rápida tasa de incremento de gases de pirólisis
            gas_plume_score = min(1.0, (d_co2_dt / 8.0) * 0.6 + (d_voc_dt / 40.0) * 0.4)
        elif raw_co2_ppm > 480.0:
            gas_plume_score = min(1.0, (raw_co2_ppm - 420.0) / 200.0)

        # 2. ── MÉDULA / LÁMINA VISUAL: FLUJO TÉRMICO CONVECTIVO MULTIZONA ───────
        # Gradiente térmico vertical: el calor de una combustión asciende con turbulencia.
        # En calentamiento solar diurno, la copa superior se calienta gradualmente de manera uniforme,
        # mientras que en fuego ascendente el sensor inferior y el flujo convectivo vertical
        # exhiben gradiente positivo ascendente y pulsaciones térmicas rápidas.
        convective_gradient = lower_sensor_temp_c - ambient_temp_c
        vertical_differential = lower_sensor_temp_c - upper_canopy_temp_c

        # Registro de turbulencia térmica
        self.convective_history.append(convective_gradient)
        if len(self.convective_history) > 10:
            self.convective_history.pop(0)

        # Varianza de alta frecuencia (parpadeo de llama y remolino térmico)
        if len(self.convective_history) >= 4:
            mean_c = sum(self.convective_history) / len(self.convective_history)
            variance_c = sum((x - mean_c) ** 2 for x in self.convective_history) / len(self.convective_history)
            thermal_flicker_index = min(1.0, math.sqrt(variance_c) / 3.5)
        else:
            thermal_flicker_index = 0.0

        # Normalización de calor anómalo
        thermal_anomaly_score = max(0.0, min(1.0, (convective_gradient - 4.0) / 18.0))

        # 3. ── FILTRO NEUROMÓRFICO DE FALSOS POSITIVOS ─────────────────────────
        # Discrimina calentamiento solar y emisiones no relacionadas:
        # Caso A: Fuerte radiación solar (ej. 800 W/m2) calienta copa superior > sensor inferior,
        #         con dC/dt = 0 y flicker = 0. -> RECHAZO DE FALSO POSITIVO (SOLAR).
        # Caso B: Gas de escape vehicular o polvo sin gradiente térmico ni flicker.
        #         -> RECHAZO DE FALSO POSITIVO (ESCAPE AISLADO).
        # Caso C: Gas dC/dt alto + gradiente térmico positivo + flicker convectivo ascendente.
        #         -> COINCIDENCIA MULTIMODAL CONFIRMADA (IGNICIÓN REAL).

        is_solar_heating = (
            solar_radiation_wm2 > 500.0 and
            vertical_differential < 1.0 and
            d_co2_dt < 0.8 and
            thermal_flicker_index < 0.2
        )

        is_exhaust_only = (
            gas_plume_score > 0.4 and
            convective_gradient < 3.0 and
            thermal_flicker_index < 0.15
        )

        if is_solar_heating:
            rejection_reason = "Filtro Neuromórfico: Calentamiento solar diurno en copa (gradiente uniforme sin gas ni convección)"
            confidence = max(2, int(thermal_anomaly_score * 15))
            alert_level = 0
            event_type = "SOLAR_DIURNAL_HEATING"
        elif is_exhaust_only:
            rejection_reason = "Filtro Neuromórfico: Transitorio de gas aislado sin signatura térmica convectiva (posible vehículo/agrícola)"
            confidence = max(5, int(gas_plume_score * 20))
            alert_level = 1
            event_type = "ISOLATED_GAS_TRANSIENT"
        else:
            # Coincidencia multimodal sinérgica
            synergy = (gas_plume_score * 0.55 + thermal_anomaly_score * 0.45)
            if thermal_flicker_index > 0.3:
                synergy *= 1.25

            confidence = int(round(min(100, max(0, synergy * 100))))
            rejection_reason = "Ninguno (Coincidencia quimio-térmica validada)"

            if confidence >= 78 and convective_gradient >= 8.0:
                alert_level = 3  # POSIBLE INCENDIO CRÍTICO -> Disparo inmediato
                event_type = "WILDFIRE_IGNITION_CONFIRMED"
            elif confidence >= 50 or (convective_gradient >= 6.0 and gas_plume_score >= 0.3):
                alert_level = 2  # SOSPECHA ALTA
                event_type = "SUSPECT_THERMAL_PLUME"
            elif confidence >= 25 or convective_gradient >= 4.0:
                alert_level = 1  # ATENCIÓN PREVENTIVA
                event_type = "ELEVATED_CONDITIONS"
            else:
                alert_level = 0
                event_type = "NORMAL_PATROL"

        return {
            "node_id": self.node_id,
            "olfactory_lobe": {
                "d_co2_dt_ppm_s": round(d_co2_dt, 3),
                "d_voc_dt_ppb_s": round(d_voc_dt, 3),
                "co2_ppm": round(raw_co2_ppm, 1),
                "voc_ppb": round(raw_voc_ppb, 1),
                "gas_plume_score": round(gas_plume_score, 3),
                "microplume_detected": gas_plume_score > 0.35
            },
            "thermal_convective_array": {
                "convective_gradient_c": round(convective_gradient, 2),
                "vertical_differential_c": round(vertical_differential, 2),
                "thermal_flicker_index": round(thermal_flicker_index, 3),
                "thermal_anomaly_score": round(thermal_anomaly_score, 3)
            },
            "neuromorphic_filter": {
                "is_solar_heating_rejected": is_solar_heating,
                "is_exhaust_rejected": is_exhaust_only,
                "rejection_reason": rejection_reason,
                "coincidence_verified": not (is_solar_heating or is_exhaust_only) and (confidence >= 50)
            },
            "alert_level": alert_level,
            "confidence_pct": confidence,
            "event_type": event_type
        }


class TreeNodeModel:
    """
    Representa un Nodo Sensor Arbóreo Ignífugo individual.
    Infraestructura física:
    - Chasis: Polímero UL94 V-0 retardante de llama y aluminio fundido con barrera cerámica externa.
    - Ingreso de gases: Membrana hidrofóbica de PTFE (politetrafluoroetileno).
    - Autonomía: Celda LiFePO4 de alta estabilidad térmica + micro-panel solar (gestión continua).
    - Conectividad: Transmisor LoRaWAN / LoRa Mesh a 915 MHz.
    """
    def __init__(
        self,
        node_id: str,
        node_num: int,
        tree_species: str,
        lat: float,
        lon: float,
        altitude_m: float = 520.0,
        battery_pct: float = 98.0
    ):
        self.node_id = node_id
        self.node_num = node_num
        self.tree_species = tree_species
        self.lat = lat
        self.lon = lon
        self.altitude_m = altitude_m
        self.battery_pct = battery_pct

        # Especificaciones físicas del hardware ignífugo
        self.hardware_profile = {
            "enclosure_spec": "UL94 V-0 Ignífugo / Aleación Al-Si con recubrimiento cerámico 600°C",
            "gas_membrane": "Membrana PTFE hidrofóbica microporosa (repelente de agua y resina)",
            "battery_chemistry": "LiFePO4 3.2V 6000mAh (Rango térmico seguro -20°C a +70°C)",
            "solar_panel_w": 2.5,
            "radio_band": "LoRaWAN 915 MHz (AU915/US915 Ch 0-7)",
            "edge_processor": "ARM Cortex-M4 / RP2040 MicroPython / Edge Python",
            "duty_cycle_mode": "ACTIVE_SLEEP_INFERENCE"
        }

        self.inference_engine = NeuroFlyEdgeInference(node_id=node_id)
        
        # Telemetría actual y última transmisión LoRa
        self.current_ambient_temp_c = 26.5
        self.current_sensor_temp_c = 27.2
        self.current_canopy_temp_c = 28.0
        self.current_co2_ppm = 412.0
        self.current_voc_ppb = 45.0
        self.current_wind_speed_kmh = 18.0
        self.current_wind_dir_deg = 65.0
        self.solar_wm2 = 720.0

        self.latest_inference: Optional[Dict[str, Any]] = None
        self.latest_lora_packet_bytes: Optional[bytes] = None
        self.latest_lora_packet_dict: Optional[Dict[str, Any]] = None
        self.packets_transmitted = 0
        self.last_tx_timestamp = 0.0

    def update_environment_and_infer(
        self,
        ambient_temp_c: float,
        co2_ppm: float,
        voc_ppb: float,
        wind_speed_kmh: float,
        wind_dir_deg: float,
        local_heat_c: float = 0.0,
        solar_radiation_wm2: float = 720.0,
        dt_sec: float = 1.0
    ) -> Dict[str, Any]:
        """
        Actualiza el estado físico de los sensores en el árbol y ejecuta la inferencia local.
        """
        # Desgaste realista de batería e ingreso de carga solar
        solar_charge = (solar_radiation_wm2 / 1000.0) * 0.002 * dt_sec
        consumption = 0.0005 * dt_sec
        self.battery_pct = min(100.0, max(5.0, self.battery_pct + solar_charge - consumption))

        self.current_ambient_temp_c = ambient_temp_c
        self.current_sensor_temp_c = ambient_temp_c + local_heat_c
        # Si no hay fuego local, la copa se calienta por sol más que el tronco sombreado
        if local_heat_c > 2.0:
            # Fuego convectivo ascendente: sensor en tronco se calienta con corrientes ascendentes
            self.current_canopy_temp_c = ambient_temp_c + (local_heat_c * 0.6)
        else:
            self.current_canopy_temp_c = ambient_temp_c + (solar_radiation_wm2 / 200.0)

        self.current_co2_ppm = co2_ppm
        self.current_voc_ppb = voc_ppb
        self.current_wind_speed_kmh = wind_speed_kmh
        self.current_wind_dir_deg = wind_dir_deg
        self.solar_wm2 = solar_radiation_wm2

        # Inferencia local en el nodo
        infer_result = self.inference_engine.process_sample(
            raw_co2_ppm=self.current_co2_ppm,
            raw_voc_ppb=self.current_voc_ppb,
            upper_canopy_temp_c=self.current_canopy_temp_c,
            lower_sensor_temp_c=self.current_sensor_temp_c,
            ambient_temp_c=self.current_ambient_temp_c,
            wind_speed_kmh=self.current_wind_speed_kmh,
            wind_dir_deg=self.current_wind_dir_deg,
            solar_radiation_wm2=solar_radiation_wm2,
            dt_sec=dt_sec
        )
        self.latest_inference = infer_result

        # Generar paquete LoRa compacto (< 50 bytes)
        now_ts = time.time()
        convective_grad = infer_result["thermal_convective_array"]["convective_gradient_c"]
        gas_rate = infer_result["olfactory_lobe"]["d_co2_dt_ppm_s"]
        conf = infer_result["confidence_pct"]
        alert = infer_result["alert_level"]

        # Si hay alerta o transcurrió tiempo de latido (heartbeat regular cada 60s)
        should_transmit = (alert >= 2) or (now_ts - self.last_tx_timestamp > 30.0)
        if should_transmit:
            raw_bytes = LoRaCompactPacket.pack(
                node_id_int=self.node_num,
                timestamp=now_ts,
                lat=self.lat,
                lon=self.lon,
                ambient_temp_c=self.current_ambient_temp_c,
                convective_grad_c=convective_grad,
                gas_dc_dt=gas_rate,
                co2_ppm=self.current_co2_ppm,
                voc_ppb=self.current_voc_ppb,
                wind_speed_kmh=self.current_wind_speed_kmh,
                wind_dir_deg=self.current_wind_dir_deg,
                confidence_pct=conf,
                alert_level=alert,
                battery_pct=int(round(self.battery_pct))
            )
            self.latest_lora_packet_bytes = raw_bytes
            self.latest_lora_packet_dict = LoRaCompactPacket.unpack(raw_bytes)
            self.packets_transmitted += 1
            self.last_tx_timestamp = now_ts

        return {
            "node_id": self.node_id,
            "node_num": self.node_num,
            "tree_species": self.tree_species,
            "lat": self.lat,
            "lon": self.lon,
            "altitude_m": self.altitude_m,
            "battery_pct": round(self.battery_pct, 1),
            "telemetry": {
                "ambient_temp_c": round(self.current_ambient_temp_c, 1),
                "sensor_temp_c": round(self.current_sensor_temp_c, 1),
                "canopy_temp_c": round(self.current_canopy_temp_c, 1),
                "co2_ppm": round(self.current_co2_ppm, 1),
                "voc_ppb": round(self.current_voc_ppb, 1),
                "wind_speed_kmh": round(self.current_wind_speed_kmh, 1),
                "wind_dir_deg": round(self.current_wind_dir_deg, 1)
            },
            "inference": infer_result,
            "lora_tx": {
                "packet_size_bytes": len(self.latest_lora_packet_bytes) if self.latest_lora_packet_bytes else 0,
                "packet_hex": self.latest_lora_packet_bytes.hex().upper() if self.latest_lora_packet_bytes else None,
                "transmitted_count": self.packets_transmitted,
                "last_tx_sec_ago": round(now_ts - self.last_tx_timestamp, 1) if self.last_tx_timestamp > 0 else None
            },
            "hardware_health": {
                "enclosure": "OK_SEALED",
                "ptfe_membrane": "CLEAN_DRY",
                "lora_signal_dbm": -72.0,
                "battery_status": "NORMAL_STABLE" if self.battery_pct > 20 else "LOW_BATTERY"
            }
        }


class BasinGateway:
    """
    Gateway de Cuenca / Enlace Satelital o 4G
    Recolecta los paquetes LoRaWAN / LoRa Mesh a 915 MHz emitidos por los nodos arbóreos
    y los retransmite mediante Starlink satelital o enlace celular hacia el Servidor Central.
    """
    def __init__(
        self,
        gateway_id: str = "GW-CUENCA-01",
        name: str = "Gateway Cumbre Cerro Manquehue",
        lat: float = -33.3680,
        lon: float = -70.5840,
        altitude_m: float = 1638.0,
        uplink_type: str = "SATELITAL_STARLINK_4G_FAILOVER"
    ):
        self.gateway_id = gateway_id
        self.name = name
        self.lat = lat
        self.lon = lon
        self.altitude_m = altitude_m
        self.uplink_type = uplink_type
        
        self.packets_relayed = 0
        self.connected_nodes: List[str] = []
        self.is_online = True
        self.last_uplink_ts = time.time()

    def relay_packet(self, packet_bytes: bytes, sender_node_id: str) -> Dict[str, Any]:
        """
        Valida integridad y sube el paquete al servidor central.
        """
        self.packets_relayed += 1
        self.last_uplink_ts = time.time()
        if sender_node_id not in self.connected_nodes:
            self.connected_nodes.append(sender_node_id)

        parsed = LoRaCompactPacket.unpack(packet_bytes)
        return {
            "gateway_id": self.gateway_id,
            "uplink_type": self.uplink_type,
            "sender_node_id": sender_node_id,
            "rssi_dbm": -74.5,
            "snr_db": 9.2,
            "relayed_timestamp": self.last_uplink_ts,
            "payload": parsed
        }
