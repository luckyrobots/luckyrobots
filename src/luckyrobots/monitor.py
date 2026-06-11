"""Event-style observer over StreamRobotController.

Subscribes to per-frame RobotControllerSummary updates from the engine and
emits high-level events when state changes are detected. Designed to be
single-threaded and asyncio-friendly.

Usage (sync, helper thread):
    mon = PolicyMonitor(session, entity_id=robot.entity_id)
    mon.on_active_change(lambda slot, was_active, now_active:
        print(f"slot {slot.name} active={now_active}"))
    mon.on_descriptor_swap(...)
    mon.run_in_thread()      # background thread, daemon=True
    ...
    mon.stop()

Events emitted:
- on_active_change(slot, was_active, now_active)
- on_ready_change(slot, was_ready, now_ready)
- on_descriptor_swap(slot, old_path, new_path)
- on_joint_claim_change(slot, added: list[str], removed: list[str])
- on_motion_graph_active_change(was_active, now_active)
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Iterator, Optional

from luckyrobots.grpc.generated import agent_pb2, common_pb2

logger = logging.getLogger("luckyrobots.monitor")

SlotChangeCallback = Callable[..., None]


class PolicyMonitor:
    """Observe per-frame RobotControllerSummary updates and emit events.

    Tracks the previous frame's slot list (keyed by slot_id) and compares
    each new frame to compute deltas. Callbacks are invoked from whichever
    thread drives the iterator (the helper thread when run_in_thread() is
    used, otherwise the caller's thread).
    """

    def __init__(self, session: Any, entity_id: int, target_fps: int = 30) -> None:
        self._session = session
        self._entity_id = int(entity_id)
        self._target_fps = int(target_fps)

        # Event listeners. Multiple callbacks per event are allowed.
        self._on_active: list[SlotChangeCallback] = []
        self._on_ready: list[SlotChangeCallback] = []
        self._on_descriptor: list[SlotChangeCallback] = []
        self._on_joint_claim: list[SlotChangeCallback] = []
        self._on_motion_graph: list[Callable[[bool, bool], None]] = []

        # Previous-frame state for delta computation.
        self._prev_slots: dict[int, agent_pb2.PolicySlotSummary] = {}
        self._prev_motion_graph_active: Optional[bool] = None

        # Stream + thread state.
        self._stream_call: Any = None
        self._thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()

    # Callback registration.
    def on_active_change(self, cb: SlotChangeCallback) -> None:
        self._on_active.append(cb)

    def on_ready_change(self, cb: SlotChangeCallback) -> None:
        self._on_ready.append(cb)

    def on_descriptor_swap(self, cb: SlotChangeCallback) -> None:
        self._on_descriptor.append(cb)

    def on_joint_claim_change(self, cb: SlotChangeCallback) -> None:
        self._on_joint_claim.append(cb)

    def on_motion_graph_active_change(self, cb: Callable[[bool, bool], None]) -> None:
        self._on_motion_graph.append(cb)

    # Iterator API. Yields RobotControllerSummary protos until stopped.
    def __iter__(self) -> Iterator[agent_pb2.RobotControllerSummary]:
        agent_stub = self._session.engine_client.agent
        request = agent_pb2.StreamRobotControllerRequest(
            entity=common_pb2.EntityId(id=self._entity_id),
            target_fps=self._target_fps,
        )
        try:
            self._stream_call = agent_stub.StreamRobotController(request)
        except Exception as e:
            logger.debug("StreamRobotController failed to open: %s", e)
            return

        try:
            for frame in self._stream_call:
                if self._stop_evt.is_set():
                    break
                self._dispatch(frame)
                yield frame
        except Exception as e:
            # grpc.RpcError, OperationCanceledException, etc. — terminate cleanly.
            logger.debug("PolicyMonitor stream ended: %s", e)
        finally:
            self._stream_call = None

    # Helper-thread API.
    def run_in_thread(self) -> threading.Thread:
        """Run the iterator in a daemon thread, dispatching events as they arrive."""
        if self._thread is not None and self._thread.is_alive():
            return self._thread

        self._stop_evt.clear()

        def _loop() -> None:
            for _ in self:
                if self._stop_evt.is_set():
                    break

        t = threading.Thread(
            target=_loop,
            name=f"PolicyMonitor-{self._entity_id}",
            daemon=True,
        )
        self._thread = t
        t.start()
        return t

    def stop(self) -> None:
        """Cancel the gRPC stream and join the helper thread (if any)."""
        self._stop_evt.set()
        call = self._stream_call
        if call is not None:
            try:
                call.cancel()
            except Exception:
                pass
        t = self._thread
        if t is not None and t.is_alive():
            t.join(timeout=2.0)
        self._thread = None

    # Optional asyncio iterator. Not implemented yet.
    async def __aiter__(self):  # type: ignore[override]
        raise NotImplementedError(
            "PolicyMonitor async iteration is not implemented yet. "
            "Use the sync iterator or run_in_thread()."
        )

    # Internals.
    def _dispatch(self, frame: agent_pb2.RobotControllerSummary) -> None:
        # Motion-graph active toggle.
        mg = bool(frame.motion_graph_active)
        if self._prev_motion_graph_active is None:
            self._prev_motion_graph_active = mg
        elif mg != self._prev_motion_graph_active:
            was = self._prev_motion_graph_active
            self._prev_motion_graph_active = mg
            for cb in self._on_motion_graph:
                self._safe_call(cb, was, mg)

        # Per-slot diffs, keyed by slot_id.
        new_slots: dict[int, agent_pb2.PolicySlotSummary] = {
            int(s.slot_id): s for s in frame.slots
        }

        for slot_id, slot in new_slots.items():
            prev = self._prev_slots.get(slot_id)
            if prev is None:
                # First sighting — don't fire change events; just seed.
                continue

            if bool(prev.active) != bool(slot.active):
                for cb in self._on_active:
                    self._safe_call(cb, slot, bool(prev.active), bool(slot.active))

            if bool(prev.ready) != bool(slot.ready):
                for cb in self._on_ready:
                    self._safe_call(cb, slot, bool(prev.ready), bool(slot.ready))

            if str(prev.descriptor_path) != str(slot.descriptor_path):
                for cb in self._on_descriptor:
                    self._safe_call(
                        cb, slot, str(prev.descriptor_path), str(slot.descriptor_path)
                    )

            prev_joints = set(prev.driven_joints)
            new_joints = set(slot.driven_joints)
            added = sorted(new_joints - prev_joints)
            removed = sorted(prev_joints - new_joints)
            if added or removed:
                for cb in self._on_joint_claim:
                    self._safe_call(cb, slot, added, removed)

        self._prev_slots = new_slots

    @staticmethod
    def _safe_call(cb: Callable[..., None], *args: Any) -> None:
        try:
            cb(*args)
        except Exception as e:
            logger.warning("PolicyMonitor callback raised: %s", e)
