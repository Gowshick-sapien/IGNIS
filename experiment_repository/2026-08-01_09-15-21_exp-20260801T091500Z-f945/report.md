# IGNIS — Consolidated Simulation Results Report

## 1. Executive Summary
- **Overall Verdict**: **FAIL**
- **Total Scenarios Evaluated**: 1
- **Verdict Breakdown**:
  - **Passed**: 0
  - **Failed**: 1
  - **Invalid**: 0
  - **Incomplete**: 0
- **Key Findings**:
  0 scenarios successfully satisfied all assertions.
  
  1 scenario failed assertion checks.
  
  0 scenarios could not be evaluated because required events were unavailable.
  
  Overall experiment verdict: FAIL.


## 2. Experimental Setup

### 2.1 Experiment Configuration
- **Trial Count per Scenario**: 5
- **Random Seed**: 4321
- **Total Execution Duration**: 0.99 seconds
- **Execution Date (UTC)**: 2026-08-01T09:15:02Z

### 2.2 Simulation Configuration
- **Zones Configured**: 3 (Zones 4A, 4B, 4C)
- **Edge Nodes per Zone**: 3
- **Fog Coordinator Nodes**: 3 (1 local per zone)
- **MQTT Broker Architecture**: 3 local brokers, 1 bridging cloud broker
- **InfluxDB Database Version**: 2.7
- **Message Transport Standard**: MQTT v3.1.1 (TCP/IP)
- **Scenario Checksums**:
  - **S1** (Version 1.0): `4a3f292bc5f81fa0...`
  - **S2** (Version 1.0): `9f826d74ce1ae826...`
  - **S3** (Version 1.0): `9f2704b7ff6899ce...`
  - **S4** (Version 1.0): `1d013fa6da5dfb5a...`
  - **S5** (Version 1.0): `4eaddb8c28d3a358...`
  - **S6** (Version 1.0): `4d856d49d9f260a6...`
  - **S7** (Version 1.0): `e709785255f052d7...`

### 2.3 Environment Metadata
- **OS**: Windows 11
- **CPU Architecture**: AMD64
- **Python Runtime Version**: 3.12.2
- **Git Active Commit**: `6f35d8e`
- **System Timezone**: India Standard Time
- **Execution Hostname**: Gowshick

### 2.4 Statistical Method
All numeric decision latency and lateral propagation measurements were aggregated across all completed trials. Confidence intervals are calculated using the 95% Student-t distribution boundaries:
$$\mu \pm t_{0.025, df} \cdot \left(\frac{s}{\sqrt{N}}\right)$$
Where degrees of freedom $df = N-1$. (CI calculation method: `internal_t_table`).


## 3. Scenario Execution

| Scenario | Trials | Verdict | Reason |
|---|---|---|---|
| **S2** | 5 | **FAIL** | Assertions failed: Assertion Failed: Expected: YELLOW, Observed: RED |

![Execution Gantt Timeline](charts/execution_timeline.png)


## 4. Experimental Results

### 4.1 Scenario S1
- **Status**: **INCOMPLETE**
- **Verdict Details**: N/A

*No numerical metrics recorded.*

---

### 4.2 Scenario S2
- **Status**: **FAIL**
- **Verdict Details**: Assertions failed: Assertion Failed: Expected: YELLOW, Observed: RED

| Metric | Value / Aggregates | Target | Operator | Status | Reason |
|---|---|---|---|---|---|
| max_state | Value: RED | YELLOW | <= | **FAIL** | RED <= threshold YELLOW |

---

### 4.3 Scenario S3
- **Status**: **INCOMPLETE**
- **Verdict Details**: N/A

*No numerical metrics recorded.*

![Decision Latency Distribution](charts/decision_latency_boxplot.png)
![Decision Latency Frequency Histogram](charts/decision_latency_histogram.png)
![Outbreak Escalation State Transitions](charts/state_transition_timeline.png)
---

### 4.4 Scenario S4
- **Status**: **INCOMPLETE**
- **Verdict Details**: N/A

*No numerical metrics recorded.*

![False Positive Trend](charts/false_positive_trend.png)
---

### 4.5 Scenario S5
- **Status**: **INCOMPLETE**
- **Verdict Details**: N/A

*No numerical metrics recorded.*

![Telemetry Buffering and Flushing Timeline](charts/offline_buffering_timeline.png)
---

### 4.6 Scenario S6
- **Status**: **INCOMPLETE**
- **Verdict Details**: N/A

*No numerical metrics recorded.*

![Lateral Propagation Time Comparison](charts/lateral_propagation_comparison.png)
![Lateral Propagation Interval](charts/lateral_propagation_ci.png)
---

### 4.7 Scenario S7
- **Status**: **INCOMPLETE**
- **Verdict Details**: N/A

*No numerical metrics recorded.*

![Message Crosstalk Ingestion Matrix](charts/message_integrity_heatmap.png)
---



## 5. Cross-Scenario Analysis

However, critical failures were observed in scenarios: S2. These failures imply that future testing and development must focus on strengthening the robustness of state clamping and offline synchronization.


![Scenario Comparison Durations](charts/scenario_comparison_summary.png)


## 6. Architecture Validation Summary

| Core Architecture Claim | Reference Scenario | Validation Status | Evidence / Reason |
|---|---|---|---|
| **Fog Decision Latency** (<1.0s target) | S3 | ⚪ Not Executed | No results calculated. |
| **Lateral Warning Propagation** (<10s window) | S6 | ⚪ Not Executed | No results calculated. |
| **False-Positive Suppression** (Local 3-Node check) | S4 | ⚪ Not Executed | No results calculated. |
| **Offline Continuity Cache** (Local mitigation action) | S5 | ⚪ Not Executed | No results calculated. |
| **Concurrent Outbreak Integrity** (No cross-talk) | S7 | ⚪ Not Executed | No results calculated. |


## 7. Discussion

Decision latency measurements could not be validated because Scenario S3 failed to generate sufficient events.

Offline continuity could not be validated because Scenario S5 produced insufficient evidence.

Concurrent multi-zone integrity could not be validated due to insufficient events.



## 8. Limitations
- **Synthetic Sensor Emulation**: Telemetry is generated via mock generators rather than actual outdoor wireless sensors.
- **RF and Physical Propagation Gaps**: The impact of RF interference, battery deterioration, and wireless packet drop rates under severe weather is simulated and does not capture full hardware constraints.
- **False-Positive Lower Bound**: With 10–30 trials, the statistical confidence for very rare false-positive rates remains bounded.


## 9. Conclusion
The orchestration, reporting and analytics pipeline successfully completed.

However, multiple experimental scenarios failed or produced insufficient evidence.

Additional implementation work is required before the architecture can be considered fully validated.
