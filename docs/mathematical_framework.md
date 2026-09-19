# IGNIS -- Mathematical Framework

This document defines every mathematical formula, normalization function, scoring equation, confirmation rule, and configurable parameter used in the IGNIS V1 decision pipeline. It serves as the authoritative technical reference for the scoring subsystem.

---

## 1. Scoring Pipeline Overview

```
Raw Sensors --> Clamped Normalization --> Normalized [0.0, 1.0]
                    |                            |
                    v                            v
         Confirmation Thresholds      Weighted Dot Product
                    |                            |
                    v                            v
         Confirming Sensor Count      Wildfire Hazard Index (WHI)
                    |                            |
                    +----------+---------+-------+
                               |
                               v
                    Deterministic State Machine
                    - GREEN  : WHI < 0.35
                    - YELLOW : WHI >= 0.35 or Lateral Warning
                    - ORANGE : WHI >= 0.60 AND Confirmations >= 3
                    - RED    : WHI >= 0.80 AND Confirmations >= 3
                    - If WHI >= 0.60 but Confirmations < 3:
                      --> CLAMP TO YELLOW (Single Fault Guard)
                               |
                               v
                    Max-State Zone Aggregator
                    - Zone State = max(Node States)
```

---

## 2. Sensor Normalization Functions

Raw sensor inputs are converted into dimensionless risk coefficients bounded to [0.0, 1.0] using parameter-specific clamping and inversion.

### 2.1. Standard Positive Linear Normalization (Higher is Riskier)

Applied to: Temperature, Wind Speed, Gas/Smoke Concentration, Thermal Anomaly.

$$S_i = \frac{\text{clamp}(x_i, \min_i, \max_i) - \min_i}{\max_i - \min_i}$$

Where `clamp(x, min, max)` constrains the input to the range [min, max].

### 2.2. Inverted Linear Normalization (Lower is Riskier)

Applied to: Relative Humidity, Soil Moisture.

$$S_i = 1.0 - \left( \frac{\text{clamp}(x_i, \min_i, \max_i) - \min_i}{\max_i - \min_i} \right)$$

Low humidity and low soil moisture indicate dry, fire-prone conditions, so the risk coefficient increases as the raw value decreases.

### 2.3. Cyclical Diurnal Time-of-Day Normalization

Diurnal solar radiation peaks during early afternoon. Let H be the current hour (0-23) extracted from the telemetry timestamp:

$$S_{\text{TOD}} = \max\left(0.0, \; 1.0 - \frac{|H - 14|}{12}\right)$$

- At 14:00 (2:00 PM): S_TOD = 1.0 (maximum thermal vulnerability)
- At 02:00 (2:00 AM): S_TOD = 0.0 (minimum vulnerability)
- At 08:00 (8:00 AM): S_TOD = 0.5 (rising risk)
- At 20:00 (8:00 PM): S_TOD = 0.5 (declining risk)

The peak at 14:00 accounts for the atmospheric thermal lag beyond solar noon (approximately 12:00-12:30).

### 2.4. Seasonal Baseline

A dimensionless macro-seasonal drought risk factor S_SB provided as a configurable input per simulation run. Values closer to 1.0 represent peak fire season (pre-monsoon dry period); values closer to 0.0 represent low-risk seasons (monsoon wet period). In V1, this is a static parameter per scenario. In V2, it would be dynamically ingested from India Meteorological Department (IMD) API feeds.

---

## 3. Parameter Limits and Confirmation Matrix

| Parameter | Unit | Min | Max | Invert? | Confirmation Threshold | Weight |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Temperature (T) | deg C | 20.0 | 45.0 | No | >= 40.0 deg C | 0.20 |
| Relative Humidity (H) | % | 15.0 | 70.0 | Yes | <= 25.0% | 0.15 |
| Wind Speed (W) | km/h | 0.0 | 40.0 | No | >= 25.0 km/h | 0.10 |
| Soil Moisture (SM) | % | 5.0 | 35.0 | Yes | <= 10.0% | 0.15 |
| Gas / Smoke (G) | ppm | 10.0 | 100.0 | No | >= 30.0 ppm | 0.15 |
| Thermal Anomaly (TA) | deg C above ambient | 0.0 | 10.0 | No | >= 3.0 deg C | 0.15 |
| Time of Day (TOD) | Hour (0-23) | 0 | 23 | Cyclical | N/A (scoring only) | 0.05 |
| Seasonal Baseline (SB) | Dimensionless | 0.0 | 1.0 | None | N/A (scoring only) | 0.05 |
| **Total** | | | | | | **1.00** |

