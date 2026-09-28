"""
FIREWATCH & FLYBRIDGE API Server — Centro Táctico Multiorganismo
FastAPI server serving:
- Telemetría en tiempo real de la Red de Nodos Arbóreos Ignífugos (Inferencia NeuroFly Edge)
- Reubicación interactiva de nodos en mapa (Drag & Drop) y Presets de separación 500-1000m
- Extinción / Reset de focos de simulacro a demanda
- Pilotaje manual del dron verificador con dinámica NeuroFly y Retorno a Base (RTL)
- Telemetría FPV HUD y control de Gimbal / Zoom
- Gateway de Cuenca (LoRaWAN Estrella Redundante / 915 MHz SUBTEL Chile / Satelital Starlink)
- Estación Drone-in-a-Box en dependencias de Autoridades (Bomberos / Carabineros / CONAF)
- Despacho operativo para Bomberos y Carabineros CENCO
- WebSocket Hub en tiempo real
"""

import os
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List

from flybridge.mission_server import CentralMissionServer

app = FastAPI(
    title="FLYBRIDGE FIREWATCH — Red de Nodos Arbóreos & Drone-in-a-Box",
    description="Sistema bio-inspirado en NeuroFly para prevención temprana y verificación de incendios forestales",
    version="1.1.0"
)

# Servidor Central de Misiones Singleton
mission_server = CentralMissionServer()

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

class FeedbackRequest(BaseModel):
    incident_id: str
    verdict: str  # 'CONFIRMADO_INCENDIO' or 'FALSO_POSITIVO'
    operator_notes: Optional[str] = ""

class WindUpdateRequest(BaseModel):
    speed_kmh: float
    direction_deg: float

class NodeTriggerRequest(BaseModel):
    node_id: str  # e.g. "NODE-ARBOR-03"
    peak_temp_c: Optional[float] = 68.0

class NodeMoveRequest(BaseModel):
    node_id: str
    lat: float
    lon: float

class NodePresetRequest(BaseModel):
    preset_name: str

class DroneLaunchRequest(BaseModel):
    target_node_id: Optional[str] = "NODE-ARBOR-03"

class DronePilotRequest(BaseModel):
    command: str  # "MOVE", "FORWARD", "BACKWARD", "YAW_LEFT", "YAW_RIGHT", "ROTATE", "HOVER", "ALTITUDE_UP", "ALTITUDE_DOWN", "ALTITUDE", "RTL", "ORBIT", "GIMBAL"
    speed: Optional[float] = None
    speed_factor: Optional[float] = None
    heading: Optional[float] = None
    alt_delta: Optional[float] = None
    delta_alt_m: Optional[float] = None
    pitch: Optional[float] = None
    gimbal_pitch_delta: Optional[float] = None
    gimbal_yaw_delta: Optional[float] = None
    zoom: Optional[float] = None
    camera_mode: Optional[str] = None

@app.get("/api/status")
async def get_status():
    """Retorna el estado completo del sistema en tiempo real."""
    data = mission_server.step(dt=0.3)
    drone_telemetry = data["verifier_drone"]
    compat_drone = {
        "drone_id": drone_telemetry["drone_id"],
        "status": drone_telemetry["status"],
        "latitude": drone_telemetry["latitude"],
        "longitude": drone_telemetry["longitude"],
        "altitude_m": drone_telemetry["altitude_m"],
        "heading_deg": drone_telemetry["heading_deg"],
        "speed_kmh": drone_telemetry["speed_kmh"],
        "battery_pct": drone_telemetry["battery_pct"],
        "temperature_c": drone_telemetry["thermal_flir"].get("core_temp_c", 28.0),
        "smoke_concentration": 0.85 if drone_telemetry["thermal_flir"].get("target_acquired") else 0.05,
        "co2_ppm": 680.0 if drone_telemetry["thermal_flir"].get("target_acquired") else 415.0,
        "mission": f"VERIFICACION_{drone_telemetry['target_node'] or 'STANDBY'}",
        "trajectory": drone_telemetry["trajectory"],
        "fpv_hud": drone_telemetry.get("fpv_hud", {}),
        "flybridge": {
            "internal_state": "CONFIRMACIÓN" if drone_telemetry["thermal_flir"].get("target_acquired") else "ALERTA",
            "neural_state": "THREAT_CRITICAL" if drone_telemetry["thermal_flir"].get("target_acquired") else "SEARCH_FOCUSED",
            "recommended_action": "DESPACHO_BOMBEROS_Y_CENCO",
            "environmental_state": {
                "fire_risk": 0.92 if drone_telemetry["thermal_flir"].get("target_acquired") else 0.45,
                "thermal_anomaly": 0.88,
                "smoke_probability": 0.75,
                "wind_risk": 0.65,
                "vegetation_dryness": 0.88
            },
            "context_justification": f"Foco verificado por FLIR y Óptica 4K. Despegue en {drone_telemetry['launch_elapsed_sec']}s (<45s verificado)."
        }
    }

    data["drones"] = [compat_drone]
    data["risk_analysis"] = {
        "alert_level": data["incident"]["alert_level"] if data["incident"] else 1,
        "risk_label": "CRÍTICO" if data["incident"] and data["incident"]["alert_level"] >= 3 else "MEDIO",
        "badge_color": "red" if data["incident"] and data["incident"]["alert_level"] >= 3 else "yellow",
        "explanation": (
            f"Alerta originada en {data['incident']['origin_node_id']} transmitida vía LoRaWAN 915 MHz. "
            f"Verificador despegó en {drone_telemetry['launch_elapsed_sec']}s desde el cuartel oficial."
            if data["incident"] else "Condiciones estables en cuenca forestal. Nodos en reposo activo."
        ),
        "primary_incident": data["incident"],
        "all_incidents": [data["incident"]] if data["incident"] else []
    }
    return JSONResponse(content=data)

