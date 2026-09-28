/**
 * FLYBRIDGE v0.1 — Client-side GIS Tactical Dashboard & Drone-in-a-Box Cockpit
 * 
 * Key Innovations:
 * 1. Tree-mounted fire-resistant sensor nodes (UL94 V-0, PTFE membrane) with NeuroFly Edge inference.
 * 2. Redundant LoRaWAN Star-of-Stars Topology (915 MHz SUBTEL Res. 1985 / 2017 - Max 1W EIRP).
 * 3. Basin Gateway in summit (1,120 m) with Starlink satellite/4G uplink feeding the FLYBRIDGE spatial brain.
 * 4. Automated Drone-in-a-Box (<45s launch) stationed in official authority facilities (Bomberos 132 / Carabineros 133).
 * 5. NeuroFly Biological Flight Dynamics (optomotor reflexes, turning saccades, haltere damping).
 * 6. Interactive drone piloting (W/A/S/D, altitude, speed, hover, orbit, RTL).
 * 7. Live synthetic FPV cockpit (FLIR radiometric IR vs 4K optical forensic zoom with SHA-256 integrity hash).
 * 8. Draggable nodes and Site Survey (500 m & 1.000 m) coverage analysis.
 * 9. Multiorganizational dispatch: Bomberos (vehicular route & fire spread) + CENCO (forensic evidence dossier).
 */

