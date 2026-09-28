@echo off
title FLYBRIDGE v0.1 - Centro de Mando Tactico
echo ======================================================================
echo  🌲 FLYBRIDGE v0.1 - Centro de Mando Tactico GIS
echo  Red de Nodos Arboreos Ignifugos ^& Drone-in-a-Box en Cuartel
echo ======================================================================
echo.
echo Iniciando servidor en http://localhost:8000 ...
echo.
python -m uvicorn firewatch.server:app --host 0.0.0.0 --port 8000 --reload
pause
