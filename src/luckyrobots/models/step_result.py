"""Step result model for the Gym-compatible API."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StepResult:
    """Result of a single simulation step.

    Returned by ``LuckyEngineClient.step()`` and ``Session.step()``.
    Contains everything the user needs for an RL loop: observations,
    reward signals for user-side reward computation, episode boundaries,
    and auxiliary info.

    Usage::

        result = client.step(actions=[0.0] * 12)

        # Observations (flat vector for policy input)
        result.observations        # [0.1, 0.2, ...]
        result.observation_names   # ["proj_grav_x", "proj_grav_y", ...]

        # Reward signals (raw physics quantities — user computes reward from these)
        result.reward_signals      # {"lin_vel_error": 0.05, "feet_air_time": 0.3, ...}

        # Episode boundaries
        result.terminated          # True if hard termination (fell over, diverged)
        result.truncated           # True if soft termination (time limit)

        # Auxiliary data
        result.info                # {"physics_step_us": 412.0, ...}
    """

    observations: list[float] = field(default_factory=list)
    """Flat observation vector from the agent's observation spec."""

    observation_names: list[str] | None = None
    """Observation names from agent schema (enables named access). None if schema not fetched."""

    actions: list[float] = field(default_factory=list)
    """Last applied actions (echoed back from engine)."""

    action_names: list[str] | None = None
    """Action names from agent schema. None if schema not fetched."""

    reward_signals: dict[str, float] = field(default_factory=dict)
    """Raw physics quantities for user-side reward computation.

    The engine populates this with whatever signals are available for
    the current robot/scene. Users write reward functions over these::

        def my_reward(signals: dict[str, float]) -> float:
            return 1.0 * exp(-3 * signals["lin_vel_error"])
    """

    terminated: bool = False
    """Hard termination flag. True when the episode ends due to a failure
    condition (robot fell over, physics divergence, etc.)."""

    truncated: bool = False
    """Soft termination flag. True when the episode ends due to a time
    limit or external stop, not a failure."""

    info: dict[str, float] = field(default_factory=dict)
    """Auxiliary data: timing, diagnostics, per-scene custom values."""

    timestamp_ms: int = 0
    """Wall-clock timestamp in milliseconds."""

    frame_number: int = 0
    """Monotonic frame counter."""

    agent_name: str = ""
    """Agent identifier."""

    def obs_dict(self) -> dict[str, float]:
        """Convert observations to a name->value dict.

        Uses ``observation_names`` if available, otherwise ``obs_0``, ``obs_1``, etc.
        """
        if self.observation_names is not None:
            return dict(zip(self.observation_names, self.observations))
        return {f"obs_{i}": v for i, v in enumerate(self.observations)}
