"""Benchmark models for LuckyRobots performance measurement."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    """Result of a client benchmark run.

    Attributes:
        method: The method that was benchmarked (e.g. "step").
        duration_seconds: Total wall-clock time of the benchmark.
        frame_count: Number of frames/calls completed.
        actual_fps: Measured frames per second.
        avg_latency_ms: Mean per-call latency in milliseconds.
        min_latency_ms: Minimum per-call latency in milliseconds.
        max_latency_ms: Maximum per-call latency in milliseconds.
        std_latency_ms: Standard deviation of per-call latency.
        p50_latency_ms: 50th percentile (median) latency in milliseconds.
        p99_latency_ms: 99th percentile latency in milliseconds.
    """

    method: str
    duration_seconds: float
    frame_count: int
    actual_fps: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    std_latency_ms: float
    p50_latency_ms: float
    p99_latency_ms: float


class FPS:
    """Simple sliding-window FPS counter.

    Usage:
        fps = FPS(frame_window=30)
        while running:
            do_work()
            current_fps = fps.measure()
    """

    def __init__(self, frame_window: int = 30) -> None:
        self._timestamps: deque[float] = deque(maxlen=frame_window)

    def measure(self) -> float:
        """Record a frame and return the current FPS estimate.

        Returns:
            Estimated frames per second based on the sliding window.
            Returns 0.0 if fewer than 2 frames have been recorded.
        """
        now = time.perf_counter()
        self._timestamps.append(now)

        if len(self._timestamps) < 2:
            return 0.0

        elapsed = self._timestamps[-1] - self._timestamps[0]
        if elapsed <= 0:
            return 0.0

        return (len(self._timestamps) - 1) / elapsed
