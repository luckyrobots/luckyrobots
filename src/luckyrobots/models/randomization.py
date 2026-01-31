"""
Domain randomization configuration for physics parameters.

This model maps to the DomainRandomizationConfig proto message in agent.proto.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class DomainRandomizationConfig(BaseModel):
    """Domain randomization configuration for physics parameters.

    All range fields are [min, max] tuples. None/empty means "use defaults".

    Usage:
        randomization_cfg = DomainRandomizationConfig(
            friction_range=(0.5, 1.5),
            mass_scale_range=(0.8, 1.2),
            joint_position_noise=0.05,
        )
        client.reset_agent(randomization_cfg=randomization_cfg)
    """

    model_config = ConfigDict(frozen=True)

    # Initial state randomization
    pose_position_noise: Optional[tuple[float, float, float]] = Field(
        default=None, description="[x, y, z] position noise std"
    )
    pose_orientation_noise: Optional[float] = Field(
        default=None, description="Orientation noise std (radians)"
    )
    joint_position_noise: Optional[float] = Field(
        default=None, description="Joint position noise std"
    )
    joint_velocity_noise: Optional[float] = Field(
        default=None, description="Joint velocity noise std"
    )

    # Physics parameters (all [min, max] ranges)
    friction_range: Optional[tuple[float, float]] = Field(
        default=None, description="Surface friction coefficient [min, max]"
    )
    restitution_range: Optional[tuple[float, float]] = Field(
        default=None, description="Bounce/restitution coefficient [min, max]"
    )
    mass_scale_range: Optional[tuple[float, float]] = Field(
        default=None, description="Body mass multiplier [min, max]"
    )
    com_offset_range: Optional[tuple[float, float]] = Field(
        default=None, description="Center of mass offset [min, max]"
    )

    # Motor/actuator randomization
    motor_strength_range: Optional[tuple[float, float]] = Field(
        default=None, description="Motor strength multiplier [min, max]"
    )
    motor_offset_range: Optional[tuple[float, float]] = Field(
        default=None, description="Motor position offset [min, max]"
    )

    # External disturbances
    push_interval_range: Optional[tuple[float, float]] = Field(
        default=None, description="Time between pushes [min, max]"
    )
    push_velocity_range: Optional[tuple[float, float]] = Field(
        default=None, description="Push velocity magnitude [min, max]"
    )

    # Terrain configuration
    terrain_type: Optional[str] = Field(
        default=None, description="Terrain type identifier"
    )
    terrain_difficulty: Optional[float] = Field(
        default=None, description="Terrain difficulty level"
    )
