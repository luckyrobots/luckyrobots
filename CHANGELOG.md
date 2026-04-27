# Changelog

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
