# Phase E2 Walkthrough: Fog Node Cloud-Disconnect Resilience

Phase E2 implements the integration of Phase E1's abstractions (injectable clock and reusable buffered publisher) into `FogNodeRunner` to ensure local execution continuity and telemetry queuing during cloud broker outages.

## Architecture

```mermaid
graph TD
    runner["src/fog_node_runner.py<br/>FogNodeRunner"]
    publisher["src/buffered_publisher.py<br/>BufferedPublisher"]
    clock["src/clock.py<br/>Clock/MockClock"]
    broker["Cloud MQTT Broker"]

    runner -->|wraps publish| publisher
    runner -->|timestamps/sleeps| clock
    publisher -->|connected = True| broker
    publisher -.->|connected = False (queue)| buffer[(deque)]
```

---

## 1. Injectable Clock Integration
- Added support for the `clock` parameter in `FogNodeRunner.__init__`, storing it in `self.clock` (defaulting to `default_clock`).
- Bypassed all standard `time.time()`, `time.sleep()`, and `time.strftime()` calls with `self.clock.time()`, `self.clock.sleep()`, and `self.clock.strftime()`.
- This decouples the time tracking inside the runner from system time, allowing deterministic unit test execution (e.g. TTL checks, offline time progression) via `MockClock`.

---

## 2. Reusable Buffered Publisher Integration
- Wrapped the cloud client connection (`self.client_cloud`) using the `BufferedPublisher` instance:
  `self.cloud_publisher = BufferedPublisher(self.client_cloud, clock=self.clock)`
- Replaced all raw calls to `self.client_cloud.publish()` with `self.cloud_publisher.publish()`.
- Wired the network disconnect callback:
  ```python
  def on_disconnect_cloud(self, client, userdata, rc):
      self.cloud_publisher.on_disconnect()
      logger.warning(f"Disconnected from CLOUD MQTT broker. Return code: {rc}")
  ```
- Updated the connect callback `on_connect_cloud()` to invoke `self.cloud_publisher.on_connect()` and trigger `self.cloud_publisher.flush()`. This guarantees that enqueued telemetry automatically drains in sequential (FIFO) order when the cloud connection returns.

---

## 3. Local Continuity Logging
- Introduced stdout info logs whenever emergency action logs (`ORANGE` or `RED` risk state mitigations) are triggered while offline:
  ```python
  if not self.cloud_publisher.is_connected:
      logger.info(f"[Offline Continuity] Action Log: {json.dumps(action_payload)}")
  ```
- This ensures operators on-site have confirmation of local action execution despite central broker outages.

---

## 4. Legacy Backward Compatibility
- Implemented `@property` getter/setter fallbacks for `clock` and `cloud_publisher` on the `FogNodeRunner` class.
- When subclassed by existing mock runners in legacy test modules (`test_aggregation.py`, `test_cloud_resilience.py`) that bypass `__init__`, these properties automatically construct default instances, maintaining 100% test compatibility.
