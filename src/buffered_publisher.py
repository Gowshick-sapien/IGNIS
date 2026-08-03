import collections
import threading
import logging
from src.clock import default_clock

logger = logging.getLogger("buffered_publisher")

class BufferedPublisher:
    def __init__(self, client, clock=default_clock, maxlen=5000):
        self.client = client
        self.clock = clock
        self.maxlen = maxlen
        self.buffer = collections.deque(maxlen=maxlen)
        self._is_connected = False
        self.lock = threading.Lock()

    def publish(self, topic: str, payload: str) -> bool:
        with self.lock:
            if self._is_connected:
                try:
                    res = self.client.publish(topic, payload)
                    if res is not None and hasattr(res, 'rc'):
                        if isinstance(res.rc, int) and res.rc != 0:
                            self.buffer.append((topic, payload))
                            return False
                    return True
                except Exception as e:
                    logger.warning(f"Failed to publish directly, buffering message. Error: {e}")
                    self.buffer.append((topic, payload))
                    return False
            else:
                self.buffer.append((topic, payload))
                return False

    def flush(self) -> int:
        flushed_count = 0
        with self.lock:
            if not self._is_connected:
                return 0
            while self.buffer:
                topic, payload = self.buffer[0]
                try:
                    # Inject buffering metadata if payload is JSON
                    try:
                        import json
                        data = json.loads(payload)
                        if isinstance(data, dict):
                            data["was_buffered"] = True
                            data["buffer_flush_timestamp"] = self.clock.strftime("%Y-%m-%dT%H:%M:%SZ")
                            payload = json.dumps(data)
                    except Exception:
                        pass
                    res = self.client.publish(topic, payload)
                    if res is not None and hasattr(res, 'rc'):
                        if isinstance(res.rc, int) and res.rc != 0:
                            break
                    self.buffer.popleft()
                    flushed_count += 1
                except Exception as e:
                    logger.warning(f"Error during buffer flush: {e}")
                    break
        return flushed_count

    def on_connect(self):
        with self.lock:
            self._is_connected = True

    def on_disconnect(self):
        with self.lock:
            self._is_connected = False

    @property
    def is_connected(self) -> bool:
        with self.lock:
            return self._is_connected

    @property
    def buffer_size(self) -> int:
        with self.lock:
            return len(self.buffer)
