from .grpc.session import GrpcConfig, GrpcSession
from .env.agent_env import AgentEnv, AgentSchemaView, AgentStep

# RL module (optional - only imported if dependencies are available)
try:
    from .rl import PiperLegoEnv, RslVecEnvWrapper, make_vec_env
    _rl_available = True
except ImportError:
    _rl_available = False

__all__ = [
    "GrpcConfig",
    "GrpcSession",
    "AgentEnv",
    "AgentSchemaView",
    "AgentStep",
]

if _rl_available:
    __all__.extend(["PiperLegoEnv", "RslVecEnvWrapper", "make_vec_env"])
