# Architecture Overview

```mermaid
graph TD
    %% Style definitions
    classDef cloudStyle fill:#f5f5f7,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;
    classDef fogStyle fill:#f9f9fb,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;
    classDef edgeStyle fill:#ffffff,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;
    classDef centerStyle fill:#ffffff,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;

    %% Nodes
    Cloud["**CLOUD LAYER**<br><br>• National/State Command Center | FSI / NRSC Integration<br>• Historical Analysis | Long-term Pattern Recognition<br>• Policy-level Decision Making | Cross-region Coordination"]:::cloudStyle
    
    Fog["**FOG LAYER (LOCAL BRAIN)**<br><br>• Distributed Fog Nodes per Forest Zone/Division<br>• Real-time Scenario Modelling | Risk Scoring<br>• Autonomous Pre-Suppression Commands | Alert Dispatch<br>• Lateral Communication Between Fog Nodes"]:::fogStyle
    
    Edge["**EDGE LAYER**<br><br>• Sensor Clusters<br>• Data Acquisition<br>• Local Pre-filter"]:::edgeStyle
    
    LCC["**LOCAL CONTROL CENTER**<br><br>• Forest Range Office<br>• Ground Teams<br>• Drone Dispatch"]:::centerStyle

    %% Connections
    Cloud <--> |"Bidirectional (MQTT / HTTPS)"| Fog
    Fog <--> |"Bidirectional"| Edge
    Fog <-- |"Alert"| LCC
```

The proposed system operates on three tiers described below.

## Edge Layer — Field Sensor Clusters

Each Edge Node is a weatherproof sensor cluster deployed at strategic points across the forest (based on fire risk mapping). They continuously sample environmental parameters and transmit to the nearest fog node.

### Sensor Stack (per Edge Node)

| Sensor | Parameter Measured | Relevance to Fire Risk |
| :--- | :--- | :--- |
| **DHT22 / SHT40** | Temperature + Relative Humidity | Dry, hot conditions = high risk |
| **Anemometer + Wind Vane** | Wind speed + direction | Determines fire spread vector |
| **Capacitive Soil Moisture Sensor** | Soil moisture content | Dry soil = high fuel load |
| **MQ-2 / MQ-7 Gas Sensor** | Smoke, CO, LPG | Early combustion indicator |
| **FLIR Lepton / MLX90640** | Infrared thermal imaging | Surface temperature anomaly |
| **BH1750 / TSL2591** | Ambient light intensity | Time-of-day context |
| **Rain Gauge (Tipping Bucket)** | Precipitation | Natural suppression factor |
| **GPS Module (NEO-8M)** | Geo-location | Spatial mapping of events |

### Edge Node Communication

*   **Protocol:** LoRa (Long Range, Low Power) — 868 MHz band in India
*   **Range:** 2–15 km line-of-sight in open terrain; 1–5 km in forested areas
*   **Data rate:** Low (sensor telemetry is small payloads — this is appropriate for LoRa)
*   **Topology:** Star topology to nearest Fog Node; mesh fallback between edge nodes

### Power Design

*   **Primary:** Solar panel (10W–20W monocrystalline) + LiFePO4 battery bank (sufficient for 5–7 days of overcast operation)
*   **Backup:** Supercapacitor bank for surge protection
*   **Rationale:** Eliminates grid dependency entirely; designed for deployment in remote forest zones

---

## Fog Layer — The Local Brain

This is the core innovation of the proposed system. Each fog node is an intelligent computing unit deployed at the forest range/beat level — physically close to the field, not at the district control center.

### What the Fog Node Is

A fog node is a ruggedized edge server — not a cloud server, not a microcontroller. It sits in the middle of the compute hierarchy.

**Candidate hardware (mid-level spec):**
*   NVIDIA Jetson Orin NX (for AI inference capability)
*   **Or:** Industrial-grade ARM server (e.g., Advantech EPC-R3720) for non-AI-intensive deployments
*   Redundant storage (eMMC + SD backup)
*   Cellular modem (4G LTE + fallback 2G) for cloud uplink
*   Local LoRa gateway for edge communication
*   Housed in IP67-rated enclosure

### What the Fog Node Does

#### Step 1 — Continuous Data Ingestion
Receives time-series sensor data from all edge nodes in its zone via LoRa gateway. Maintains a rolling local data buffer.

#### Step 2 — Scenario Construction
The fog node doesn't just threshold-check individual sensors. It builds a composite risk scenario by correlating multiple parameters:

$$	ext{Risk Scenario} = f(	ext{Temperature}, 	ext{Humidity}, 	ext{Wind Speed}, 	ext{Wind Direction}, 	ext{Soil Moisture}, 	ext{Gas Levels}, 	ext{Thermal Anomaly}, 	ext{Time-of-day}, 	ext{Season}, 	ext{Historical fire data for zone})$$

This is implemented as a multi-parameter weighted risk scoring model, initially rule-based (transparent, auditable) and extensible to lightweight ML models (e.g., Random Forest, TinyML) in later phases.

#### Step 3 — Risk Classification
The scenario is classified into one of four states:

| State | Description | Action Triggered |
| :--- | :--- | :--- |
| **GREEN** | Normal | Log and report to cloud periodically |
| **YELLOW** | Elevated Risk | Increase sampling rate; alert control center |
| **ORANGE** | Imminent Risk | Pre-suppression activation; human alert + cloud notification |
| **RED** | Active Fire Detected | Full autonomous response + emergency escalation |

