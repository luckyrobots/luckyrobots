"""Session-startup validation pass.

Walks the connected scene and emits warnings about misconfiguration that
will cause silent runtime failures: missing descriptors, DrivenJoint names
that don't match descriptor joints, duplicate slot priorities, registry
RPC unavailability.

Usage:
    from luckyrobots.validation import validate_session
    warnings = validate_session(session)
    for w in warnings:
        print(w.severity, w.message)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, List, Literal, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .session import Session

logger = logging.getLogger("luckyrobots.validation")

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class ValidationWarning:
    severity: Severity
    code: str          # short stable id (e.g. "missing_descriptor", "duplicate_priority")
    message: str       # human-readable
    entity_id: Optional[int] = None
    slot_id: Optional[int] = None


# Method probed to confirm the policy RPC surface is present on the server.
_POLICY_PROBE_RPC = "hazel.rpc.AgentService/SetPolicyDrivenJoints"


def _emit(out: List[ValidationWarning], warning: ValidationWarning) -> None:
    """Append to the result list and mirror to the package logger."""
    out.append(warning)
    log_fn: Callable[..., None]
    if warning.severity == "error":
        log_fn = logger.error
    elif warning.severity == "warning":
        log_fn = logger.warning
    else:
        log_fn = logger.info
    log_fn(
        "[%s] %s%s%s",
        warning.code,
        warning.message,
        f" (entity={warning.entity_id})" if warning.entity_id is not None else "",
        f" (slot={warning.slot_id})" if warning.slot_id is not None else "",
    )


def _safe_check(
    out: List[ValidationWarning],
    name: str,
    fn: Callable[[], None],
) -> None:
    """Run ``fn`` inside a try/except so one check's failure can't block others."""
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 — validation must never raise
        _emit(
            out,
            ValidationWarning(
                severity="error",
                code="validation_internal_error",
                message=f"check '{name}' raised {type(exc).__name__}: {exc}",
            ),
        )


def validate_session(session: "Session") -> List[ValidationWarning]:
    """Run all checks; emit each via ``logger.<severity>`` AND return the list.

    Always safe to call (catches and reports its own internal errors as
    severity='error' code='validation_internal_error'). The function never
    raises; callers decide whether any returned warning is fatal.
    """
    out: List[ValidationWarning] = []

    # ---- channel + RPC surface probe ------------------------------------
    try:
        from .reflection import has_rpc
    except Exception as exc:  # noqa: BLE001
        _emit(
            out,
            ValidationWarning(
                severity="error",
                code="validation_internal_error",
                message=f"could not import reflection helpers: {exc}",
            ),
        )
        return out

    channel = None
    try:
        engine_client = getattr(session, "engine_client", None)
        if engine_client is not None:
            channel = getattr(engine_client, "channel", None)
    except Exception as exc:  # noqa: BLE001 — engine_client property may raise when disconnected
        _emit(
            out,
            ValidationWarning(
                severity="error",
                code="policy_rpcs_unavailable",
                message=f"session is not connected ({type(exc).__name__}: {exc})",
            ),
        )
        return out

    if channel is None:
        _emit(
            out,
            ValidationWarning(
                severity="error",
                code="policy_rpcs_unavailable",
                message="session has no active gRPC channel; call session.start()/connect() first",
            ),
        )
        return out

    try:
        rpc_present = has_rpc(channel, _POLICY_PROBE_RPC)
    except Exception as exc:  # noqa: BLE001
        _emit(
            out,
            ValidationWarning(
                severity="error",
                code="policy_rpcs_unavailable",
                message=f"reflection probe failed: {type(exc).__name__}: {exc}",
            ),
        )
        return out

    if not rpc_present:
        _emit(
            out,
            ValidationWarning(
                severity="error",
                code="policy_rpcs_unavailable",
                message=(
                    f"server does not advertise {_POLICY_PROBE_RPC}; the connected "
                    "engine build is too old for the policy SDK surface"
                ),
            ),
        )
        return out

    # ---- import the scene-walk helpers (defer for circular-import safety)
    try:
        from .robots.robot_controller import (
            list_policy_descriptors,
            list_robot_controllers,
        )
    except Exception as exc:  # noqa: BLE001
        _emit(
            out,
            ValidationWarning(
                severity="error",
                code="validation_internal_error",
                message=f"could not import robot_controller helpers: {exc}",
            ),
        )
        return out

    # ---- pull scene state once; subsequent checks reuse these snapshots --
    descriptors = []
    controllers = []

    def _load_descriptors() -> None:
        nonlocal descriptors
        descriptors = list(list_policy_descriptors(session))

    def _load_controllers() -> None:
        nonlocal controllers
        controllers = list(list_robot_controllers(session))

    _safe_check(out, "load_descriptors", _load_descriptors)
    _safe_check(out, "load_controllers", _load_controllers)

    # ---- check #2: registry_empty ---------------------------------------
    def _check_registry_empty() -> None:
        if not descriptors:
            _emit(
                out,
                ValidationWarning(
                    severity="warning",
                    code="registry_empty",
                    message=(
                        "list_policy_descriptors returned no entries — the engine's "
                        "PolicyRegistry.yaml may be missing or failed to load"
                    ),
                ),
            )

    _safe_check(out, "registry_empty", _check_registry_empty)

    # Build descriptor lookup once for downstream checks.
    descriptor_keys: set[str] = set()
    for d in descriptors:
        pid = getattr(d, "policy_id", "")
        path = getattr(d, "descriptor_path", "")
        if pid:
            descriptor_keys.add(pid)
        if path:
            descriptor_keys.add(path)

    # ---- per-robot, per-slot checks -------------------------------------
    for controller in controllers:
        entity_id = getattr(controller, "entity_id", None)
        slots = list(getattr(controller, "slots", ()) or ())

        # check #5: duplicate_slot_priority — within this robot, scan active
        # slots for shared priorities.
        def _check_duplicate_priority(_slots=slots, _entity_id=entity_id) -> None:
            seen: dict[int, list[int]] = {}
            for slot in _slots:
                if not getattr(slot, "active", False):
                    continue
                prio = getattr(slot, "priority", None)
                if prio is None:
                    continue
                seen.setdefault(int(prio), []).append(int(getattr(slot, "slot_id", -1)))
            for prio, slot_ids in seen.items():
                if len(slot_ids) > 1:
                    _emit(
                        out,
                        ValidationWarning(
                            severity="warning",
                            code="duplicate_slot_priority",
                            message=(
                                f"slots {slot_ids} share priority {prio}; they may "
                                "race for joint claims (sometimes intentional)"
                            ),
                            entity_id=_entity_id,
                        ),
                    )

        _safe_check(out, "duplicate_slot_priority", _check_duplicate_priority)

        for slot in slots:
            slot_id = int(getattr(slot, "slot_id", -1))
            descriptor_path = getattr(slot, "descriptor_path", "") or ""
            driven_joints = tuple(getattr(slot, "driven_joints", ()) or ())
            policy_joints = tuple(getattr(slot, "policy_joint_names", ()) or ())
            command_id_map = tuple(getattr(slot, "command_id_map", ()) or ())
            slot_active = bool(getattr(slot, "active", False))
            slot_ready = bool(getattr(slot, "ready", False))

            # check #3: missing_descriptor
            def _check_missing_descriptor(
                _path=descriptor_path,
                _entity_id=entity_id,
                _slot_id=slot_id,
            ) -> None:
                if not _path:
                    return
                if _path in descriptor_keys:
                    return
                _emit(
                    out,
                    ValidationWarning(
                        severity="error",
                        code="missing_descriptor",
                        message=(
                            f"slot references descriptor_path '{_path}' which is not "
                            "present in the loaded PolicyRegistry"
                        ),
                        entity_id=_entity_id,
                        slot_id=_slot_id,
                    ),
                )

            _safe_check(out, "missing_descriptor", _check_missing_descriptor)

            # check #4: unknown_driven_joint
            def _check_unknown_driven_joint(
                _driven=driven_joints,
                _policy=policy_joints,
                _entity_id=entity_id,
                _slot_id=slot_id,
            ) -> None:
                if not _driven or not _policy:
                    return
                policy_set = set(_policy)
                unknown = [j for j in _driven if j not in policy_set]
                if not unknown:
                    return
                _emit(
                    out,
                    ValidationWarning(
                        severity="warning",
                        code="unknown_driven_joint",
                        message=(
                            f"driven_joints {unknown} not in policy_joint_names; these "
                            "names are silently ignored at runtime"
                        ),
                        entity_id=_entity_id,
                        slot_id=_slot_id,
                    ),
                )

            _safe_check(out, "unknown_driven_joint", _check_unknown_driven_joint)

            # check #6: slot_inactive_with_commands
            def _check_inactive_with_commands(
                _cmds=command_id_map,
                _active=slot_active,
                _ready=slot_ready,
                _entity_id=entity_id,
                _slot_id=slot_id,
            ) -> None:
                if not _cmds:
                    return
                if _active or _ready:
                    return
                _emit(
                    out,
                    ValidationWarning(
                        severity="info",
                        code="slot_inactive_with_commands",
                        message=(
                            "slot has command_id_map populated but is neither active "
                            "nor ready; commands will not flow until the slot is activated"
                        ),
                        entity_id=_entity_id,
                        slot_id=_slot_id,
                    ),
                )

            _safe_check(out, "slot_inactive_with_commands", _check_inactive_with_commands)

    return out


__all__ = ["ValidationWarning", "validate_session", "Severity"]