@app.get("/api/incidents")
async def get_incidents():
    status = mission_server.step(dt=0.1)
    return JSONResponse(content={
        "primary": status.get("incident"),
        "history": [status.get("incident")] if status.get("incident") else [],
        "feedback_log": mission_server.operator_feedback_log
    })

@app.post("/api/node/trigger")
async def trigger_node(req: NodeTriggerRequest):
    """Simula una ignición en un nodo arbóreo específico para probar la respuesta automática."""
    hotspot = mission_server.inject_hotspot(node_id=req.node_id, peak_temp=req.peak_temp_c or 68.0)
    if not hotspot:
        raise HTTPException(status_code=404, detail=f"Nodo {req.node_id} no encontrado")
    return JSONResponse(content={"status": "injected", "hotspot": hotspot})

@app.post("/api/hotspot/clear")
async def clear_hotspots():
    """Extingue todos los focos de simulacro y restablece la cuenca a estado limpio."""
    res = mission_server.clear_hotspots()
    data = mission_server.step(dt=0.0)
    data["clear_result"] = res
    return JSONResponse(content=data)

@app.post("/api/node/move")
async def move_node(req: NodeMoveRequest):
    """Mueve dinámicamente un nodo a nuevas coordenadas (desde el mapa)."""
    res = mission_server.move_node(node_id=req.node_id, new_lat=req.lat, new_lon=req.lon)
    data = mission_server.step(dt=0.0)
    data["move_result"] = res
    return JSONResponse(content=data)

@app.post("/api/node/preset")
async def set_node_preset(req: NodePresetRequest):
    """Aplica disposiciones tácticas de nodos para demostrar diferentes coberturas."""
    res = mission_server.set_preset_layout(preset_name=req.preset_name)
    data = mission_server.step(dt=0.0)
    data["preset_result"] = res
    return JSONResponse(content=data)

@app.post("/api/drone/launch")
async def launch_drone(req: DroneLaunchRequest):
    """Orden de despegue de emergencia del dron verificador hacia un nodo."""
    res = mission_server.trigger_drone_launch(target_node_id=req.target_node_id)
    return JSONResponse(content=res)

@app.post("/api/drone/pilot")
async def pilot_drone(req: DronePilotRequest):
    """Comando de pilotaje manual en tiempo real para el Dron Verificador."""
    effective_alt_delta = req.delta_alt_m if req.delta_alt_m is not None else req.alt_delta
    res = mission_server.pilot_drone(
        command=req.command,
        speed=req.speed,
        heading=req.heading,
        alt_delta=effective_alt_delta,
        gimbal_pitch_delta=req.gimbal_pitch_delta,
        gimbal_yaw_delta=req.gimbal_yaw_delta,
        zoom=req.zoom,
        camera_mode=req.camera_mode,
        pitch=req.pitch
    )
    status = mission_server.step(dt=0.0)
    res["drone"] = status["verifier_drone"]
    return JSONResponse(content=res)

@app.post("/api/drone/rtl")
async def return_to_launch():
    """Ordena el retorno y aterrizaje autónomo en la base (RTL / Return to Launch)."""
    res = mission_server.recall_drone()
    status = mission_server.step(dt=0.0)
    res["drone"] = status["verifier_drone"]
    return JSONResponse(content=res)

@app.post("/api/drone/return")
async def return_drone():
    """Alias para retorno a base."""
    res = mission_server.recall_drone()
    status = mission_server.step(dt=0.0)
    res["drone"] = status["verifier_drone"]
    return JSONResponse(content=res)

