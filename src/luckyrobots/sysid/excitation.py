"""Excitation signal generators for system identification."""

from __future__ import annotations

import numpy as np


def chirp(
    duration: float,
    dt: float,
    f0: float = 0.1,
    f1: float = 5.0,
    amplitude: float = 0.3,
    num_joints: int = 12,
) -> np.ndarray:
    """Generate a chirp (frequency sweep) excitation signal.

    Args:
        duration: Total duration in seconds.
        dt: Timestep in seconds.
        f0: Starting frequency in Hz.
        f1: Ending frequency in Hz.
        amplitude: Signal amplitude.
        num_joints: Number of joints/actuators.

    Returns:
        Control sequence array of shape (T, num_joints).
    """
    T = int(duration / dt)
    t = np.linspace(0, duration, T)
    phase = 2 * np.pi * (f0 * t + (f1 - f0) / (2 * duration) * t ** 2)

    ctrl = np.zeros((T, num_joints))
    for j in range(num_joints):
        ctrl[:, j] = amplitude * np.sin(phase + 2 * np.pi * j / num_joints)

    return ctrl


def multisine(
    duration: float,
    dt: float,
    frequencies: list[float] | None = None,
    amplitude: float = 0.3,
    num_joints: int = 12,
) -> np.ndarray:
    """Generate a multi-sine excitation signal.

    Args:
        duration: Total duration in seconds.
        dt: Timestep in seconds.
        frequencies: List of frequencies in Hz. Defaults to [0.5, 1.0, 2.0, 3.5].
        amplitude: Signal amplitude per component.
        num_joints: Number of joints/actuators.

    Returns:
        Control sequence array of shape (T, num_joints).
    """
    if frequencies is None:
        frequencies = [0.5, 1.0, 2.0, 3.5]

    T = int(duration / dt)
    t = np.linspace(0, duration, T)
    ctrl = np.zeros((T, num_joints))

    rng = np.random.default_rng(42)
    for j in range(num_joints):
        for freq in frequencies:
            phase = rng.uniform(0, 2 * np.pi)
            ctrl[:, j] += amplitude / len(frequencies) * np.sin(
                2 * np.pi * freq * t + phase
            )

    return ctrl


def random_steps(
    duration: float,
    dt: float,
    hold_time: float = 0.5,
    amplitude: float = 0.3,
    num_joints: int = 12,
) -> np.ndarray:
    """Generate random step excitation signal.

    Holds a random value for hold_time seconds, then switches.

    Args:
        duration: Total duration in seconds.
        dt: Timestep in seconds.
        hold_time: How long to hold each random value (seconds).
        amplitude: Maximum amplitude of steps.
        num_joints: Number of joints/actuators.

    Returns:
        Control sequence array of shape (T, num_joints).
    """
    T = int(duration / dt)
    steps_per_hold = max(1, int(hold_time / dt))
    ctrl = np.zeros((T, num_joints))

    rng = np.random.default_rng(42)
    for t in range(0, T, steps_per_hold):
        values = rng.uniform(-amplitude, amplitude, size=num_joints)
        end = min(t + steps_per_hold, T)
        ctrl[t:end] = values

    return ctrl
