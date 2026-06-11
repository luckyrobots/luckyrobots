"""Gymnasium-compatible environment wrapper for LuckyEngine.

This is the primary interface for RL training — it replaces the 4,000+ line
LuckyLab manager framework with a thin, standard Gymnasium env.

Usage:
    import numpy as np
    from luckyrobots import LuckyEnv

    def my_reward(signals: dict[str, float]) -> float:
        return (1.0 * np.exp(-3 * signals.get("track_linear_velocity", 0))
                - 0.05 * signals.get("joint_acc_penalty", 0)
                + 0.2 * signals.get("feet_air_time", 0))

    env = LuckyEnv(
        robot="unitreego2",
        scene="velocity",
        reward_fn=my_reward,
        reward_terms=["track_linear_velocity", "joint_acc_penalty", "feet_air_time"],
        termination_terms=["fell_over", "time_out"],
    )

    obs, info = env.reset()
    for _ in range(100_000):
        action = policy(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            obs, info = env.reset()
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import gymnasium as gym
    from gymnasium import spaces

    _HAS_GYMNASIUM = True
except ImportError:
    _HAS_GYMNASIUM = False


def _require_gymnasium():
    if not _HAS_GYMNASIUM:
        raise ImportError(
            "gymnasium is required for LuckyEnv. Install it with: pip install gymnasium"
        )


class LuckyEnv:
    """Gymnasium-compatible environment wrapping LuckyEngine via gRPC.

    The engine computes observations, reward signals, and termination flags.
    The user provides a reward function that combines raw signals into a scalar.

    This class implements the Gymnasium env interface (reset, step, close)
    without inheriting from gym.Env to avoid the gymnasium dependency for
    users who only use the raw client.

    Attributes:
        observation_space: Box space matching the agent's observation size.
        action_space: Box space matching the agent's action size.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        robot: str = "unitreego2",
        scene: str = "velocity",
        reward_fn: Optional[Callable[[dict[str, float]], float]] = None,
        reward_terms: Optional[list[str]] = None,
        termination_terms: Optional[list[str]] = None,
        observation_terms: Optional[list[str]] = None,
        host: str = "127.0.0.1",
        port: int = 50051,
        timeout: float = 30.0,
        randomization_cfg: Optional[dict] = None,
        max_episode_length_s: float = 20.0,
        auto_start: bool = False,
        agent_name: str = "",
    ):
        """Initialize LuckyEnv.

        Args:
            robot: Robot identifier (e.g., "unitreego2", "so100").
            scene: Scene identifier (e.g., "velocity", "manipulation").
            reward_fn: Function that takes reward signals dict and returns scalar reward.
                If None, returns sum of all reward signals.
            reward_terms: Engine reward terms to request (e.g., ["track_linear_velocity"]).
            termination_terms: Engine termination terms (e.g., ["fell_over", "time_out"]).
            observation_terms: Observation terms to request. If None, uses agent defaults.
            host: Engine gRPC host.
            port: Engine gRPC port.
            timeout: Connection timeout in seconds.
            randomization_cfg: Domain randomization config dict for SimulationContract.
            max_episode_length_s: Maximum episode length in seconds.
            auto_start: If True, launch the engine process automatically.
            agent_name: Agent name (empty = default agent).
        """
        from .client import LuckyEngineClient

        self._robot = robot
        self._scene = scene
        self._reward_fn = reward_fn or self._default_reward_fn
        self._reward_terms = reward_terms or []
        self._termination_terms = termination_terms or []
        self._observation_terms = observation_terms
        self._randomization_cfg = randomization_cfg
        self._max_episode_length_s = max_episode_length_s
        self._agent_name = agent_name
        self._step_count = 0

        # Connect to engine
        self._client = LuckyEngineClient(host=host, port=port, timeout=timeout)
        self._client.connect()
        self._client.wait_for_server(timeout=timeout)

        # Fetch schema for observation/action dimensions
        schema_resp = self._client.get_agent_schema(agent_name=agent_name)
        schema = getattr(schema_resp, "schema", None)
        self._obs_size = int(schema.observation_size) if schema else 0
        self._act_size = int(schema.action_size) if schema else 0

        if self._obs_size == 0 or self._act_size == 0:
            raise RuntimeError(
                f"Agent schema returned obs_size={self._obs_size}, act_size={self._act_size}. "
                "Is the scene loaded and an external agent configured?"
            )

        # Build Gymnasium spaces
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self._obs_size,), dtype=np.float32
        ) if _HAS_GYMNASIUM else None

        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(self._act_size,), dtype=np.float32
        ) if _HAS_GYMNASIUM else None

        # Negotiate task contract if reward/termination terms provided
        self._session_id = None
        if self._reward_terms or self._termination_terms:
            self._negotiate_contract()

        logger.info(
            "LuckyEnv initialized: robot=%s, obs=%d, act=%d, rewards=%s, terms=%s",
            robot, self._obs_size, self._act_size,
            self._reward_terms, self._termination_terms,
        )

    def _negotiate_contract(self):
        """Send task contract to engine for validation and configuration."""
        contract = {
            "task_id": f"{self._robot}_{self._scene}",
            "robot": self._robot,
            "scene": self._scene,
        }

        if self._reward_terms:
            contract["rewards"] = {
                "engine_terms": [{"name": t} for t in self._reward_terms],
            }

        if self._termination_terms:
            contract["terminations"] = {
                "terms": [
                    {
                        "name": t,
                        "is_timeout": t == "time_out",
                        "params": (
                            {"max_episode_length_s": str(self._max_episode_length_s)}
                            if t == "time_out"
                            else {}
                        ),
                    }
                    for t in self._termination_terms
                ],
            }

        if self._observation_terms:
            contract["observations"] = {
                "required": [{"name": t} for t in self._observation_terms],
            }

        result = self._client.negotiate_task(contract)
        self._session_id = result.get("session_id", "")
        logger.info("Task contract negotiated: session=%s", self._session_id)

        if "warnings" in result:
            for w in result["warnings"]:
                logger.warning(
                    "Contract warning [%s/%s]: %s — %s",
                    w["component"], w["term_name"], w["message"], w["suggestion"],
                )

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ) -> tuple[np.ndarray, dict]:
        """Reset the environment.

        Args:
            seed: Random seed (currently unused — engine handles seeding).
            options: Additional reset options (currently unused).

        Returns:
            Tuple of (observation, info).
        """
        self._step_count = 0

        self._client.reset_agent(
            agent_name=self._agent_name,
            randomization_cfg=self._randomization_cfg,
        )

        # Step with zero actions to get initial observation
        zero_actions = [0.0] * self._act_size
        obs_response = self._client.step(
            actions=zero_actions,
            agent_name=self._agent_name,
        )

        obs = np.array(obs_response.observation, dtype=np.float32)
        info = self._build_info(obs_response)

        return obs, info

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict]:
        """Take a step in the environment.

        Args:
            action: Action array matching action_space.

        Returns:
            Tuple of (observation, reward, terminated, truncated, info).
        """
        self._step_count += 1

        action_list = action.tolist() if hasattr(action, "tolist") else list(action)
        obs_response = self._client.step(
            actions=action_list,
            agent_name=self._agent_name,
        )

        obs = np.array(obs_response.observation, dtype=np.float32)

        # Compute reward from engine signals
        reward_signals = obs_response.reward_signals or {}
        reward = self._reward_fn(reward_signals)

        terminated = obs_response.terminated
        truncated = obs_response.truncated

        info = self._build_info(obs_response)
        info["reward_signals"] = reward_signals

        return obs, reward, terminated, truncated, info

    def close(self):
        """Close the environment and disconnect from engine."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def _build_info(self, obs_response) -> dict[str, Any]:
        """Build info dict from observation response."""
        info = {}
        if obs_response.info:
            info.update(obs_response.info)
        if obs_response.termination_flags:
            info["termination_flags"] = obs_response.termination_flags
        info["frame_number"] = obs_response.frame_number
        info["step_count"] = self._step_count
        return info

    @staticmethod
    def _default_reward_fn(signals: dict[str, float]) -> float:
        """Default reward: sum of all signals."""
        return sum(signals.values()) if signals else 0.0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def __del__(self):
        self.close()
