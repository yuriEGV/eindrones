# 🌲 FLYBRIDGE v0.1 — Fire-Resistant Tree Sensor Network & Authority Drone-in-a-Box Station
### *Nature's intelligence safeguarding our forests*
**Detect. Interpret. Act.** Technology inspired by the NeuroFly (*Drosophila melanogaster*) neuromorphic model for early wildfire prevention, autonomous verification, and emergency dispatch.

---

## 📌 System Overview

**FLYBRIDGE v0.1** unites the **NeuroFly** neuromorphic edge computation model deployed on a **network of fire-resistant tree-mounted sensor nodes** with an automated **Drone-in-a-Box station** operated directly inside official, secure facilities of competent authorities (**Fire stations / Bomberos, Rural Police posts / Carabineros, or CONAF/SENAPRED forest ranger stations**).

This design replaces random continuous aerial drone roaming with an energy-efficient, tactical hybrid architecture:
1. **Continuous 24/7 Tree In-Situ Sensing**: Passive-sleep tree nodes continuously sample trace chemical pyrolysis gases and convective thermal flux.
2. **On-Demand Rapid Takeoff (<45 s)**: Only when a tree node confirms an ignition anomaly with high confidence, the station in the official facility opens its motorized weather hatch and launches the high-speed verifier drone directly toward the tree's GPS coordinates.
3. **Simultaneous Dual Authority Dispatch**:
   - **Fire Department (Bomberos 132)**: Tactical sheet with the fastest vehicular access route along firebreak trails, water refilling points, and real-time fire spread cone projections.
   - **Police & Prosecution (Carabineros CENCO 133 / Fiscalía)**: Real-time alert with 4K forensic optical captures (suspicious vehicles, fresh tire tracks, fleeing suspects), SHA-256 cryptographic chain of custody, and immediate perimeter road containment plans.

---

## 🔄 Full Operational Flow

```text
 [Forest: Tree Node]
   └── Fire-Resistant Nodes with NeuroFly Edge Inference (Python / MicroPython)
        ├── Sensors: CO2/VOCs + Multizone Thermal Gradient + Wind Anemometer
        └── Neuromorphic false-positive filter (solar diurnal heating rejection)
                 │
                 │ (LoRaWAN / LoRa Mesh Telemetry - 915 MHz | Compact Packet < 50 bytes)
                 ▼
      [Basin Summit Gateway / Starlink Satellite or 4G/LTE Uplink]
                 │
                 ▼
     [Central Server / Mission API & Huygens Spread Model]
                 │
                 ▼
 [Authority Facility: Fire Station / Police Compound / CONAF Base]
   ├── Base Station / Drone-in-a-Box on Roof or Watchtower
   ├── Immediate Autonomous Takeoff (<45 s)
   └── Real-Time Monitoring Panel (Central de Alarmas & CENCO)
```

---

## 🔬 Core Architectural Pillars

### 1. In-Tree Edge Sensory Inference (NeuroFly Edge)
* **Local Python / MicroPython Execution**: Runs on ultra-low-power edge processors (Raspberry Pi Zero 2 W, ARM Cortex-M4, RP2040).
* **Neuromorphic Olfactory Lobe**: Computes gas concentration derivative $dC/dt$ for $CO_2$, $CO$, and $VOCs$, pinpointing wind-diluted microplumes before visible thick smoke forms.
* **Visual Medulla/Lamina (Convective Thermal Flux)**: Multizone vertical thermal sensor detects fast upward convective eddy turbulence (*thermal flicker*), discriminating flame combustion from passive solar canopy warming.
* **Neuromorphic False Positive Filter**: Rejects uniform solar diurnal warming and isolated vehicle exhaust; triggers ignition alerts only upon cross-modal chemo-thermal coincidence.
* **Compact LoRa Packet (< 50 bytes)**: Emits a structured 32-byte binary payload over 915 MHz containing Node ID, timestamp, coordinates, ambient temp, convective gradient, $dC/dt$, wind vector, and LiFePO4 battery status.

### 2. Fire-Resistant Tree Node Physical Specs
* **Thermal Resistance**: Hermetic enclosure rated **UL94 V-0** flame retardant with external ceramic thermal barrier resistant up to 600°C.
* **Gas Intake**: Hydrophobic **PTFE** microporous membrane allowing free gas exchange while repelling rain, dew, dust, and tree sap.
* **Long-Term Autonomy**: Thermally stable **LiFePO4** battery (no thermal runaway risk) coupled with a compact solar panel.

### 3. Authority-Housed Drone-in-a-Box Station
* **Official Facility Security**: Housed inside official premises (fire station or police post) protected from vandalism and theft, backed by 220V grid power + UPS.
* **Rapid Deployment (<45 s)**: Motorized hatch opens in <15 s, self-calibrates, and takes off autonomously in under 45 seconds toward the alerting node.
* **Dual Specialized Payload**:
  1. **Radiometric Thermal Camera (FLIR)**: Measures core flame temperature (°C), fire perimeter (m), and linear heat intensity (kW/m).
  2. **4K Optical Zoom Forensic Camera**: 360° perimeter scan of access tracks, detecting vehicles, tire tracks, and fleeing persons with SHA-256 cryptographic verification.

### 4. Real-Time Multiorganization Tactical Dispatch
* **Fire Alarm Dispatch (Bomberos)**: Fastest vehicular route, ETA in minutes, water reservoir sources, and real-time Huygens fire spread cone.
* **Police Communications (Carabineros CENCO)**: Instantaneous forensic evidence transmission, road containment checkpoints, and digital prosecutor dossier for arson prosecution.

---

## 💻 Quick Start & Testing

```bash
# Run tests
python tests/test_tree_nodes.py
python tests/test_docking_and_drone.py
python tests/test_mission_server.py
python tests/test_api_server.py

# Launch Tactical GIS Web Dashboard
uvicorn firewatch.server:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at `http://localhost:8000/`.