All values are defined in `config/zones_config.json` and can be overridden per zone.

---

## 4. Wildfire Hazard Index (WHI) Composite Formula

The continuous composite Wildfire Hazard Index is calculated as a weighted dot product of normalized sensor coefficients:

$$\text{WHI} = \sum_{i=1}^{8} w_i \cdot S_i$$

Expanding:

$$\text{WHI} = 0.20 \cdot S_T + 0.15 \cdot S_H + 0.10 \cdot S_W + 0.15 \cdot S_{SM} + 0.15 \cdot S_G + 0.15 \cdot S_{TA} + 0.05 \cdot S_{\text{TOD}} + 0.05 \cdot S_{\text{SB}}$$

The resulting WHI is bounded to [0.0, 1.0].

### Weight Rationale (Simlipal Calibration)

- **Temperature (0.20):** Highest weight as the primary thermal driver in dry deciduous forest fires. Simlipal pre-monsoon temperatures regularly exceed 40 deg C.
- **Humidity (0.15):** Critical indicator of fine fuel moisture content. Air desiccation below 25% enables leaf litter flashover.
- **Wind Speed (0.10):** Primary accelerator of flame propagation. Moderate weight because wind is more of a spread factor than an ignition factor.
- **Soil Moisture (0.15):** Deep ground fuel desiccation indicator. Sal leaf litter becomes explosive tinder below 10%.
- **Gas/Smoke (0.15):** Rapid indicator of smoldering combustion. Background air is 8-15 ppm; 30 ppm indicates active combustion.
- **Thermal Anomaly (0.15):** Direct infrared surface heating detection. 3 deg C above ambient indicates a localized heat source.
- **Time of Day (0.05):** Accounts for diurnal solar radiation peak. Lower weight because it is a contextual modifier, not a direct fire indicator.
- **Seasonal Baseline (0.05):** Macro-seasonal drought context. Lower weight because it changes slowly and is supplementary.

---

## 5. Multi-Sensor Confirmation Logic

### 5.1. Confirmation Indicators

For each confirmable sensor parameter, define an indicator function:

$$C_T = \mathbb{I}(x_T \ge 40.0), \quad C_H = \mathbb{I}(x_H \le 25.0), \quad C_W = \mathbb{I}(x_W \ge 25.0)$$
$$C_{SM} = \mathbb{I}(x_{SM} \le 10.0), \quad C_G = \mathbb{I}(x_G \ge 30.0), \quad C_{TA} = \mathbb{I}(x_{TA} \ge 3.0)$$

Where the indicator function returns 1 if the condition is true, 0 otherwise.

### 5.2. Total Confirmation Count

$$K_{\text{conf}} = \sum_{i \in \{T, H, W, SM, G, TA\}} C_i$$

The maximum possible value is 6 (all confirmable sensors exceeding thresholds).

### 5.3. Purpose

The confirmation count gates access to ORANGE and RED states. A high WHI driven by extreme values in only 1 or 2 parameters (e.g., a single faulty temperature sensor) cannot escalate the system past YELLOW. This is the primary false positive suppression mechanism.

---

## 6. State Evaluation and Clamping Rules

| WHI Range | Confirmation Count | Assigned State | Clamped? |
| :--- | :--- | :--- | :--- |
| WHI < 0.35 | Any | GREEN | No |
| 0.35 <= WHI < 0.60 | Any | YELLOW | No |
| 0.60 <= WHI < 0.80 | K_conf >= 3 | ORANGE | No |
| 0.60 <= WHI < 0.80 | K_conf < 3 | YELLOW | Yes (Single Fault Guard) |
| WHI >= 0.80 | K_conf >= 3 | RED | No |
| WHI >= 0.80 | K_conf < 3 | YELLOW | Yes (Single Fault Guard) |

### Additional Transition Rules

