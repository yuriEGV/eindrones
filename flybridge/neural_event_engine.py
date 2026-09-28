"""
FLYBRIDGE — Capa 5: Motor de Eventos Neuronales (Neural Event Engine)
Convierte actividad nerviosa e interpretaciones de estado en Eventos Calificados.
Aplica arquitectura orientada a eventos (Event-Driven Edge Computing):
- En estado NORMAL: no satura la red transmitiendo telemetría continua innecesaria.
- En estado ATENCIÓN / SOSPECHA / ALERTA: emite eventos calificados para FIREWATCH.
"""

import time
from typing import Dict, Any, Optional, List

class NeuralEventEngine:
    """
    Convierte la actividad del sistema nervioso artificial en eventos discretos comprensibles.
    Filtra el ruido sensorial continuo y comunica solo eventos biológicamente relevantes.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.last_event_emitted: Optional[Dict[str, Any]] = None
        self.last_emission_time: float = 0.0
        self.event_sequence_num: int = 1

    def process_and_emit(
        self,
        interpretation: Dict[str, Any],
        sensory_packet: Dict[str, Any],
        memory_context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Determina si el estado actual amerita emitir un evento neuronal hacia FIREWATCH.
        Retorna el evento estructurado o None si el dron está en reposo normal (Edge Filtering).
        """
        state = interpretation["internal_state"]
        env_state = interpretation["environmental_state"]
        coords = sensory_packet["spatial_sense"]
        current_time = time.time()

        # Si el estado es NORMAL, no transmitimos eventos de alerta
        # (Solo un latido de vida / heartbeat periódico cada 30 segundos si fuera necesario)
        if state == "NORMAL":
            return None

        # Condición de emisión:
        # Emitir si hubo una transición de estado, o si estamos en ALERTA/CONFIRMACIÓN cada 4 segundos
        time_since_last = current_time - self.last_emission_time
        should_emit = (
            interpretation["state_transition_occurred"] or
            (state in ("ALERTA", "CONFIRMACIÓN") and time_since_last >= 4.0) or
            (state == "SOSPECHA" and time_since_last >= 10.0)
        )

        if not should_emit:
            return None

        # Clasificación del tipo de evento
        if state == "CONFIRMACIÓN":
            event_type = "FIRE_CONFIRMED"
            priority = "CRITICAL"
            confidence = min(0.99, 0.85 + env_state["fire_risk"] * 0.14)
        elif state == "ALERTA":
            event_type = "THERMAL_ANOMALY"
            priority = "HIGH"
            confidence = min(0.95, 0.70 + env_state["fire_risk"] * 0.25)
        elif state == "SOSPECHA":
            event_type = "SUSPICIOUS_HEAT_OR_SMOKE"
            priority = "MEDIUM"
            confidence = 0.65
        else: # ATENCIÓN
            event_type = "FAVORABLE_FIRE_CONDITIONS"
            priority = "LOW"
            confidence = 0.50

        neural_event = {
            "event": event_type,
            "event_id": f"NE-{self.agent_id}-{int(current_time)}-{self.event_sequence_num:03d}",
            "agent_id": self.agent_id,
            "timestamp": round(current_time, 2),
            "internal_state": state,
            "neural_state": interpretation["neural_state"],
            "priority": priority,
            "confidence": round(float(confidence), 2),
            "location": {
                "lat": coords["lat"],
                "lon": coords["lon"],
                "altitude_m": sensory_packet["proprioception"]["altitude_m"]
            },
            "environmental_state": env_state,
            "context_justification": memory_context["context_summary"],
            "recommended_action": interpretation["recommended_action"],
            "sensory_evidence": {
                "thermal_surface_c": sensory_packet["eyes"]["thermal_surface_c"],
                "smoke_concentration": sensory_packet["antennae"]["smoke_concentration"],
                "wind_kmh": sensory_packet["environment"]["wind_speed_kmh"],
                "vegetation_dryness": sensory_packet["eyes"]["vegetation_dryness"]
            }
        }

        self.last_event_emitted = neural_event
        self.last_emission_time = current_time
        self.event_sequence_num += 1

        return neural_event
