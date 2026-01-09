"""
RSL-RL VecEnv wrapper for LuckyRobots single-agent environments.

This wrapper adapts a single PiperLegoEnv to the RSL-RL VecEnv interface,
enabling training with RSL-RL's PPO implementation.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import torch
from tensordict import TensorDict

from .piper_lego_env import PiperLegoEnv, PiperLegoEnvConfig


class RslVecEnvWrapper:
    """
    VecEnv-style wrapper for a single LuckyRobots environment.
    
    This class provides the interface expected by RSL-RL's OnPolicyRunner:
    - num_envs, num_obs, num_actions, device
    - get_observations() -> TensorDict
    - step(actions) -> (obs, rewards, dones, extras)
    """
    
    def __init__(
        self,
        env: PiperLegoEnv,
        device: str = "cpu",
    ) -> None:
        self._env = env
        self.device = torch.device(device)
        
        # Required attributes for RSL-RL
        self.num_envs = 1
        self.num_obs = env.num_obs
        self.num_actions = env.num_actions
        self.max_episode_length = env.cfg.max_episode_steps
        
        # Episode tracking
        self.episode_length_buf = torch.zeros(1, device=self.device, dtype=torch.long)
        
        # Observation groups (RSL-RL uses TensorDict with named groups)
        self._obs_keys = ["policy"]
        
        # Current observation buffer
        self._current_obs: Optional[torch.Tensor] = None
        
        # Configuration placeholder
        self.cfg = env.cfg
    
    def _to_tensor(self, arr) -> torch.Tensor:
        """Convert numpy array to torch tensor on device."""
        return torch.from_numpy(arr).float().to(self.device)
    
    def _obs_to_tensordict(self, obs: torch.Tensor) -> TensorDict:
        """Wrap observation tensor in TensorDict for RSL-RL."""
        return TensorDict(
            {"policy": obs.unsqueeze(0)},  # Add batch dim
            batch_size=[1],
            device=self.device,
        )
    
    def get_observations(self) -> TensorDict:
        """Return current observations as TensorDict."""
        if self._current_obs is None:
            # Initial reset if needed
            obs_np = self._env.reset()
            self._current_obs = self._to_tensor(obs_np)
            self.episode_length_buf.zero_()
        
        return self._obs_to_tensordict(self._current_obs)
    
    def reset(self) -> TensorDict:
        """Reset all environments (just one in our case)."""
        obs_np = self._env.reset()
        self._current_obs = self._to_tensor(obs_np)
        self.episode_length_buf.zero_()
        return self.get_observations()
    
    def step(
        self, actions: torch.Tensor
    ) -> Tuple[TensorDict, torch.Tensor, torch.Tensor, Dict]:
        """
        Step the environment with the given actions.
        
        Args:
            actions: Tensor of shape (num_envs, num_actions)
        
        Returns:
            observations: TensorDict with policy observations
            rewards: Tensor of shape (num_envs,)
            dones: Tensor of shape (num_envs,)
            extras: Dict with additional info (time_outs, log)
        """
        # Convert actions to numpy
        action_np = actions[0].cpu().numpy()
        
        # Step environment
        obs_np, reward, done, info = self._env.step(action_np)
        
        # Update episode length
        self.episode_length_buf += 1
        
        # Convert to tensors
        self._current_obs = self._to_tensor(obs_np)
        rewards = torch.tensor([reward], device=self.device, dtype=torch.float32)
        dones = torch.tensor([done], device=self.device, dtype=torch.bool)
        
        # Build extras dict
        extras: Dict = {}
        
        # Time-outs for proper value bootstrapping
        if info.get("is_timeout", False):
            extras["time_outs"] = torch.tensor([True], device=self.device, dtype=torch.bool)
        else:
            extras["time_outs"] = torch.tensor([False], device=self.device, dtype=torch.bool)
        
        # Logging info
        log_info = {}
        if done:
            log_info["/episode/return"] = info.get("episode_return", 0.0)
            log_info["/episode/length"] = info.get("step_count", 0)
            log_info["/episode/success"] = 1.0 if info.get("is_success", False) else 0.0
        extras["log"] = log_info
        
        # Auto-reset on done
        if done:
            obs_np = self._env.reset()
            self._current_obs = self._to_tensor(obs_np)
            self.episode_length_buf.zero_()
        
        return self.get_observations(), rewards, dones, extras
    
    def close(self) -> None:
        """Clean up the environment."""
        self._env.close()


def make_vec_env(
    address: str = "127.0.0.1:50051",
    agent_name: str = "PiperAgent",
    device: str = "cpu",
    **kwargs,
) -> RslVecEnvWrapper:
    """
    Factory function to create a wrapped Piper-Lego environment.
    
    Args:
        address: gRPC server address
        agent_name: Name of the agent in the scene
        device: Torch device for tensors
        **kwargs: Additional config overrides for PiperLegoEnvConfig
    
    Returns:
        RslVecEnvWrapper ready for RSL-RL training
    """
    cfg = PiperLegoEnvConfig(address=address, agent_name=agent_name, **kwargs)
    env = PiperLegoEnv(cfg)
    return RslVecEnvWrapper(env, device=device)


__all__ = ["RslVecEnvWrapper", "make_vec_env"]

