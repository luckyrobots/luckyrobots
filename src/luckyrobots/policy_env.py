"""Gymnasium-compatible env where actions are *commands* into a PolicySlot.

Sibling to LuckyEnv. Whereas LuckyEnv treats actions as raw mujoco ctrl
values (low-level joint torques), PolicyEnv treats actions as scalar
commands fed into a PolicySlot's CommandStore. Use this for training a
high-level controller that *issues commands to* a fixed lower-level
PolicyRuntime — e.g. a navigation policy emitting (vx, vy, yaw_rate)
into a fixed Walker policy.

Action layout: action[i] -> SetPolicyCommandFloat(slot, command_names[i],
action[i]). One forward physics step per ``step()`` via AgentService.Step.

Observation: by default, the policy's last raw inference output (from
GetPolicyLastAction). Pass ``observation_mode="full_state_filtered"`` to
instead use MujocoScene.state(filter=by_slot) for richer observation.

Reward: caller-supplied callable receiving the StepResponse and returning
a float. Termination: caller-supplied callable receiving the StepResponse
and returning bool.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)

try:
    import gymnasium as gym
    from gymnasium import spaces

    _HAS_GYMNASIUM = True
except ImportError:
    _HAS_GYMNASIUM = False
    gym = None  # type: ignore
    spaces = None  # type: ignore


def _require_gymnasium() -> None:
    if not _HAS_GYMNASIUM:
        raise ImportError(
            "PolicyEnv requires `gymnasium`. Install it with: pip install gymnasium"
        )


# Use a real gym.Env base class only when gymnasium is importable; otherwise
# fall back to ``object`` so importing this module never fails.
_BASE = gym.Env if _HAS_GYMNASIUM else object  # type: ignore[misc]


class PolicyEnv(_BASE):  # type: ignore[misc,valid-type]
    """Gymnasium env whose actions are PolicySlot commands.

    See module docstring. The class implements the standard Gymnasium API
    (``reset`` / ``step`` / ``close``); when gymnasium is unavailable at
    import time the import-time failure is deferred to ``__init__`` so the
    rest of the package still loads.

    Attributes:
        observation_space: Box space (sized lazily on first observation
            for ``last_action`` mode, eagerly for ``full_state_filtered``).
        action_space: Box space sized to ``len(command_names)``.
    """

    metadata = {"render_modes": []}

    def __init__(
        self,
        session,
        robot_entity_id: int,
        slot: Union[int, str],
        command_names: list[str],
        reward_fn: Callable[[Any], float],
        termination_fn: Optional[Callable[[Any], bool]] = None,
        observation_mode: str = "last_action",   # "last_action" | "full_state_filtered"
        action_low: float = -1.0,
        action_high: float = 1.0,
        observation_low: float = -10.0,
        observation_high: float = 10.0,
        max_steps: Optional[int] = None,
        timeout_s: float = 5.0,
    ) -> None:
        """Initialize PolicyEnv.

        Args:
            session: A connected ``luckyrobots.Session``.
            robot_entity_id: Entity id of the target RobotController.
            slot: PolicySlot id (uint) or inspector name (str).
            command_names: Names of the slot commands written each step.
                ``action[i]`` is forwarded to ``SetPolicyCommandFloat`` for
                ``command_names[i]``.
            reward_fn: Callable mapping the engine's StepResponse to a float.
            termination_fn: Optional callable mapping the StepResponse to bool.
                Defaults to "never terminates" if not supplied.
            observation_mode: "last_action" returns the policy's most-recent
                raw inference output (via ``GetPolicyLastAction``).
                "full_state_filtered" returns ``[qpos | qvel]`` from
                ``MujocoScene.state`` filtered to this slot.
            action_low, action_high: Bounds for the action Box.
            observation_low, observation_high: Bounds for the observation Box.
            max_steps: Optional truncation horizon; ``None`` disables it.
            timeout_s: Server-side physics-step timeout (``StepRequest.timeout_s``).
        """
        _require_gymnasium()

        # Local imports so module-level import never depends on these.
        from .robots.robot_controller import RobotController, list_robot_controllers

        if observation_mode not in ("last_action", "full_state_filtered"):
            raise ValueError(
                f"observation_mode must be 'last_action' or 'full_state_filtered', "
                f"got {observation_mode!r}"
            )
        if not command_names:
            raise ValueError("command_names must be non-empty")

        self._session = session
        self._robot_entity_id = int(robot_entity_id)
        self._command_names = list(command_names)
        self._reward_fn = reward_fn
        self._termination_fn = termination_fn
        self._observation_mode = observation_mode
        self._timeout_s = float(timeout_s)
        self._max_steps = max_steps
        self._step_count = 0

        # ---- Locate the RobotController for our entity ----
        controllers = list_robot_controllers(session)
        match_state = next(
            (c for c in controllers if c.entity_id == self._robot_entity_id),
            None,
        )
        if match_state is None:
            raise LookupError(
                f"No RobotControllerComponent on entity {self._robot_entity_id}. "
                f"Found ids: {[c.entity_id for c in controllers]}"
            )
        self._robot = RobotController.from_state(session, match_state)

        # ---- Resolve slot to a uint id and cache the slot state ----
        slot_state = match_state.slot(slot)
        if slot_state is None:
            available = [s.name for s in match_state.slots]
            raise KeyError(
                f"PolicySlot {slot!r} not found on entity {self._robot_entity_id}. "
                f"Available: {available}"
            )
        self._slot_id: int = int(slot_state.slot_id)
        self._slot_name: str = slot_state.name
        self._slot_state = slot_state

        # ---- Resolve each command name to its uint id (cache for fast step()) ----
        self._command_ids: list[int] = []
        for name in self._command_names:
            cmd_id = slot_state.command_id(name)
            if cmd_id is None:
                declared = [c.name for c in slot_state.command_id_map]
                raise KeyError(
                    f"Slot {self._slot_name!r} has no command named {name!r}. "
                    f"Declared commands: {declared}"
                )
            self._command_ids.append(int(cmd_id))

        # ---- Action space ----
        self.action_space = spaces.Box(
            low=float(action_low),
            high=float(action_high),
            shape=(len(self._command_names),),
            dtype=np.float32,
        )

        # ---- Observation space ----
        # For "last_action": placeholder sized to len(command_names); the
        # actual policy action vector size is only known after the first
        # successful inference (the runtime publishes joint_names then).
        # For "full_state_filtered": query the scene model and size to
        # nq+nv of the filtered slot.
        self._obs_low = float(observation_low)
        self._obs_high = float(observation_high)

        if self._observation_mode == "full_state_filtered":
            self._scene = self._build_scene()
            obs_size = self._compute_full_state_obs_size()
        else:
            self._scene = None
            # Best-effort placeholder; resized on first step if it changes.
            obs_size = len(self._command_names)

        self.observation_space = spaces.Box(
            low=self._obs_low,
            high=self._obs_high,
            shape=(obs_size,),
            dtype=np.float32,
        )

        logger.info(
            "PolicyEnv initialized: entity=%d slot=%s(%d) commands=%s mode=%s",
            self._robot_entity_id,
            self._slot_name,
            self._slot_id,
            self._command_names,
            self._observation_mode,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_scene(self):
        """Lazily import MujocoScene; let ImportError propagate so it is
        raised at instantiation rather than module import time."""
        from .scene.mujoco_scene import MujocoScene
        return MujocoScene(self._session)

    def _compute_full_state_obs_size(self) -> int:
        """Return ``nq + nv`` for the slot-filtered MujocoScene state.

        Falls back to the full model size if the engine doesn't yet expose
        a slot filter for this build (older snapshots).
        """
        assert self._scene is not None
        try:
            snap = self._scene.state(filter={"filter_by_slot_id": self._slot_id})
        except Exception:
            snap = self._scene.state()
        return int(snap.qpos.shape[0]) + int(snap.qvel.shape[0])

    def _step_engine(self):
        """Drive one physics step via AgentService.Step.

        ``actions`` is left empty: this env steers via SetPolicyCommandFloat
        side-effects, not raw ctrl actions. Server-side ``timeout_s`` bounds
        how long the engine waits for the physics tick.
        """
        client = self._session.engine_client
        if client is None:
            raise RuntimeError(
                "Session is not connected — call session.start()/connect() first."
            )
        from .grpc.generated import agent_pb2 as _agent_pb2
        return client.agent.Step(
            _agent_pb2.StepRequest(
                agent_name="",
                actions=[],
                timeout_s=float(self._timeout_s),
            ),
            timeout=self._timeout_s + 5.0,
        )

    def _build_observation(self, step_response) -> np.ndarray:
        """Build the next observation per ``observation_mode``."""
        if self._observation_mode == "full_state_filtered":
            assert self._scene is not None
            try:
                snap = self._scene.state(filter={"filter_by_slot_id": self._slot_id})
            except Exception:
                snap = self._scene.state()
            return np.concatenate(
                [snap.qpos.astype(np.float32), snap.qvel.astype(np.float32)]
            )

        # "last_action" mode — read the policy's most recent inference output.
        try:
            action_values, _names = self._robot.get_last_action(self._slot_id)
            return np.asarray(action_values, dtype=np.float32)
        except LookupError:
            # Slot inactive or hasn't inferred yet — return zeros sized to
            # the current observation_space so the array stays well-formed.
            return np.zeros(self.observation_space.shape, dtype=np.float32)

    def _maybe_resize_obs_space(self, obs: np.ndarray) -> None:
        """If our placeholder shape doesn't match the live observation,
        rebuild ``observation_space`` so wrappers see the truth."""
        if obs.shape != self.observation_space.shape:
            logger.debug(
                "PolicyEnv: resizing observation_space from %s to %s",
                self.observation_space.shape, obs.shape,
            )
            self.observation_space = spaces.Box(
                low=self._obs_low,
                high=self._obs_high,
                shape=obs.shape,
                dtype=np.float32,
            )

    # ------------------------------------------------------------------
    # Gymnasium API
    # ------------------------------------------------------------------

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict] = None,
    ) -> tuple[np.ndarray, dict]:
        """Reset the environment.

        Args:
            seed: Forwarded to ``gym.Env.reset`` for RNG bookkeeping; engine
                seeding happens server-side and is unaffected.
            options: Reserved for future use.

        Returns:
            ``(initial_obs, info)`` — the initial observation is taken from
            the policy's most recent inference (or zero-filled if nothing
            has been inferred yet).
        """
        if _HAS_GYMNASIUM:
            super().reset(seed=seed)
        self._step_count = 0

        # Best-effort: ask the session to reset the agent so the episode
        # starts from a defined state. If the session/engine doesn't support
        # it (e.g. a session without a contracted agent), swallow the error.
        try:
            self._session.reset()
        except Exception as exc:  # pragma: no cover - defensive only
            logger.debug("PolicyEnv.reset(): session.reset() failed: %s", exc)

        # Build initial observation without driving an extra physics step.
        if self._observation_mode == "full_state_filtered":
            assert self._scene is not None
            try:
                snap = self._scene.state(filter={"filter_by_slot_id": self._slot_id})
            except Exception:
                snap = self._scene.state()
            obs = np.concatenate(
                [snap.qpos.astype(np.float32), snap.qvel.astype(np.float32)]
            )
        else:
            try:
                action_values, _names = self._robot.get_last_action(self._slot_id)
                obs = np.asarray(action_values, dtype=np.float32)
            except LookupError:
                obs = np.zeros(self.observation_space.shape, dtype=np.float32)

        self._maybe_resize_obs_space(obs)
        return obs, {"step_count": self._step_count}

    def step(
        self, action: np.ndarray
    ) -> tuple[np.ndarray, float, bool, bool, dict]:
        """Take a step: write commands, advance physics, build observation.

        Args:
            action: 1-D array of length ``len(command_names)`` matching
                ``action_space``.

        Returns:
            ``(obs, reward, terminated, truncated, info)``. ``info`` includes
            ``"step_response"`` (the raw proto) for downstream debugging.
        """
        self._step_count += 1

        # Coerce to flat list for the per-command writes below.
        action_list = (
            action.tolist()
            if hasattr(action, "tolist")
            else list(action)
        )
        if len(action_list) != len(self._command_ids):
            raise ValueError(
                f"action has length {len(action_list)}; expected "
                f"{len(self._command_ids)} (one per command_name)"
            )

        # 1) Push each scalar command into the slot's CommandStore.
        for cmd_id, value in zip(self._command_ids, action_list):
            self._robot.set_command_float(self._slot_id, cmd_id, float(value))

        # 2) Advance physics. We rely on the SetPolicyCommandFloat
        #    side-effects above; ``actions`` stays empty.
        step_response = self._step_engine()

        # 3) Build observation per mode.
        obs = self._build_observation(step_response)
        self._maybe_resize_obs_space(obs)

        # 4) Reward / termination / truncation.
        reward = float(self._reward_fn(step_response))
        terminated = (
            bool(self._termination_fn(step_response))
            if self._termination_fn is not None
            else False
        )
        truncated = (
            self._max_steps is not None and self._step_count >= int(self._max_steps)
        )

        info: dict[str, Any] = {
            "step_response": step_response,
            "step_count": self._step_count,
            "slot_id": self._slot_id,
            "slot_name": self._slot_name,
        }
        return obs, reward, bool(terminated), bool(truncated), info

    def close(self) -> None:
        """Release the slot we drove so we don't leak state across runs."""
        try:
            self._robot.set_policy_active(self._slot_id, False)
        except Exception:  # already disconnected, slot gone, etc.
            pass

    # ---- context manager sugar ----

    def __enter__(self) -> "PolicyEnv":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False
