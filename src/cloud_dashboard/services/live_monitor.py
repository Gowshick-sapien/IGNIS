"""IGNIS SSE Progress Broadcaster (Phase G3).

Asynchronous Server-Sent Events broadcaster supporting multi-client fan-out, 15s heartbeats, bounded queues, and active experiment replay.
"""

import os
import json
import logging
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional, Any

logger = logging.getLogger("live_monitor")


class LiveMonitor:
    """Singleton SSE broadcaster delivering progress events to connected client queues."""

    _instance: Optional["LiveMonitor"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LiveMonitor, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, workspace_dir: Optional[str] = None):
        with self._lock:
            if workspace_dir:
                self.workspace_dir = os.path.abspath(workspace_dir)
                self.jsonl_path = os.path.join(self.workspace_dir, "results", "progress_events.jsonl")

            if getattr(self, "_initialized", False):
                return

            if not hasattr(self, "workspace_dir"):
                self.workspace_dir = os.path.abspath(workspace_dir or os.getcwd())
                self.jsonl_path = os.path.join(self.workspace_dir, "results", "progress_events.jsonl")

            self.client_queues: Set[asyncio.Queue] = set()
            self._heartbeat_task: Optional[asyncio.Task] = None
            self._initialized = True
            logger.info("LiveMonitor singleton initialized.")

    def register_client(self, maxsize: int = 5000) -> asyncio.Queue:
        """Create and register a bounded client queue for SSE streaming."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self.client_queues.add(queue)
        logger.info(f"Registered new SSE client. Total active clients: {len(self.client_queues)}")
        return queue

    def unregister_client(self, queue: asyncio.Queue) -> None:
        """Remove a client queue upon disconnect."""
        self.client_queues.discard(queue)
        logger.info(f"Unregistered SSE client. Total active clients: {len(self.client_queues)}")

    def broadcast_event(self, event_payload: Dict[str, Any]) -> None:
        """Fan-out event payload to all registered client queues."""
        if not self.client_queues:
            return

        dead_queues = set()
        for q in list(self.client_queues):
            try:
                q.put_nowait(event_payload)
            except asyncio.QueueFull:
                logger.warning("Client SSE queue full (maxsize=5000 reached), dropping client queue.")
                dead_queues.add(q)
            except Exception as e:
                logger.debug(f"Error broadcasting to client queue: {e}")
                dead_queues.add(q)

        for dq in dead_queues:
            self.client_queues.discard(dq)

    def replay_active_experiment(self, queue: asyncio.Queue, active_experiment_id: Optional[str]) -> int:
        """Replay progress_events.jsonl filtered strictly by active_experiment_id to catch up new clients."""
        if not active_experiment_id or not os.path.exists(self.jsonl_path):
            return 0

        replayed_count = 0
        try:
            with open(self.jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event_data = json.loads(line)
                        if event_data.get("experiment_id") == active_experiment_id:
                            queue.put_nowait(event_data)
                            replayed_count += 1
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Error replaying active experiment events: {e}")

        logger.info(f"Replayed {replayed_count} events for experiment {active_experiment_id} to new client.")
        return replayed_count

    def get_heartbeat_payload(self) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "event": "HEARTBEAT",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def _heartbeat_loop(self) -> None:
        """Periodic background task sending HEARTBEAT every 15s."""
        logger.info("SSE Heartbeat loop started (15s interval).")
        try:
            while True:
                await asyncio.sleep(15)
                if self.client_queues:
                    hb = self.get_heartbeat_payload()
                    self.broadcast_event(hb)
        except asyncio.CancelledError:
            logger.info("SSE Heartbeat loop cancelled.")
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")

    def start_heartbeat(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Start the background heartbeat task if not running."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            target_loop = loop or asyncio.get_event_loop()
            self._heartbeat_task = target_loop.create_task(self._heartbeat_loop())

    def stop_heartbeat(self) -> None:
        """Cancel the background heartbeat task."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
