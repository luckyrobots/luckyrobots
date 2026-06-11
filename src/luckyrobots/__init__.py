"""LuckyRobots - Robotics simulation framework with gRPC communication.

This package provides a Python API for controlling robots in the LuckyEngine
simulation environment via gRPC.
"""

from luckyrobots.client import GrpcConnectionError as GrpcConnectionError
from luckyrobots.client import LuckyEngineClient as LuckyEngineClient
from luckyrobots.models import BenchmarkResult as BenchmarkResult
from luckyrobots.models import FPS as FPS
from luckyrobots.models import CameraFrame as CameraFrame
from luckyrobots.models import ObservationResponse as ObservationResponse
from luckyrobots.lucky_env import LuckyEnv as LuckyEnv
from luckyrobots.session import Session as Session
from luckyrobots.robots import RobotController as RobotController
from luckyrobots.robots import PolicySlotState as PolicySlotState
from luckyrobots.robots import RobotControllerState as RobotControllerState
from luckyrobots.robots import PolicyDescriptorInfo as PolicyDescriptorInfo
from luckyrobots.robots import list_robot_controllers as list_robot_controllers
from luckyrobots.robots import list_policy_descriptors as list_policy_descriptors

# Worker A — MujocoScene wrapper
from luckyrobots.scene import MujocoScene as MujocoScene
from luckyrobots.scene import JointInfo as JointInfo
from luckyrobots.scene import ActuatorInfo as ActuatorInfo
from luckyrobots.scene import ActuatorGainInfo as ActuatorGainInfo
from luckyrobots.scene import ModelInfo as ModelInfo
from luckyrobots.scene import FullStateSnapshot as FullStateSnapshot

# Worker B — pose teleport helper + command-store view
from luckyrobots.poses import set_robot_pose as set_robot_pose
from luckyrobots.robots.robot_controller import CommandStoreView as CommandStoreView

# Worker C — reflection feature detection + validation
from luckyrobots.reflection import has_rpc as has_rpc
from luckyrobots.reflection import supported_services as supported_services
from luckyrobots.reflection import supported_methods as supported_methods
from luckyrobots.validation import validate_session as validate_session
from luckyrobots.validation import ValidationWarning as ValidationWarning

# Worker E — PolicyEnv (Gymnasium command-driven env)
from luckyrobots.policy_env import PolicyEnv as PolicyEnv

# Worker F — PolicyMonitor + debug overlay
from luckyrobots.monitor import PolicyMonitor as PolicyMonitor
from luckyrobots.debug_overlay import draw_policy_overlay as draw_policy_overlay

# Worker G — recording / replay + stream multiplexer
from luckyrobots.recording import SessionRecording as SessionRecording
from luckyrobots.recording import RecordedEvent as RecordedEvent
from luckyrobots.recording import record_session as record_session
from luckyrobots.streams import StreamMultiplexer as StreamMultiplexer

# Worker H — async wrappers
from luckyrobots.async_session import AsyncSession as AsyncSession
from luckyrobots.async_robots import AsyncRobotController as AsyncRobotController
