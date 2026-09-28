"""
FLYBRIDGE — Capa 3: Interpretación & Estados Internos Neuromórficos
Evalúa qué está ocurriendo mediante un autómata de estados biológicos:
NORMAL ──► ATENCIÓN ──► SOSPECHA ──► ALERTA ──► CONFIRMACIÓN
Genera el vector de estado ambiental cuantificado y el estado neural (REST, SEARCH, THREAT).
"""

from typing import Dict, Any

class InterpretationEngine:
    """
    Motor de interpretación neuromórfico que gestiona la dinámica de estados internos.
    No es una simple regla estática `if temp > 50`, sino una transición de activación nerviosa.
    """
    # Estados biológicos válidos
    STATE_NORMAL       = "NORMAL"
    STATE_ATENCION     = "ATENCIÓN"
    STATE_SOSPECHA     = "SOSPECHA"
    STATE_ALERTA       = "ALERTA"
    STATE_CONFIRMACION = "CONFIRMACIÓN"

    def __init__(self):
        self.current_state = self.STATE_NORMAL
        self.state_persistence_steps = 0
        self.threat_level = 0.0

    def interpret(
        self,
        integrated_packet: Dict[str, Any],
        memory_context: Dict[str, Any],
        sensory_packet: Dict[str, Any]
    ) -> Dict[str, Any]:
        salience = integrated_packet["integrated_salience"]
        ts_synergy = integrated_packet["thermal_smoke_synergy"]
        c_surprise = memory_context["contextual_surprise"]
        is_abnormal = memory_context["is_abnormal"]
        
        thermal_c = sensory_packet["eyes"]["thermal_surface_c"]
        ambient_c = sensory_packet["environment"]["ambient_temp_c"]
        smoke_conc = sensory_packet["antennae"]["smoke_concentration"]
        dryness = sensory_packet["eyes"]["vegetation_dryness"]
        wind_kmh = sensory_packet["environment"]["wind_speed_kmh"]
        habitat = sensory_packet["spatial_sense"]["habitat_type"]

        # 1. Vector de estado ambiental cuantificado
        thermal_anomaly_score = float(min(1.0, max(0.0, (thermal_c - ambient_c) / 25.0)))
        smoke_prob = float(min(1.0, smoke_conc * 1.25))
        wind_risk = float(min(1.0, wind_kmh / 45.0))
        fire_risk = float(min(1.0, (
            thermal_anomaly_score * 0.40 +
            smoke_prob * 0.30 +
            dryness * 0.15 +
            wind_risk * 0.15
        )))

        # 2. Dinámica de transición de Estados Internos (Transición continua)
        prev_state = self.current_state

        if fire_risk >= 0.78 and ts_synergy >= 0.65 and self.state_persistence_steps >= 4:
            self.current_state = self.STATE_CONFIRMACION
            neural_state = "THREAT_CRITICAL"
            recommended_action = "INTERVENCIÓN_INMEDIATA"
        elif fire_risk >= 0.60 or (thermal_anomaly_score >= 0.65 and smoke_prob >= 0.3):
            self.current_state = self.STATE_ALERTA
            neural_state = "THREAT"
            recommended_action = "VERIFICAR"
        elif fire_risk >= 0.40 or is_abnormal or smoke_prob >= 0.2:
            self.current_state = self.STATE_SOSPECHA
            neural_state = "SEARCH_FOCUSED"
            recommended_action = "INVESTIGAR_ZONA"
        elif salience >= 0.25 or thermal_anomaly_score >= 0.3 or dryness >= 0.75:
            self.current_state = self.STATE_ATENCION
            neural_state = "ATTENTIVE"
            recommended_action = "AUMENTAR_VIGILANCIA"
        else:
            self.current_state = self.STATE_NORMAL
            neural_state = "REST_PATROL"
            recommended_action = "PATRULLA_RUTINARIA"

        if self.current_state == prev_state:
            self.state_persistence_steps += 1
        else:
            self.state_persistence_steps = 1

        state_transition_occurred = (self.current_state != prev_state)

        return {
            "internal_state": self.current_state,
            "neural_state": neural_state,
            "state_persistence_steps": self.state_persistence_steps,
            "state_transition_occurred": state_transition_occurred,
            "recommended_action": recommended_action,
            "environmental_state": {
                "environment": habitat,
                "thermal_anomaly": round(thermal_anomaly_score, 2),
                "smoke_probability": round(smoke_prob, 2),
                "vegetation_dryness": round(dryness, 2),
                "wind_risk": round(wind_risk, 2),
                "fire_risk": round(fire_risk, 2)
            }
        }
