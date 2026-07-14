# Testing Guidelines — Phase D, Sub-Phase D2: Docker Compose Multi-Zone Infrastructure

This document describes the validation and integration testing procedures for **Phase D, Sub-Phase D2 (Docker Compose Multi-Zone Infrastructure)** of the IGNIS system.

---

## Verification Procedures

### 1. Schema Validation
Verify that the `docker-compose.yml` config is structurally valid and YAML anchors expand correctly:
```bash
docker compose config
```
This should output the full resolved YAML configuration without raising syntax or parsing errors.

### 2. Stack Deployment (Manual)
To verify that all services and containers spin up correctly, run:
```bash
docker compose up --build -d
```

Ensure the following ports are mapped and accessible:
- NOC Cloud Dashboard: `http://localhost:9000`
- Zone 4B Control Center: `http://localhost:8000`
- InfluxDB: `http://localhost:8086`
- Central Cloud MQTT Broker: `localhost:1884`
- Zone 4A MQTT Broker: `localhost:1881`
- Zone 4B MQTT Broker: `localhost:1883`
- Zone 4C MQTT Broker: `localhost:1885`

### 3. Container Verification
Check container logs to verify the edge sims and runners are connected to their proper brokers:
```bash
# Verify fog-node-4a logs and connection
docker logs ignis-fog-node-4a

# Verify edge nodes of Zone 4A are publishing telemetry to broker 4A
docker logs ignis-edge-4a-e1
```
Ensure there are no connection errors in any container logs.
