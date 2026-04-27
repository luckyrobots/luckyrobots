"""Visualize policy ownership in the editor via DebugService.

Calls the existing `DebugService.Draw` RPC each frame to render arrows or
lines that highlight which joints each active PolicySlot is driving. Useful
during multi-policy debugging to see at a glance which slot owns what.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from luckyrobots.grpc.generated import agent_pb2, common_pb2, debug_pb2

if TYPE_CHECKING:
    from .session import Session

logger = logging.getLogger("luckyrobots.debug_overlay")

# Predefined color palette per slot id (cycled).
_SLOT_COLORS: list[tuple[float, float, float, float]] = [
    (1.0, 0.4, 0.4, 1.0),   # red
    (0.4, 1.0, 0.4, 1.0),   # green
    (0.4, 0.4, 1.0, 1.0),   # blue
    (1.0, 1.0, 0.3, 1.0),   # yellow
    (1.0, 0.4, 1.0, 1.0),   # magenta
    (0.4, 1.0, 1.0, 1.0),   # cyan
]


def _color_for_slot(slot_id: int) -> tuple[float, float, float, float]:
    return _SLOT_COLORS[int(slot_id) % len(_SLOT_COLORS)]


def draw_policy_overlay(
    session: "Session",
    robot_entity_id: int,
    *,
    color_by: str = "slot",
    base_pose_arrow_scale: float = 0.5,
    clear_previous: bool = True,
) -> bool:
    """Submit one frame of debug-draw primitives that highlight active
    PolicySlots on the given robot.

    Strategy:
    1. Query GetRobotController for slot list + joint claims.
    2. For each active slot, pick a color from _SLOT_COLORS[slot.id % N].
    3. Query GetPolicyBasePose for that slot and draw a single colored arrow
       at the policy's base pose pointing along its yaw direction.
    4. Issue a single DebugDrawRequest per call.

    Args:
        session: Connected luckyrobots Session.
        robot_entity_id: Engine entity id of the robot whose slots to overlay.
        color_by: Currently only "slot" is supported.
        base_pose_arrow_scale: Scale factor passed to each DebugArrow.
        clear_previous: If True, the engine clears prior overlay primitives
            before rendering this frame's set.

    Returns:
        True if the draw RPC succeeded, False otherwise.
    """
    if color_by != "slot":
        raise ValueError(f"Unsupported color_by={color_by!r}; only 'slot' is supported")

    client = session.engine_client
    if client is None:
        logger.debug("draw_policy_overlay: session has no engine_client; skipping")
        return False

    agent_stub = client.agent
    debug_stub = client.debug

    entity = common_pb2.EntityId(id=int(robot_entity_id))

    # 1. Pull the controller summary so we know which slots are active.
    try:
        ctrl_resp = agent_stub.GetRobotController(
            agent_pb2.GetRobotControllerRequest(entity=entity)
        )
    except Exception as e:
        logger.debug("draw_policy_overlay: GetRobotController failed: %s", e)
        return False

    if not ctrl_resp.found:
        logger.debug("draw_policy_overlay: no controller for entity %d", robot_entity_id)
        return False

    arrows: list[Any] = []
    for slot in ctrl_resp.controller.slots:
        if not slot.active:
            continue

        try:
            pose = agent_stub.GetPolicyBasePose(
                agent_pb2.GetPolicyBasePoseRequest(entity=entity, slot_id=slot.slot_id)
            )
        except Exception as e:
            logger.debug(
                "draw_policy_overlay: GetPolicyBasePose(slot=%s) failed: %s",
                slot.slot_id,
                e,
            )
            continue

        if not pose.success:
            continue

        r, g, b, a = _color_for_slot(slot.slot_id)

        # Direction = yaw vector in MuJoCo XY plane. Magnitude carries the scale.
        import math

        cy = math.cos(float(pose.yaw))
        sy = math.sin(float(pose.yaw))

        arrows.append(
            debug_pb2.DebugArrow(
                origin=debug_pb2.DebugVector3(
                    x=float(pose.x), y=float(pose.y), z=0.0
                ),
                direction=debug_pb2.DebugVector3(x=cy, y=sy, z=0.0),
                color=debug_pb2.DebugColor(r=r, g=g, b=b, a=a),
                scale=float(base_pose_arrow_scale),
            )
        )

    request = debug_pb2.DebugDrawRequest(
        arrows=arrows,
        clear_previous=bool(clear_previous),
    )

    try:
        resp = debug_stub.Draw(request)
        return bool(resp.success)
    except Exception as e:
        logger.debug("draw_policy_overlay: Draw RPC failed: %s", e)
        return False
