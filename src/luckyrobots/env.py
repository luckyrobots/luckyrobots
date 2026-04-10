"""Gymnasium-compatible environment wrapper for LuckyEngine.

Usage::

    from luckyrobots import LuckyEnv

    env = LuckyEnv(robot="unitreego2", scene="velocity")
    obs, info = env.reset()

    for _ in range(10_000):
        action = my_policy(obs)
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated:
            obs, info = env.reset()

    env.close()

With a custom reward function::

    from math import exp

    def my_reward(signals: dict[str, float]) -> float:
        return 1.0 * exp(-3 * signals.get("lin_vel_error", 0.0))

    env = LuckyEnv(robot="unitreego2", scene="velocity", reward_fn=my_reward)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:
    raise ImportError(
        "gymnasium is required for LuckyEnv. Install it with: pip install gymnasium"
    )

from .session import Session

logger = logging.getLogger("luckyrobots.env")


class LuckyEnv(gym.Env):
    """Gymnasium environment backed by LuckyEngine via gRPC.

    This is the primary user-facing API for interacting with LuckyEngine.
    It follows the standard Gymnasium interface so any RL library
    (Stable Baselines3, skrl, CleanRL, custom loops, etc.) can use it directly.

    Args:
        robot: Robot name (must exist in ``robots.yaml``). E.g., ``"unitreego2"``.
        scene: Scene name. E.g., ``"velocity"``.
        task: Task name. E.g., ``"locomotion"``.
        reward_fn: Optional callable ``(signals: dict[str, float]) -> float``.
            If provided, reward is computed by calling this function with the
            raw physics signals from the engine. If ``None``, reward is 0.0
            and raw signals are available in ``info["reward_signals"]``.
        host: gRPC server host.
        port: gRPC server port.
        headless: Launch engine without rendering.
        executable_path: Path to LuckyEngine executable (auto-detected if None).
        simulation_mode: One of ``"fast"``, ``"realtime"``, ``"deterministic"``.
        randomization_cfg: Domain randomization config sent on each reset.
        connect_only: If True, connect to an already-running engine instead of launching one.
        timeout_s: Timeout for waiting for the engine to start.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        robot: str,
        scene: str,
        task: str = "",
        reward_fn: Callable[[dict[str, float]], float] | None = None,
        host: str = "127.0.0.1",
        port: int = 50051,
        headless: bool = False,
        executable_path: str | None = None,
        simulation_mode: str = "fast",
        randomization_cfg: Any = None,
        connect_only: bool = False,
        timeout_s: float = 120.0,
    ) -> None:
        super().__init__()

        self._robot = robot
        self._scene = scene
        self._task = task
        self._reward_fn = reward_fn
        self._simulation_mode = simulation_mode
        self._randomization_cfg = randomization_cfg

        # Create session and connect
        self._session = Session(host=host, port=port)

        if connect_only:
            self._session.connect(timeout_s=timeout_s, robot=robot)
        else:
            self._session.start(
                scene=scene,
                robot=robot,
                task=task or "locomotion",
                executable_path=executable_path,
                headless=headless,
                timeout_s=timeout_s,
            )

        self._session.set_simulation_mode(simulation_mode)

        # Fetch schema to know observation/action dimensions
        schema_resp = self._session.engine_client.get_agent_schema()
        schema = schema_resp.schema
        self._obs_size = schema.observation_size
        self._act_size = schema.action_size

        # Define Gymnasium spaces
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self._obs_size,), dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(self._act_size,), dtype=np.float32
        )

        logger.info(
            "LuckyEnv ready: robot=%s scene=%s obs=%d act=%d reward_fn=%s",
            robot,
            scene,
            self._obs_size,
            self._act_size,
            reward_fn.__name__ if reward_fn else "None",
        )

    @property
    def session(self) -> Session:
        """Access the underlying Session for advanced operations."""
        return self._session

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Reset the environment and return initial observation.

        Args:
            seed: Random seed (currently unused — engine handles randomization).
            options: Additional options. Supports ``"randomization_cfg"`` to
                override the default DR config for this reset.

        Returns:
            Tuple of (observation, info).
        """
        super().reset(seed=seed)

        dr_cfg = (
            options.get("randomization_cfg", self._randomization_cfg)
            if options
            else self._randomization_cfg
        )

        self._session.reset(randomization_cfg=dr_cfg)

        # Step with zero actions to get the initial observation
        result = self._session.gym_step(actions=[0.0] * self._act_size)

        obs = np.array(result.observations, dtype=np.float32)
        info: dict[str, Any] = dict(result.info)
        info["reward_signals"] = result.reward_signals

        return obs, info

    def step(
        self, action: np.ndarray
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        """Take one step in the environment.

        Args:
            action: Action array of shape ``(action_size,)``.

        Returns:
            Tuple of ``(obs, reward, terminated, truncated, info)``.
        """
        action_list = action.astype(np.float32).flatten().tolist()

        result = self._session.gym_step(actions=action_list)

        obs = np.array(result.observations, dtype=np.float32)

        # Compute reward from signals using user-provided function, or return 0.0
        if self._reward_fn is not None and result.reward_signals:
            reward = float(self._reward_fn(result.reward_signals))
        else:
            reward = 0.0

        info: dict[str, Any] = dict(result.info)
        info["reward_signals"] = result.reward_signals

        return obs, reward, result.terminated, result.truncated, info

    def close(self) -> None:
        """Close the environment and stop the engine."""
        if self._session is not None:
            self._session.close(stop_engine=True)

    def __repr__(self) -> str:
        return f"LuckyEnv(robot={self._robot!r}, scene={self._scene!r})"
