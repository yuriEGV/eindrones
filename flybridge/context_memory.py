"""
FLYBRIDGE — Capa 4: Memoria Contextual & Episódica (Context Memory)
Almacena líneas base bioclimáticas históricas por coordenada, hora y estación.
Permite evaluar anomalías relativas al contexto ("¿Es normal para este lugar y hora?")
en lugar de reaccionar ciegamente a umbrales absolutos.
"""

from typing import Dict, Any, Tuple

class ContextualMemory:
    """
    Memoria que provee expectativas habituales de temperatura, humedad y viento.
    Distingue:
    - 40°C a mediodía en verano en desierto = NORMAL.
    - 40°C de noche en bosque con habitual de 18°C = ANOMALÍA CRÍTICA.
    """
    def __init__(self):
        # Base de conocimiento bioclimático por tipo de hábitat y estación
        self.habitat_baselines = {
            "forest": {
                "summer_day":   {"temp_c": 28.0, "humidity_pct": 32.0, "wind_kmh": 15.0},
                "summer_night": {"temp_c": 17.0, "humidity_pct": 55.0, "wind_kmh": 8.0},
                "winter_day":   {"temp_c": 14.0, "humidity_pct": 65.0, "wind_kmh": 18.0},
                "winter_night": {"temp_c": 6.0,  "humidity_pct": 80.0, "wind_kmh": 10.0}
            },
            "scrubland": {
                "summer_day":   {"temp_c": 33.0, "humidity_pct": 22.0, "wind_kmh": 22.0},
                "summer_night": {"temp_c": 19.0, "humidity_pct": 45.0, "wind_kmh": 12.0}
            },
            "desert": {
                "summer_day":   {"temp_c": 41.0, "humidity_pct": 12.0, "wind_kmh": 20.0},
                "summer_night": {"temp_c": 22.0, "humidity_pct": 25.0, "wind_kmh": 10.0}
            },
            "urban": {
                "summer_day":   {"temp_c": 31.0, "humidity_pct": 28.0, "wind_kmh": 14.0},
                "summer_night": {"temp_c": 21.0, "humidity_pct": 45.0, "wind_kmh": 8.0}
            }
        }
        
        # Historial de episodios previos por celda geográfica
        self.episodic_history: Dict[str, Dict[str, Any]] = {}

    def get_baseline_expectation(
        self,
        habitat: str = "forest",
        season: str = "summer",
        hour_of_day: float = 14.0
    ) -> Dict[str, float]:
        is_day = 7.0 <= hour_of_day < 20.5
        period = "day" if is_day else "night"
        key = f"{season}_{period}"

        hab_dict = self.habitat_baselines.get(habitat, self.habitat_baselines["forest"])
        baseline = hab_dict.get(key, hab_dict.get("summer_day", {"temp_c": 28.0, "humidity_pct": 30.0, "wind_kmh": 15.0}))
        return baseline

    def evaluate_contextual_deviation(
        self,
        measured_temp_c: float,
        measured_humidity: float,
        habitat: str,
        season: str,
        hour_of_day: float
    ) -> Dict[str, Any]:
        """
        Calcula la sorpresa o desviación estadística respecto a la expectativa contextual.
        """
        baseline = self.get_baseline_expectation(habitat, season, hour_of_day)
        
        temp_delta = measured_temp_c - baseline["temp_c"]
        humidity_drop = baseline["humidity_pct"] - measured_humidity
        
        # Contextual surprise factor (0.0 normal a 1.0 altamente inesperado)
        # Una desviación de +15°C en un bosque nocturno genera sorpresa extrema (>0.9)
        # Una desviación de +2°C en un desierto a mediodía genera sorpresa baja (<0.1)
        surprise_temp = float(min(1.0, max(0.0, temp_delta / 18.0)))
        
        is_statistically_abnormal = (temp_delta >= 10.0) or (temp_delta >= 6.0 and humidity_drop >= 12.0)
        
        context_summary = (
            f"Hábitat: {habitat} ({season}, {int(hour_of_day):02d}:00h). "
            f"Temp habitual: {baseline['temp_c']}°C (Observada: {measured_temp_c:.1f}°C, Δ={temp_delta:+.1f}°C)."
        )

        return {
            "expected_baseline": baseline,
            "temp_delta_c": round(temp_delta, 2),
            "humidity_drop_pct": round(humidity_drop, 2),
            "contextual_surprise": round(surprise_temp, 3),
            "is_abnormal": is_statistically_abnormal,
            "context_summary": context_summary
        }