#### Step 4 — Autonomous Pre-Suppression (ORANGE/RED)
Within the fog node's safe action envelope (defined actions that are pre-authorized and bounded), it can directly command:
*   Activation of fixed mist/sprinkler systems at perimeter fire-break points
*   Deployment command to pre-positioned autonomous drones (if available)
*   Activation of acoustic deterrent systems to drive wildlife away from risk zone
*   Triggering of physical firebreak actuators (motorized clearing barriers, if installed)

**All autonomous actions are:**
*   Logged with timestamp and sensor justification
*   Bounded to pre-defined safe envelopes (cannot exceed authorized scope)
*   Immediately reported to human control center with reason

#### Step 5 — Dual Parallel Reporting
Simultaneously with autonomous action:
*   **Report A → Local Control Center (immediate, short-format alert)**
    *   *Contains:* Zone ID, Risk Level, Key parameters, Actions taken
*   **Report B → Cloud Layer (full data packet)**
    *   *Contains:* Raw sensor time-series + Scenario analysis + Decision log + Actions taken + Request for cloud-level analysis

#### Step 6 — Receiving Cloud Commands
If the cloud layer sends override or refined commands based on its broader analysis, the fog node adjusts its behavior accordingly. The fog node always defers to cloud commands when connectivity is available — it only operates autonomously when cloud is unreachable or during the response latency window.

### Fog Node Clustering and Lateral Communication

Multiple fog nodes are deployed across forest divisions. They communicate laterally via:
*   **Primary:** 4G LTE mesh (where available)
*   **Fallback:** Long-range WiFi (802.11ah — 900 MHz sub-GHz band) or licensed RF links

**Lateral communication enables:**
*   **Fire spread prediction:** If Node A detects ignition and wind is blowing toward Node B's zone, Node A proactively alerts Node B to enter pre-suppression state
*   **Shared situational awareness:** All nodes maintain a synchronized regional risk map
*   **Redundancy:** If one fog node fails, adjacent nodes expand their coverage zone

### Fog Node Power Design

*   **Primary:** Solar + battery (larger capacity than edge nodes — 100Ah+ LiFePO4 bank)
*   **Backup:** Small diesel/petrol generator for extended outage
*   **Rationale:** Fog nodes are semi-permanent installations at range offices or designated forest posts; limited grid access is acceptable; full off-grid preferred

---

## Cloud Layer

The cloud layer serves as the strategic intelligence and long-term management brain. It does not replace operational fog decisions but provides context that fog nodes cannot generate alone.

**Functions:**
*   Ingests fog node reports and raw sensor data
*   Runs historical comparison models (current conditions vs. same season in past years)
*   Maintains national-level fire risk maps updated in near-real-time
*   Interfaces with FSI/NRSC satellite systems — correlating satellite hotspot data with fog-level sensor data
*   Sends advisory commands to fog nodes (e.g., recalibrate risk thresholds for incoming heat wave)
*   Generates post-event analysis reports for forest department records and policy use
*   Hosts the administrative dashboard for district/state/national forest officers

**Cloud infrastructure:** Can be hosted on NIC Cloud (Government of India's MeghRaj) or state data centers, aligning with data sovereignty requirements.

---

# System Workflow — End to End

## Normal Operation (GREEN State)

1.  **Edge sensors** → LoRa → **Fog Node**
2.  **Fog Node:** Rolling data collection, scenario scoring, GREEN state confirmed
3.  **Fog Node** → Cloud: Periodic telemetry batch (every 15–30 min)
4.  **Cloud:** Updates national risk map, no action required

## Elevated Risk (YELLOW State)

1.  **Fog Node** detects rising temperature + dropping humidity + increasing wind speed
2.  Risk Score crosses YELLOW threshold
3.  **Fog Node:** Increases sampling rate (edge nodes polled every 30 sec instead of 5 min)
4.  **Fog Node** → Control Center: *"Zone 4B: Elevated risk. Monitor."*
5.  **Fog Node** → Cloud: Real-time streaming begins
6.  **Fog Node** → Adjacent Fog Nodes: *"Zone 4B elevated — downstream zones stand by"*

## Imminent Risk / Autonomous Action (ORANGE State)

1.  Gas sensor detects CO spike. Thermal camera shows surface temp anomaly.
2.  Soil moisture critically low. Wind direction: toward fuel-dense zone.
3.  Risk Score crosses ORANGE threshold.
4.  **Fog Node (within seconds):**
    *   **ACTION:** Activates perimeter mist systems at fire-break points
    *   **ACTION:** Sends deployment command to nearest drone station
    *   **ALERT → Control Center:** Full scenario brief + actions taken
    *   **REPORT → Cloud:** Complete data packet + decision log
5.  **Control Center receives alert:**
    *   Reviews fog node assessment
    *   Dispatches ground team (with fog-generated zone map)
    *   Can override fog actions if needed
6.  **Cloud receives report:**
    *   Cross-references satellite data
    *   Runs predictive spread model
    *   Sends refined tactical advisory back to fog node

## Active Fire (RED State)

1.  **Fog Node** confirms active fire (thermal + gas + visual)
2.  **Full escalation:**
    *   All pre-suppression systems at maximum
    *   Emergency alert to control center + state fire department
    *   Fog lateral broadcast: all neighboring nodes escalate to ORANGE
3.  **Cloud:** Emergency coordination mode activated
4.  Integration with **NDMA (National Disaster Management Authority)** protocols
