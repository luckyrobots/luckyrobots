"""luckyrobots.sysid - System identification for sim-to-real transfer.

Provides tools to collect trajectory data from robots (real or simulated),
identify physical parameters by comparing real vs. simulated behavior,
and apply calibrated parameters to MuJoCo XML models.

Install: pip install luckyrobots[sysid]
"""

# Data
from .trajectory import TrajectoryData as TrajectoryData

# Parameters
from .parameters import ParamSpec as ParamSpec
from .parameters import get_param as get_param
from .parameters import set_param as set_param
from .parameters import load_preset as load_preset

# System identification
from .sysid import SysIdResult as SysIdResult
from .sysid import identify as identify

# Calibration
from .calibrate import apply_params as apply_params

# Collection
from .collector import Collector as Collector
from .collector import EngineCollector as EngineCollector

# Excitation signals
from .excitation import chirp as chirp
from .excitation import multisine as multisine
from .excitation import random_steps as random_steps

__all__ = [
    "TrajectoryData",
    "ParamSpec",
    "get_param",
    "set_param",
    "load_preset",
    "SysIdResult",
    "identify",
    "apply_params",
    "Collector",
    "EngineCollector",
    "chirp",
    "multisine",
    "random_steps",
]
