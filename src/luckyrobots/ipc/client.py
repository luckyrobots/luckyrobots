"""
IPC shared memory client for LuckyEngine.

Opens the shared memory region created by IpcHost on the engine side,
creates zero-copy numpy views for observations/actions, and implements
the lock-step protocol via atomic sequence counters.
"""

from __future__ import annotations

import ctypes
import json
import logging
import mmap
import os
import time
from typing import Any, Optional

import numpy as np

from .ring_buffer import SpscRingWriter, SpscRingReader
from .shm_header import ShmHeader, HEADER_SIZE

logger = logging.getLogger("luckyrobots.ipc")


class IpcClient:
    """Shared memory IPC client for zero-copy RL training communication.

    Opens the engine's shared memory region and provides numpy array views
    into the observation, action, reward, done, and reset regions.

    Usage::

        client = IpcClient("luckyengine_12345")
        client.wait_for_engine(timeout=30.0)

        obs = client.obs  # numpy view, zero-copy
        client.act[:] = my_actions
        obs, rewards, dones = client.step(my_actions)

        client.close()
    """

    def __init__(self, shm_name: str) -> None:
        self._shm_name = shm_name
        self._shm_path = f"/dev/shm/{shm_name}"
        self._fd: Optional[int] = None
        self._mm: Optional[mmap.mmap] = None
        self._header: Optional[ShmHeader] = None

        # Numpy views (zero-copy into shared memory)
        self._obs: Optional[np.ndarray] = None
        self._act: Optional[np.ndarray] = None
        self._reward: Optional[np.ndarray] = None
        self._done: Optional[np.ndarray] = None
        self._reset: Optional[np.ndarray] = None

        # Ring buffer command channel
        self._cmd_writer: Optional[SpscRingWriter] = None  # Python → Engine (CmdIn)
        self._resp_reader: Optional[SpscRingReader] = None  # Engine → Python (CmdOut)
        self._next_corr_id: int = 1
        self._cmd_ring_size: int = 512 * 1024

        # Local tracking of sequence counters
        self._last_frame_seq: int = 0

    @property
    def shm_name(self) -> str:
        return self._shm_name

    @property
    def obs(self) -> np.ndarray:
        """Zero-copy numpy view of the observation region. Shape: (num_envs, obs_size)."""
        if self._obs is None:
            raise RuntimeError("IPC client not connected. Call wait_for_engine() first.")
        return self._obs

    @property
    def act(self) -> np.ndarray:
        """Zero-copy numpy view of the action region. Shape: (num_envs, act_size)."""
        if self._act is None:
            raise RuntimeError("IPC client not connected. Call wait_for_engine() first.")
        return self._act

    @property
    def reward(self) -> np.ndarray:
        """Zero-copy numpy view of the reward region. Shape: (num_envs,)."""
        if self._reward is None:
            raise RuntimeError("IPC client not connected. Call wait_for_engine() first.")
        return self._reward

    @property
    def done(self) -> np.ndarray:
        """Zero-copy numpy view of the done region. Shape: (num_envs,)."""
        if self._done is None:
            raise RuntimeError("IPC client not connected. Call wait_for_engine() first.")
        return self._done

    @property
    def header(self) -> ShmHeader:
        """The shared memory header."""
        if self._header is None:
            raise RuntimeError("IPC client not connected.")
        return self._header

    @property
    def num_envs(self) -> int:
        return self.header.num_envs

    @property
    def obs_size(self) -> int:
        return self.header.obs_size

    @property
    def act_size(self) -> int:
        return self.header.act_size

    def wait_for_engine(self, timeout: float = 30.0, poll_interval: float = 0.1) -> bool:
        """Wait for the engine to create the shared memory and set EngineReady.

        Args:
            timeout: Maximum time to wait in seconds.
            poll_interval: Time between checks.

        Returns:
            True if connected successfully, False if timeout.
        """
        deadline = time.monotonic() + timeout

        # Wait for the shm file to appear
        while time.monotonic() < deadline:
            if os.path.exists(self._shm_path):
                break
            time.sleep(poll_interval)
        else:
            logger.error("Timeout waiting for shared memory file: %s", self._shm_path)
            return False

        # Open and map
        try:
            self._open()
        except Exception as e:
            logger.error("Failed to open shared memory: %s", e)
            return False

        # Wait for EngineReady flag
        while time.monotonic() < deadline:
            if self._header.engine_ready != 0:
                break
            time.sleep(poll_interval)
        else:
            logger.error("Timeout waiting for engine ready flag")
            self.close()
            return False

        # Create numpy views
        self._create_views()

        # Mark client as ready
        self._header.client_pid = os.getpid()
        self._header.client_ready = 1

        # Initialize sequence tracking from current state
        self._last_frame_seq = self._header.frame_seq

        logger.info(
            "IPC connected: shm='%s', envs=%d, obs=%d, act=%d",
            self._shm_name,
            self._header.num_envs,
            self._header.obs_size,
            self._header.act_size,
        )
        return True

    def step(self, actions: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Execute one RL step through shared memory.

        Writes actions, increments ActionSeq, waits for engine to step
        (FrameSeq increment), returns (obs, rewards, dones).

        Args:
            actions: Action array, shape (num_envs, act_size) or (act_size,) for single env.

        Returns:
            Tuple of (observations, rewards, dones) as numpy views.
            These are views into shared memory — do not hold references across steps.
        """
        if self._header is None:
            raise RuntimeError("IPC client not connected.")

        # Write actions to shared memory
        flat_actions = actions.ravel().astype(np.float32)
        np.copyto(self._act.ravel(), flat_actions[: self._act.size])

        # Increment ActionSeq to signal engine (atomic on x86-64 for aligned int64)
        self._header.action_seq += 1

        # Spin-wait for engine to step (FrameSeq > last seen)
        self._spin_wait_frame()

        return self._obs, self._reward, self._done

    def reset(self, env_ids: Optional[list[int]] = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Reset environments by setting reset flags and stepping.

        Args:
            env_ids: List of environment indices to reset. None = all.

        Returns:
            Tuple of (observations, rewards, dones) after reset.
        """
        if self._header is None:
            raise RuntimeError("IPC client not connected.")

        # Set reset flags in shared memory
        reset_buf = np.frombuffer(
            self._mm,
            dtype=np.uint8,
            count=self._header.num_envs,
            offset=self._header.reset_offset,
        )
        if env_ids is None:
            reset_buf[:] = 1
        else:
            for eid in env_ids:
                if 0 <= eid < self._header.num_envs:
                    reset_buf[eid] = 1

        # Send a zero-action step to trigger the reset processing
        zero_actions = np.zeros_like(self._act)
        return self.step(zero_actions)

    def get_schema(self) -> dict:
        """Read observation and action names from the schema region.

        Returns:
            Dict with 'obs_names' and 'act_names' lists.
        """
        if self._header is None or self._mm is None:
            raise RuntimeError("IPC client not connected.")

        schema_offset = self._header.schema_offset
        schema_bytes = self._mm[schema_offset: schema_offset + 64 * 1024]

        obs_names = []
        act_names = []

        # Parse null-terminated strings: obs section ends with double-null,
        # then act section ends with double-null
        pos = 0
        current_list = obs_names
        while pos < len(schema_bytes) - 1:
            if schema_bytes[pos] == 0:
                # Double null = switch to next section or end
                if current_list is obs_names:
                    current_list = act_names
                    pos += 1
                    continue
                else:
                    break
            # Find next null terminator
            end = schema_bytes.index(0, pos)
            name = schema_bytes[pos:end].decode("utf-8")
            current_list.append(name)
            pos = end + 1

        return {"obs_names": obs_names, "act_names": act_names}

    # ── Ring Buffer Commands ──

    METHOD_RESET_AGENT = 1
    METHOD_SET_SIMULATION_MODE = 2

    def send_command(
        self,
        method_id: int,
        payload: dict,
        timeout_s: float = 5.0,
    ) -> dict:
        """Send a command through the ring buffer and wait for a response.

        Args:
            method_id: Command method ID.
            payload: JSON-serializable payload dict.
            timeout_s: Max time to wait for response.

        Returns:
            Response payload dict.

        Raises:
            TimeoutError: If no response received within timeout.
            RuntimeError: If the command failed (non-zero status).
        """
        if self._cmd_writer is None or self._resp_reader is None:
            raise RuntimeError("Ring buffers not initialized")

        corr_id = self._next_corr_id
        self._next_corr_id += 1

        payload_bytes = json.dumps(payload).encode("utf-8")
        if not self._cmd_writer.write(corr_id, method_id, payload_bytes):
            raise RuntimeError("IPC command ring buffer full")

        # Wait for matching response
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            result = self._resp_reader.read()
            if result is not None:
                resp_corr_id, status, resp_payload = result
                if resp_corr_id == corr_id:
                    resp_dict = json.loads(resp_payload) if resp_payload else {}
                    if status != 0:
                        raise RuntimeError(
                            f"IPC command failed (status={status}): "
                            f"{resp_dict.get('error', 'unknown')}"
                        )
                    return resp_dict
                # Mismatched correlation ID — discard (stale response)
                logger.debug("Discarding stale response corr_id=%d", resp_corr_id)
            time.sleep(0)  # yield

        raise TimeoutError(f"IPC command timeout after {timeout_s}s (method={method_id})")

    def reset_agent_cmd(
        self,
        agent_name: str = "",
        simulation_contract: Optional[dict] = None,
    ) -> dict:
        """Reset an agent via ring buffer command (supports domain randomization).

        Args:
            agent_name: Agent name (empty = default).
            simulation_contract: Optional DR config dict with fields like
                pose_position_noise, joint_position_noise, vel_command_x_range, etc.

        Returns:
            Response dict with 'success' and 'message'.
        """
        payload: dict[str, Any] = {"agent_name": agent_name}
        if simulation_contract is not None:
            payload["simulation_contract"] = simulation_contract
        return self.send_command(self.METHOD_RESET_AGENT, payload)

    def set_simulation_mode_cmd(self, mode: str = "fast") -> dict:
        """Set simulation mode via ring buffer command.

        Args:
            mode: "realtime", "deterministic", or "fast".

        Returns:
            Response dict.
        """
        return self.send_command(self.METHOD_SET_SIMULATION_MODE, {"mode": mode})

    def close(self) -> None:
        """Disconnect from shared memory."""
        if self._header is not None:
            try:
                self._header.client_ready = 0
                self._header.client_pid = 0
            except Exception:
                pass

        self._obs = None
        self._act = None
        self._reward = None
        self._done = None
        self._reset = None
        self._header = None

        if self._mm is not None:
            try:
                self._mm.close()
            except Exception:
                pass
            self._mm = None

        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None

        logger.info("IPC client closed")

    def __enter__(self) -> IpcClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()

    # ── Private ──

    def _open(self) -> None:
        """Open and memory-map the shared memory file."""
        self._fd = os.open(self._shm_path, os.O_RDWR)
        file_size = os.fstat(self._fd).st_size
        if file_size < HEADER_SIZE:
            raise ValueError(
                f"Shared memory file too small: {file_size} bytes "
                f"(minimum {HEADER_SIZE})"
            )

        self._mm = mmap.mmap(self._fd, file_size)

        # Map the header struct onto the mmap buffer
        self._header = ShmHeader.from_buffer(self._mm)
        self._header.validate()

    def _create_views(self) -> None:
        """Create numpy array views into the shared memory regions."""
        h = self._header
        num_envs = h.num_envs
        obs_size = h.obs_size
        act_size = h.act_size

        # Observations: float32[num_envs * obs_size]
        self._obs = np.frombuffer(
            self._mm,
            dtype=np.float32,
            count=num_envs * obs_size,
            offset=h.obs_offset,
        ).reshape(num_envs, obs_size)

        # Actions: float32[num_envs * act_size]
        self._act = np.frombuffer(
            self._mm,
            dtype=np.float32,
            count=num_envs * act_size,
            offset=h.act_offset,
        ).reshape(num_envs, act_size)

        # Rewards: float32[num_envs]
        self._reward = np.frombuffer(
            self._mm,
            dtype=np.float32,
            count=num_envs,
            offset=h.reward_offset,
        )

        # Dones: uint8[num_envs]
        self._done = np.frombuffer(
            self._mm,
            dtype=np.uint8,
            count=num_envs,
            offset=h.done_offset,
        )

        # Ring buffers for command channel
        # CmdIn: Python writes (producer), Engine reads (consumer)
        # CmdOut: Engine writes (producer), Python reads (consumer)
        mm_view = memoryview(self._mm)
        self._cmd_writer = SpscRingWriter(mm_view, h.cmd_in_offset, self._cmd_ring_size)
        self._resp_reader = SpscRingReader(mm_view, h.cmd_out_offset, self._cmd_ring_size)

    def _spin_wait_frame(self, timeout_s: float = 5.0) -> None:
        """Spin-wait for FrameSeq to increment past _last_frame_seq.

        Uses a hybrid strategy: tight spin for ~100us, then yield.
        """
        target = self._last_frame_seq
        deadline = time.monotonic() + timeout_s
        spins = 0

        while True:
            current = self._header.frame_seq
            if current > target:
                self._last_frame_seq = current
                return

            spins += 1
            if spins > 1000:
                # After initial tight spin, yield to reduce CPU usage
                if time.monotonic() > deadline:
                    raise TimeoutError(
                        f"IPC step timeout: FrameSeq stuck at {current} "
                        f"(expected > {target}) after {timeout_s}s"
                    )
                time.sleep(0)  # yield
                spins = 0
