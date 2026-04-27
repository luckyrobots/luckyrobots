"""Record + replay sessions for offline RL / debugging.

Captures every Set*/Get* call against a Session into a structured event log
that can be saved as Parquet (preferred) or JSONL (fallback when pyarrow
isn't installed). Replay re-issues the events in order at the original
timestamps (or scaled by `speed`).

Usage:
    with session.record() as rec:
        for _ in range(100):
            robot.set_command_float("Walker", "SetVx", 0.5)
            sess.step(...)
    rec.save("episode.parquet")   # or "episode.jsonl"

    # Later:
    rec2 = SessionRecording.load("episode.parquet")
    rec2.replay(session, speed=1.0)
"""
from __future__ import annotations

import contextlib
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, ContextManager, Dict, Iterator, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .session import Session

logger = logging.getLogger("luckyrobots.recording")


# ── Stub introspection ────────────────────────────────────────────────────

# RPC name → request proto class. Populated lazily by `_build_rpc_registry`.
_RPC_REQUEST_REGISTRY: Optional[Dict[str, type]] = None
# Service short name → (stub class, attribute on engine_client)
_STUB_BINDINGS = (
    ("AgentService", "agent"),
    ("MujocoSceneService", "mujoco_scene"),
    ("MujocoService", "mujoco"),
    ("SceneService", "scene"),
    ("CameraService", "camera"),
    ("DebugService", "debug"),
)


def _build_rpc_registry() -> Dict[str, type]:
    """Walk the generated *_pb2_grpc Stub classes and extract method → request type.

    The generated stubs hold method handles as ``channel.unary_unary(...)``
    calls inside ``__init__``; the request class is referenced via the
    ``request_serializer=<Cls>.SerializeToString`` argument. Rather than
    parse source, we instantiate each stub against a recording dummy
    channel that captures the (method_path, request_serializer) pairs.
    """
    global _RPC_REQUEST_REGISTRY
    if _RPC_REQUEST_REGISTRY is not None:
        return _RPC_REQUEST_REGISTRY

    registry: Dict[str, type] = {}

    class _Probe:
        """Mimics enough of grpc.Channel to capture serializer types."""

        def __init__(self) -> None:
            self.records: List[tuple] = []

        def _record(self, method, request_serializer=None, **_kw):  # noqa: ANN001
            self.records.append((method, request_serializer))

            def _call(*_a, **_kw2):  # pragma: no cover - never invoked
                raise RuntimeError("probe stub is not callable")

            return _call

        unary_unary = _record
        unary_stream = _record
        stream_unary = _record
        stream_stream = _record

    try:
        from .grpc.generated import (  # type: ignore
            agent_pb2_grpc,
            mujoco_scene_pb2_grpc,
            mujoco_pb2_grpc,
            scene_pb2_grpc,
            camera_pb2_grpc,
            debug_pb2_grpc,
        )
    except Exception as e:  # pragma: no cover
        logger.warning("Could not load generated stubs for RPC registry: %s", e)
        _RPC_REQUEST_REGISTRY = registry
        return registry

    stub_modules = [
        ("AgentService", agent_pb2_grpc.AgentServiceStub),
        ("MujocoSceneService", mujoco_scene_pb2_grpc.MujocoSceneServiceStub),
        ("MujocoService", mujoco_pb2_grpc.MujocoServiceStub),
        ("SceneService", scene_pb2_grpc.SceneServiceStub),
        ("CameraService", camera_pb2_grpc.CameraServiceStub),
        ("DebugService", debug_pb2_grpc.DebugServiceStub),
    ]

    for short_name, stub_cls in stub_modules:
        probe = _Probe()
        try:
            stub_cls(probe)
        except Exception as e:  # pragma: no cover
            logger.debug("Could not introspect %s: %s", stub_cls, e)
            continue
        for method_path, serializer in probe.records:
            # method_path looks like "/hazel.rpc.AgentService/SetPolicyCommandFloat"
            tail = method_path.rsplit("/", 1)[-1] if isinstance(method_path, str) else None
            if not tail:
                continue
            request_cls = getattr(serializer, "__self__", None) if serializer else None
            # SerializeToString is a bound method on the proto class instance,
            # but at registration time it's the unbound `Cls.SerializeToString`,
            # so __self__ is None. Recover the class via __qualname__.
            if request_cls is None and serializer is not None:
                qual = getattr(serializer, "__qualname__", "")
                cls_name = qual.split(".", 1)[0] if qual else ""
                if cls_name:
                    # Hunt the class through the same module the stub came from
                    pb2_module_name = stub_cls.__module__.replace("_pb2_grpc", "_pb2")
                    try:
                        import importlib
                        pb2_mod = importlib.import_module(pb2_module_name)
                        request_cls = getattr(pb2_mod, cls_name, None)
                    except Exception:
                        request_cls = None
            if request_cls is None:
                continue
            registry[f"{short_name}.{tail}"] = request_cls

    _RPC_REQUEST_REGISTRY = registry
    return registry


