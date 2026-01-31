"""
LuckyRobots - Robotics simulation framework with gRPC communication.

This package provides a Python API for controlling robots in the LuckyEngine
simulation environment via gRPC.
"""

from .luckyrobots import LuckyRobots
from .client import LuckyEngineClient, GrpcConnectionError, BenchmarkResult
from .models import (
    ObservationResponse,
    StateSnapshot,
    CameraData,
    CameraShape,
    DomainRandomizationConfig,
)
from .utils import FPS
from .engine import check_updates


__all__ = [
    # High-level API
    "LuckyRobots",
    # Low-level client
    "LuckyEngineClient",
    "GrpcConnectionError",
    "BenchmarkResult",
    # Models
    "ObservationResponse",
    "StateSnapshot",
    "CameraData",
    "CameraShape",
    "DomainRandomizationConfig",
    # Utilities
    "FPS",
    "check_updates",
]
