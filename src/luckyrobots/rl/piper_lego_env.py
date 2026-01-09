"""
Piper-Lego pick-and-place environment for PPO training.

This environment:
- Connects to LuckyEditor via gRPC (AgentService + SceneService)
- Provides observations: joint positions/velocities, end-effector pos, block pos, target pos
- Computes shaped rewards for reaching, grasping, and placing
- Resets by randomizing block position
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np

from ..env.agent_env import AgentEnv, AgentStep
from ..grpc.session import GrpcConfig, GrpcSession, pb


@dataclass
class PiperLegoEnvConfig:
    """Configuration for the Piper-Lego environment."""
    
    # gRPC connection
    address: str = "127.0.0.1:50051"
    agent_name: str = "PiperAgent"
    target_fps: int = 30
    
    # Episode settings
    max_episode_steps: int = 200
    
    # Entity names in the scene
    end_effector_name: str = "link6"
    block_name: str = "Red Block"
    target_name: str = "BoxTarget"
    
    # Block randomization ranges (matching PiperLego.cs)
    block_x_range: Tuple[float, float] = (0.04, 0.44)  # 0.24 ± 0.2
    block_z_range: Tuple[float, float] = (-0.25, 0.25)
    block_y: float = 0.015  # Height above table
    
    # Reward weights
    reach_weight: float = 1.0
    grasp_weight: float = 2.0
    lift_weight: float = 8.0
    place_weight: float = 3.0
    release_weight: float = 3.0
    success_bonus: float = 100.0
    action_penalty: float = 0.01
    gripper_action_weight: float = 0.5
    
    # Success thresholds
    grasp_dist_threshold: float = 0.05  # 5cm to consider "grasped"
    lift_height: float = 0.10  # 10cm above table to consider "lifted"
    place_dist_threshold: float = 0.08  # 8cm to consider "placed"
    release_dist_threshold: float = 0.10  # ee must move away to count as released


class PiperLegoEnv:
    """
    Single-agent Piper-Lego pick-and-place environment.
    
    Observations (dim=25):
      - joint_pos (6): normalized joint positions
      - joint_vel (6): normalized joint velocities  
      - ee_pos (3): end-effector position
      - block_pos (3): block position
      - target_pos (3): target position
      - ee_to_block (3): vector from ee to block
      - block_to_target (1): distance from block to target
    
    Actions (dim=7):
      - joint commands (6): normalized [-1, 1] for each arm joint
      - gripper (1): -1 = close, +1 = open
    """
    
    def __init__(self, cfg: Optional[PiperLegoEnvConfig] = None) -> None:
        self.cfg = cfg or PiperLegoEnvConfig()
        
        # Connect to LuckyEditor
        self._session = GrpcSession(GrpcConfig(address=self.cfg.address, secure=False))
        self._agent_env = AgentEnv(
            agent_name=self.cfg.agent_name,
            session=self._session,
            target_fps=self.cfg.target_fps,
        )
        
        # Cache entity IDs
        self._ee_id: Optional[int] = None
        self._block_id: Optional[int] = None
        self._target_id: Optional[int] = None
        
        # Episode state
        self._step_count = 0
        self._episode_return = 0.0
        self._last_obs: Optional[np.ndarray] = None
        
        # Observation/action dimensions
        self.num_obs = 25
        self.num_actions = 7
        
        # Discover and cache entity IDs
        self._discover_entities()
    
    def _discover_entities(self) -> None:
        """Find and cache entity IDs for ee, block, and target."""
        for name, attr in [
            (self.cfg.end_effector_name, "_ee_id"),
            (self.cfg.block_name, "_block_id"),
            (self.cfg.target_name, "_target_id"),
        ]:
            resp = self._session.scene.GetEntity(pb.GetEntityRequest(name=name))
            if resp.found:
                setattr(self, attr, resp.entity.id.id)
            else:
                print(f"[PiperLegoEnv] Warning: Entity '{name}' not found in scene")
    
    def _get_entity_position(self, entity_id: Optional[int]) -> np.ndarray:
        """Get the world position of an entity by ID."""
        if entity_id is None:
            return np.zeros(3, dtype=np.float32)
        
        resp = self._session.scene.GetEntity(pb.GetEntityRequest(id=pb.EntityId(id=entity_id)))
        if not resp.found:
            return np.zeros(3, dtype=np.float32)
        
        t = resp.entity.transform.position
        return np.array([t.x, t.y, t.z], dtype=np.float32)
    
    def _build_observation(self, agent_step: AgentStep) -> np.ndarray:
        """Build full observation vector from agent step and scene queries."""
        # Agent observations: joint_pos (6) + joint_vel (6) + last_act (7) = 19
        # We'll use joint_pos and joint_vel, ignore last_act for policy obs
        agent_obs = agent_step.observations
        
        # Extract joint positions and velocities (first 12 dims of agent obs)
        joint_pos = agent_obs[0:6] if len(agent_obs) >= 6 else np.zeros(6, dtype=np.float32)
        joint_vel = agent_obs[6:12] if len(agent_obs) >= 12 else np.zeros(6, dtype=np.float32)
        
        # Get world positions
        ee_pos = self._get_entity_position(self._ee_id)
        block_pos = self._get_entity_position(self._block_id)
        target_pos = self._get_entity_position(self._target_id)
        
        # Compute relative vectors
        ee_to_block = block_pos - ee_pos
        block_to_target_dist = np.linalg.norm(block_pos - target_pos)
        
        # Concatenate full observation
        obs = np.concatenate([
            joint_pos,                                    # 6
            joint_vel,                                    # 6
            ee_pos,                                       # 3
            block_pos,                                    # 3
            target_pos,                                   # 3
            ee_to_block,                                  # 3
            np.array([block_to_target_dist], dtype=np.float32),  # 1
        ]).astype(np.float32)
        
        return obs
    
    def _compute_reward(
        self,
        obs: np.ndarray,
        action: np.ndarray,
        prev_obs: Optional[np.ndarray],
    ) -> Tuple[float, bool, Dict]:
        """Compute shaped reward and done flag."""
        # Extract positions from observation
        ee_pos = obs[12:15]
        block_pos = obs[15:18]
        target_pos = obs[18:21]
        
        ee_to_block_dist = np.linalg.norm(ee_pos - block_pos)
        block_to_target_dist = obs[24]  # Already computed
        block_height = block_pos[1]  # Y is up in Hazel

        # Action semantics: last dim is gripper; negative closes, positive opens.
        gripper = float(action[-1]) if action.size >= 1 else 0.0
        
        reward = 0.0
        info: Dict = {}
        
        # 1. Reaching reward: encourage moving ee toward block
        reach_reward = -self.cfg.reach_weight * ee_to_block_dist
        reward += reach_reward
        info["reach_reward"] = reach_reward
        
        # 2. Grasp shaping: encourage closing gripper when close to the block.
        is_near_block = ee_to_block_dist < self.cfg.grasp_dist_threshold
        if is_near_block:
            # Reward closing (gripper < 0) near the block, penalize opening.
            grasp_shaping = self.cfg.grasp_weight * (-gripper)
            reward += grasp_shaping
            info["grasp_shaping"] = grasp_shaping
        
        # 3. Lift reward: bonus when block is lifted
        is_lifted = block_height > self.cfg.lift_height
        if is_lifted:
            reward += self.cfg.lift_weight
            info["lift_bonus"] = self.cfg.lift_weight
        
        # 4. Placing reward: encourage block toward target
        place_reward = -self.cfg.place_weight * block_to_target_dist
        reward += place_reward
        info["place_reward"] = place_reward
        
        # 5. Release shaping near target: encourage opening gripper near the target
        is_near_target = block_to_target_dist < self.cfg.place_dist_threshold * 1.5
        if is_near_target and is_lifted:
            release_shaping = self.cfg.release_weight * (gripper)
            reward += release_shaping
            info["release_shaping"] = release_shaping

        # 6. Success: block is close to BoxTarget and appears \"settled\" (low height) with gripper open-ish.
        # We don't have contact sensors, so use conservative heuristics.
        is_released = ee_to_block_dist > self.cfg.release_dist_threshold and gripper > 0.2
        is_settled = block_height < max(self.cfg.block_y + 0.05, 0.06)
        is_success = (block_to_target_dist < self.cfg.place_dist_threshold) and is_released and is_settled
        if is_success:
            reward += self.cfg.success_bonus
            info["success_bonus"] = self.cfg.success_bonus
        
        # 7. Action penalty
        action_cost = self.cfg.action_penalty * np.sum(action ** 2)
        reward -= action_cost
        info["action_cost"] = action_cost
        
        # Done conditions
        done = is_success or self._step_count >= self.cfg.max_episode_steps
        info["is_success"] = is_success
        info["is_timeout"] = self._step_count >= self.cfg.max_episode_steps
        
        return float(reward), done, info
    
    def _randomize_block(self) -> None:
        """Randomize block position for episode reset."""
        if self._block_id is None:
            return

        # Preserve the original block scale from the scene (the Lego blocks are small).
        # If we overwrite scale with (1,1,1) the block appears as a huge cube.
        current = self._session.scene.GetEntity(pb.GetEntityRequest(id=pb.EntityId(id=self._block_id)))
        if current.found:
            s = current.entity.transform.scale
            scale = pb.Vec3(x=s.x, y=s.y, z=s.z)
        else:
            # Sensible fallback, but ideally the entity exists.
            scale = pb.Vec3(x=0.025, y=0.025, z=0.03)
        
        # Random position within configured ranges
        x = np.random.uniform(*self.cfg.block_x_range)
        z = np.random.uniform(*self.cfg.block_z_range)
        y = self.cfg.block_y
        
        # Random yaw rotation
        yaw = np.random.uniform(-np.pi, np.pi)
        
        # Convert yaw to quaternion (rotation around Y axis)
        qw = np.cos(yaw / 2)
        qy = np.sin(yaw / 2)
        
        transform = pb.Transform(
            position=pb.Vec3(x=x, y=y, z=z),
            rotation=pb.Quat(x=0, y=qy, z=0, w=qw),
            scale=scale,
        )
        
        self._session.scene.SetEntityTransform(
            pb.SetEntityTransformRequest(
                id=pb.EntityId(id=self._block_id),
                transform=transform,
            )
        )
    
    def reset(self) -> np.ndarray:
        """Reset the environment for a new episode."""
        self._step_count = 0
        self._episode_return = 0.0
        
        # Randomize block position
        self._randomize_block()
        
        # Send zero actions to settle the arm
        zero_action = np.zeros(self.num_actions, dtype=np.float32)
        for _ in range(5):
            step = self._agent_env.step(zero_action)
            time.sleep(0.02)
        
        # Get initial observation
        step = self._agent_env.step(zero_action)
        self._last_obs = self._build_observation(step)
        
        return self._last_obs.copy()
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Take a step in the environment.
        
        Args:
            action: Action vector of shape (num_actions,), values in [-1, 1]
        
        Returns:
            obs: Observation vector
            reward: Scalar reward
            done: Episode done flag
            info: Additional info dict
        """
        self._step_count += 1
        
        # Clip and send action
        action = np.clip(action, -1.0, 1.0).astype(np.float32)
        agent_step = self._agent_env.step(action)
        
        # Build observation
        obs = self._build_observation(agent_step)
        
        # Compute reward and done
        reward, done, info = self._compute_reward(obs, action, self._last_obs)
        
        self._episode_return += reward
        info["episode_return"] = self._episode_return
        info["step_count"] = self._step_count
        
        self._last_obs = obs
        
        return obs, reward, done, info
    
    def close(self) -> None:
        """Clean up resources."""
        self._session.close()
    
    @property
    def observation_space_shape(self) -> Tuple[int, ...]:
        return (self.num_obs,)
    
    @property
    def action_space_shape(self) -> Tuple[int, ...]:
        return (self.num_actions,)


__all__ = ["PiperLegoEnv", "PiperLegoEnvConfig"]

