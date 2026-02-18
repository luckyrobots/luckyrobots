"""Data collection for system identification."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

import numpy as np

from .trajectory import TrajectoryData

logger = logging.getLogger("luckyrobots.sysid")


class Collector(ABC):
    """Interface for collecting trajectory data from a robot (real or sim)."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def collect(self, ctrl_sequence: np.ndarray, dt: float) -> TrajectoryData: ...

    @abstractmethod
    def close(self) -> None: ...

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()


class EngineCollector(Collector):
    """Collect trajectory data from LuckyEngine via gRPC.

    Requires the ``luckyrobots`` package (pip install luckyrobots).
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 50051,
        robot_name: str = "unitreego2",
    ):
        self.host = host
        self.port = port
        self.robot_name = robot_name
        self._client = None

    def connect(self) -> None:
        from luckyrobots import LuckyEngineClient

        self._client = LuckyEngineClient(
            host=self.host, port=self.port, robot_name=self.robot_name,
        )
        self._client.connect()
        self._client.wait_for_server(timeout=30.0)
        self._client.set_simulation_mode("deterministic")

    def collect(self, ctrl_sequence: np.ndarray, dt: float) -> TrajectoryData:
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        T, nu = ctrl_sequence.shape
        times = np.zeros(T)
        qpos_list = []
        qvel_list = []
        ctrl_list = []

        self._client.reset_agent()

        for t in range(T):
            ctrl = ctrl_sequence[t].tolist()

            state = self._client.get_joint_state(self.robot_name)
            qpos_list.append(np.array(state.state.positions))
            qvel_list.append(np.array(state.state.velocities))

            self._client.step(actions=ctrl)
            ctrl_list.append(ctrl_sequence[t])
            times[t] = t * dt

        return TrajectoryData(
            times=times,
            qpos=np.array(qpos_list),
            qvel=np.array(qvel_list),
            ctrl=np.array(ctrl_list),
            metadata={
                "source": "luckyengine",
                "host": self.host,
                "port": self.port,
                "robot": self.robot_name,
                "dt": dt,
            },
        )

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
