"""
FLYBRIDGE — Sistema Nervioso Artificial Biológico Unificado
Integra las 5 capas neuromórficas:
1. Recepción Sensorial
2. Integración Multisensorial
3. Interpretación & Estados Internos (NORMAL -> ATENCIÓN -> SOSPECHA -> ALERTA -> CONFIRMACIÓN)
4. Memoria Contextual
5. Respuesta vía Neural Event Engine
"""

from typing import Dict, Any, Optional
from .sensory_encoder import SensoryEncoder
from .multisensory_integration import MultisensoryIntegrator
from .interpretation_engine import InterpretationEngine
from .context_memory import ContextualMemory
from .neural_event_engine import NeuralEventEngine

class FlybridgeNervousSystem:
    """
    Sistema Nervioso Artificial completo de FLYBRIDGE para un agente dron.
    Convierte el dron en un cuerpo biológico perceptivo e interpretativo.
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        # Las 5 capas de FLYBRIDGE
        self.encoder = SensoryEncoder(agent_id=agent_id)
        self.integrator = MultisensoryIntegrator()
        self.memory = ContextualMemory()
        self.interpreter = InterpretationEngine()
        self.event_engine = NeuralEventEngine(agent_id=agent_id)

    def process(
        self,
        thermal_c: float,
        vegetation_rgb_index: float,
        smoke_conc: float,
        voc_ppm: float,
        alt_m: float,
        speed_ms: float,
        heading_deg: float,
        battery_pct: float,
        lat: float,
        lon: float,
        habitat_type: str,
        ambient_temp_c: float,
        humidity_pct: float,
        wind_speed_kmh: float,
        wind_dir_deg: float,
        season: str = "summer",
        hour_of_day: float = 14.5
    ) -> Dict[str, Any]:
        """
        Ciclo completo del sistema nervioso:
        Percibir -> Contextualizar -> Integrar -> Interpretar -> Generar Evento
        """
        # 1. Recepción y codificación sensorial
        sensory_packet = self.encoder.encode(
            thermal_c=thermal_c,
            vegetation_rgb_index=vegetation_rgb_index,
            smoke_conc=smoke_conc,
            voc_ppm=voc_ppm,
            alt_m=alt_m,
            speed_ms=speed_ms,
            heading_deg=heading_deg,
            battery_pct=battery_pct,
            lat=lat,
            lon=lon,
            habitat_type=habitat_type,
            ambient_temp_c=ambient_temp_c,
            humidity_pct=humidity_pct,
            wind_speed_kmh=wind_speed_kmh,
            wind_dir_deg=wind_dir_deg,
            season=season,
            hour_of_day=hour_of_day
        )

        # 2. Consulta a Memoria Contextual (Expectativa habitual vs desviación)
        memory_context = self.memory.evaluate_contextual_deviation(
            measured_temp_c=thermal_c,
            measured_humidity=humidity_pct,
            habitat=habitat_type,
            season=season,
            hour_of_day=hour_of_day
        )

        # 3. Integración Multisensorial
        integrated_packet = self.integrator.integrate(sensory_packet, memory_context)

        # 4. Interpretación y Dinámica de Estados Internos
        interpretation = self.interpreter.interpret(integrated_packet, memory_context, sensory_packet)

        # 5. Motor de Eventos Neuronales (Neural Event Engine)
        neural_event = self.event_engine.process_and_emit(interpretation, sensory_packet, memory_context)

        return {
            "agent_id": self.agent_id,
            "sensory_packet": sensory_packet,
            "memory_context": memory_context,
            "integrated_packet": integrated_packet,
            "interpretation": interpretation,
            "neural_event": neural_event,
            # Perceptual telemetry for UI / Dashboard
            "internal_state": interpretation["internal_state"],
            "neural_state": interpretation["neural_state"],
            "environmental_state": interpretation["environmental_state"],
            "recommended_action": interpretation["recommended_action"]
        }
