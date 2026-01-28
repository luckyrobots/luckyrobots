"""
RL observation models for LuckyRobots.

These are the primary return types for the simplified API:
- ObservationResponse: returned by get_observation()
- StateSnapshot: returned by get_state()
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ObservationResponse(BaseModel):
    """RL observation data from an agent.

    This is the return type for LuckyEngineClient.get_observation() and
    LuckyRobots.get_observation(). It contains the RL observation vector
    with optional named access for debugging.

    Usage:
        obs = client.get_observation()

        # Flat vector for RL training
        obs.observation  # [0.1, 0.2, 0.3, ...]

        # Named access (if schema was fetched)
        obs["proj_grav_x"]  # 0.1
        obs.to_dict()  # {"proj_grav_x": 0.1, "proj_grav_y": 0.2, ...}
    """

    model_config = ConfigDict(frozen=True)

    observation: List[float] = Field(
        description="Flat observation vector from the agent's observation spec"
    )
    actions: List[float] = Field(description="Last applied actions")
    timestamp_ms: int = Field(description="Wall-clock timestamp in milliseconds")
    frame_number: int = Field(description="Monotonic frame counter")
    agent_name: str = Field(description="Agent identifier")

    # Optional named access (populated if schema is available)
    observation_names: Optional[List[str]] = Field(
        default=None,
        description="Observation names from agent schema (enables named access)",
    )
    action_names: Optional[List[str]] = Field(
        default=None,
        description="Action names from agent schema",
    )

    def __getitem__(self, key: str) -> float:
        """Access observation value by name.

        Args:
            key: Observation name (e.g., "proj_grav_x", "joint_pos_0").

        Returns:
            The observation value.

        Raises:
            KeyError: If names not available or key not found.
        """
        if self.observation_names is None:
            raise KeyError(
                f"No observation names available. "
                f"Ensure client has fetched schema via get_agent_schema()."
            )
        try:
            idx = self.observation_names.index(key)
            return self.observation[idx]
        except ValueError:
            raise KeyError(
                f"Unknown observation name: '{key}'. "
                f"Available: {self.observation_names}"
            )

    def get(self, key: str, default: Optional[float] = None) -> Optional[float]:
        """Get observation value by name with optional default.

        Args:
            key: Observation name.
            default: Value to return if key not found.

        Returns:
            The observation value or default.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def to_dict(self) -> Dict[str, float]:
        """Convert observations to a name->value dictionary.

        Returns:
            Dict mapping observation names to values. If names not available,
            uses "obs_0", "obs_1", etc.
        """
        if self.observation_names is not None:
            return dict(zip(self.observation_names, self.observation))
        return {f"obs_{i}": v for i, v in enumerate(self.observation)}

    def actions_to_dict(self) -> Dict[str, float]:
        """Convert actions to a name->value dictionary.

        Returns:
            Dict mapping action names to values. If names not available,
            uses "action_0", "action_1", etc.
        """
        if self.action_names is not None:
            return dict(zip(self.action_names, self.actions))
        return {f"action_{i}": v for i, v in enumerate(self.actions)}


class StateSnapshot(BaseModel):
    """Bundled snapshot of multiple data sources.

    Use LuckyEngineClient.get_state() to get a bundled snapshot when you need
    multiple data types in one efficient call. For streaming data like telemetry,
    use the dedicated streaming methods instead.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    observation: Optional[ObservationResponse] = Field(
        default=None, description="RL observation data (if include_observation=True)"
    )
    joint_state: Optional[Any] = Field(
        default=None, description="Joint positions/velocities (if include_joint_state=True)"
    )
    camera_frames: Optional[List[Any]] = Field(
        default=None, description="Camera frames (if camera_names provided)"
    )
    timestamp_ms: int = Field(default=0, description="Wall-clock timestamp in milliseconds")
    frame_number: int = Field(default=0, description="Monotonic frame counter")