- **Lateral escalation:** If a lateral peer warning is received with aligned wind bearing and the current state is GREEN, escalate to YELLOW regardless of WHI.
- **De-escalation hysteresis:** State can only decrease one level at a time per evaluation cycle, and only after sustained improvement in readings.
- **Override precedence:** If an operator advisory override is active, the overridden state takes precedence over the calculated state.

---

## 7. Circular Vector Wind Averaging

When multiple edge nodes report differing wind directions and speeds, calculating an arithmetic mean yields invalid results near the 0/360 degree boundary. IGNIS implements circular trigonometric vector averaging:

### 7.1. Direction Averaging

$$\bar{x} = \frac{1}{N} \sum_{k=1}^{N} \cos\left(\frac{\pi \theta_k}{180}\right)$$

$$\bar{y} = \frac{1}{N} \sum_{k=1}^{N} \sin\left(\frac{\pi \theta_k}{180}\right)$$

$$\bar{\theta}_{\text{deg}} = \text{atan2}(\bar{y}, \bar{x}) \cdot \frac{180}{\pi} \pmod{360}$$

### 7.2. Speed Averaging

$$\bar{v} = \frac{1}{N} \sum_{k=1}^{N} v_k$$

Speed averaging uses the standard arithmetic mean since speed magnitudes do not wrap around a circular domain.

---

## 8. Zone-Level State Aggregation

To ensure that an intense localized wildfire detected by a single edge node is not diluted by benign readings from distant nodes, the zone-level state is derived using a maximum-state operator:

$$\text{ZoneState} = \max_{j \in \text{Nodes}} \left( \text{State}(j) \right)$$

$$\text{ZoneWHI} = \max_{j \in \text{Nodes}} \left( \text{WHI}(j) \right)$$

State ordering: GREEN (0) < YELLOW (1) < ORANGE (2) < RED (3).

---

## 9. Lateral Wind-Alignment Verification

When a lateral peer broadcast is received, the receiving fog node must determine whether the reported wind direction poses a propagation risk to its own zone.

Let:
- theta_wind = broadcast wind direction (degrees)
- theta_bearing = geometric bearing from the reporting zone to the receiving zone (degrees)
- delta_tol = angular tolerance (configurable, default: +/-45 degrees)

$$\Delta\theta = |\theta_{\text{wind}} - \theta_{\text{bearing}}| \pmod{360}$$

$$\Delta\theta_{\text{minimal}} = \min(\Delta\theta, \; 360 - \Delta\theta)$$

$$\text{IsAligned} = \left( \Delta\theta_{\text{minimal}} \le \delta_{\text{tol}} \right)$$

If IsAligned is true and the broadcast state is >= YELLOW, the receiving node registers an active lateral warning.

---

## 10. Complete Hardcoded Parameters Inventory

The following table documents every hardcoded constant, threshold, timeout, network port, buffer size, and mathematical weight in IGNIS V1. For each parameter, the V1 value, engineering rationale, and recommended V2 dynamic strategy are provided.

### 10.1. Scoring Parameters

| Location | Parameter | V1 Value | Rationale | V2 Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `config/zones_config.json` | `weights.temperature_c` | 0.20 | Highest primary thermal driver | Seasonal weight adaptation |
| `config/zones_config.json` | `weights.humidity_pct` | 0.15 | Fine fuel moisture indicator | Calibrate from FMC maps |
| `config/zones_config.json` | `weights.wind_speed_kmh` | 0.10 | Flame propagation accelerator | Topographical wind models |
| `config/zones_config.json` | `weights.soil_moisture_pct` | 0.15 | Ground fuel desiccation | Depth-stratified probes |
| `config/zones_config.json` | `weights.gas_ppm` | 0.15 | Smoldering combustion indicator | CO/CO2/VOC gas-specific ratios |
| `config/zones_config.json` | `weights.thermal_anomaly_c` | 0.15 | Infrared heating detection | Thermal camera radiometric feeds |
| `config/zones_config.json` | `weights.time_of_day` | 0.05 | Diurnal solar radiation peak | Real solar angle sensor |
| `config/zones_config.json` | `weights.seasonal_baseline` | 0.05 | Macro-seasonal drought factor | IMD API integration |

### 10.2. Confirmation Thresholds

