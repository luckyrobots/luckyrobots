"""High-level pose teleport helpers built on top of MujocoScene.set_qpos.

MuJoCo's qpos layout is joint-type-dependent (free joint = 7 floats, ball =
4, slide/hinge = 1). This module wraps that layout in a friendly Python API
so callers don't have to compute qpos slot offsets manually.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Mapping, Optional, Sequence

import numpy as np

if TYPE_CHECKING:
    from .scene.mujoco_scene import MujocoScene  # forward-only


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def set_robot_pose(
    scene: "MujocoScene",
    *,
    base_xyz: Optional[Sequence[float]] = None,           # 3 floats, world frame
    base_quat: Optional[Sequence[float]] = None,          # 4 floats (w, x, y, z) MuJoCo convention
    joint_angles: Optional[Mapping[str, float]] = None,   # by joint name
    skip_policy_reseed: bool = False,
    force: bool = False,
) -> None:
    """Build an indexed qpos write from human-friendly inputs.

    Resolves each joint's ``qpos_adr`` from ``scene.model_info()`` and writes:

    * 3 floats for the free joint position (if ``base_xyz`` given)
    * 4 floats for the free joint quaternion (if ``base_quat`` given) — MuJoCo
      order is ``(w, x, y, z)``; the proto packs them at
      ``qpos[qpos_adr+3..6]``.
    * 1 float per hinge/slide joint named in ``joint_angles``
    * Ball joints are not yet supported (raises ``NotImplementedError`` if
      someone tries to set a ball joint via this helper).

    Calls ``scene.set_qpos(indexed=...)`` with the merged dict; honors
    ``skip_policy_reseed`` / ``force`` on the way through.
    """
    indexed: Dict[int, float] = {}

    needs_free_joint = base_xyz is not None or base_quat is not None
    free_joint = _find_free_joint(scene) if needs_free_joint else None

    if base_xyz is not None:
        xyz = _validate_floats(base_xyz, expected=3, label="base_xyz")
        adr = int(free_joint.qpos_adr)  # type: ignore[union-attr]
        indexed[adr + 0] = xyz[0]
        indexed[adr + 1] = xyz[1]
        indexed[adr + 2] = xyz[2]

    if base_quat is not None:
        quat = _validate_floats(base_quat, expected=4, label="base_quat")
        adr = int(free_joint.qpos_adr)  # type: ignore[union-attr]
        # MuJoCo quaternion order: (w, x, y, z) at qpos[adr+3..6].
        indexed[adr + 3] = quat[0]
        indexed[adr + 4] = quat[1]
        indexed[adr + 5] = quat[2]
        indexed[adr + 6] = quat[3]

    if joint_angles:
        for name, angle in joint_angles.items():
            joint = scene.joint(name)
            if joint is None:
                raise KeyError(f"Joint '{name}' not found on the active scene.")
            jtype = (joint.type or "").lower()
            if jtype in ("hinge", "slide"):
                indexed[int(joint.qpos_adr)] = float(angle)
            elif jtype == "ball":
                raise NotImplementedError(
                    f"Joint '{name}' is a ball joint; set_robot_pose does not "
                    f"support ball joints yet (requires a 4-float quaternion)."
                )
            elif jtype == "free":
                raise NotImplementedError(
                    f"Joint '{name}' is a free joint; pass base_xyz / base_quat "
                    f"instead of writing it via joint_angles."
                )
            else:
                raise NotImplementedError(
                    f"Joint '{name}' has unsupported type '{joint.type}' for "
                    f"set_robot_pose."
                )

    if not indexed:
        return

    scene.set_qpos(
        indexed=indexed,
        skip_policy_reseed=skip_policy_reseed,
        force=force,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_free_joint(scene: "MujocoScene"):
    """Return the FIRST free joint in the active model (MuJoCo convention
    for a robot's base joint). Raises LookupError when none exists."""
    for joint in scene.model_info().joints:
        if (joint.type or "").lower() == "free":
            return joint
    raise LookupError(
        "No free joint found in the active MuJoCo model; cannot apply "
        "base_xyz / base_quat. (Robot base must be a free joint.)"
    )


def _validate_floats(values: Sequence[float], *, expected: int, label: str) -> np.ndarray:
    arr = np.asarray(list(values), dtype=np.float64)
    if arr.shape != (expected,):
        raise ValueError(
            f"{label} must be a length-{expected} sequence of floats; "
            f"got shape {tuple(arr.shape)}."
        )
    return arr
