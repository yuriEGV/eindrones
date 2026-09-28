"""
Lanzador directo de FLYBRIDGE v0.1
Ejecuta el servidor táctico FastAPI y el Hub WebSocket sin depender del PATH de uvicorn.
"""
import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print("🌲 FLYBRIDGE v0.1 — Centro de Mando Táctico GIS")
    print("Red de Nodos Arbóreos Ignífugos & Estación Drone-in-a-Box en Cuartel")
    print("=" * 70)
    print("Iniciando servidor local en: http://localhost:8000")
    print("Presione Ctrl+C para detener el servidor.")
    print("=" * 70)
    uvicorn.run("firewatch.server:app", host="0.0.0.0", port=8000, reload=True)
