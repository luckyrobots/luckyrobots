"""Trajectory data container for system identification."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class TrajectoryData:
    """Container for robot trajectory data used in system identification.

    Attributes:
        times: Timestamps in seconds, shape (T,).
        qpos: Joint positions at each timestep, shape (T, nq).
        qvel: Joint velocities at each timestep, shape (T, nv).
        ctrl: Control inputs at each timestep, shape (T, nu).
        metadata: Arbitrary metadata (robot name, source, etc.).
    """

    times: np.ndarray
    qpos: np.ndarray
    qvel: np.ndarray
    ctrl: np.ndarray
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        T = len(self.times)
        if self.qpos.shape[0] != T:
            raise ValueError(f"qpos has {self.qpos.shape[0]} steps, expected {T}")
        if self.qvel.shape[0] != T:
            raise ValueError(f"qvel has {self.qvel.shape[0]} steps, expected {T}")
        if self.ctrl.shape[0] != T:
            raise ValueError(f"ctrl has {self.ctrl.shape[0]} steps, expected {T}")

    @property
    def duration(self) -> float:
        return float(self.times[-1] - self.times[0]) if len(self.times) > 1 else 0.0

    @property
    def dt(self) -> float:
        return float(np.median(np.diff(self.times))) if len(self.times) > 1 else 0.0

    @property
    def num_steps(self) -> int:
        return len(self.times)

    def save(self, path: str | Path) -> Path:
        """Save trajectory to .npz file."""
        path = Path(path)
        np.savez(
            path,
            times=self.times,
            qpos=self.qpos,
            qvel=self.qvel,
            ctrl=self.ctrl,
            metadata=np.array([self.metadata]),
        )
        return path

    @classmethod
    def load(cls, path: str | Path) -> TrajectoryData:
        """Load trajectory from .npz file."""
        data = np.load(path, allow_pickle=True)
        metadata = data["metadata"].item() if "metadata" in data else {}
        return cls(
            times=data["times"],
            qpos=data["qpos"],
            qvel=data["qvel"],
            ctrl=data["ctrl"],
            metadata=metadata,
        )

    @classmethod
    def from_csv(
        cls,
        path: str | Path,
        column_map: dict[str, str | list[str]],
        dt: float | None = None,
    ) -> TrajectoryData:
        """Import trajectory from CSV file.

        Args:
            path: Path to CSV file.
            column_map: Mapping from field names to column names.
                Required keys: "qpos", "qvel", "ctrl".
                Optional: "time". Each value is a column name or list of column names.
            dt: Timestep to use if no time column. Required if "time" not in column_map.
        """
        import csv

        path = Path(path)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        def extract(keys: str | list[str]) -> np.ndarray:
            if isinstance(keys, str):
                keys = [keys]
            return np.array([[float(row[k]) for k in keys] for row in rows])

        qpos = extract(column_map["qpos"])
        qvel = extract(column_map["qvel"])
        ctrl = extract(column_map["ctrl"])

        if "time" in column_map:
            times = extract(column_map["time"]).squeeze()
        elif dt is not None:
            times = np.arange(len(rows)) * dt
        else:
            raise ValueError("Either 'time' column_map key or dt must be provided")

        return cls(
            times=times,
            qpos=qpos,
            qvel=qvel,
            ctrl=ctrl,
            metadata={"source": str(path)},
        )