| Location | Parameter | V1 Value | Rationale | V2 Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `config/zones_config.json` | Temperature confirmation | 40.0 deg C | Simlipal summer danger ceiling | 7-day rolling diurnal maximum |
| `config/zones_config.json` | Humidity confirmation | 25.0% | Air desiccation flashover point | Temperature-scaled dynamic threshold |
| `config/zones_config.json` | Wind speed confirmation | 25.0 km/h | Beaufort 4, ember-carrying breeze | Terrain-specific channeling |
| `config/zones_config.json` | Soil moisture confirmation | 10.0% | Explosive tinder point for Sal litter | Soil-type retention curves |
| `config/zones_config.json` | Gas/smoke confirmation | 30.0 ppm | Background 8-15 ppm; 30 = combustion | Dynamic baseline subtraction |
| `config/zones_config.json` | Thermal anomaly confirmation | 3.0 deg C | Surface elevation above ambient | Canopy shading index calibration |

### 10.3. State Thresholds

| Location | Parameter | V1 Value | Rationale | V2 Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `config/zones_config.json` | YELLOW threshold | 0.35 | Lower bound for heightened monitoring | Empirical ROC curve analysis |
| `config/zones_config.json` | ORANGE threshold | 0.60 | Pre-suppression trigger | Empirical ROC curve analysis |
| `config/zones_config.json` | RED threshold | 0.80 | Emergency NOC alert | Empirical ROC curve analysis |
| `src/scoring/state_machine.py` | Confirmation requirement | 3 sensors | 0% false positives under dual failure | Configurable per zone |

### 10.4. Timing and Network Parameters

| Location | Parameter | V1 Value | Rationale | V2 Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `config/zones_config.json` | Lateral warning timeout | 30 s | Expired warnings clear on wind shift | Dynamic: d/v calculation |
| `config/zones_config.json` | Neighbor distance | 8.0 km | Simlipal range outpost distance | Exact GIS centroid computation |
| `config/zones_config.json` | Bearing tolerance | 45.0 deg | Downwind dispersion quadrant | Gaussian puff plume model |
| `src/scoring/normalization.py` | Diurnal peak hour | 14 (2 PM) | Solar noon + thermal lag | GPS-based local solar noon |
| `src/fog_node_runner.py` | Node timeout duration | 15.0 s | 5 missed ticks at 3s interval | Exponential backoff heartbeat |
| `src/fog_node_runner.py` | Security cache max size | 1000 IDs | Prevent OOM in dedup cache | Redis/SQLite ring buffer |
| `src/fog_node_runner.py` | Advisory command TTL | 300 s | Replay window cutoff | Operator-specified TTL |
| `src/fog_node_runner.py` | Clock skew tolerance | 60 s | NTP sync drift margin | Hardware RTC / GPS PPS |
| `src/edge_sim.py` | Telemetry tick interval | 3.0 s | Balance responsiveness vs CPU | Adaptive sampling on WHI |
| `src/edge_sim.py` | Default GPS coordinates | [21.94, 86.32] | Simlipal Core Zone centroid | Hardware GPS NMEA parsing |
| `src/buffered_publisher.py` | Buffer deque capacity | 5000 items | ~4h offline telemetry per node | Persistent disk WAL |

### 10.5. Infrastructure Parameters

| Location | Parameter | V1 Value | Rationale | V2 Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `docker-compose.yml` | Port 1881 | Zone 4A Broker | Isolated local MQTT | DNS discovery |
| `docker-compose.yml` | Port 1883 | Zone 4B Broker | Isolated local MQTT | DNS discovery |
| `docker-compose.yml` | Port 1885 | Zone 4C Broker | Isolated local MQTT | DNS discovery |
| `docker-compose.yml` | Port 1884 | Cloud Broker | Central communication | Managed Kafka/EMQX |
| `docker-compose.yml` | Port 8086 | InfluxDB v2 | Time-series database | Distributed InfluxDB IOx |
| `docker-compose.yml` | Port 9000 | Cloud Dashboard | Web operations portal | Nginx + SSL termination |
| `src/cloud_dashboard/database.py` | Max query limit | 500 records | Sub-second API payloads | Paginated streaming cursor |
| `src/cloud_dashboard/database.py` | Ingestion buffer | 1000 items | Memory fallback during DB restart | Persistent WAL |
