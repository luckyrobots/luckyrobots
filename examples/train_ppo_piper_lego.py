#!/usr/bin/env python3
"""
PPO training script for Piper-Lego pick-and-place task.

This script:
1. Connects to LuckyEditor running the Piper-Lego scene via gRPC
2. Creates a single-agent RL environment
3. Trains a PPO policy using RSL-RL
4. Logs training progress to console and optionally W&B

Prerequisites:
    - LuckyEditor running with Piper-Lego scene
    - gRPC server started with Scene + MuJoCo + Agent services
    - ExternalRlMode enabled on the piper entity
    
Usage:
    python -m examples.train_ppo_piper_lego --address 192.168.1.240:50051 --iterations 100
    
    # With Weights & Biases:
    python -m examples.train_ppo_piper_lego --address 192.168.1.240:50051 --iterations 2000 --wandb

Install dependencies:
    pip install torch tensordict rsl-rl-lib wandb
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

import torch


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train PPO on Piper-Lego pick-and-place",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--address", "-a",
        default="127.0.0.1:50051",
        help="gRPC server address (default: 127.0.0.1:50051)",
    )
    parser.add_argument(
        "--agent-name",
        default="PiperAgent",
        help="Agent name in the scene (default: PiperAgent)",
    )
    parser.add_argument(
        "--iterations", "-n",
        type=int,
        default=100,
        help="Number of PPO iterations (default: 100)",
    )
    parser.add_argument(
        "--steps-per-iter",
        type=int,
        default=64,
        help="Environment steps per PPO iteration (default: 64)",
    )
    parser.add_argument(
        "--device",
        # Default to CUDA; if you don't have a CUDA build of PyTorch, we'll fail fast with a clear message.
        default="cuda",
        help="Torch device (default: cuda if available)",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=3e-4,
        help="Learning rate (default: 3e-4)",
    )
    parser.add_argument(
        "--save-path",
        type=str,
        default=None,
        help="Path to save trained model (default: None)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--step-log-every",
        type=int,
        default=0,
        help="If >0, print a heartbeat every N env steps during rollout (default: 0)",
    )
    # W&B arguments
    parser.add_argument(
        "--wandb",
        action="store_true",
        help="Enable Weights & Biases logging",
    )
    parser.add_argument(
        "--wandb-project",
        type=str,
        default="piper-lego-ppo",
        help="W&B project name (default: piper-lego-ppo)",
    )
    parser.add_argument(
        "--wandb-run-name",
        type=str,
        default=None,
        help="W&B run name (default: auto-generated)",
    )
    parser.add_argument(
        "--wandb-entity",
        type=str,
        default=None,
        help="W&B entity/team name (default: your default entity)",
    )
    args = parser.parse_args(argv)
    
    # Enforce CUDA if requested (default).
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        print("\n[Error] --device is set to CUDA but torch.cuda.is_available() is False.")
        print("You likely have a CPU-only PyTorch install. Install a CUDA-enabled build of torch, then retry.")
        return 2

    # Set seeds
    torch.manual_seed(args.seed)
    
    print("=" * 60)
    print("Piper-Lego PPO Training")
    print("=" * 60)
    print(f"  Address:        {args.address}")
    print(f"  Agent:          {args.agent_name}")
    print(f"  Device:         {args.device}")
    print(f"  Iterations:     {args.iterations}")
    print(f"  Steps/iter:     {args.steps_per_iter}")
    print(f"  Learning rate:  {args.lr}")
    print(f"  W&B:            {'enabled' if args.wandb else 'disabled'}")
    print("=" * 60)
    
    # Initialize W&B if requested
    wandb_run = None
    if args.wandb:
        try:
            import wandb
            
            wandb_config = {
                "address": args.address,
                "agent_name": args.agent_name,
                "iterations": args.iterations,
                "steps_per_iter": args.steps_per_iter,
                "learning_rate": args.lr,
                "seed": args.seed,
                "device": args.device,
                # PPO hyperparams
                "num_learning_epochs": 5,
                "num_mini_batches": 4,
                "clip_param": 0.2,
                "gamma": 0.99,
                "lam": 0.95,
                "value_loss_coef": 1.0,
                "entropy_coef": 0.01,
                "max_grad_norm": 1.0,
                # Network architecture
                "actor_hidden_dims": [256, 128, 64],
                "critic_hidden_dims": [256, 128, 64],
                "activation": "elu",
                "init_noise_std": 1.0,
            }
            
            wandb_run = wandb.init(
                project=args.wandb_project,
                entity=args.wandb_entity,
                name=args.wandb_run_name,
                config=wandb_config,
                save_code=True,
            )
            print(f"  W&B run:        {wandb_run.url}")
        except ImportError:
            print("\n[Warning] wandb not installed. Install with: pip install wandb")
            print("Continuing without W&B logging...")
            args.wandb = False
    
    # Import here to avoid import errors if deps missing
    try:
        from tensordict import TensorDict
        from rsl_rl.algorithms import PPO
        from rsl_rl.modules import ActorCritic
        from rsl_rl.storage import RolloutStorage
    except ImportError as e:
        print(f"\n[Error] Missing dependencies: {e}")
        print("Install with: pip install torch tensordict rsl-rl-lib")
        return 1
    
    # Import our environment
    # Add src to path for local development
    src_path = str(Path(__file__).parent.parent / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    from luckyrobots.rl.rsl_vec_env import make_vec_env
    
    # Create environment
    print("\n[1/4] Creating environment...")
    try:
        env = make_vec_env(
            address=args.address,
            agent_name=args.agent_name,
            device=args.device,
        )
        print(f"  Observations: {env.num_obs}")
        print(f"  Actions:      {env.num_actions}")
    except Exception as e:
        print(f"\n[Error] Failed to create environment: {e}")
        print("Make sure LuckyEditor is running with the Piper-Lego scene and gRPC enabled.")
        return 1
    
    # Get initial observation for policy/storage initialization
    init_obs = env.get_observations()
    
    # Define obs_groups mapping (RSL-RL style)
    obs_groups = {
        "policy": ["policy"],  # Use "policy" obs group for actor
        "critic": ["policy"],  # Use same for critic (no privileged obs)
    }
    
    # Create actor-critic network
    print("\n[2/4] Creating policy network...")
    policy = ActorCritic(
        obs=init_obs,
        obs_groups=obs_groups,
        num_actions=env.num_actions,
        actor_hidden_dims=[256, 128, 64],
        critic_hidden_dims=[256, 128, 64],
        activation="elu",
        init_noise_std=1.0,
    ).to(args.device)
    
    num_params = sum(p.numel() for p in policy.parameters())
    print(f"  Network parameters: {num_params:,}")
    
    # Create rollout storage
    print("\n[3/4] Creating rollout storage...")
    storage = RolloutStorage(
        training_type="rl",
        num_envs=env.num_envs,
        num_transitions_per_env=args.steps_per_iter,
        obs=init_obs,
        actions_shape=(env.num_actions,),
        device=args.device,
    )
    
    # Create PPO algorithm
    ppo = PPO(
        policy=policy,
        storage=storage,
        num_learning_epochs=5,
        num_mini_batches=4,
        clip_param=0.2,
        gamma=0.99,
        lam=0.95,
        value_loss_coef=1.0,
        entropy_coef=0.01,
        learning_rate=args.lr,
        max_grad_norm=1.0,
        device=args.device,
    )
    
    # Training loop
    print("\n[4/4] Starting training...")
    print("-" * 60)
    
    total_steps = 0
    episode_returns = []
    episode_successes = []
    
    t_start = time.time()
    
    for iteration in range(1, args.iterations + 1):
        # Reset for new rollout
        obs = env.get_observations()
        
        # Collect rollout
        for step in range(args.steps_per_iter):
            # Get action from policy
            with torch.no_grad():
                actions = ppo.act(obs)
            
            # Step environment
            next_obs, rewards, dones, extras = env.step(actions)
            
            # Optional heartbeat so it's obvious we're stepping + sending nonzero actions
            if args.step_log_every and (total_steps % args.step_log_every == 0):
                a_mean = float(actions.abs().mean().item())
                # Joint0 position is obs[0] in our env layout.
                j0 = float(next_obs["policy"][0, 0].item())
                r0 = float(rewards[0].item())
                print(f"  step={total_steps:6d} | |a|mean={a_mean:0.3f} | j0={j0:+0.3f} | r={r0:+0.3f}")

            # Process step for PPO
            ppo.process_env_step(next_obs, rewards, dones, extras)
            
            # Track episode stats
            if "log" in extras and extras["log"]:
                log = extras["log"]
                if "/episode/return" in log:
                    episode_returns.append(log["/episode/return"])
                if "/episode/success" in log:
                    episode_successes.append(log["/episode/success"])
            
            obs = next_obs
            total_steps += 1
        
        # Compute returns and update policy
        ppo.compute_returns(obs)
        losses = ppo.update()
        
        # Compute metrics
        elapsed = time.time() - t_start
        fps = total_steps / elapsed
        avg_return = sum(episode_returns[-10:]) / max(1, len(episode_returns[-10:]))
        avg_success = sum(episode_successes[-10:]) / max(1, len(episode_successes[-10:]))
        
        # W&B logging (every iteration)
        if args.wandb and wandb_run is not None:
            import wandb
            wandb.log({
                "iteration": iteration,
                "total_steps": total_steps,
                "fps": fps,
                "episode/return_avg10": avg_return,
                "episode/success_avg10": avg_success,
                "loss/surrogate": losses["surrogate"],
                "loss/value": losses["value"],
                "loss/entropy": losses.get("entropy", 0.0),
            }, step=total_steps)
        
        # Console logging (every 5 iterations)
        if iteration % 5 == 0 or iteration == 1:
            print(
                f"Iter {iteration:4d} | "
                f"Steps {total_steps:6d} | "
                f"FPS {fps:5.1f} | "
                f"Return {avg_return:7.2f} | "
                f"Success {avg_success:4.1%} | "
                f"Loss: surr={losses['surrogate']:.4f} val={losses['value']:.4f}"
            )
    
    print("-" * 60)
    elapsed = time.time() - t_start
    print(f"\nTraining completed in {elapsed:.1f}s ({total_steps} steps, {total_steps/elapsed:.1f} FPS)")
    
    # Save model if requested
    if args.save_path:
        save_path = Path(args.save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(policy.state_dict(), save_path)
        print(f"Model saved to: {save_path}")
        
        # Log model as W&B artifact
        if args.wandb and wandb_run is not None:
            import wandb
            artifact = wandb.Artifact(
                name=f"piper-ppo-model-{wandb_run.id}",
                type="model",
                description="Trained PPO policy for Piper-Lego pick-and-place",
            )
            artifact.add_file(str(save_path))
            wandb_run.log_artifact(artifact)
            print(f"Model uploaded to W&B as artifact")
    
    # Final stats
    final_return = sum(episode_returns[-10:]) / len(episode_returns[-10:]) if episode_returns else 0.0
    final_success = sum(episode_successes[-10:]) / len(episode_successes[-10:]) if episode_successes else 0.0
    
    if episode_returns:
        print(f"\nFinal 10-episode average return: {final_return:.2f}")
    if episode_successes:
        print(f"Final 10-episode success rate:   {final_success:.1%}")
    
    # Log final summary to W&B
    if args.wandb and wandb_run is not None:
        import wandb
        wandb.summary["final_return"] = final_return
        wandb.summary["final_success_rate"] = final_success
        wandb.summary["total_steps"] = total_steps
        wandb.summary["training_time_sec"] = elapsed
        wandb.finish()
    
    # Cleanup
    env.close()
    print("\nDone!")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