@app.get("/api/subtel/compliance")
async def get_subtel_compliance():
    """Retorna las especificaciones de cumplimiento regulatorio SUBTEL Chile (915 MHz)."""
    return JSONResponse(content=mission_server.subtel_compliance)

@app.post("/api/feedback")
async def submit_feedback(fb: FeedbackRequest):
    result = mission_server.record_feedback(verdict=fb.verdict, notes=fb.operator_notes or "")
    return JSONResponse(content={"status": "recorded", "feedback": result})

@app.post("/api/wind")
async def update_wind(req: WindUpdateRequest):
    mission_server.set_wind(req.speed_kmh, req.direction_deg)
    return JSONResponse(content={"status": "updated", "wind": {"speed_kmh": req.speed_kmh, "direction_deg": req.direction_deg}})

@app.get("/api/bomberos/route")
async def get_bomberos_route():
    """Ficha táctica con ruta de acceso y modelo de propagación para Bomberos."""
    status = mission_server.step(dt=0.1)
    return JSONResponse(content=status.get("bomberos_dispatch", {}))

@app.get("/api/cenco/forensics")
async def get_cenco_forensics():
    """Ficha probatoria con capturas periciales y plan de cortes de ruta para Carabineros CENCO."""
    status = mission_server.step(dt=0.1)
    return JSONResponse(content=status.get("cenco_dispatch", {}))

@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Paso de simulación a 2.5 Hz (0.4s)
            snapshot = mission_server.step(dt=0.4)
            drone_telemetry = snapshot["verifier_drone"]
            compat_drone = {
                "drone_id": drone_telemetry["drone_id"],
                "status": drone_telemetry["status"],
                "latitude": drone_telemetry["latitude"],
                "longitude": drone_telemetry["longitude"],
                "altitude_m": drone_telemetry["altitude_m"],
                "heading_deg": drone_telemetry["heading_deg"],
                "speed_kmh": drone_telemetry["speed_kmh"],
                "battery_pct": drone_telemetry["battery_pct"],
                "temperature_c": drone_telemetry["thermal_flir"].get("core_temp_c", 28.0),
                "smoke_concentration": 0.85 if drone_telemetry["thermal_flir"].get("target_acquired") else 0.05,
                "co2_ppm": 680.0 if drone_telemetry["thermal_flir"].get("target_acquired") else 415.0,
                "mission": f"VERIFICACION_{drone_telemetry['target_node'] or 'STANDBY'}",
                "trajectory": drone_telemetry["trajectory"],
                "fpv_hud": drone_telemetry.get("fpv_hud", {}),
                "flybridge": {
                    "internal_state": "CONFIRMACIÓN" if drone_telemetry["thermal_flir"].get("target_acquired") else "ALERTA",
                    "neural_state": "THREAT_CRITICAL" if drone_telemetry["thermal_flir"].get("target_acquired") else "SEARCH_FOCUSED",
                    "recommended_action": "DESPACHO_BOMBEROS_Y_CENCO",
                    "environmental_state": {
                        "fire_risk": 0.92 if drone_telemetry["thermal_flir"].get("target_acquired") else 0.45,
                        "thermal_anomaly": 0.88,
                        "smoke_probability": 0.75,
                        "wind_risk": 0.65,
                        "vegetation_dryness": 0.88
                    },
                    "context_justification": f"Foco verificado por FLIR y Óptica 4K. Despegue en {drone_telemetry['launch_elapsed_sec']}s (<45s verificado)."
                }
            }
            snapshot["drones"] = [compat_drone]
            snapshot["risk_analysis"] = {
                "alert_level": snapshot["incident"]["alert_level"] if snapshot["incident"] else 1,
                "risk_label": "CRÍTICO" if snapshot["incident"] and snapshot["incident"]["alert_level"] >= 3 else "MEDIO",
                "badge_color": "red" if snapshot["incident"] and snapshot["incident"]["alert_level"] >= 3 else "yellow",
                "explanation": (
                    f"Alerta en {snapshot['incident']['origin_node_id']} transmitida vía LoRaWAN 915 MHz. "
                    f"Dron verificador desplegado en {drone_telemetry['launch_elapsed_sec']}s desde cuartel oficial."
                    if snapshot["incident"] else "Condiciones estables en cuenca forestal."
                ),
                "primary_incident": snapshot["incident"],
                "all_incidents": [snapshot["incident"]] if snapshot["incident"] else []
            }

            await websocket.send_json(snapshot)
            await asyncio.sleep(0.4)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass

# Mount static files and serve index.html
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(content={"message": "FLYBRIDGE FIREWATCH activo. Interfaz en /static/index.html"})
