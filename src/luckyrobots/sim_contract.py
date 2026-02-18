"""Simulation contract proto builder.

Converts Python config objects to gRPC SimulationContract protobuf
messages used by LuckyEngine agent resets.
"""

from __future__ import annotations

from typing import Any


def to_proto(pb_agent: Any, config: Any) -> Any:
    """Convert a config object to a SimulationContract protobuf message.

    Args:
        pb_agent: The agent protobuf module (client.pb.agent).
        config: Config object with optional simulation contract attributes
            (randomization, velocity commands, terrain, etc.).

    Returns:
        A SimulationContract protobuf message.
    """
    proto_kwargs: dict[str, Any] = {}

    def get_val(name: str, default=None):
        val = getattr(config, name, default)
        if val is None or (isinstance(val, (tuple, list)) and len(val) == 0):
            return None
        return val

    # Initial state randomization
    pose_pos = get_val("pose_position_noise")
    if pose_pos is not None:
        proto_kwargs["pose_position_noise"] = list(pose_pos)

    pose_ori = get_val("pose_orientation_noise")
    if pose_ori is not None and pose_ori != 0.0:
        proto_kwargs["pose_orientation_noise"] = pose_ori

    joint_pos = get_val("joint_position_noise")
    if joint_pos is not None and joint_pos != 0.0:
        proto_kwargs["joint_position_noise"] = joint_pos

    joint_vel = get_val("joint_velocity_noise")
    if joint_vel is not None and joint_vel != 0.0:
        proto_kwargs["joint_velocity_noise"] = joint_vel

    # Physics parameters
    friction = get_val("friction_range")
    if friction is not None:
        proto_kwargs["friction_range"] = list(friction)

    restitution = get_val("restitution_range")
    if restitution is not None:
        proto_kwargs["restitution_range"] = list(restitution)

    mass_scale = get_val("mass_scale_range")
    if mass_scale is not None:
        proto_kwargs["mass_scale_range"] = list(mass_scale)

    com_offset = get_val("com_offset_range")
    if com_offset is not None:
        proto_kwargs["com_offset_range"] = list(com_offset)

    # Motor/actuator
    motor_strength = get_val("motor_strength_range")
    if motor_strength is not None:
        proto_kwargs["motor_strength_range"] = list(motor_strength)

    motor_offset = get_val("motor_offset_range")
    if motor_offset is not None:
        proto_kwargs["motor_offset_range"] = list(motor_offset)

    # External disturbances
    push_interval = get_val("push_interval_range")
    if push_interval is not None:
        proto_kwargs["push_interval_range"] = list(push_interval)

    push_velocity = get_val("push_velocity_range")
    if push_velocity is not None:
        proto_kwargs["push_velocity_range"] = list(push_velocity)

    # Terrain
    terrain_type = get_val("terrain_type")
    if terrain_type is not None and terrain_type != "":
        proto_kwargs["terrain_type"] = terrain_type

    terrain_diff = get_val("terrain_difficulty")
    if terrain_diff is not None and terrain_diff != 0.0:
        proto_kwargs["terrain_difficulty"] = terrain_diff

    # Velocity command ranges (sampled by engine)
    vel_x = get_val("vel_command_x_range")
    if vel_x is not None:
        proto_kwargs["vel_command_x_range"] = list(vel_x)

    vel_y = get_val("vel_command_y_range")
    if vel_y is not None:
        proto_kwargs["vel_command_y_range"] = list(vel_y)

    vel_yaw = get_val("vel_command_yaw_range")
    if vel_yaw is not None:
        proto_kwargs["vel_command_yaw_range"] = list(vel_yaw)

    resample_time = get_val("vel_command_resampling_time_range")
    if resample_time is not None:
        proto_kwargs["vel_command_resampling_time_range"] = list(resample_time)

    standing_prob = get_val("vel_command_standing_probability")
    if standing_prob is not None and standing_prob != 0.0:
        proto_kwargs["vel_command_standing_probability"] = standing_prob

    return pb_agent.SimulationContract(**proto_kwargs)
