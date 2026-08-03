# IGNIS Research Reproducibility Bundle

**Experiment ID**: `exp-20260803T041519Z-aad9`  
**Overall Verdict**: `PASS`  
**Git Commit**: `unknown`  
**Trial Count**: `10`  
**Execution Duration**: `3.3356 seconds`  

---

## 1. System & Environment Requirements
- **Python Version**: 3.11.15
- **Operating System**: Linux 6.6.87.2-microsoft-standard-WSL2
- **Docker Version**: unknown
- **Required Container Images**:
  - `python:3.11-slim` (fog-node, edge-sim)
  - `eclipse-mosquitto:2` (mqtt-broker)
  - `influxdb:2.7` (influxdb time-series)

---

## 2. How to Reproduce Results
1. Install Python dependencies: `pip install -r environment/requirements.txt`
2. Start background container services: `docker compose up -d`
3. Execute deterministic scenario replay:
   ```bash
   python -m src.run_experiment --trials 10 --seed 4321
   ```
4. Verify generated outputs against `data/metrics.json` and `report/report.html`.

---

## 3. Core Artifact SHA256 Checksums
| File | SHA256 Hash |
|---|---|
| `data/metrics.json` | `ea4088ae15817a1e78fc5b80d3548d8ea741673efb624d3e52db40cd37366cd9` |
| `data/raw_results.json` | `13e34dbbb694e2d06c5097b863a43bb36ce778185534fa61c8a45f49e041c182` |
| `data/experiment_manifest.json` | `5096042964f4ae824cd37106a9226feabb2f0010dd4f612cdcb98b091878309a` |
| `report/report.html` | `75eec1793ed77f36ac498cbfc8145a4b28fd85527415d1767406f5256491dfb6` |
| `report/project_results_report.md` | `7c9a47aa181abb71441d364260156857b731a43844ab747a3560a12667bf8a60` |
