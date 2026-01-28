"""Engine lifecycle management for LuckyEngine."""

from .check_updates import check_updates
from .download import apply_changes, get_base_url, get_os_type
from .manager import (
    find_luckyengine_executable,
    is_luckyengine_running,
    launch_luckyengine,
    stop_luckyengine,
)

__all__ = [
    # Manager functions
    "launch_luckyengine",
    "stop_luckyengine",
    "is_luckyengine_running",
    "find_luckyengine_executable",
    # Update functions
    "check_updates",
    "apply_changes",
    "get_base_url",
    "get_os_type",
]