document.addEventListener('DOMContentLoaded', () => {
  // -------------------------------------------------------------
  // 1. INITIALIZE LEAFLET MAP
  // -------------------------------------------------------------
  const BASIN_CENTER = [-33.4150, -70.5750];
  const map = L.map('gisMap', {
    zoomControl: false,
    attributionControl: false
  }).setView(BASIN_CENTER, 14);

  // Satellite Imagery Basemap
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: 'Esri, Maxar, Earthstar Geographics'
  }).addTo(map);

  L.control.zoom({ position: 'bottomright' }).addTo(map);

  // -------------------------------------------------------------
  // 2. LAYER CONTAINERS & STATE
  // -------------------------------------------------------------
  const nodeMarkers = {};
  const loraStarLines = [];
  const siteSurvey500Circles = [];
  const siteSurvey1000Circles = [];
  let gatewayMarker = null;
  let authorityMarker = null;
  let droneMarker = null;
  let droneTrailLine = null;
  let fireSpreadPolygon = null;
  let bomberosRouteLine = null;
  const roadblockMarkers = [];

  let selectedNodeId = 'NODE-ARBOR-03';
  let latestTelemetryData = null;
  let currentWind = { speed_kmh: 27.0, direction_deg: 65.0 };
  let cameraMode = 'OPTICAL'; // 'OPTICAL' or 'THERMAL'
  let fpvGimbalPitch = -35.0;
  let fpvZoom = 12.5;

  // -------------------------------------------------------------
  // 3. SVG CUSTOM MAP ICONS
  // -------------------------------------------------------------
  function createTreeNodeIcon(nodeId, alertLevel, isSelected) {
    const isAlert = alertLevel >= 3;
    const isElevated = alertLevel >= 2;
    const strokeColor = isAlert ? '#ff3b14' : (isElevated ? '#ff9100' : '#00e676');
    const glowColor = isAlert ? 'rgba(255, 59, 20, 0.85)' : (isElevated ? 'rgba(255, 145, 0, 0.7)' : 'rgba(0, 230, 118, 0.55)');
    const selectedRing = isSelected ? `stroke="#00e5ff" stroke-width="2.5" stroke-dasharray="3,3"` : '';

    const svg = `
      <div style="position: relative; width: 36px; height: 36px; cursor: grab;">
        <svg viewBox="0 0 36 36" width="36" height="36" style="filter: drop-shadow(0 0 8px ${glowColor});">
          <circle cx="18" cy="18" r="15" fill="#0d1420" stroke="${strokeColor}" stroke-width="2.5" ${selectedRing} />
          <!-- Tree Canopy Icon -->
          <polygon points="18,6 25,16 11,16" fill="${strokeColor}" />
          <polygon points="18,12 27,23 9,23" fill="${strokeColor}" />
          <rect x="16" y="23" width="4" height="6" fill="#8d6e63" />
        </svg>
        <div style="position: absolute; top: -14px; left: -18px; width: 72px; text-align: center; font-size: 9px; font-weight: 800; font-family: monospace; color: #fff; text-shadow: 0 1px 3px #000; pointer-events: none;">
          ${nodeId.replace('NODE-ARBOR-', 'N-')}
        </div>
      </div>
    `;
    return L.divIcon({ html: svg, className: 'custom-tree-icon', iconSize: [36, 36], iconAnchor: [18, 18] });
  }

  function createGatewayIcon() {
    const svg = `
      <div style="position: relative; width: 40px; height: 40px;">
        <svg viewBox="0 0 40 40" width="40" height="40" style="filter: drop-shadow(0 0 9px rgba(179, 136, 255, 0.85));">
          <polygon points="20,4 36,36 4,36" fill="#140f24" stroke="#b388ff" stroke-width="2" />
          <circle cx="20" cy="14" r="3.5" fill="#b388ff" />
          <line x1="20" y1="17" x2="20" y2="36" stroke="#b388ff" stroke-width="2" />
          <line x1="13" y1="27" x2="27" y2="27" stroke="#b388ff" stroke-width="1.5" />
        </svg>
        <div style="position: absolute; top: -13px; left: -26px; width: 92px; text-align: center; font-size: 9px; font-weight: 800; font-family: monospace; color: #e1bee7; text-shadow: 0 1px 3px #000;">
          GW CUMBRE (1.120m)
        </div>
      </div>
    `;
    return L.divIcon({ html: svg, className: 'custom-gw-icon', iconSize: [40, 40], iconAnchor: [20, 20] });
  }

  function createAuthorityIcon(name) {
    const svg = `
      <div style="position: relative; width: 44px; height: 44px;">
        <svg viewBox="0 0 44 44" width="44" height="44" style="filter: drop-shadow(0 0 10px rgba(0, 176, 255, 0.85));">
          <rect x="5" y="10" width="34" height="30" rx="4" fill="#0b172a" stroke="#00b0ff" stroke-width="2" />
          <!-- Helipad H inside box -->
          <circle cx="22" cy="25" r="11" fill="none" stroke="#00e5ff" stroke-width="1.5" stroke-dasharray="2,2" />
          <text x="22" y="29.5" font-size="13" font-weight="900" fill="#00e5ff" text-anchor="middle" font-family="sans-serif">H</text>
        </svg>
        <div style="position: absolute; top: -14px; left: -32px; width: 108px; text-align: center; font-size: 9px; font-weight: 800; font-family: monospace; color: #80d8ff; text-shadow: 0 1px 3px #000;">
          DOCK &amp; CUARTEL
        </div>
      </div>
    `;
    return L.divIcon({ html: svg, className: 'custom-authority-icon', iconSize: [44, 44], iconAnchor: [22, 22] });
  }

  function createDroneIcon(headingDeg, status) {
    const isTargeting = (status === 'RECON_ORBIT' || status === 'TRANSIT_OUT' || status === 'MANUAL_PILOT');
    const glowColor = isTargeting ? '#ff3b14' : '#00e5ff';
    const svg = `
      <div style="position: relative; width: 42px; height: 42px; transform: rotate(${headingDeg}deg); transition: transform 0.2s linear;">
        <svg viewBox="0 0 42 42" width="42" height="42" style="filter: drop-shadow(0 0 9px ${glowColor});">
          <line x1="9" y1="9" x2="33" y2="33" stroke="${glowColor}" stroke-width="2.5" />
          <line x1="33" y1="9" x2="9" y2="33" stroke="${glowColor}" stroke-width="2.5" />
          <circle cx="9" cy="9" r="4.5" fill="none" stroke="${glowColor}" stroke-width="1.5" />
          <circle cx="33" cy="9" r="4.5" fill="none" stroke="${glowColor}" stroke-width="1.5" />
          <circle cx="9" cy="33" r="4.5" fill="none" stroke="${glowColor}" stroke-width="1.5" />
          <circle cx="33" cy="33" r="4.5" fill="none" stroke="${glowColor}" stroke-width="1.5" />
          <circle cx="21" cy="21" r="7" fill="#090f1a" stroke="${glowColor}" stroke-width="2" />
          <polygon points="21,9 25,16 17,16" fill="${glowColor}" />
        </svg>
        <div style="position: absolute; top: -14px; left: -12px; width: 66px; text-align: center; font-size: 9px; font-weight: 800; font-family: monospace; color: #fff; text-shadow: 0 1px 3px #000;">
          DRON &lt;45s
        </div>
      </div>
    `;
    return L.divIcon({ html: svg, className: 'custom-drone-icon', iconSize: [42, 42], iconAnchor: [21, 21] });
  }

  function createRoadblockIcon(name) {
    const svg = `
      <div style="position: relative; width: 32px; height: 32px;">
        <svg viewBox="0 0 32 32" width="32" height="32" style="filter: drop-shadow(0 0 7px rgba(76, 175, 80, 0.85));">
          <circle cx="16" cy="16" r="13" fill="#0e2412" stroke="#4caf50" stroke-width="2" />
          <rect x="8" y="14" width="16" height="4" fill="#ffeb3b" />
        </svg>
      </div>
    `;
    return L.divIcon({ html: svg, className: 'custom-roadblock-icon', iconSize: [32, 32], iconAnchor: [16, 16] });
  }

  // -------------------------------------------------------------
  // 4. MAP UPDATE LOGIC (DRAGGABLE NODES, SITE SURVEY, STAR LORAWAN)
  // -------------------------------------------------------------
  function renderMapLayers(data) {
    const showNodes = document.getElementById('layerNodes').checked;
    const showLora = document.getElementById('layerLoraMesh').checked;
    const show500m = document.getElementById('layerCoverage500m').checked;
    const show1000m = document.getElementById('layerCoverage1000m').checked;
    const showBase = document.getElementById('layerAuthorityBase').checked;
    const showDrone = document.getElementById('layerDroneFlight').checked;
    const showSpread = document.getElementById('layerFireSpread').checked;
    const showRoute = document.getElementById('layerBomberosRoute').checked;
    const showRoadblocks = document.getElementById('layerCencoRoadblocks').checked;

    // 1. Gateway Cumbre
    const gw = data.gateway;
    if (gw) {
      if (!gatewayMarker) {
        gatewayMarker = L.marker(gw.coords, { icon: createGatewayIcon() }).addTo(map);
        gatewayMarker.bindPopup(`
          <div style="font-family: Outfit, sans-serif; font-size: 12px; color: #111;">
            <b style="color: #6a1b9a; font-size: 13px;">📡 ${gw.name}</b><br>
            <b>Cota de Elevación:</b> ${gw.altitude_m} m (Línea de Vista Óptima)<br>
            <b>Enlace Backhaul:</b> ${gw.uplink}<br>
            <b>Paquetes Relayer:</b> ${gw.packets_relayed}<br>
            <b>Norma SUBTEL:</b> AU915 ISM (915–928 MHz)
          </div>
        `);
      } else {
        gatewayMarker.setLatLng(gw.coords);
        if (showLora && !map.hasLayer(gatewayMarker)) map.addLayer(gatewayMarker);
        if (!showLora && map.hasLayer(gatewayMarker)) map.removeLayer(gatewayMarker);
      }
    }

    // 2. Limpiar líneas LoRa Star y círculos Site Survey
    loraStarLines.forEach(l => map.removeLayer(l));
    loraStarLines.length = 0;
    siteSurvey500Circles.forEach(c => map.removeLayer(c));
    siteSurvey500Circles.length = 0;
    siteSurvey1000Circles.forEach(c => map.removeLayer(c));
    siteSurvey1000Circles.length = 0;

    // 3. Nodos Arbóreos (Arrastrables con Leaflet Drag & Drop)
    data.tree_nodes.forEach(node => {
      const pos = [node.lat, node.lon];
      const alertLvl = node.inference ? node.inference.alert_level : 0;
      const isSelected = (node.node_id === selectedNodeId);

      // Crear o actualizar marcador
      if (!nodeMarkers[node.node_id]) {
        const marker = L.marker(pos, {
          icon: createTreeNodeIcon(node.node_id, alertLvl, isSelected),
          draggable: true
        }).addTo(map);

        marker.on('click', () => {
          selectedNodeId = node.node_id;
          updateDashboardUI(latestTelemetryData);
        });

        // Evento dragend: Reubicación de nodo en tiempo real
        marker.on('dragend', (e) => {
          const newPos = e.target.getLatLng();
          fetch('/api/node/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              node_id: node.node_id,
              lat: newPos.lat,
              lon: newPos.lng
            })
          })
          .then(res => res.json())
          .then(updated => {
            console.log(`[FLYBRIDGE] Nodo ${node.node_id} reubicado a:`, newPos.lat, newPos.lng);
            updateDashboardUI(updated);
          })
          .catch(err => console.error("Error al mover nodo", err));
        });

        marker.bindTooltip(`🌳 ${node.node_id} (${node.tree_species})<br>Temp: ${node.telemetry.sensor_temp_c}°C | CO2: ${node.telemetry.co2_ppm.toFixed(0)} ppm<br><i>Arrastra para reubicar en mapa</i>`, {
          direction: 'top',
          className: 'map-tooltip-safe'
        });

        nodeMarkers[node.node_id] = marker;
      } else {
        const marker = nodeMarkers[node.node_id];
        // Solo mover si no se está arrastrando en este instante
        if (!marker.isDragging && !marker._dragging) {
          marker.setLatLng(pos);
        }
        marker.setIcon(createTreeNodeIcon(node.node_id, alertLvl, isSelected));
        if (showNodes && !map.hasLayer(marker)) map.addLayer(marker);
        if (!showNodes && map.hasLayer(marker)) map.removeLayer(marker);
      }

      // Línea LoRaWAN Estrella Redundante hacia Gateway de cumbre
      if (showLora && gw) {
        const distKm = getDistanceKm(pos[0], pos[1], gw.coords[0], gw.coords[1]);
        const line = L.polyline([pos, gw.coords], {
          color: alertLvl >= 3 ? '#ff3b14' : '#00e5ff',
          weight: alertLvl >= 3 ? 2.5 : 1.5,
          opacity: alertLvl >= 3 ? 0.9 : 0.45,
          dashArray: alertLvl >= 3 ? 'none' : '3, 6'
        }).addTo(map);

        line.bindTooltip(`📡 Enlace LoRaWAN Estrella Redundante: ${node.node_id} ➔ ${gw.name}<br>Distancia: ${distKm.toFixed(2)} km | SUBTEL 915 MHz (100 mW)`, {
          sticky: true
        });
        loraStarLines.push(line);
      }

      // Site Survey: Anillos de Cobertura 500 m (separación inicial orientativa)
      if (show500m) {
        const c500 = L.circle(pos, {
          radius: 500,
          color: '#00e676',
          fillColor: '#00e676',
          fillOpacity: 0.05,
          weight: 1,
          dashArray: '3, 4'
        }).addTo(map);
        siteSurvey500Circles.push(c500);
      }

      // Site Survey: Anillos de Cobertura 1.000 m (alcance máximo en cuenca)
      if (show1000m) {
        const c1000 = L.circle(pos, {
          radius: 1000,
          color: '#00e5ff',
          fillColor: '#00e5ff',
          fillOpacity: 0.03,
          weight: 1,
          dashArray: '5, 5'
        }).addTo(map);
        siteSurvey1000Circles.push(c1000);
      }
    });

    // 4. Cuartel de Autoridades & Drone-in-a-Box
    const fac = data.docking_station.facility;
    if (fac) {
      if (!authorityMarker) {
        authorityMarker = L.marker(fac.coords, { icon: createAuthorityIcon(fac.name) }).addTo(map);
        authorityMarker.bindPopup(`
          <div style="font-family: Outfit, sans-serif; font-size: 12px; color: #111;">
            <b style="color: #0077c2; font-size: 13px;">🏢 ${fac.name}</b><br>
            <b>Recinto Oficial:</b> ${fac.security}<br>
            <b>Suministro Eléctrico:</b> ${fac.power_grid}<br>
            <b>Efectivos en Guardia:</b> ${fac.personnel_on_duty}<br>
            <b>Tiempo Apertura Compuerta:</b> &lt;45s
          </div>
        `);
      } else {
        if (showBase && !map.hasLayer(authorityMarker)) map.addLayer(authorityMarker);
        if (!showBase && map.hasLayer(authorityMarker)) map.removeLayer(authorityMarker);
      }
    }

    // 5. Dron Verificador y trayectoria con dinámica biológica
    const drone = data.verifier_drone;
    if (drone) {
      const dronePos = [drone.latitude, drone.longitude];
      if (!droneMarker) {
        droneMarker = L.marker(dronePos, {
          icon: createDroneIcon(drone.heading_deg, drone.status)
        }).addTo(map);
      } else {
        droneMarker.setLatLng(dronePos);
        droneMarker.setIcon(createDroneIcon(drone.heading_deg, drone.status));
        if (showDrone && !map.hasLayer(droneMarker)) map.addLayer(droneMarker);
        if (!showDrone && map.hasLayer(droneMarker)) map.removeLayer(droneMarker);
      }

      if (drone.trajectory && drone.trajectory.length > 1) {
        if (!droneTrailLine) {
          droneTrailLine = L.polyline(drone.trajectory, {
            color: '#ffc400',
            weight: 2.2,
            opacity: 0.8,
            dashArray: '4, 6'
          }).addTo(map);
        } else {
          droneTrailLine.setLatLngs(drone.trajectory);
          if (showDrone && !map.hasLayer(droneTrailLine)) map.addLayer(droneTrailLine);
          if (!showDrone && map.hasLayer(droneTrailLine)) map.removeLayer(droneTrailLine);
        }
      }
    }

    // 6. Cono de Propagación del Fuego (Huygens Ellipse)
    if (fireSpreadPolygon) {
      map.removeLayer(fireSpreadPolygon);
      fireSpreadPolygon = null;
    }
    const bDisp = data.bomberos_dispatch;
    if (showSpread && bDisp && bDisp.fire_behavior && data.active_hotspots && data.active_hotspots.length > 0) {
      const targetCoords = bDisp.target_coordinates.decimal;
      const headCoords = bDisp.fire_behavior.projected_head_coords_30m;
      const angleRad = (bDisp.fire_behavior.spread_heading_deg * Math.PI) / 180.0;
      const flankDistDeg = 0.0014;

      const p1 = targetCoords;
      const p2 = [headCoords[0] + flankDistDeg * Math.sin(angleRad), headCoords[1] - flankDistDeg * Math.cos(angleRad)];
      const p3 = headCoords;
      const p4 = [headCoords[0] - flankDistDeg * Math.sin(angleRad), headCoords[1] + flankDistDeg * Math.cos(angleRad)];

      fireSpreadPolygon = L.polygon([p1, p2, p3, p4], {
        color: '#ff3b14',
        fillColor: '#ff9100',
        fillOpacity: 0.28,
        weight: 1.8,
        dashArray: '5, 5'
      }).addTo(map);

      fireSpreadPolygon.bindTooltip(`🔥 CONO DE PROPAGACIÓN HUYGENS (30 min): ${bDisp.fire_behavior.threatened_area_hectares_30m} ha`, {
        sticky: true
      });
    }

    // 7. Ruta de Acceso Vehicular de Bomberos
    if (bomberosRouteLine) {
      map.removeLayer(bomberosRouteLine);
      bomberosRouteLine = null;
    }
    if (showRoute && fac && bDisp && data.active_hotspots && data.active_hotspots.length > 0) {
      const startP = fac.coords;
      const targetP = bDisp.target_coordinates.decimal;
      const midP = [-33.4090, -70.5520];
      bomberosRouteLine = L.polyline([startP, midP, targetP], {
        color: '#d50000',
        weight: 3.5,
        opacity: 0.85,
        dashArray: '6, 6'
      }).addTo(map);
      bomberosRouteLine.bindTooltip(`🚒 RUTA CARROS BOMBA: ${bDisp.access_route.road_name} (ETA: ${bDisp.access_route.estimated_arrival_time_min} min)`, {
        sticky: true
      });
    }

    // 8. Cortes de Ruta CENCO
    const cenco = data.cenco_dispatch;
    if (showRoadblocks && cenco && cenco.perimeter_containment_plan && data.active_hotspots && data.active_hotspots.length > 0) {
      if (roadblockMarkers.length === 0) {
        cenco.perimeter_containment_plan.checkpoints.forEach(cp => {
          const m = L.marker(cp.coords, { icon: createRoadblockIcon(cp.name) }).addTo(map);
          m.bindTooltip(`🚧 ${cp.name}<br>${cp.instruction}`, { sticky: true });
          roadblockMarkers.push(m);
        });
      }
    } else if (!data.active_hotspots || data.active_hotspots.length === 0) {
      roadblockMarkers.forEach(m => map.removeLayer(m));
      roadblockMarkers.length = 0;
    }
  }

  function getDistanceKm(lat1, lon1, lat2, lon2) {
    const R = 6371.0;
    const dLat = (lat2 - lat1) * Math.PI / 180.0;
    const dLon = (lon2 - lon1) * Math.PI / 180.0;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180.0) * Math.cos(lat2 * Math.PI / 180.0) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  // -------------------------------------------------------------
  // 5. WIND VECTOR CANVAS ANIMATION
  // -------------------------------------------------------------
  const windCanvas = document.getElementById('windCanvas');
  const windCtx = windCanvas.getContext('2d');
  let particles = [];
  const NUM_PARTICLES = 65;

  function resizeCanvas() {
    windCanvas.width = windCanvas.parentElement.clientWidth;
    windCanvas.height = windCanvas.parentElement.clientHeight;
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  for (let i = 0; i < NUM_PARTICLES; i++) {
    particles.push({
      x: Math.random() * windCanvas.width,
      y: Math.random() * windCanvas.height,
      length: 12 + Math.random() * 16,
      speed: 1.0 + Math.random() * 1.5,
      alpha: 0.2 + Math.random() * 0.4
    });
  }

  function drawWind() {
    windCtx.clearRect(0, 0, windCanvas.width, windCanvas.height);
    const windAngleRad = ((currentWind.direction_deg - 90) * Math.PI) / 180.0;
    const speedFactor = currentWind.speed_kmh / 25.0;

    windCtx.lineWidth = 1.5;
    particles.forEach(p => {
      windCtx.strokeStyle = `rgba(0, 229, 255, ${p.alpha})`;
      windCtx.beginPath();
      windCtx.moveTo(p.x, p.y);
      const tailX = p.x - Math.cos(windAngleRad) * p.length;
      const tailY = p.y - Math.sin(windAngleRad) * p.length;
      windCtx.lineTo(tailX, tailY);
      windCtx.stroke();

      p.x += Math.cos(windAngleRad) * p.speed * speedFactor;
      p.y += Math.sin(windAngleRad) * p.speed * speedFactor;
      if (p.x < 0) p.x = windCanvas.width;
      if (p.x > windCanvas.width) p.x = 0;
      if (p.y < 0) p.y = windCanvas.height;
      if (p.y > windCanvas.height) p.y = 0;
    });
    requestAnimationFrame(drawWind);
  }
  requestAnimationFrame(drawWind);

  // -------------------------------------------------------------
  // 6. FPV COCKPIT CANVAS & SYNTHETIC CAMERA STREAMING
  // -------------------------------------------------------------
  const fpvCanvas = document.getElementById('fpvCanvas');
  const fpvCtx = fpvCanvas ? fpvCanvas.getContext('2d') : null;
  let fpvFrameCount = 0;

  function renderFPVCanvas() {
    if (!fpvCtx) return;
    fpvFrameCount++;
    const w = fpvCanvas.width;
    const h = fpvCanvas.height;

    const drone = latestTelemetryData?.verifier_drone;
    const isThermal = (cameraMode === 'THERMAL');
    const isHotspotActive = latestTelemetryData?.active_hotspots && latestTelemetryData.active_hotspots.length > 0;
    const flightState = drone?.bio_flight_state || 'CRUISE_BIOMIMETIC';

    fpvCtx.clearRect(0, 0, w, h);

    if (isThermal) {
      // ── MODO TÉRMICO RADIOMÉTRICO FLIR ──
      // Paleta falso color FLIR (ironbow)
      const grad = fpvCtx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, '#0a0320'); // Cielo frío
      grad.addColorStop(0.48, '#1b0942');
      grad.addColorStop(0.52, '#38006b'); // Horizonte
      grad.addColorStop(1, '#120024'); // Tierra
      fpvCtx.fillStyle = grad;
      fpvCtx.fillRect(0, 0, w, h);

      // Líneas de terreno infrarrojo
      fpvCtx.strokeStyle = 'rgba(255, 100, 50, 0.25)';
      fpvCtx.lineWidth = 1;
      for (let i = 0; i < 4; i++) {
        const y = h * 0.55 + i * 22;
        fpvCtx.beginPath();
        fpvCtx.moveTo(0, y);
        fpvCtx.quadraticCurveTo(w * 0.5, y + 10 * Math.sin((fpvFrameCount + i * 20) * 0.05), w, y);
        fpvCtx.stroke();
      }

      // Si hay foco activo: Mancha de calor radiante con parpadeo
      if (isHotspotActive) {
        const heatX = w * 0.5 + Math.sin(fpvFrameCount * 0.03) * 15;
        const heatY = h * 0.52 + Math.cos(fpvFrameCount * 0.04) * 8;
        const heatRadius = 38 + Math.sin(fpvFrameCount * 0.12) * 5;

        const radial = fpvCtx.createRadialGradient(heatX, heatY, 3, heatX, heatY, heatRadius);
        radial.addColorStop(0, '#ffffff'); // Núcleo súper caliente >540°C
        radial.addColorStop(0.25, '#ffee55');
        radial.addColorStop(0.55, '#ff3b14');
        radial.addColorStop(0.85, '#990033');
        radial.addColorStop(1, 'transparent');

        fpvCtx.fillStyle = radial;
        fpvCtx.beginPath();
        fpvCtx.arc(heatX, heatY, heatRadius, 0, Math.PI * 2);
        fpvCtx.fill();

        // Pluma de calor ascendente
        fpvCtx.fillStyle = 'rgba(255, 80, 0, 0.15)';
        fpvCtx.beginPath();
        fpvCtx.moveTo(heatX - 18, heatY);
        fpvCtx.lineTo(heatX - 35, heatY - 55);
        fpvCtx.lineTo(heatX + 35, heatY - 55);
        fpvCtx.lineTo(heatX + 18, heatY);
        fpvCtx.fill();
      }

      // Barra de escala de temperatura FLIR en lateral derecho
      const barX = w - 18;
      const barGrad = fpvCtx.createLinearGradient(0, 20, 0, h - 20);
      barGrad.addColorStop(0, '#ffffff');
      barGrad.addColorStop(0.2, '#ffff00');
      barGrad.addColorStop(0.5, '#ff3b14');
      barGrad.addColorStop(0.8, '#800080');
      barGrad.addColorStop(1, '#000033');
      fpvCtx.fillStyle = barGrad;
      fpvCtx.fillRect(barX, 20, 8, h - 40);

    } else {
      // ── MODO ÓPTICO 4K FORENSE CON ZOOM ──
      // Cielo diurno
      const skyGrad = fpvCtx.createLinearGradient(0, 0, 0, h * 0.5);
      skyGrad.addColorStop(0, '#10223d');
      skyGrad.addColorStop(1, '#3b6287');
      fpvCtx.fillStyle = skyGrad;
      fpvCtx.fillRect(0, 0, w, h * 0.5);

      // Terreno y dosel forestal
      const groundGrad = fpvCtx.createLinearGradient(0, h * 0.5, 0, h);
      groundGrad.addColorStop(0, '#1f2e1a');
      groundGrad.addColorStop(1, '#0e180d');
      fpvCtx.fillStyle = groundGrad;
      fpvCtx.fillRect(0, h * 0.5, w, h * 0.5);

      // Pista forestal / camino de maicillo
      fpvCtx.fillStyle = '#4a3f2f';
      fpvCtx.beginPath();
      fpvCtx.moveTo(w * 0.48, h * 0.5);
      fpvCtx.lineTo(w * 0.52, h * 0.5);
      fpvCtx.lineTo(w * 0.68, h);
      fpvCtx.lineTo(w * 0.32, h);
      fpvCtx.closePath();
      fpvCtx.fill();

      // Siluetas de árboles nativos (Litre, Quillay, Boldo)
      fpvCtx.fillStyle = '#162814';
      for (let i = 0; i < 16; i++) {
        const tx = (i * 42 + fpvFrameCount * 0.4) % (w + 40) - 20;
        const ty = h * 0.52 + (i % 3) * 18;
        fpvCtx.beginPath();
        fpvCtx.arc(tx, ty, 14, 0, Math.PI * 2);
        fpvCtx.fill();
      }

      // Si hay foco: Columna de humo real con partículas
      if (isHotspotActive) {
        fpvCtx.fillStyle = 'rgba(70, 75, 80, 0.45)';
        for (let p = 0; p < 7; p++) {
          const px = w * 0.52 + Math.sin(fpvFrameCount * 0.04 + p) * (12 + p * 6);
          const py = h * 0.5 - p * 15;
          const pr = 10 + p * 7;
          fpvCtx.beginPath();
          fpvCtx.arc(px, py, pr, 0, Math.PI * 2);
          fpvCtx.fill();
        }
      }
    }

    requestAnimationFrame(renderFPVCanvas);
  }
  requestAnimationFrame(renderFPVCanvas);

  // -------------------------------------------------------------
  // 7. UI UPDATE & REAL-TIME DATA BINDING
  // -------------------------------------------------------------
  function updateDashboardUI(data) {
    if (!data) return;
    latestTelemetryData = data;
    currentWind = data.environment?.wind || currentWind;

    // Header Badges
    document.getElementById('badgeWind').textContent = `${currentWind.speed_kmh} km/h ↗ ${currentWind.cardinal || 'NE'}`;
    document.getElementById('badgeNodes').textContent = `${data.tree_nodes.length} INDEPENDIENTES (915MHz)`;
    document.getElementById('badgeGateway').textContent = data.gateway?.status.includes('SATELLITE') ? 'STARLINK ACTIVO' : '4G ACTIVO';

    const drone = data.verifier_drone;
    const droneStatus = drone.status;
    const badgeDock = document.getElementById('badgeDock');
    if (droneStatus === 'DOCK_CHARGING') {
      badgeDock.textContent = 'STANDBY (<45s)';
      badgeDock.className = 'badge-value';
    } else {
      badgeDock.textContent = `VUELO ACTIVO (${drone.launch_elapsed_sec.toFixed(0)}s)`;
      badgeDock.className = 'badge-value alert-pulse';
    }

    // ── LEFT SIDEBAR: TREE NODES LIST ──
    const nodesListEl = document.getElementById('treeNodesList');
    nodesListEl.innerHTML = data.tree_nodes.map(n => {
      const isAlert = n.inference && n.inference.alert_level >= 3;
      const isSel = (n.node_id === selectedNodeId);
      const cardClass = `tree-node-card ${isSel ? 'active' : ''} ${isAlert ? 'alert-card' : ''}`;
      return `
        <div class="${cardClass}" onclick="selectNode('${n.node_id}')">
          <div>
            <div class="tn-name">${n.node_id}</div>
            <div class="tn-species">${n.tree_species}</div>
          </div>
          <div class="tn-metrics">
            <div style="color: ${n.telemetry.sensor_temp_c > 35 ? '#ff3b14' : '#00e676'}; font-weight:800;">
              ${n.telemetry.sensor_temp_c.toFixed(1)}°C
            </div>
            <div style="color: #9aa8c2;">CO2: ${n.telemetry.co2_ppm.toFixed(0)}</div>
          </div>
        </div>
      `;
    }).join('');

    // ── LEFT SIDEBAR: INSPECT NODE (NEUROFLY EDGE) ──
    const inspected = data.tree_nodes.find(n => n.node_id === selectedNodeId) || data.tree_nodes[2];
    if (inspected && inspected.inference) {
      document.getElementById('inspectNodeName').textContent = `${inspected.node_id} · ${inspected.tree_species}`;
      const alertLvl = inspected.inference.alert_level;
      const statusPill = document.getElementById('inspectNodeStatus');
      statusPill.textContent = alertLvl >= 3 ? 'ALERTA IGNICIÓN' : (alertLvl >= 2 ? 'SOSPECHA' : 'NORMAL');
      statusPill.className = `status-pill ${alertLvl >= 3 ? 'alert' : 'normal'}`;

      // Lóbulo Olfativo
      const olf = inspected.inference.olfactory_lobe;
      document.getElementById('valGasDcDt').textContent = `${olf.d_co2_dt_ppm_s >= 0 ? '+' : ''}${olf.d_co2_dt_ppm_s.toFixed(2)} ppm/s`;
      const gasPct = Math.min(100, Math.max(10, Math.round(olf.gas_plume_score * 100)));
      document.getElementById('barGasRate').style.width = `${gasPct}%`;

      // Flujo Térmico Convectivo
      const th = inspected.inference.thermal_convective_array;
      document.getElementById('valConvectiveGrad').textContent = `Δ=+${th.convective_gradient_c.toFixed(1)} °C`;
      const thPct = Math.min(100, Math.max(10, Math.round(th.thermal_anomaly_score * 100)));
      document.getElementById('barConvectiveGrad').style.width = `${thPct}%`;

      // Filtro Neuromórfico
      const nf = inspected.inference.neuromorphic_filter;
      document.getElementById('filterExplanation').textContent = nf.rejection_reason;

      // Paquete LoRa Compacto (<50 bytes)
      if (inspected.lora_tx && inspected.lora_tx.packet_hex) {
        document.getElementById('loraHexBox').textContent = inspected.lora_tx.packet_hex;
        document.getElementById('loraSizeTag').textContent = `${inspected.lora_tx.packet_size_bytes} BYTES (<50 B)`;
      }
      document.getElementById('lpId').textContent = inspected.node_num;
      document.getElementById('lpTemp').textContent = `${inspected.telemetry.sensor_temp_c.toFixed(1)}°C`;
      document.getElementById('lpDcdt').textContent = `${olf.d_co2_dt_ppm_s.toFixed(1)}`;
      document.getElementById('lpWind').textContent = `${inspected.telemetry.wind_speed_kmh} km/h`;
      document.getElementById('lpConf').textContent = `${inspected.inference.confidence_pct}%`;
      document.getElementById('lpBat').textContent = `${inspected.battery_pct}%`;

      // Distancia al Gateway de cumbre
      if (data.gateway) {
        const gwDist = getDistanceKm(inspected.lat, inspected.lon, data.gateway.coords[0], data.gateway.coords[1]);
        const lpGwDistEl = document.getElementById('lpGwDist');
        if (lpGwDistEl) lpGwDistEl.textContent = `${gwDist.toFixed(1)} km`;
      }
    }

    // ── FPV COCKPIT & PILOT OSD ──
    const hudFlightState = document.getElementById('hudFlightState');
    if (hudFlightState) {
      hudFlightState.textContent = `ESTADO BIOLÓGICO: ${drone.bio_flight_state || 'CRUISE_BIOMIMETIC'} · DINÁMICA NEUROFLY`;
    }

    const osdSpeedVal = document.getElementById('osdSpeedVal');
    if (osdSpeedVal) osdSpeedVal.textContent = drone.speed_kmh.toFixed(1);

    const osdAltVal = document.getElementById('osdAltVal');
    if (osdAltVal) osdAltVal.textContent = drone.altitude_m.toFixed(0);

    const osdHeadingVal = document.getElementById('osdHeadingVal');
    if (osdHeadingVal) osdHeadingVal.textContent = `${Math.round(drone.heading_deg).toString().padStart(3, '0')}°`;

    const osdBatteryVal = document.getElementById('osdBatteryVal');
    if (osdBatteryVal) osdBatteryVal.textContent = `${drone.battery_pct.toFixed(0)}%`;

    const osdHashVal = document.getElementById('osdHashVal');
    if (osdHashVal && drone.optical_forensics_4k) {
      osdHashVal.textContent = (drone.optical_forensics_4k.evidence_hash_sha256 || 'SHA-256-PENDING').substring(0, 16);
    }

    const osdGimbalPitch = document.getElementById('osdGimbalPitch');
    if (osdGimbalPitch) osdGimbalPitch.textContent = `${drone.gimbal_pitch_deg || fpvGimbalPitch}°`;

    const osdGimbalYaw = document.getElementById('osdGimbalYaw');
    if (osdGimbalYaw) osdGimbalYaw.textContent = `${drone.gimbal_yaw_deg || 0}°`;

    const osdZoomLevel = document.getElementById('osdZoomLevel');
    if (osdZoomLevel) osdZoomLevel.textContent = `${(drone.zoom_optical || fpvZoom).toFixed(1)}x`;

    const osdCrosshairTemp = document.getElementById('osdCrosshairTemp');
    if (osdCrosshairTemp) {
      if (cameraMode === 'THERMAL') {
        const coreT = drone.thermal_flir?.core_temp_c || 542.0;
        osdCrosshairTemp.textContent = `${coreT.toFixed(1)} °C`;
      } else {
        osdCrosshairTemp.textContent = '4K FORENSE';
      }
    }

    // Horizonte Artificial OSD
    const horizonLine = document.getElementById('horizonLine');
    if (horizonLine) {
      const bank = drone.bio_flight_state === 'SACCADE_TURN' ? 18.0 : (drone.status === 'RECON_ORBIT' ? 12.0 : 0.0);
      horizonLine.style.transform = `rotate(${-bank}deg) translateY(0px)`;
    }

    // Capa de Detecciones Forenses (solo en modo óptico)
    const detectionsLayer = document.getElementById('osdDetectionsLayer');
    if (detectionsLayer) {
      detectionsLayer.style.display = (cameraMode === 'OPTICAL') ? 'block' : 'none';
    }

    // ── RIGHT SIDEBAR: BOMBEROS TAB ──
    const bDisp = data.bomberos_dispatch;
    if (bDisp) {
      document.getElementById('bTargetNode').textContent = bDisp.target_node_id;
      document.getElementById('bCoords').textContent = `${bDisp.target_coordinates.decimal[0].toFixed(4)}, ${bDisp.target_coordinates.decimal[1].toFixed(4)}`;
      document.getElementById('bRouteName').textContent = bDisp.access_route.road_name;
      document.getElementById('bSurface').textContent = bDisp.access_route.surface_type;
      document.getElementById('bGate').textContent = bDisp.access_route.entry_gate;
      document.getElementById('bDist').textContent = `${bDisp.access_route.distance_km} km`;
      document.getElementById('bEta').textContent = `${bDisp.access_route.estimated_arrival_time_min} min`;
      document.getElementById('bUnits').textContent = bDisp.access_route.recommended_vehicles;

      if (bDisp.fire_behavior) {
        document.getElementById('bSpreadRate').textContent = `${bDisp.fire_behavior.head_rate_m_min} m/min`;
        document.getElementById('bSpreadDir').textContent = `↗ ${bDisp.fire_behavior.cardinal_direction} (${bDisp.fire_behavior.spread_heading_deg}°)`;
        document.getElementById('bFlameLen').textContent = `${bDisp.fire_behavior.flame_length_est_m} m`;
        document.getElementById('bArea30m').textContent = `${bDisp.fire_behavior.threatened_area_hectares_30m} ha`;
        document.getElementById('bBehaviorText').textContent = bDisp.fire_behavior.behavior_summary;
      }
    }

    // ── RIGHT SIDEBAR: CARABINEROS CENCO TAB ──
    const cDisp = data.cenco_dispatch;
    if (cDisp) {
      document.getElementById('cencoCode').textContent = `CÓDIGO: ${cDisp.dispatch_code} · PRIORIDAD 1`;

      const fItemsEl = document.getElementById('forensicItemsList');
      if (cDisp.forensic_detections && cDisp.forensic_detections.length > 0) {
        fItemsEl.innerHTML = cDisp.forensic_detections.map(d => `
          <div class="forensic-card">
            <div class="fc-type">🚨 ${d.type} (${Math.round(d.confidence * 100)}%)</div>
            <div class="fc-desc">${d.description}</div>
            <div class="fc-coords">📍 Coords: ${d.coords[0].toFixed(4)}, ${d.coords[1].toFixed(4)}</div>
          </div>
        `).join('');
      } else {
        fItemsEl.innerHTML = `<div style="font-size:0.68rem; color:#62728f;">Sin detecciones sospechosas en el radio actual.</div>`;
      }

      const rbListEl = document.getElementById('roadblockList');
      if (cDisp.perimeter_containment_plan && cDisp.perimeter_containment_plan.checkpoints) {
        rbListEl.innerHTML = cDisp.perimeter_containment_plan.checkpoints.map(cp => `
          <div class="roadblock-card">
            <div class="rb-name">🚧 ${cp.name} (${cp.distance_from_fire_km} km)</div>
            <div class="rb-instruction">${cp.instruction}</div>
          </div>
        `).join('');
      }
    }

    // Renderizar capas GIS en mapa Leaflet
    renderMapLayers(data);
  }

  // -------------------------------------------------------------
  // 8. WEBSOCKET REAL-TIME STREAMING
  // -------------------------------------------------------------
  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log("[FLYBRIDGE] WebSocket conectado con éxito.");
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        updateDashboardUI(payload);
      } catch (e) {
        console.error("Error al decodificar telemetría", e);
      }
    };

    socket.onerror = () => {
      startRestPolling();
    };

    socket.onclose = () => {
      setTimeout(connectWebSocket, 3000);
    };
  }

  function startRestPolling() {
    setInterval(() => {
      fetch('/api/status')
        .then(res => res.json())
        .then(data => updateDashboardUI(data))
        .catch(err => console.error("Poll error", err));
    }, 1000);
  }

  connectWebSocket();

  // -------------------------------------------------------------
  // 9. INTERACTIVE DRONE PILOTING (D-PAD & KEYBOARD SHORTCUTS)
  // -------------------------------------------------------------
  function sendPilotCommand(cmd, extra = {}) {
    fetch('/api/drone/pilot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: cmd, ...extra })
    })
    .then(res => res.json())
    .then(r => {
      if (r.drone) {
        latestTelemetryData.verifier_drone = r.drone;
        updateDashboardUI(latestTelemetryData);
      }
    })
    .catch(err => console.error("Error en comando de pilotaje", err));
  }

  // D-pad button events
  document.getElementById('btnPilotFwd')?.addEventListener('click', () => sendPilotCommand('FORWARD', { speed_factor: 1.0 }));
  document.getElementById('btnPilotBack')?.addEventListener('click', () => sendPilotCommand('BACKWARD', { speed_factor: 1.0 }));
  document.getElementById('btnPilotLeft')?.addEventListener('click', () => sendPilotCommand('YAW_LEFT'));
  document.getElementById('btnPilotRight')?.addEventListener('click', () => sendPilotCommand('YAW_RIGHT'));
  document.getElementById('btnPilotHover')?.addEventListener('click', () => sendPilotCommand('HOVER'));

  document.getElementById('btnAltUp')?.addEventListener('click', () => sendPilotCommand('ALTITUDE_UP', { delta_alt_m: 5.0 }));
  document.getElementById('btnAltDown')?.addEventListener('click', () => sendPilotCommand('ALTITUDE_DOWN', { delta_alt_m: -5.0 }));
  document.getElementById('btnOrbitMode')?.addEventListener('click', () => sendPilotCommand('ORBIT'));

  // Return to Launch (RTL) buttons
  const triggerRTL = () => {
    fetch('/api/drone/rtl', { method: 'POST' })
      .then(res => res.json())
      .then(r => {
        alert("🏠 RETORNO A BASE (RTL) ACTIVADO: El dron verificador regresa de forma autónoma a la estación de despegue y recarga en el recinto oficial.");
        if (r.drone && latestTelemetryData) {
          latestTelemetryData.verifier_drone = r.drone;
          updateDashboardUI(latestTelemetryData);
        }
      });
  };

  document.getElementById('btnDroneRTLTop')?.addEventListener('click', triggerRTL);
  document.getElementById('btnDroneRTLHud')?.addEventListener('click', triggerRTL);
  document.getElementById('btnRTLPilot')?.addEventListener('click', triggerRTL);

  // Gimbal and Zoom sliders
  const sliderPitch = document.getElementById('sliderGimbalPitch');
  const txtPitch = document.getElementById('txtGimbalPitch');
  sliderPitch?.addEventListener('input', (e) => {
    fpvGimbalPitch = parseFloat(e.target.value);
    txtPitch.textContent = `${fpvGimbalPitch}°`;
    sendPilotCommand('GIMBAL', { pitch: fpvGimbalPitch, zoom: fpvZoom });
  });

  const sliderZoom = document.getElementById('sliderZoom');
  const txtZoom = document.getElementById('txtZoomVal');
  sliderZoom?.addEventListener('input', (e) => {
    fpvZoom = parseFloat(e.target.value);
    txtZoom.textContent = `${fpvZoom.toFixed(1)}x`;
    sendPilotCommand('GIMBAL', { pitch: fpvGimbalPitch, zoom: fpvZoom });
  });

  // Keyboard control listener (W/A/S/D / Arrows / Space / Q / E / H)
  window.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;

    const key = e.key.toLowerCase();
    if (key === 'w' || e.key === 'ArrowUp') {
      sendPilotCommand('FORWARD', { speed_factor: 1.0 });
      highlightPilotButton('btnPilotFwd');
    } else if (key === 's' || e.key === 'ArrowDown') {
      sendPilotCommand('BACKWARD', { speed_factor: 1.0 });
      highlightPilotButton('btnPilotBack');
    } else if (key === 'a' || e.key === 'ArrowLeft') {
      sendPilotCommand('YAW_LEFT');
      highlightPilotButton('btnPilotLeft');
    } else if (key === 'd' || e.key === 'ArrowRight') {
      sendPilotCommand('YAW_RIGHT');
      highlightPilotButton('btnPilotRight');
    } else if (key === ' ') {
      e.preventDefault();
      sendPilotCommand('HOVER');
      highlightPilotButton('btnPilotHover');
    } else if (key === 'q' || key === 'r') {
      sendPilotCommand('ALTITUDE_UP', { delta_alt_m: 5.0 });
    } else if (key === 'e' || key === 'f') {
      sendPilotCommand('ALTITUDE_DOWN', { delta_alt_m: -5.0 });
    } else if (key === 'h') {
      triggerRTL();
    }
  });

  function highlightPilotButton(btnId) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.style.boxShadow = '0 0 14px #00e5ff';
    setTimeout(() => { btn.style.boxShadow = ''; }, 200);
  }

  // -------------------------------------------------------------
  // 10. CAMERA MODE TOGGLE (OPTICAL 4K vs FLIR THERMAL)
  // -------------------------------------------------------------
  const btnCamOptical = document.getElementById('btnCamOptical');
  const btnCamThermal = document.getElementById('btnCamThermal');

  btnCamOptical?.addEventListener('click', () => {
    cameraMode = 'OPTICAL';
    btnCamOptical.classList.add('active');
    btnCamThermal.classList.remove('active');
  });

  btnCamThermal?.addEventListener('click', () => {
    cameraMode = 'THERMAL';
    btnCamThermal.classList.add('active');
    btnCamOptical.classList.remove('active');
  });

  // -------------------------------------------------------------
  // 11. NODE PRESET SELECTION & SITE SURVEY
  // -------------------------------------------------------------
  document.getElementById('selectNodePreset')?.addEventListener('change', (e) => {
    const presetName = e.target.value;
    fetch('/api/node/preset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ preset_name: presetName })
    })
    .then(res => res.json())
    .then(updated => {
      console.log(`[FLYBRIDGE] Disposición de nodos cambiada a: ${presetName}`);
      updateDashboardUI(updated);
    });
  });

  // Layer toggles update on change
  ['layerNodes', 'layerLoraMesh', 'layerCoverage500m', 'layerCoverage1000m', 'layerAuthorityBase', 'layerDroneFlight', 'layerFireSpread', 'layerBomberosRoute', 'layerCencoRoadblocks'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', () => {
      if (latestTelemetryData) renderMapLayers(latestTelemetryData);
    });
  });

  // -------------------------------------------------------------
  // 12. EXTINGUISH HOTSPOT & END SIMULATION DRILL
  // -------------------------------------------------------------
  document.getElementById('btnExtinguishHotspot')?.addEventListener('click', () => {
    fetch('/api/hotspot/clear', { method: 'POST' })
      .then(res => res.json())
      .then(updated => {
        alert("🧯 FOCO EXTINGUIDO: El simulacro de ignición ha concluido. Se han restablecido los baselines de temperatura y CO2 en los nodos arbóreos.");
        updateDashboardUI(updated);
      });
  });

  // -------------------------------------------------------------
  // 13. GLOBAL ACTIONS: TRIGGER, LAUNCH, FEEDBACK
  // -------------------------------------------------------------
  window.selectNode = function(nodeId) {
    selectedNodeId = nodeId;
    if (latestTelemetryData) updateDashboardUI(latestTelemetryData);
  };

  // Tabs switching (Bomberos vs CENCO)
  const tabBomberos = document.getElementById('tabBomberos');
  const tabCenco = document.getElementById('tabCenco');
  const contentBomberos = document.getElementById('contentBomberos');
  const contentCenco = document.getElementById('contentCenco');

  tabBomberos?.addEventListener('click', () => {
    tabBomberos.classList.add('active');
    tabCenco.classList.remove('active');
    contentBomberos.classList.add('active');
    contentCenco.classList.remove('active');
  });

  tabCenco?.addEventListener('click', () => {
    tabCenco.classList.add('active');
    tabBomberos.classList.remove('active');
    contentCenco.classList.add('active');
    contentBomberos.classList.remove('active');
  });

  // Action: Simular Foco
  document.getElementById('btnSimulateIgnition')?.addEventListener('click', () => {
    fetch('/api/node/trigger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_id: selectedNodeId || 'NODE-ARBOR-03', peak_temp_c: 68.0 })
    }).then(res => res.json()).then(r => {
      alert(`⚡ Ignición simulada en ${selectedNodeId}. Inferencia NeuroFly Edge activada, transmisión LoRa 915MHz emitida y despegue de Drone-in-a-Box iniciado (<45s).`);
    });
  });

  // Action: Despegar Dron
  document.getElementById('btnLaunchDroneManual')?.addEventListener('click', () => {
    fetch('/api/drone/launch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_node_id: selectedNodeId || 'NODE-ARBOR-03' })
    }).then(res => res.json()).then(r => {
      alert(`🚀 Despegue de emergencia activado desde ${r.facility_name}. Dron Verificador en ruta a ${r.target_node}.`);
    });
  });

  // Action: Feedback Human-in-the-Loop
  document.getElementById('btnConfirmWildfire')?.addEventListener('click', () => {
    fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ incident_id: selectedNodeId, verdict: 'CONFIRMADO_INCENDIO', operator_notes: 'Verificado por Bomberos y Dron' })
    }).then(r => alert("✅ Foco confirmado. Se refuerzan los pesos sinápticos del lóbulo olfativo."));
  });

  document.getElementById('btnMarkFalsePositive')?.addEventListener('click', () => {
    fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ incident_id: selectedNodeId, verdict: 'FALSO_POSITIVO', operator_notes: 'Falso positivo térmico solar' })
    }).then(r => alert("❌ Falso positivo registrado. Se eleva el umbral de discriminación solar."));
  });

  // -------------------------------------------------------------
  // 14. MODALS: BOMBEROS, CENCO & SUBTEL CHILE
  // -------------------------------------------------------------
  const modalB = document.getElementById('bomberosModal');
  const modalC = document.getElementById('cencoModal');
  const modalSubtel = document.getElementById('subtelModal');

  document.getElementById('btnOpenBomberosModal')?.addEventListener('click', () => {
    renderBomberosModal();
    modalB.classList.add('open');
  });

  document.getElementById('btnOpenCencoModal')?.addEventListener('click', () => {
    renderCencoModal();
    modalC.classList.add('open');
  });

  document.getElementById('btnOpenSubtelModal')?.addEventListener('click', () => {
    modalSubtel.classList.add('open');
  });

  document.getElementById('btnCloseBomberosModal')?.addEventListener('click', () => modalB.classList.remove('open'));
  document.getElementById('btnCloseCencoModal')?.addEventListener('click', () => modalC.classList.remove('open'));
  document.getElementById('btnCloseSubtelModal')?.addEventListener('click', () => modalSubtel.classList.remove('open'));
  document.getElementById('btnOkSubtel')?.addEventListener('click', () => modalSubtel.classList.remove('open'));

  document.getElementById('btnDispatchBomberosDirect')?.addEventListener('click', () => {
    renderBomberosModal();
    modalB.classList.add('open');
  });

  document.getElementById('btnExportProsecutorDossier')?.addEventListener('click', () => {
    renderCencoModal();
    modalC.classList.add('open');
  });

  document.getElementById('btnDispatchFinalBomberos')?.addEventListener('click', () => {
    alert("🚒 DESPACHO OFICIAL TRANSMITIDO A CENTRAL DE ALARMAS DE BOMBEROS (132). Unidades B-14 y BF-2 en camino.");
    modalB.classList.remove('open');
  });

  document.getElementById('btnSendProsecutorFinal')?.addEventListener('click', () => {
    alert("⚖️ CARPETA INVESTIGATIVA FORENSE ENVIADA AL MINISTERIO PÚBLICO (FISCALÍA). Cadena de custodia SHA-256 registrada.");
    modalC.classList.remove('open');
  });

  function renderBomberosModal() {
    const b = latestTelemetryData?.bomberos_dispatch;
    if (!b) return;
    const body = document.getElementById('bomberosModalBody');
    body.innerHTML = `
      <div style="background: rgba(213,0,0,0.1); border: 1px solid rgba(213,0,0,0.3); padding: 0.75rem; border-radius: 6px;">
        <h3 style="color: #ff5252; margin-bottom: 0.3rem;">🚨 FICHA TÁCTICA DE INCENDIO FORESTAL — COMANDO DE INCIDENTES</h3>
        <div><b>Foco:</b> ${b.target_node_id} | <b>Sector:</b> ${b.target_coordinates.sector_name}</div>
        <div><b>Coordenadas WGS84:</b> ${b.target_coordinates.wgs84_formatted} (${b.target_coordinates.decimal.join(', ')})</div>
      </div>
      <div>
        <h4 style="color: #ffeb3b; margin-top: 0.5rem;">🛣️ RUTA VEHICULAR MÁS EXPEDITA:</h4>
        <div>• <b>Camino:</b> ${b.access_route.road_name}</div>
        <div>• <b>Superficie:</b> ${b.access_route.surface_type}</div>
        <div>• <b>Portón de Acceso:</b> ${b.access_route.entry_gate}</div>
        <div>• <b>Distancia Total:</b> ${b.access_route.distance_km} km | <b>ETA Estimado:</b> ${b.access_route.estimated_arrival_time_min} min</div>
        <div>• <b>Material Mayor:</b> ${b.access_route.recommended_vehicles}</div>
      </div>
      <div>
        <h4 style="color: #ff9100; margin-top: 0.5rem;">🔥 COMPORTAMIENTO Y PROPAGACIÓN DEL FUEGO:</h4>
        <div>• <b>Velocidad Frente de Avance:</b> ${b.fire_behavior.head_rate_m_min} m/min hacia el ${b.fire_behavior.cardinal_direction} (${b.fire_behavior.spread_heading_deg}°)</div>
        <div>• <b>Longitud Estimada de Llama:</b> ${b.fire_behavior.flame_length_est_m} m</div>
        <div>• <b>Proyección de Área a 30 min:</b> ${b.fire_behavior.threatened_area_hectares_30m} hectáreas comprometidas</div>
        <div>• <b>Estrategia Recomendada:</b> ${b.recommended_strategy}</div>
      </div>
      <div>
        <h4 style="color: #00e5ff; margin-top: 0.5rem;">💧 FUENTES DE ABASTECIMIENTO DE AGUA:</h4>
        ${b.tactical_water_sources.map(w => `<div>• <b>${w.name}:</b> ${w.capacity_liters.toLocaleString()} L (${w.type}) a ${w.distance_km} km</div>`).join('')}
      </div>
    `;
  }

  function renderCencoModal() {
    const c = latestTelemetryData?.cenco_dispatch;
    if (!c) return;
    const body = document.getElementById('cencoModalBody');
    body.innerHTML = `
      <div style="background: rgba(27,94,32,0.15); border: 1px solid rgba(76,175,80,0.4); padding: 0.75rem; border-radius: 6px;">
        <h3 style="color: #81c784; margin-bottom: 0.3rem;">👮 CARABINEROS DE CHILE — CENCO / UNIDAD FORENSE</h3>
        <div><b>Código Despacho:</b> ${c.dispatch_code} | <b>Timestamp UTC:</b> ${c.timestamp_utc}</div>
        <div><b>Hash de Integridad Probatoria:</b> <span style="font-family:monospace; color:#a5d6a7;">${c.evidence_integrity_hash}</span></div>
      </div>
      <div>
        <h4 style="color: #ff9100; margin-top: 0.5rem;">📷 HALLAZGOS PERICIALES ÓPTICOS 4K:</h4>
        ${c.forensic_detections.map(d => `
          <div style="background: rgba(0,0,0,0.3); padding: 0.4rem; border-radius: 4px; margin-bottom: 0.3rem;">
            <b>${d.type} (${Math.round(d.confidence*100)}%):</b> ${d.description}<br>
            <span style="font-family:monospace; font-size:11px; color:#80d8ff;">📍 Coords: ${d.coords.join(', ')}</span>
          </div>
        `).join('')}
      </div>
      <div>
        <h4 style="color: #4caf50; margin-top: 0.5rem;">🚧 CIERRE PERIMETRAL DE RUTAS Y PUNTOS DE CONTROL:</h4>
        ${c.perimeter_containment_plan.checkpoints.map(cp => `
          <div>• <b>${cp.name}:</b> ${cp.instruction} (a ${cp.distance_from_fire_km} km del foco)</div>
        `).join('')}
      </div>
      <div>
        <h4 style="color: #ce93d8; margin-top: 0.5rem;">⚖️ MINISTERIO PÚBLICO (FISCALÍA):</h4>
        <div>• <b>Destinatario:</b> ${c.prosecutor_dossier.destinatario}</div>
        <div>• <b>Cadena de Custodia:</b> ${c.prosecutor_dossier.chain_of_custody}</div>
        <div>• <b>Estado:</b> ${c.prosecutor_dossier.status}</div>
      </div>
    `;
  }
});
