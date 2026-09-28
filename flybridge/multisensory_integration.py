"""
FLYBRIDGE — Capa 2: Integración Multisensorial (Multisensory Integration)
Integra flujos dispares (ópticos, térmicos, químicos, anemométricos y espaciales)
en un conjunto perceptual coherente, calculando la congruencia multimodal.
"""

from typing import Dict, Any

class MultisensoryIntegrator:
    """
    Simula la convergencia multimodal que ocurre en el Lóbulo Antenal,
    Cuerpo Fúngico (Mushroom Body) y Complejo Central (Central Complex) de Drosophila.
    """
    def __init__(self):
        pass

    def integrate(self, sensory_packet: Dict[str, Any], memory_context: Dict[str, Any]) -> Dict[str, Any]:
        eyes = sensory_packet["eyes"]
        antennae = sensory_packet["antennae"]
        thermo = sensory_packet["thermoreceptors"]
        env = sensory_packet["environment"]
        
        # 1. Congruencia Térmica-Química:
        # Si hay alta temperatura Y presencia de gases de pirólisis (humo),
        # la probabilidad de incendio se multiplica sinérgicamente.
        t_salience = eyes["thermal_salience"]
        s_salience = antennae["smoke_concentration"]
        d_salience = eyes["vegetation_dryness"]
        w_salience = env["wind_salience"]
        c_surprise = memory_context["contextual_surprise"]

        # Congruencia multimodal no lineal (Cross-modal amplification)
        # En biología: coincidencia de dos modalidades sensoriales amplifica la respuesta de las neuronas de salida
        thermal_smoke_synergy = (t_salience * 0.6 + s_salience * 0.4) * (1.0 + 0.5 * min(t_salience, s_salience))
        thermal_smoke_synergy = min(1.0, thermal_smoke_synergy)

        # 2. Factor ambiental compuesto:
        # Viento + sequedad + déficit de humedad
        fuel_weather_congruence = (d_salience * 0.4 + w_salience * 0.35 + env["humidity_deficit"] * 0.25)

        # 3. Multimodal Salience Score (Relevancia integrada global)
        integrated_salience = (
            thermal_smoke_synergy * 0.55 +
            c_surprise * 0.25 +
            fuel_weather_congruence * 0.20
        )
        integrated_salience = float(min(1.0, max(0.0, integrated_salience)))

        return {
            "thermal_smoke_synergy": round(thermal_smoke_synergy, 3),
            "fuel_weather_congruence": round(fuel_weather_congruence, 3),
            "integrated_salience": round(integrated_salience, 3),
            "stimulus_coherence": "HIGH" if (t_salience > 0.3 and s_salience > 0.1) else "ISOLATED",
            "sensory_summary": {
                "thermal_surface_c": eyes["thermal_surface_c"],
                "ambient_temp_c": env["ambient_temp_c"],
                "smoke_concentration": s_salience,
                "vegetation_dryness": d_salience,
                "wind_speed_kmh": env["wind_speed_kmh"],
                "habitat": sensory_packet["spatial_sense"]["habitat_type"]
            }
        }
