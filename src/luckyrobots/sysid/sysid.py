"""System identification using MuJoCo simulation.

Replays recorded controls in simulation, adjusts model parameters to minimize
the difference between simulated and recorded joint positions/velocities.
Uses scipy.optimize.least_squares (Levenberg-Marquardt / Trust Region Reflective).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .trajectory import TrajectoryData
from .parameters import ParamSpec, get_param, set_param

logger = logging.getLogger("luckyrobots.sysid")


@dataclass
class SysIdResult:
    """Result of system identification."""

    params: dict[str, float]
    initial_params: dict[str, float]
    confidence: dict[str, tuple[float, float]]
    residual_before: float
    residual_after: float
    report_path: Path | None = None

    def save(self, path: str | Path) -> Path:
        """Save result to JSON."""
        path = Path(path)
        data = {
            "params": self.params,
            "initial_params": self.initial_params,
            "confidence": self.confidence,
            "residual_before": self.residual_before,
            "residual_after": self.residual_after,
        }
        path.write_text(json.dumps(data, indent=2))
        return path

    @classmethod
    def load(cls, path: str | Path) -> SysIdResult:
        """Load result from JSON."""
        data = json.loads(Path(path).read_text())
        return cls(
            params=data["params"],
            initial_params=data["initial_params"],
            confidence={k: tuple(v) for k, v in data["confidence"].items()},
            residual_before=data["residual_before"],
            residual_after=data["residual_after"],
        )


def _rollout(model, data, ctrl_sequence: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    """Rollout a control sequence and return (qpos, qvel) trajectories."""
    import mujoco

    T, nu = ctrl_sequence.shape
    nq, nv = model.nq, model.nv

    qpos_traj = np.zeros((T, nq))
    qvel_traj = np.zeros((T, nv))

    mujoco.mj_resetData(model, data)
    model.opt.timestep = dt

    for t in range(T):
        data.ctrl[:nu] = ctrl_sequence[t]
        mujoco.mj_step(model, data)
        qpos_traj[t] = data.qpos.copy()
        qvel_traj[t] = data.qvel.copy()

    return qpos_traj, qvel_traj


def identify(
    model_xml: str | Path,
    trajectories: list[TrajectoryData] | TrajectoryData,
    param_specs: list[ParamSpec],
    *,
    report_dir: str | Path | None = None,
    max_iterations: int = 100,
    qpos_weight: float = 1.0,
    qvel_weight: float = 0.1,
) -> SysIdResult:
    """Run system identification.

    Replays controls from recorded trajectories in simulation, adjusts model
    parameters to minimize the difference between simulated and recorded
    joint positions and velocities.

    Args:
        model_xml: Path to MuJoCo XML model file.
        trajectories: One or more TrajectoryData recordings.
        param_specs: Parameters to identify.
        report_dir: Directory to save identification report.
        max_iterations: Maximum optimization iterations.
        qpos_weight: Weight for position error in residual.
        qvel_weight: Weight for velocity error in residual.

    Returns:
        SysIdResult with identified parameters and diagnostics.
    """
    import mujoco
    from scipy.optimize import least_squares as scipy_lsq

    if isinstance(trajectories, TrajectoryData):
        trajectories = [trajectories]

    model_xml = Path(model_xml)
    model = mujoco.MjModel.from_xml_path(str(model_xml))
    data = mujoco.MjData(model)

    # Read initial parameter values
    initial_params = {}
    x0 = []
    bounds_lo = []
    bounds_hi = []
    for spec in param_specs:
        val = get_param(model, spec)
        initial_params[spec.name] = val
        x0.append(val)
        bounds_lo.append(spec.min_value)
        bounds_hi.append(spec.max_value)

    x0 = np.array(x0)

    def residual_fn(x: np.ndarray) -> np.ndarray:
        for i, spec in enumerate(param_specs):
            set_param(model, spec, x[i])

        all_residuals = []
        for traj in trajectories:
            dt = traj.dt
            sim_qpos, sim_qvel = _rollout(model, data, traj.ctrl, dt)

            nq_compare = min(sim_qpos.shape[1], traj.qpos.shape[1])
            nv_compare = min(sim_qvel.shape[1], traj.qvel.shape[1])

            qpos_err = (sim_qpos[:, :nq_compare] - traj.qpos[:, :nq_compare]) * qpos_weight
            qvel_err = (sim_qvel[:, :nv_compare] - traj.qvel[:, :nv_compare]) * qvel_weight

            all_residuals.append(qpos_err.ravel())
            all_residuals.append(qvel_err.ravel())

        return np.concatenate(all_residuals)

    # Compute initial residual
    residual_before = float(np.sum(residual_fn(x0) ** 2))

    # Run optimization
    result = scipy_lsq(
        residual_fn,
        x0,
        bounds=(bounds_lo, bounds_hi),
        max_nfev=max_iterations,
        method="trf",
        verbose=1,
    )

    residual_after = float(np.sum(result.fun ** 2))

    # Extract identified parameters
    identified = {}
    for i, spec in enumerate(param_specs):
        identified[spec.name] = float(result.x[i])

    # Estimate 95% confidence intervals from Jacobian
    confidence = _compute_confidence(result, param_specs)

    report_path = None
    if report_dir is not None:
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "sysid_result.json"

    sysid_result = SysIdResult(
        params=identified,
        initial_params=initial_params,
        confidence=confidence,
        residual_before=residual_before,
        residual_after=residual_after,
        report_path=report_path,
    )

    if report_path is not None:
        sysid_result.save(report_path)
        logger.info("Report saved to %s", report_path)

    return sysid_result


def _compute_confidence(result, param_specs: list[ParamSpec]) -> dict[str, tuple[float, float]]:
    """Compute 95% confidence intervals from scipy least_squares result."""
    confidence = {}
    try:
        J = result.jac
        residuals = result.fun
        n_residuals = len(residuals)
        n_params = len(param_specs)
        if n_residuals > n_params:
            sigma2 = np.sum(residuals ** 2) / (n_residuals - n_params)
            cov = sigma2 * np.linalg.inv(J.T @ J)
            for i, spec in enumerate(param_specs):
                std = np.sqrt(max(cov[i, i], 0.0))
                confidence[spec.name] = (
                    float(result.x[i] - 1.96 * std),
                    float(result.x[i] + 1.96 * std),
                )
        else:
            for spec in param_specs:
                confidence[spec.name] = (float("-inf"), float("inf"))
    except Exception:
        for spec in param_specs:
            confidence[spec.name] = (float("-inf"), float("inf"))
    return confidence