# ── Data model ────────────────────────────────────────────────────────────


@dataclass
class RecordedEvent:
    timestamp_s: float       # monotonic seconds since recording started
    rpc: str                 # e.g. "AgentService.SetPolicyCommandFloat"
    request_json: str        # canonical JSON of the request proto (MessageToJson)
    response_json: Optional[str] = None  # for getters; None for setters


@dataclass
class SessionRecording:
    started_at: float = field(default_factory=time.time)   # wall-clock for the file header
    events: List[RecordedEvent] = field(default_factory=list)

    # ---- persistence ------------------------------------------------------

    def save(self, path: str) -> None:
        """Save as parquet (.parquet) or jsonl (.jsonl). Determined by extension."""
        ext = os.path.splitext(path)[1].lower()
        if ext == ".parquet":
            self._save_parquet(path)
        elif ext in (".jsonl", ".json"):
            self._save_jsonl(path)
        else:
            raise ValueError(
                f"Unknown recording extension '{ext}'. Use .parquet or .jsonl."
            )

    def _save_jsonl(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            header = {"_header": True, "started_at": self.started_at}
            f.write(json.dumps(header) + "\n")
            for ev in self.events:
                f.write(json.dumps(asdict(ev)) + "\n")

    def _save_parquet(self, path: str) -> None:
        try:
            import pyarrow as pa  # type: ignore
            import pyarrow.parquet as pq  # type: ignore
        except ImportError as e:
            raise ImportError(
                "Saving SessionRecording as Parquet requires pyarrow. "
                "Install with `pip install pyarrow`, or save as .jsonl instead."
            ) from e

        cols = {
            "timestamp_s": [ev.timestamp_s for ev in self.events],
            "rpc": [ev.rpc for ev in self.events],
            "request_json": [ev.request_json for ev in self.events],
            "response_json": [ev.response_json for ev in self.events],
        }
        table = pa.table(cols, metadata={b"started_at": str(self.started_at).encode()})
        pq.write_table(table, path)

    @classmethod
    def load(cls, path: str) -> "SessionRecording":
        """Load from parquet or jsonl."""
        ext = os.path.splitext(path)[1].lower()
        if ext == ".parquet":
            return cls._load_parquet(path)
        if ext in (".jsonl", ".json"):
            return cls._load_jsonl(path)
        raise ValueError(f"Unknown recording extension '{ext}'. Use .parquet or .jsonl.")

    @classmethod
    def _load_jsonl(cls, path: str) -> "SessionRecording":
        rec = cls(events=[])
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if obj.get("_header"):
                    rec.started_at = float(obj.get("started_at", time.time()))
                    continue
                rec.events.append(RecordedEvent(**obj))
        return rec

    @classmethod
    def _load_parquet(cls, path: str) -> "SessionRecording":
        try:
            import pyarrow.parquet as pq  # type: ignore
        except ImportError as e:
            raise ImportError(
                "Loading Parquet SessionRecording requires pyarrow. "
                "Install with `pip install pyarrow`."
            ) from e
        table = pq.read_table(path)
        meta = table.schema.metadata or {}
        started_at = float(meta.get(b"started_at", b"0") or b"0")
        rec = cls(started_at=started_at, events=[])
        cols = table.to_pydict()
        n = len(cols.get("timestamp_s", []))
        for i in range(n):
            rec.events.append(
                RecordedEvent(
                    timestamp_s=float(cols["timestamp_s"][i]),
                    rpc=str(cols["rpc"][i]),
                    request_json=str(cols["request_json"][i]),
                    response_json=cols["response_json"][i] if cols["response_json"][i] is not None else None,
                )
            )
        return rec

    # ---- replay -----------------------------------------------------------

    def replay(
        self,
        session: "Session",
        *,
        speed: float = 1.0,
        include: Optional[set] = None,
    ) -> None:
        """Re-issue events at original spacing (scaled by speed). `include`
        filters by RPC name, e.g. {"AgentService.SetPolicyCommandFloat"}."""
        if speed == 0:
            raise ValueError("Replay speed=0 is not allowed (would be infinite speed).")
        if speed < 0:
            raise ValueError("Replay speed must be positive.")

        try:
            from google.protobuf import json_format  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "Replay requires google.protobuf (transitive dep of grpc)."
            ) from e

        registry = _build_rpc_registry()
        client = getattr(session, "engine_client", None)
        if client is None:
            raise RuntimeError("Session has no engine_client; call start()/connect() first.")

        prev_ts: Optional[float] = None
        for ev in self.events:
            if include is not None and ev.rpc not in include:
                prev_ts = ev.timestamp_s
                continue

            if prev_ts is not None:
                dt = ev.timestamp_s - prev_ts
                if dt > 0:
                    time.sleep(max(0.0, dt / speed))
            prev_ts = ev.timestamp_s

            short, _, method = ev.rpc.partition(".")
            if not method:
                logger.warning("Skipping malformed RPC name in event: %r", ev.rpc)
                continue
            stub_attr = next(
                (attr for name, attr in _STUB_BINDINGS if name == short),
                None,
            )
            if stub_attr is None:
                logger.warning("No stub binding for service %s; skipping", short)
                continue
            stub = getattr(client, stub_attr, None)
            if stub is None:
                logger.warning("Client has no `%s` stub; skipping %s", stub_attr, ev.rpc)
                continue
            handle = getattr(stub, method, None)
            if handle is None:
                logger.warning("Stub %s missing method %s; skipping", short, method)
                continue
            request_cls = registry.get(ev.rpc)
            if request_cls is None:
                logger.warning("No request type registered for %s; skipping", ev.rpc)
                continue

            try:
                req = json_format.Parse(ev.request_json, request_cls())
                handle(req)
            except Exception as e:
                logger.warning("Replay of %s failed: %s", ev.rpc, e)


