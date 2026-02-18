"""Parameter specifications, presets, and MuJoCo model accessors for system identification."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParamSpec:
    """Specification for a single identifiable parameter.

    Attributes:
        name: Human-readable name, e.g. "FL_hip_armature".
        element: MuJoCo element type: "joint", "body", "geom", "actuator".
        mj_name: Name of the element in the MuJoCo XML.
        attribute: Attribute to identify, e.g. "armature", "mass", "friction".
        nominal: Default/nominal value.
        min_value: Lower bound for identification.
        max_value: Upper bound for identification.
    """

    name: str
    element: str
    mj_name: str
    attribute: str
    nominal: float
    min_value: float
    max_value: float


# ── Go2 joint names ──
_GO2_JOINTS = [
    "FL_hip_joint", "FL_thigh_joint", "FL_calf_joint",
    "FR_hip_joint", "FR_thigh_joint", "FR_calf_joint",
    "RL_hip_joint", "RL_thigh_joint", "RL_calf_joint",
    "RR_hip_joint", "RR_thigh_joint", "RR_calf_joint",
]

_GO2_BODIES = [
    "base_link",
    "FL_hip", "FL_thigh", "FL_calf",
    "FR_hip", "FR_thigh", "FR_calf",
    "RL_hip", "RL_thigh", "RL_calf",
    "RR_hip", "RR_thigh", "RR_calf",
]

_GO2_FEET = ["FL_foot", "FR_foot", "RL_foot", "RR_foot"]


def _go2_motor_params() -> list[ParamSpec]:
    params = []
    for jname in _GO2_JOINTS:
        short = jname.replace("_joint", "")
        params.append(ParamSpec(
            name=f"{short}_armature", element="joint", mj_name=jname,
            attribute="armature", nominal=0.01, min_value=0.001, max_value=0.1,
        ))
        params.append(ParamSpec(
            name=f"{short}_damping", element="joint", mj_name=jname,
            attribute="damping", nominal=0.1, min_value=0.01, max_value=1.0,
        ))
        params.append(ParamSpec(
            name=f"{short}_frictionloss", element="joint", mj_name=jname,
            attribute="frictionloss", nominal=0.1, min_value=0.0, max_value=1.0,
        ))
    return params


def _go2_inertial_params() -> list[ParamSpec]:
    params = []
    for bname in _GO2_BODIES:
        params.append(ParamSpec(
            name=f"{bname}_mass", element="body", mj_name=bname,
            attribute="mass", nominal=1.0, min_value=0.1, max_value=20.0,
        ))
    return params


def _go2_friction_params() -> list[ParamSpec]:
    params = []
    for fname in _GO2_FEET:
        params.append(ParamSpec(
            name=f"{fname}_friction", element="geom", mj_name=fname,
            attribute="friction", nominal=1.0, min_value=0.1, max_value=3.0,
        ))
    return params


GO2_PRESETS: dict[str, list[ParamSpec]] = {
    "motor": _go2_motor_params(),
    "inertial": _go2_inertial_params(),
    "friction": _go2_friction_params(),
}


def load_preset(robot: str, group: str) -> list[ParamSpec]:
    """Load a parameter preset for a given robot and group.

    Args:
        robot: Robot name, e.g. "go2".
        group: Parameter group, e.g. "motor", "inertial", "friction".

    Returns:
        List of ParamSpec for the requested group.
    """
    presets = {
        "go2": GO2_PRESETS,
    }
    robot_presets = presets.get(robot.lower())
    if robot_presets is None:
        raise ValueError(f"Unknown robot '{robot}'. Available: {list(presets.keys())}")
    group_params = robot_presets.get(group.lower())
    if group_params is None:
        raise ValueError(
            f"Unknown group '{group}' for robot '{robot}'. "
            f"Available: {list(robot_presets.keys())}"
        )
    return group_params


# ── MuJoCo model parameter access ──


def get_param(model, spec: ParamSpec) -> float:
    """Read a parameter value from a MuJoCo model.

    Args:
        model: A mujoco.MjModel instance.
        spec: Parameter specification.

    Returns:
        The current parameter value.

    Raises:
        ValueError: If the element/attribute combination is unsupported.
    """
    import mujoco

    if spec.element == "joint":
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, spec.mj_name)
        if joint_id < 0:
            raise ValueError(f"Joint '{spec.mj_name}' not found in model")
        dof_id = model.jnt_dofadr[joint_id]
        if spec.attribute == "armature":
            return float(model.dof_armature[dof_id])
        elif spec.attribute == "damping":
            return float(model.dof_damping[dof_id])
        elif spec.attribute == "frictionloss":
            return float(model.dof_frictionloss[dof_id])
    elif spec.element == "body":
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, spec.mj_name)
        if body_id < 0:
            raise ValueError(f"Body '{spec.mj_name}' not found in model")
        if spec.attribute == "mass":
            return float(model.body_mass[body_id])
    elif spec.element == "geom":
        geom_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, spec.mj_name)
        if geom_id < 0:
            raise ValueError(f"Geom '{spec.mj_name}' not found in model")
        if spec.attribute == "friction":
            return float(model.geom_friction[geom_id, 0])
    elif spec.element == "actuator":
        act_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, spec.mj_name)
        if act_id < 0:
            raise ValueError(f"Actuator '{spec.mj_name}' not found in model")
        if spec.attribute == "gainprm":
            return float(model.actuator_gainprm[act_id, 0])

    raise ValueError(f"Unsupported element/attribute: {spec.element}/{spec.attribute}")


def set_param(model, spec: ParamSpec, value: float) -> None:
    """Write a parameter value to a MuJoCo model.

    Args:
        model: A mujoco.MjModel instance.
        spec: Parameter specification.
        value: The value to set.
    """
    import mujoco

    if spec.element == "joint":
        joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, spec.mj_name)
        dof_id = model.jnt_dofadr[joint_id]
        if spec.attribute == "armature":
            model.dof_armature[dof_id] = value
        elif spec.attribute == "damping":
            model.dof_damping[dof_id] = value
        elif spec.attribute == "frictionloss":
            model.dof_frictionloss[dof_id] = value
    elif spec.element == "body":
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, spec.mj_name)
        if spec.attribute == "mass":
            model.body_mass[body_id] = value
    elif spec.element == "geom":
        geom_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, spec.mj_name)
        if spec.attribute == "friction":
            model.geom_friction[geom_id, 0] = value
    elif spec.element == "actuator":
        act_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, spec.mj_name)
        if spec.attribute == "gainprm":
            model.actuator_gainprm[act_id, 0] = value
