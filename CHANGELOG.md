# Changelog

## 0.3.0 (2026-05-05) — Runtime gain override, scene reset, editor play/stop

Tracks the LuckyEngine `mick/policy-fixes` branch — runtime PD/scale tuning,
soft scene reset, gRPC-driven editor play/stop, and recording-aware metadata.

### Added
- `RobotController.set_policy_gains(slot, overrides)` /
  `clear_policy_gains(slot)` for per-joint runtime PD/effort/scale/default
  override on an active slot — no descriptor reload, no policy reseed.
  Unset fields preserve descriptor values (sentinel = `None` in Python,
  `NaN` on the wire). Both sync and async (`async_robots.py`) variants.
- `Session.enter_play_mode()` / `exit_play_mode()` and `AsyncSession`
  equivalents drive the editor Edit ↔ Play state machine over gRPC.
  Async transitions; poll readiness via `get_agent_schema` /
  `get_model_info`. Session boundaries, **not** pause/resume — Exit
  tears down the active recording.
- `Session.reset_scene(preserve_time=False)` and
  `MujocoScene.reset(preserve_time=False)` — soft reset back to
  `keyframe[0]` / `qpos0`, zero ctrl/forces, reseed active PolicyRuntime
  PD targets. Recording continues across the reset.
- New proto messages — `JointGainOverride`, `EnterPlayMode{Request,
  Response}`, `ExitPlayMode{Request,Response}`, `ResetScene{Request,
  Response}` — and five new RPCs (`SetPolicyGains`, `ClearPolicyGains`,
  `EnterPlayMode`, `ExitPlayMode`, `ResetScene`).

### Notes
- The recording Parquet schema gained a new `frame_flags : uint8` column
  (set engine-side). Bit 0 = `new_policy_step` (this substep ran fresh
  ONNX inference vs. holding the previous action under decimation),
  bit 1 = `post_reset` (first frame after `ResetScene`). Existing
  consumers ignore the column; new consumers should filter on it for
  correct IL training under decimation.
- Generated `*_pb2.py` / `*_pb2_grpc.py` regenerated with
  `grpcio-tools` 1.80.0 (was 1.78.0 in 0.2.0). The only functional
  difference in untouched-service stubs is the version-string constant.

## 0.2.0 (2026-04-27) — Policy + MujocoScene API

Substantial expansion to support LuckyEngine's `policy-redo` branch
(multi-slot PolicySlot, MotionGraph gating, runtime descriptor swap) and the
upgraded MujocoSceneService.

### Added
- `RobotController` high-level wrapper covering all 21 new policy + motion-
  graph RPCs (slot activation, descriptor swap, driven-joints mask, command
  store, motion-graph inputs, base pose, last action, streaming state).
- `MujocoScene` high-level wrapper for the upgraded MujocoSceneService:
  ownership map on `GetModelInfo`, `StateFilter`-aware streaming, policy-
  claim-aware `SetControl`, fully-implemented `SetQpos` with automatic PD
  reseed, `GetActuatorGains` for `NeutralizeActuatorsForTorquePolicy`
  diagnostics.
- `set_robot_pose` helper (qpos-layout-aware teleport).
- `validate_session` startup-validation pass with structured warnings.
- `validate_session` and reflection-based `has_rpc` for runtime feature
  detection (lets clients gracefully degrade against older engines).
- 4 new example scripts: single_policy_with_commands, policy_descriptor_hot_swap,
  scene_introspection, actuator_gain_inspector.
- Type stubs (`py.typed` marker) for IDE autocomplete.
- `luckyrobots inspect <host:port>` CLI for one-shot diagnostics.

### Changed
- `RobotController.get_last_action` now returns `(np.ndarray, list[str])`
  instead of `(list, list)` for direct numpy interop.

### Notes
- Generated stubs use absolute imports (matching upstream convention).
- Vendored against engine `mick/policy-redo` branch which integrates and
  extends `mick/grpc-api` (the original v0.2.0 base): preserves all
  existing task-contract / action-group / progress RPCs and
  `LuckyEnv` / `reflection.py` modules.
