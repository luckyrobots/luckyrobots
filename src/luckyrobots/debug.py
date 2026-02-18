"""Debug visualization helpers for LuckyEngine.

Standalone functions that draw debug primitives via a LuckyEngineClient.
Extracted from client.py for single-responsibility clarity.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .client import LuckyEngineClient

logger = logging.getLogger("luckyrobots.debug")


def draw_velocity_command(
    client: LuckyEngineClient,
    origin: tuple[float, float, float],
    lin_vel_x: float,
    lin_vel_y: float,
    ang_vel_z: float,
    scale: float = 1.0,
    clear_previous: bool = True,
    timeout: Optional[float] = None,
) -> bool:
    """Draw velocity command visualization in LuckyEngine.

    Args:
        client: Connected LuckyEngineClient instance.
        origin: (x, y, z) position of the robot.
        lin_vel_x: Forward velocity command.
        lin_vel_y: Lateral velocity command.
        ang_vel_z: Angular velocity command (yaw rate).
        scale: Scale factor for visualization.
        clear_previous: Clear previous debug draws before drawing.
        timeout: RPC timeout in seconds.

    Returns:
        True if draw succeeded, False otherwise.
    """
    timeout = timeout or client.timeout
    pb = client.pb

    velocity_cmd = pb.debug.DebugVelocityCommand(
        origin=pb.debug.DebugVector3(x=origin[0], y=origin[1], z=origin[2]),
        lin_vel_x=lin_vel_x,
        lin_vel_y=lin_vel_y,
        ang_vel_z=ang_vel_z,
        scale=scale,
    )

    request = pb.debug.DebugDrawRequest(
        velocity_command=velocity_cmd,
        clear_previous=clear_previous,
    )

    try:
        resp = client.debug.Draw(request, timeout=timeout)
        return resp.success
    except Exception as e:
        logger.debug(f"Debug draw failed: {e}")
        return False


def draw_arrow(
    client: LuckyEngineClient,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    color: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 1.0),
    scale: float = 1.0,
    clear_previous: bool = False,
    timeout: Optional[float] = None,
) -> bool:
    """Draw a debug arrow in LuckyEngine.

    Args:
        client: Connected LuckyEngineClient instance.
        origin: (x, y, z) start position.
        direction: (x, y, z) direction and magnitude.
        color: (r, g, b, a) color values (0-1 range).
        scale: Scale factor for visualization.
        clear_previous: Clear previous debug draws before drawing.
        timeout: RPC timeout in seconds.

    Returns:
        True if draw succeeded, False otherwise.
    """
    timeout = timeout or client.timeout
    pb = client.pb

    arrow = pb.debug.DebugArrow(
        origin=pb.debug.DebugVector3(x=origin[0], y=origin[1], z=origin[2]),
        direction=pb.debug.DebugVector3(
            x=direction[0], y=direction[1], z=direction[2]
        ),
        color=pb.debug.DebugColor(
            r=color[0], g=color[1], b=color[2], a=color[3]
        ),
        scale=scale,
    )

    request = pb.debug.DebugDrawRequest(
        arrows=[arrow],
        clear_previous=clear_previous,
    )

    try:
        resp = client.debug.Draw(request, timeout=timeout)
        return resp.success
    except Exception as e:
        logger.debug(f"Debug draw failed: {e}")
        return False


def draw_line(
    client: LuckyEngineClient,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    clear_previous: bool = False,
    timeout: Optional[float] = None,
) -> bool:
    """Draw a debug line in LuckyEngine.

    Args:
        client: Connected LuckyEngineClient instance.
        start: (x, y, z) start position.
        end: (x, y, z) end position.
        color: (r, g, b, a) color values (0-1 range).
        clear_previous: Clear previous debug draws before drawing.
        timeout: RPC timeout in seconds.

    Returns:
        True if draw succeeded, False otherwise.
    """
    timeout = timeout or client.timeout
    pb = client.pb

    line = pb.debug.DebugLine(
        start=pb.debug.DebugVector3(x=start[0], y=start[1], z=start[2]),
        end=pb.debug.DebugVector3(x=end[0], y=end[1], z=end[2]),
        color=pb.debug.DebugColor(
            r=color[0], g=color[1], b=color[2], a=color[3]
        ),
    )

    request = pb.debug.DebugDrawRequest(
        lines=[line],
        clear_previous=clear_previous,
    )

    try:
        resp = client.debug.Draw(request, timeout=timeout)
        return resp.success
    except Exception as e:
        logger.debug(f"Debug draw failed: {e}")
        return False
