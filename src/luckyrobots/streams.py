"""Timestamp-aligned multiplexer over multiple gRPC server-streams.

Combines N concurrent streams (e.g. StreamRobotController + StreamFullState
+ StreamCamera) into a single iterator of synchronized frames. Useful for
dataset collection where you want each yielded item to contain the latest
update from each source as of a common timestamp.

Usage:
    from luckyrobots.streams import StreamMultiplexer
    mux = StreamMultiplexer()
    mux.add("robot", session.engine_client.agent.StreamRobotController(req1))
    mux.add("state", session.engine_client.mujoco_scene.StreamFullState(req2))
    for batch in mux.run(period_s=0.05, timeout_s=10.0):
        # batch is a dict like {"robot": <RobotControllerSummary>, "state": <FullState>}
        ...
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Any, Dict, Iterable, Iterator, List, Optional

logger = logging.getLogger("luckyrobots.streams")


class StreamMultiplexer:
    """Merge multiple server-streams into one timestamp-aligned iterator."""

    def __init__(self) -> None:
        self._queues: Dict[str, "queue.Queue[Any]"] = {}
        self._streams: Dict[str, Iterable[Any]] = {}
        self._threads: List[threading.Thread] = []
        self._stop_event = threading.Event()

    def add(self, name: str, stream: Iterable[Any]) -> None:
        """Register a server-stream by friendly name. Spawns a daemon thread
        that drains the stream into an internal queue, keeping only the
        latest item (drops older ones — backpressure-friendly)."""
        if name in self._queues:
            raise ValueError(f"Stream {name!r} already registered.")
        q: "queue.Queue[Any]" = queue.Queue(maxsize=1)
        self._queues[name] = q
        self._streams[name] = stream

        def _drain(stream_ref: Iterable[Any], q_ref: "queue.Queue[Any]", name_ref: str) -> None:
            try:
                for item in stream_ref:
                    if self._stop_event.is_set():
                        break
                    # Drop older item to keep only the latest.
                    try:
                        q_ref.put_nowait(item)
                    except queue.Full:
                        try:
                            q_ref.get_nowait()
                        except queue.Empty:
                            pass
                        try:
                            q_ref.put_nowait(item)
                        except queue.Full:
                            pass
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.debug("Stream %s drain ended: %s", name_ref, e)

        t = threading.Thread(
            target=_drain,
            args=(stream, q, name),
            name=f"StreamMux[{name}]",
            daemon=True,
        )
        self._threads.append(t)
        t.start()

    def run(
        self,
        *,
        period_s: float = 0.05,
        timeout_s: Optional[float] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Yield dicts {name: latest_item}. `period_s` controls the merge
        cadence (server-stream items arrive at their own rates; this
        emits one merged dict every period_s). Stops when `timeout_s`
        elapsed or `stop()` was called."""
        if period_s <= 0:
            raise ValueError("period_s must be > 0")

        latest: Dict[str, Any] = {name: None for name in self._queues}
        deadline = (time.monotonic() + timeout_s) if timeout_s is not None else None

        next_emit = time.monotonic()
        while not self._stop_event.is_set():
            if deadline is not None and time.monotonic() >= deadline:
                break

            # Drain the freshest item per queue (non-blocking).
            for name, q in self._queues.items():
                latest_item = latest[name]
                while True:
                    try:
                        latest_item = q.get_nowait()
                    except queue.Empty:
                        break
                latest[name] = latest_item

            yield dict(latest)

            next_emit += period_s
            sleep_for = next_emit - time.monotonic()
            if sleep_for > 0:
                # Sleep in small chunks so stop()/timeout reacts quickly.
                if self._stop_event.wait(timeout=sleep_for):
                    break
            else:
                # Behind schedule; reset cadence to now to avoid runaway catch-up.
                next_emit = time.monotonic()

    def stop(self) -> None:
        """Signal all stream threads to stop and wait for them to exit."""
        self._stop_event.set()
        # Try to cancel each underlying gRPC stream so blocking iteration unblocks.
        for name, stream in self._streams.items():
            cancel = getattr(stream, "cancel", None)
            if callable(cancel):
                try:
                    cancel()
                except Exception as e:
                    logger.debug("cancel() on stream %s failed: %s", name, e)
        for t in self._threads:
            try:
                t.join(timeout=2.0)
            except Exception:
                pass
