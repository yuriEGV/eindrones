/**
 * FLYBRIDGE v0.1 — Client-side GIS Tactical Dashboard
 * Architecture:
 * 1. Tree-mounted fire-resistant sensor nodes (Nodos Ignífugos) with NeuroFly Edge inference.
 * 2. Basin LoRaWAN Gateway (915 MHz) with satellite/4G uplink.
 * 3. Authority facility (Cuartel Bomberos / Retén Carabineros) with automated Drone-in-a-Box (<45s launch).
 * 4. Dual specialized payload: FLIR radiometric thermal + 4K optical forensic zoom.
 * 5. Multiorganizational dispatch: Bomberos (vehicular route & fire spread) + Carabineros CENCO (evidentiary dossier).
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

  // Satellite Imagery
  L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    maxZoom: 19,
    attribution: 'Esri, Maxar, Earthstar Geographics'
  }).addTo(map);

  L.control.zoom({ position: 'bottomright' }).addTo(map);

  // -------------------------------------------------------------
  // 2. LAYER CONTAINERS
  // -------------------------------------------------------------
  const nodeMarkers = {};
  const loraMeshLines = [];
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

  // -------------------------------------------------------------
  // 3. SVG CUSTOM MAP ICONS
  // -------------------------------------------------------------
  function createTreeNodeIcon(nodeId, alertLevel, isSelected) {
    const isAlert = alertLevel >= 3;
    const isElevated = alertLevel >= 2;
    const strokeColor = isAlert ? '#ff3b14' : (isElevated ? '#ff9100' : '#00e676');
    const glowColor = isAlert ? 'rgba(255, 59, 20, 0.8)' : (isElevated ? 'rgba(255, 145, 0, 0.7)' : 'rgba(0, 230, 118, 0.5)');
    const selectedRing = isSelected ? `stroke="#00e5ff" stroke-width="2" stroke-dasharray="3,3"` : '';

    const svg = `
      <div style="position: relative; width: 34px; height: 34px;">
        <svg viewBox="0 0 34 34" width="34" height="34" style="filter: drop-shadow(0 0 7px ${glowColor});">
          <circle cx="17" cy="17" r="14" fill="#0d1420" stroke="${strokeColor}" stroke-width="2.5" ${selectedRing} />
          <!-- Tree Icon -->
          <polygon points="17,6 23,16 11,16" fill="${strokeColor}" />
          <polygon points="17,11 25,22 9,22" fill="${strokeColor}" />
          <rect x="15" y="22" width="4" height="6" fill="#8d6e63" />
        </svg>
        <div style="position: absolute; top: -14px; left: -15px; width: 64px; text-align: center; font-size: 9px; font-weight: 800; font-family: monospace; color: #fff; text-shadow: 0 1px 3px #000;">
          ${nodeId.replace('NODE-ARBOR-', 'N-')}
        </div>
      </div>
    `;
    return L.divIcon({ html: svg, className: 'custom-tree-icon', iconSize: [34, 34], iconAnchor: [17, 17] });
  }

  function createGatewayIcon() {
    const svg = `
      <div style="position: relative; width: 38px; height: 38px;">
        <svg viewBox="0 0 38 38" width="38" height="38" style="filter: drop-shadow(0 0 8px rgba(179, 136, 255, 0.8));">
          <polygon points="19,4 34,34 4,34" fill="#140f24" stroke="#b388ff" stroke-width="2" />
          <circle cx="19" cy="14" r="3" fill="#b388ff" />
          <line x1="19" y1="17" x2="19" y2="34" stroke="#b388ff" stroke-width="2" />
          <line x1="12" y1="26" x2="26" y2="26" stroke="#b388ff" stroke-width="1.5" />
        </svg>
        <div style="position: absolute; top: -13px; left: -25px; width: 88px; text-align: center; font-size: 9px; font-weight: 800; font-family: monospace; color: #e1bee7; text-shadow: 0 1px 3px #000;">
          GW CUMBRE
        </div>
      </div>
    `;
    return L.divIcon({ html: svg, className: 'custom-gw-icon', iconSize: [38, 38], iconAnchor: [19, 19] });
  }

  function createAuthorityIcon(name) {
    const svg = `
      <div style="position: relative; width: 42px; height: 42px;">
        <svg viewBox="0 0 42 42" width="42" height="42" style="filter: drop-shadow(0 0 9px rgba(0, 176, 255, 0.8));">
          <rect x="5" y="10" width="32" height="28" rx="4" fill="#0b172a" stroke="#00b0ff" stroke-width="2" />
          <!-- Helipad H inside box -->
          <circle cx="21" cy="24" r="10" fill="none" stroke="#00e5ff" stroke-width="1.5" stroke-dasharray="2,2" />
          <text x="21" y="28" font-size="12" font-weight="900" fill="#00e5ff" text-anchor="middle" font-family="sans-serif">H</text>
        </svg>
        <div style="position: absolute; top: -14px; left: -30px; width: 102px; text-align: center; font-size: 9px; font-weight: 800; font-family: monospace; color: #80d8ff; text-shadow: 0 1px 3px #000;">
          CUARTEL &amp; DOCK
        </div>
      </div>
    `;
    return L.divIcon({ html: svg, className: 'custom-authority-icon', iconSize: [42, 42], iconAnchor: [21, 21] });
  }

  function createDroneIcon(headingDeg, status) {
    const isTargeting = (status === 'RECON_ORBIT' || status === 'TRANSIT_OUT');
    const glowColor = isTargeting ? '#ff3b14' : '#00e5ff';
    const svg = `
      <div style="position: relative; width: 40px; height: 40px; transform: rotate(${headingDeg}deg);">
        <svg viewBox="0 0 40 40" width="40" height="40" style="filter: drop-shadow(0 0 8px ${glowColor});">
          <line x1="8" y1="8" x2="32" y2="32" stroke="${glowColor}" stroke-width="2.5" />
          <line x1="32" y1="8" x2="8" y2="32" stroke="${glowColor}" stroke-width="2.5" />
          <circle cx="8" cy="8" r="4.5" fill="none" stroke="${glowColor}" stroke-width="1.5" />
          <circle cx="32" cy="8" r="4.5" fill="none" stroke="${glowColor}" stroke-width="1.5" />
          <circle cx="8" cy="32" r="4.5" fill="none" stroke="${glowColor}" stroke-width="1.5" />
          <circle cx="32" cy="32" r="4.5" fill="none" stroke="${glowColor}" stroke-width="1.5" />
          <circle cx="20" cy="20" r="7" fill="#090f1a" stroke="${glowColor}" stroke-width="2" />
          <polygon points="20,8 24,15 16,15" fill="${glowColor}" />
        </svg>
        <div style="position: absolute; top: -14px; left: -10px; width: 60px; text-align: center; font-size: 9px; font-weight: 800; font-family: monospace; color: #fff; text-shadow: 0 1px 3px #000;">
          DRON &lt;45s
        </div>
      </div>
    `;
    return L.divIcon({ html: svg, className: 'custom-drone-icon', iconSize: [40, 40], iconAnchor: [20, 20] });
  }

  function createRoadblockIcon(name) {
    const svg = `
      <div style="position: relative; width: 30px; height: 30px;">
        <svg viewBox="0 0 30 30" width="30" height="30" style="filter: drop-shadow(0 0 6px rgba(76, 175, 80, 0.8));">
          <circle cx="15" cy="15" r="12" fill="#0e2412" stroke="#4caf50" stroke-width="2" />
          <rect x="7" y="13" width="16" height="4" fill="#ffeb3b" />
        </svg>
      </div>
    `;
    return L.divIcon({ html: svg, className: 'custom-roadblock-icon', iconSize: [30, 30], iconAnchor: [15, 15] });
  }

  // -------------------------------------------------------------
  // 4. MAP UPDATE LOGIC
  // -------------------------------------------------------------
  function renderMapLayers(data) {
    const showNodes = document.getElementById('layerNodes').checked;
    const showLora = document.getElementById('layerLoraMesh').checked;
    const showBase = document.getElementById('layerAuthorityBase').checked;
    const showDrone = document.getElementById('layerDroneFlight').checked;
    const showSpread = document.getElementById('layerFireSpread').checked;
    const showRoute = document.getElementById('layerBomberosRoute').checked;
    const showRoadblocks = document.getElementById('layerCencoRoadblocks').checked;

    // 1. Gateway cumbre
    const gw = data.gateway;
    if (gw) {
      if (!gatewayMarker) {
        gatewayMarker = L.marker(gw.coords, { icon: createGatewayIcon() }).addTo(map);
        gatewayMarker.bindPopup(`
          <div style="font-family: Outfit, sans-serif; font-size: 12px; color: #111;">
            <b style="color: #6a1b9a; font-size: 13px;">📡 ${gw.name}</b><br>
            <b>Altitud:</b> ${gw.altitude_m} m<br>
            <b>Enlace:</b> ${gw.uplink}<br>
            <b>Paquetes Relayer:</b> ${gw.packets_relayed}
          </div>
        `);
      } else {
        gatewayMarker.setLatLng(gw.coords);
        if (showLora && !map.hasLayer(gatewayMarker)) map.addLayer(gatewayMarker);
        if (!showLora && map.hasLayer(gatewayMarker)) map.removeLayer(gatewayMarker);
      }
    }

    // 2. Nodos arbóreos e hilos LoRa
    // Limpiar líneas anteriores
    loraMeshLines.forEach(l => map.removeLayer(l));
    loraMeshLines.length = 0;

    data.tree_nodes.forEach(node => {
      const pos = [node.lat, node.lon];
      const alertLvl = node.inference ? node.inference.alert_level : 0;
      const isSelected = (node.node_id === selectedNodeId);

      // Marcador
      if (!nodeMarkers[node.node_id]) {
        const marker = L.marker(pos, {
          icon: createTreeNodeIcon(node.node_id, alertLvl, isSelected)
        }).addTo(map);

        marker.on('click', () => {
          selectedNodeId = node.node_id;
          updateDashboardUI(latestTelemetryData);
        });

        marker.bindTooltip(`🌳 ${node.node_id} (${node.tree_species})<br>Temp: ${node.telemetry.sensor_temp_c}°C | CO2: ${node.telemetry.co2_ppm} ppm`, {
          direction: 'top',
          className: 'map-tooltip-safe'
        });

        nodeMarkers[node.node_id] = marker;
      } else {
        const marker = nodeMarkers[node.node_id];
        marker.setLatLng(pos);
        marker.setIcon(createTreeNodeIcon(node.node_id, alertLvl, isSelected));
        if (showNodes && !map.hasLayer(marker)) map.addLayer(marker);
        if (!showNodes && map.hasLayer(marker)) map.removeLayer(marker);
      }

      // Línea LoRa hacia Gateway
      if (showLora && gw) {
        const line = L.polyline([pos, gw.coords], {
          color: alertLvl >= 3 ? '#ff3b14' : '#00e5ff',
          weight: 1.5,
          opacity: 0.45,
          dashArray: '3, 6'
        }).addTo(map);
        loraMeshLines.push(line);
      }
    });

    // 3. Cuartel de Autoridades & Drone-in-a-Box
    const fac = data.docking_station.facility;
    if (fac) {
      if (!authorityMarker) {
        authorityMarker = L.marker(fac.coords, { icon: createAuthorityIcon(fac.name) }).addTo(map);
        authorityMarker.bindPopup(`
          <div style="font-family: Outfit, sans-serif; font-size: 12px; color: #111;">
            <b style="color: #0077c2; font-size: 13px;">🏢 ${fac.name}</b><br>
            <b>Recinto:</b> ${fac.security}<br>
            <b>Suministro:</b> ${fac.power_grid}<br>
            <b>Personal Guardia:</b> ${fac.personnel_on_duty} efectivos
          </div>
        `);
      } else {
        if (showBase && !map.hasLayer(authorityMarker)) map.addLayer(authorityMarker);
        if (!showBase && map.hasLayer(authorityMarker)) map.removeLayer(authorityMarker);
      }
    }

    // 4. Dron Verificador y trayectoria
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
            weight: 2,
            opacity: 0.75,
            dashArray: '4, 6'
          }).addTo(map);
        } else {
          droneTrailLine.setLatLngs(drone.trajectory);
          if (showDrone && !map.hasLayer(droneTrailLine)) map.addLayer(droneTrailLine);
          if (!showDrone && map.hasLayer(droneTrailLine)) map.removeLayer(droneTrailLine);
        }
      }
    }

    // 5. Cono de Propagación del Fuego (Huygens Ellipse)
    if (fireSpreadPolygon) {
      map.removeLayer(fireSpreadPolygon);
      fireSpreadPolygon = null;
    }
    const bDisp = data.bomberos_dispatch;
    if (showSpread && bDisp && bDisp.fire_behavior) {
      const targetCoords = bDisp.target_coordinates.decimal;
      const headCoords = bDisp.fire_behavior.projected_head_coords_30m;
      // Aproximación de elipse convexa
      const angleRad = (bDisp.fire_behavior.spread_heading_deg * Math.PI) / 180.0;
      const flankDistDeg = 0.0012;

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

      fireSpreadPolygon.bindTooltip(`🔥 CONO DE PROPAGACIÓN (30 min): ${bDisp.fire_behavior.threatened_area_hectares_30m} ha`, {
        sticky: true
      });
    }

    // 6. Ruta de Acceso Vehicular de Bomberos
    if (bomberosRouteLine) {
      map.removeLayer(bomberosRouteLine);
      bomberosRouteLine = null;
    }
    if (showRoute && fac && bDisp) {
      const startP = fac.coords;
      const targetP = bDisp.target_coordinates.decimal;
      // Camino con punto intermedio simulado
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

    // 7. Cortes de Ruta CENCO
    const cenco = data.cenco_dispatch;
    if (showRoadblocks && cenco && cenco.perimeter_containment_plan) {
      if (roadblockMarkers.length === 0) {
        cenco.perimeter_containment_plan.checkpoints.forEach(cp => {
          const m = L.marker(cp.coords, { icon: createRoadblockIcon(cp.name) }).addTo(map);
          m.bindTooltip(`🚧 ${cp.name}<br>${cp.instruction}`, { sticky: true });
          roadblockMarkers.push(m);
        });
      }
    }
  }

  // -------------------------------------------------------------
  // 5. WIND VECTOR CANVAS ANIMATION
  // -------------------------------------------------------------
  const canvas = document.getElementById('windCanvas');
  const ctx = canvas.getContext('2d');
  let particles = [];
  const NUM_PARTICLES = 65;

  function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight;
  }
  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  for (let i = 0; i < NUM_PARTICLES; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      length: 12 + Math.random() * 16,
      speed: 1.0 + Math.random() * 1.5,
      alpha: 0.2 + Math.random() * 0.4
    });
  }

  function drawWind() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const windAngleRad = ((currentWind.direction_deg - 90) * Math.PI) / 180.0;
    const speedFactor = currentWind.speed_kmh / 25.0;

    ctx.lineWidth = 1.5;
    particles.forEach(p => {
      ctx.strokeStyle = `rgba(0, 229, 255, ${p.alpha})`;
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      const tailX = p.x - Math.cos(windAngleRad) * p.length;
      const tailY = p.y - Math.sin(windAngleRad) * p.length;
      ctx.lineTo(tailX, tailY);
      ctx.stroke();

      p.x += Math.cos(windAngleRad) * p.speed * speedFactor;
      p.y += Math.sin(windAngleRad) * p.speed * speedFactor;
      if (p.x < 0) p.x = canvas.width;
      if (p.x > canvas.width) p.x = 0;
      if (p.y < 0) p.y = canvas.height;
      if (p.y > canvas.height) p.y = 0;
    });
    requestAnimationFrame(drawWind);
  }
  requestAnimationFrame(drawWind);

  // -------------------------------------------------------------
  // 6. UI UPDATE & RENDERING
  // -------------------------------------------------------------
  function updateDashboardUI(data) {
    latestTelemetryData = data;
    currentWind = data.environment.wind;

    // Header Badges
    document.getElementById('badgeWind').textContent = `${data.environment.wind.speed_kmh} km/h ↗ ${data.environment.wind.cardinal}`;
    document.getElementById('badgeNodes').textContent = `${data.tree_nodes.length} ACTIVOS (LoRa 915MHz)`;
    document.getElementById('badgeGateway').textContent = data.gateway.status.includes('SATELLITE') ? 'STARLINK ACTIVO' : '4G ACTIVO';

    const droneStatus = data.verifier_drone.status;
    const badgeDock = document.getElementById('badgeDock');
    if (droneStatus === 'DOCK_CHARGING') {
      badgeDock.textContent = 'STANDBY (<45s)';
      badgeDock.className = 'badge-value';
    } else {
      badgeDock.textContent = `VUELO ACTIVO (${data.verifier_drone.launch_elapsed_sec}s)`;
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
              ${n.telemetry.sensor_temp_c}°C
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

      // Paquete LoRa
      if (inspected.lora_tx && inspected.lora_tx.packet_hex) {
        document.getElementById('loraHexBox').textContent = inspected.lora_tx.packet_hex;
        document.getElementById('loraSizeTag').textContent = `${inspected.lora_tx.packet_size_bytes} BYTES (<50 B)`;
      }
      document.getElementById('lpId').textContent = inspected.node_num;
      document.getElementById('lpTemp').textContent = `${inspected.telemetry.sensor_temp_c}°C`;
      document.getElementById('lpDcdt').textContent = `${olf.d_co2_dt_ppm_s.toFixed(1)}`;
      document.getElementById('lpWind').textContent = `${inspected.telemetry.wind_speed_kmh} km/h`;
      document.getElementById('lpConf').textContent = `${inspected.inference.confidence_pct}%`;
      document.getElementById('lpBat').textContent = `${inspected.battery_pct}%`;
    }

    // ── CENTER HUD: DRONE-IN-A-BOX & VERIFIER DRONE ──
    const dState = data.docking_station;
    const drone = data.verifier_drone;
    document.getElementById('hudFacilityName').textContent = dState.facility.name;
    document.getElementById('hudHatchVal').textContent = `${dState.hatch.status} (${dState.hatch.open_pct}%)`;
    document.getElementById('hudLaunchTime').textContent = drone.launch_elapsed_sec.toFixed(1);

    const lBadge = document.getElementById('hudLaunchBadge');
    if (drone.takeoff_under_45s) {
      lBadge.textContent = '✅ DESPEGUE EXITOSO (<45s)';
      lBadge.className = 'c-tag verified';
    } else {
      lBadge.textContent = '⚠️ DESPEGUE EN CURSO';
      lBadge.className = 'c-tag';
    }

    document.getElementById('hudDroneStatus').textContent = drone.status;
    document.getElementById('hudDroneSpeed').textContent = `${drone.speed_kmh.toFixed(1)} km/h`;
    document.getElementById('hudDroneAlt').textContent = `${drone.altitude_m.toFixed(0)} m`;
    document.getElementById('hudDroneBattery').textContent = `${drone.battery_pct.toFixed(0)}%`;

    // FLIR Radiométrico
    if (drone.thermal_flir) {
      document.getElementById('flirCoreTemp').textContent = `${drone.thermal_flir.core_temp_c} °C`;
      document.getElementById('flirPerimeter').textContent = `${drone.thermal_flir.fire_perimeter_m} m`;
      document.getElementById('flirSpreadRate').textContent = `${drone.thermal_flir.spread_velocity_m_min} m/min`;
      document.getElementById('flirIntensity').textContent = `${drone.thermal_flir.fireline_intensity_kw_m || 1850} kW/m`;
    }

    // Óptica 4K Forense
    if (drone.optical_forensics_4k) {
      document.getElementById('opticalHash').textContent = drone.optical_forensics_4k.evidence_hash_sha256 || 'SHA-256-PENDING';
      document.getElementById('opticalTime').textContent = drone.optical_forensics_4k.timestamp_utc || '';
    }

    // ── RIGHT SIDEBAR: BOMBEROS TAB ──
    const bDisp = data.bomberos_dispatch;
    if (bDisp) {
      document.getElementById('bTargetNode').textContent = bDisp.target_node_id;
      document.getElementById('bCoords').textContent = `${bDisp.target_coordinates.decimal[0]}, ${bDisp.target_coordinates.decimal[1]}`;
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
            <div class="fc-coords">📍 Coords: ${d.coords[0]}, ${d.coords[1]}</div>
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

    // Map Rendering
    renderMapLayers(data);
  }

  // -------------------------------------------------------------
  // 7. WEBSOCKET REAL-TIME STREAMING
  // -------------------------------------------------------------
  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      console.log("WebSocket FLYBRIDGE conectado");
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        updateDashboardUI(payload);
      } catch (e) {
        console.error("Error al procesar telemetría", e);
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
  // 8. GLOBAL HANDLERS & BUTTONS
  // -------------------------------------------------------------
  window.selectNode = function(nodeId) {
    selectedNodeId = nodeId;
    if (latestTelemetryData) updateDashboardUI(latestTelemetryData);
  };

  // Tabs switching
  const tabBomberos = document.getElementById('tabBomberos');
  const tabCenco = document.getElementById('tabCenco');
  const contentBomberos = document.getElementById('contentBomberos');
  const contentCenco = document.getElementById('contentCenco');

  tabBomberos.addEventListener('click', () => {
    tabBomberos.classList.add('active');
    tabCenco.classList.remove('active');
    contentBomberos.classList.add('active');
    contentCenco.classList.remove('active');
  });

  tabCenco.addEventListener('click', () => {
    tabCenco.classList.add('active');
    tabBomberos.classList.remove('active');
    contentCenco.classList.add('active');
    contentBomberos.classList.remove('active');
  });

  // Action: Simular Foco
  document.getElementById('btnSimulateIgnition').addEventListener('click', () => {
    fetch('/api/node/trigger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ node_id: selectedNodeId || 'NODE-ARBOR-03', peak_temp_c: 68.0 })
    }).then(res => res.json()).then(r => {
      alert(`⚡ Ignición simulada en ${selectedNodeId}. Inferencia NeuroFly Edge activada, transmisión LoRa 915MHz emitida y despegue de Drone-in-a-Box iniciado (<45s).`);
    });
  });

  // Action: Despegar Dron
  document.getElementById('btnLaunchDroneManual').addEventListener('click', () => {
    fetch('/api/drone/launch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_node_id: selectedNodeId || 'NODE-ARBOR-03' })
    }).then(res => res.json()).then(r => {
      alert(`🚀 Despegue de emergencia activado desde ${r.facility_name}. Dron Verificador en ruta a ${r.target_node}.`);
    });
  });

  // Action: Feedback Human-in-the-Loop
  document.getElementById('btnConfirmWildfire').addEventListener('click', () => {
    fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ incident_id: selectedNodeId, verdict: 'CONFIRMADO_INCENDIO', operator_notes: 'Verificado por Bomberos y Dron' })
    }).then(r => alert("✅ Foco confirmado. Se refuerzan los pesos sinápticos del lóbulo olfativo."));
  });

  document.getElementById('btnMarkFalsePositive').addEventListener('click', () => {
    fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ incident_id: selectedNodeId, verdict: 'FALSO_POSITIVO', operator_notes: 'Falso positivo térmico solar' })
    }).then(r => alert("❌ Falso positivo registrado. Se eleva el umbral de discriminación solar."));
  });

  // -------------------------------------------------------------
  // 9. MODALS: BOMBEROS & CENCO
  // -------------------------------------------------------------
  const modalB = document.getElementById('bomberosModal');
  const modalC = document.getElementById('cencoModal');

  document.getElementById('btnOpenBomberosModal').addEventListener('click', () => {
    renderBomberosModal();
    modalB.classList.add('open');
  });

  document.getElementById('btnOpenCencoModal').addEventListener('click', () => {
    renderCencoModal();
    modalC.classList.add('open');
  });

  document.getElementById('btnCloseBomberosModal').addEventListener('click', () => modalB.classList.remove('open'));
  document.getElementById('btnCloseCencoModal').addEventListener('click', () => modalC.classList.remove('open'));

  document.getElementById('btnDispatchBomberosDirect').addEventListener('click', () => {
    renderBomberosModal();
    modalB.classList.add('open');
  });

  document.getElementById('btnExportProsecutorDossier').addEventListener('click', () => {
    renderCencoModal();
    modalC.classList.add('open');
  });

  document.getElementById('btnDispatchFinalBomberos').addEventListener('click', () => {
    alert("🚒 DESPACHO OFICIAL TRANSMITIDO A CENTRAL DE ALARMAS DE BOMBEROS (132). Unidades B-14 y BF-2 en camino.");
    modalB.classList.remove('open');
  });

  document.getElementById('btnSendProsecutorFinal').addEventListener('click', () => {
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