# ── Recording context ────────────────────────────────────────────────────


def _wrap_stub_callables(
    stub: Any,
    service_short_name: str,
    recording: SessionRecording,
    start_monotonic: float,
) -> Dict[str, Any]:
    """Wrap each public callable on `stub` with a logging wrapper.

    Returns a dict mapping attribute name to its original callable so the
    context manager can restore them afterwards.
    """
    try:
        from google.protobuf import json_format  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "Recording requires google.protobuf (transitive dep of grpc)."
        ) from e

    originals: Dict[str, Any] = {}

    for attr_name in dir(stub):
        if attr_name.startswith("_"):
            continue
        original = getattr(stub, attr_name, None)
        if not callable(original):
            continue
        # Skip non-method attributes (we only want gRPC method handles).
        # gRPC method handles are MultiCallable instances, but they may also
        # be plain functions in tests; treat any callable as wrap-able.
        rpc_name = f"{service_short_name}.{attr_name}"

        def make_wrapper(orig: Any, name: str) -> Callable[..., Any]:
            def wrapper(request, *args, **kwargs):
                ts = time.monotonic() - start_monotonic
                try:
                    req_json = json_format.MessageToJson(
                        request, preserving_proto_field_name=True
                    )
                except Exception:
                    req_json = ""
                response = orig(request, *args, **kwargs)
                resp_json: Optional[str] = None
                # Only serialize unary responses; streams are not recorded here.
                try:
                    if hasattr(response, "DESCRIPTOR"):
                        resp_json = json_format.MessageToJson(
                            response, preserving_proto_field_name=True
                        )
                except Exception:
                    resp_json = None
                recording.events.append(
                    RecordedEvent(
                        timestamp_s=ts,
                        rpc=name,
                        request_json=req_json,
                        response_json=resp_json,
                    )
                )
                return response

            return wrapper

        try:
            setattr(stub, attr_name, make_wrapper(original, rpc_name))
            originals[attr_name] = original
        except Exception:
            # Some attributes may be read-only on certain stub objects; skip.
            continue

    return originals


@contextlib.contextmanager
def record_session(session: "Session") -> Iterator[SessionRecording]:
    """Wrap the session's stub method handles to log every call.

    Restores the original methods on exit (even if an exception was raised
    inside the ``with`` block).
    """
    client = getattr(session, "engine_client", None)
    if client is None:
        raise RuntimeError(
            "Session has no engine_client. Call session.start()/connect() before recording."
        )

    recording = SessionRecording()
    start_monotonic = time.monotonic()

    # Save the originals so we can restore them on exit. Stored per-stub.
    saved: List[tuple] = []  # (stub, {attr: original})
    try:
        for short_name, attr in _STUB_BINDINGS:
            stub = getattr(client, attr, None)
            if stub is None:
                continue
            originals = _wrap_stub_callables(stub, short_name, recording, start_monotonic)
            if originals:
                saved.append((stub, originals))
        yield recording
    finally:
        for stub, originals in saved:
            for attr_name, orig in originals.items():
                try:
                    setattr(stub, attr_name, orig)
                except Exception:
                    pass
