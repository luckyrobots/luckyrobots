# LuckyEngine + LeRobot: Getting Started

A short, do-this-then-this tutorial for taking a LuckyEngine (LE) scene through
to a trained imitation-learning policy that runs in LE, then in Genesis, then on
a real robot. About a weekend of work end-to-end if your scene is already built.

```{note}
**SO-100 Sim2Real without the teleop.** Record in sim, deploy on real. Instead
of manual leader-arm teleop (one human, one demo at a time), demos are scripted
in LuckyEngine — hands-free, repeatable, same dataset format. A checkpoint
trained *only* on those sim recordings reached **72% success on the real
SO-100**, with no domain randomization and no real-data fine-tuning.
```

Video assets for this tutorial stream from the companion GitHub Pages site at
<https://luckyrobots.github.io/lerobot-luckyengine-tutorial/>; they are embedded
below rather than committed to this repository.

```{raw} html
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0;">
  <figure style="margin:0;">
    <video autoplay muted loop playsinline preload="metadata" style="width:100%;border-radius:8px;background:#000;"
      src="https://luckyrobots.github.io/lerobot-luckyengine-tutorial/videos/hero_teleop.mp4"></video>
    <figcaption><b>Manual leader-arm teleop.</b> One human, one demo at a time.</figcaption>
  </figure>
  <figure style="margin:0;">
    <video autoplay muted loop playsinline preload="metadata" style="width:100%;border-radius:8px;background:#000;"
      src="https://luckyrobots.github.io/lerobot-luckyengine-tutorial/videos/hero_sim.mp4"></video>
    <figcaption><b>Scripted in LuckyEngine.</b> Hands-free, repeatable, same dataset format.</figcaption>
  </figure>
</div>
<figure style="margin:16px 0;">
  <video autoplay muted loop playsinline preload="metadata" style="width:100%;border-radius:8px;background:#000;"
    src="https://luckyrobots.github.io/lerobot-luckyengine-tutorial/videos/hero_sim2real.mp4"></video>
  <figcaption>The same checkpoint, autonomous on the real SO-100. Two-camera DICE-IMLE @ 30 Hz.</figcaption>
</figure>
```

**Steps**

1. Record demos in LE
2. Train (ACT)
3. Evaluate in LE (in-domain)
4. Evaluate in Genesis (sim-to-sim)
5. Evaluate on the real robot
6. Case study — what we shipped
7. Going deeper
8. Supplementary

## 1 · Record demos in LE

Today, LE demos are produced by **scripted C# scene scripts**, not by human
teleop. The script drives the robot through waypoints; the C++ engine writes a
LeRobot 3.0 dataset to disk in parallel.

```{raw} html
<figure style="margin:16px 0;">
  <video controls preload="metadata" style="width:100%;border-radius:8px;background:#000;"
    src="https://luckyrobots.github.io/lerobot-luckyengine-tutorial/videos/recording_walkthrough.mp4"></video>
  <figcaption>Video 1.0 — End-to-end walkthrough of recording demonstrations in LE.</figcaption>
</figure>
<figure style="margin:16px 0;">
  <video autoplay muted loop playsinline preload="metadata" style="width:100%;border-radius:8px;background:#000;"
    src="https://luckyrobots.github.io/lerobot-luckyengine-tutorial/videos/so100_sim.mp4"></video>
  <figcaption>Video 1.1 — SO-100 pick-and-place recorded inside LuckyEngine — the dataset behind the case study in §6.</figcaption>
</figure>
```

### 1.1 Start a recording

Two ways to drive the recorder. Either is fine; pick whichever matches how you
want to iterate.

**From a C# scene script.** The path the case study used. See
`Assets/ContentVault/Examples/SO100 Pick And Place/SO100PickAndPlace.cs` for a
complete example. The minimum is:

```csharp
// Hazel-ScriptCore/Source/Hazel/Data/Observer.cs
Observer.RegisterTask(0, "Pick up the lego block and place it on the target");
Observer.StartRecording();

foreach (var episode in episodes) {
    DriveSO100ToWaypoints();              // drive RobotControllerComponent
    bool ok = CheckTaskSuccess();         // task-specific heuristic
    Observer.EndCurrentEpisode(ok);
    ResetSceneForNextEpisode();
}

Observer.StopRecording();
```

### 1.2 What ends up in each frame

| Field | Contents |
|-------|----------|
| `action` | float32 list, one entry per actuator (`m->nu`). |
| `observation.state` | float32 list — *all* actuated joint qpos. Often wider than your policy needs; trim in the cleanup pass (§2). |
| `observation.images.<cam>` | uint8 RGB written as h264 mp4 chunks (not embedded in parquet). |

```{tip}
**Use 96×96 cameras.** Bigger costs you the 30 Hz inference budget.
```

### 1.3 What ends up on disk

LE writes the LeRobot 3.0 layout directly — the directory it produces under
`DataSessions/session_<ts>/` is the directory `LeRobotDataset(root=...)` opens.
No format conversion is needed, but you'll usually want a small Python pass to
trim `observation.state` down to the joints your policy needs and to drop any
cameras you don't want to train on.

```text
session_<ts>/
├── data/chunk-NNN/file-NNN.parquet     # one parquet per episode
├── videos/observation.images.<cam>/    # h264 mp4 per camera per episode
└── meta/info.json + stats.json + tasks.parquet + episodes/
```

## 2 · Train (ACT)

Use ACT to start. It's the policy LeRobot recommends out of the box, fast to
train, and strong on tabletop manipulation
([Zhao et al. 2023](https://arxiv.org/abs/2304.13705)).

```bash
lerobot-train \
  --dataset.root=path/to/your_session \
  --dataset.repo_id=local/your_session \
  --policy.type=act \
  --policy.chunk_size=100 \
  --batch_size=8 \
  --steps=100000 \
  --output_dir=outputs/act_my_task \
  --job_name=act_my_task \
  --wandb.enable=true
```

ACT auto-adapts to your dataset's number of cameras, state dim, and action dim
from `meta/info.json`, so most knobs are task-agnostic. The ones that matter:

| Knob | Effect |
|------|--------|
| `policy.chunk_size` | actions predicted per forward pass. 100 is a fine default; smaller = more reactive. |
| `policy.kl_weight` | CVAE KL term. Default 10. Lower if the latent collapses. |
| `batch_size` | start at 8; raise as VRAM allows. |
| `steps` | ~100k for ~200 demos on a tabletop task is a solid recipe. |

Wall-clock: 2–6 hours on a consumer GPU (RTX 3090 / 4070 / 4090 class),
dominated by video decoding. Checkpoints land in
`outputs/<job_name>/checkpoints/<step>/`. **Keep at least the last few** — policy
quality is non-monotonic across training and the best checkpoint is rarely the
final step.

## 3 · Evaluate in LE (in-domain)

The fastest signal you have is closing the loop in the same simulator you
trained in. Talk to the running LE process from Python through the
[`luckyrobots`](https://github.com/luckyrobots/luckyrobots) SDK. `step()` returns a synchronous post-step
`ObservationResponse` — state and any synchronized camera frames in one object —
so there's no async stream to race against.

```{raw} html
<figure style="margin:16px auto;max-width:560px;">
  <video controls preload="metadata" style="width:100%;border-radius:8px;background:#000;"
    src="https://luckyrobots.github.io/lerobot-luckyengine-tutorial/videos/le_finalist_trials.mp4"></video>
  <figcaption style="text-align:center;">Trained policy running in LE during in-domain eval — finalist checkpoint at 96×96 / 30 fps.</figcaption>
</figure>
```

```python
from luckyrobots import Session

with Session(host="127.0.0.1", port=50051) as session:
    # Launch + connect (or use session.connect(...) if LE is already running):
    session.start(scene="my_scene", robot="my_robot", task="my_task")

    # Opt in to synchronized camera frames on every step / reset:
    session.configure_cameras([
        {"name": "CameraFront",   "width": 96, "height": 96},
        {"name": "LaptopCamera",  "width": 96, "height": 96},
    ])

    policy, pre, post = load_policy(checkpoint_dir)
    state_dim = 6

    for trial in range(N_TRIALS):
        obs_resp = session.reset()                    # ObservationResponse
        for _ in range(SETTLE_STEPS):
            obs_resp = session.step(HOME_ACTION)

        for step in range(MAX_STEPS):
            state  = obs_resp.observation[:state_dim]                   # list[float]
            frames = {cf.name: cf.image for cf in obs_resp.camera_frames}
            action = predict(policy, pre, post, build_obs(state, frames))
            obs_resp = session.step(action.tolist())
            if success(obs_resp):
                break
```

```{note}
**A few things readers tripped on.**

- **`task` is required** in `session.start(...)`.
- **State lives at `obs_resp.observation`** (a flat `list[float]`), not at a
  nested `.observation.observations`. Slice the first `state_dim` entries to get
  the joint state your policy was trained on.
- **Camera frames are part of the same response** after
  `configure_cameras([...])`. No separate stream to subscribe to.
```

## 4 · Evaluate in Genesis (sim-to-sim)

LE → LE is necessary but not sufficient: the policy is being graded by the same
simulator it learned the quirks of. Mirroring your scene in
[Genesis](https://github.com/Genesis-Embodied-AI/Genesis) — a different physics
solver and a different renderer — gives you a cheap, hardware-free
generalization probe.

1. **Convert axes.** LE is Y-up, Genesis is Z-up — apply
   `hz_to_gs(p) = (p[0], -p[2], p[1])` to positions, lookats, and lights.
2. **Reuse the MJCF.** Pass the same `so_arm100.xml` to both sims and match the
   home-pose keyframe.
3. **Place cameras by intrinsics.** Same position, lookat, FOV, and 96×96 render
   size.
4. **Rebuild task objects.** Close enough is good enough — you're testing
   generalization, not pixel parity.

The reference `genesis_backend.py` wraps a built-in SO-100 scene behind a small
Python interface (`connect`, `reset`, `step`, `get_observation`, …). Your eval
driver loads the same checkpoint and calls those instead of LE's. Same
checkpoint, different driver.

```{raw} html
<figure style="margin:16px auto;max-width:560px;">
  <video controls preload="metadata" style="width:100%;border-radius:8px;background:#000;"
    src="https://luckyrobots.github.io/lerobot-luckyengine-tutorial/videos/genesis_sim2sim.mp4"></video>
  <figcaption style="text-align:center;">Vanilla IMLE checkpoint <code>044800</code>, zero-shot in Genesis. 96×96 @ 30 fps.</figcaption>
</figure>
```

## 5 · Evaluate on the real robot

Once your checkpoint clears LE → LE and LE → Genesis, the deployment loop is
mechanically simple: read cameras + joints, run the policy, send a position
command, repeat.

```{raw} html
<figure style="margin:16px auto;max-width:560px;">
  <video controls preload="metadata" style="width:100%;border-radius:8px;background:#000;"
    src="https://luckyrobots.github.io/lerobot-luckyengine-tutorial/videos/sim2real_real_robot.mp4"></video>
  <figcaption style="text-align:center;">Real SO-100 running the same checkpoint trained only on simulator demos.</figcaption>
</figure>
```

**Figure 5.1 — Real-robot inference loop** (measured latencies, SO-100 IMLE on
RTX 5090), within a 33 ms (30 Hz) budget:

```text
cameras            preprocess        policy.predict     action mapper      robot.send_position
async_read    →    resize 96x96  →   EMA + AMP      →   rad → deg, clip →  follower bus
+ joint encoder    state→units       fwd pass / queue   safety scan        @ 30 Hz, no-wait
~5-8 ms            ~2-3 ms           9-17 ms            <1 ms              ~2-4 ms
          └──────────── precise sleep to 33 ms (30 Hz) ────────────┘
```

1. **Match cameras & control rate.** Same model, resolution, mounting pose, and
   Hz as your LE scene. If you mirrored a camera in LE, mirror it on the real cam
   (`cv2.flip(..., 1)`) — without that flip the policy sees a mirror-image arm
   and fails silently.
2. **Match action units.** Convert radians↔degrees if needed and verify the
   dataset's min/max against the calibrated joint range.
3. **Calibrate joint zeros.** Re-run calibration so "0 rad in the dataset" maps
   to physical home consistently across power cycles.
4. **Add a safety scan.** Workspace + per-joint position + velocity caps. Abort
   (don't clip silently) if the policy drifts off-distribution.

```python
from lerobot.robots.so_follower.so_follower import SOFollower
from lerobot.robots.so_follower.config_so_follower import SOFollowerRobotConfig
from lerobot.cameras.realsense.camera_realsense import RealSenseCamera
from lerobot.cameras.realsense.configuration_realsense import RealSenseCameraConfig

# --- robot + cameras --------------------------------------------------------
follower = SOFollower(SOFollowerRobotConfig(
    port="COM5", id="my_follower", use_degrees=True))
follower.connect(calibrate=True)            # uses cached calibration

cam_a = RealSenseCamera(RealSenseCameraConfig(   # LaptopCamera
    serial_number_or_name=SERIAL_A, fps=30, width=640, height=480))
cam_b = RealSenseCamera(RealSenseCameraConfig(   # CameraFront
    serial_number_or_name=SERIAL_B, fps=30, width=640, height=480))
cam_a.connect(); cam_b.connect()

policy, pre, post = load_checkpoint(CKPT_DIR)
mapper = ActionMapper(stats_path=STATS, calib_path=CALIB)

# --- 30 Hz inference loop ---------------------------------------------------
dt = 1.0 / 30.0
while step < max_steps:
    t0 = time.perf_counter()

    # state: dict like {"shoulder_pan.pos": deg,...} -> vector in JOINT_NAMES order
    obs = follower.get_observation()
    state_real  = np.array([obs[f"{j}.pos"] for j in JOINT_NAMES], dtype=np.float32)
    state_train = mapper.state_to_training(state_real)

    # cameras: native res, then horizontal flip on LaptopCamera, then 96x96
    img_a = cv2.flip(cam_a.async_read(), 1)
    img_b = cam_b.async_read()
    frames = {
        "LaptopCamera": cv2.resize(img_a, (96, 96), interpolation=cv2.INTER_LINEAR),
        "CameraFront":  cv2.resize(img_b, (96, 96), interpolation=cv2.INTER_LINEAR),
    }

    action_rad  = policy.predict(state_train, frames)
    action_real, _, outside = mapper.action_to_real(action_rad)
    if outside: abort("action outside calibrated range")

    follower.send_action({f"{n}.pos": float(v)
                          for n, v in zip(JOINT_NAMES, action_real)})
    precise_sleep(dt - (time.perf_counter() - t0))
```

```{warning}
**33 ms is tight, but achievable.** On an RTX 5090 the SO-100 forward pass is
9–17 ms with `cudnn.benchmark=True` + AMP + warmup. Use `async_read` camera
backends so I/O overlaps with the previous step's policy call. If you can't hold
30 Hz, drop to 20 Hz *uniformly* — jitter hurts more than a lower steady rate.
```

## 6 · Case study — what we shipped

```{note}
**Bottom line.** Vanilla IMLE: **84%** success in LE, **67%** in Genesis
(zero-shot, gap = 17 pp). DICE-IMLE: **76%** Genesis sim-to-sim and **72%** on
the real SO-100 — closing the sim-real gap with no domain randomization.
```

200 LE-recorded SO-100 episodes, 30 Hz, 96×96, two cameras (CameraFront +
LaptopCamera). Vanilla IMLE policy with a shared ResNet18 + SpatialSoftmax
encoder (ImageNet-pretrained, not frozen), 6-DOF joint state, 1D U-Net generator
(~66 M params) trained with RS-IMLE + EMA + AMP — single forward pass, no
diffusion denoising.

### 6.1 Vanilla IMLE in LE — 84% on the best finalist

Three checkpoints survived a coarse 5-trial sweep across 51 k training steps;
each was then re-run for 25 trials. Checkpoint `044800` won decisively.

**Figure 6.1 — LE finalist evaluation, 25 trials × 3 checkpoints** (success /
lift / grasp %):

| Checkpoint | success | lift | grasp |
|-----------|---------|------|-------|
| `020160` | 52 | 72 | 68 |
| `022400` | 60 | 92 | 92 |
| `044800` | **84** | 96 | 96 |

```{raw} html
<figure style="margin:16px auto;max-width:480px;">
  <video controls preload="metadata" style="width:100%;border-radius:8px;background:#000;image-rendering:pixelated;"
    src="https://luckyrobots.github.io/lerobot-luckyengine-tutorial/videos/le_finalist_trials.mp4"></video>
  <figcaption style="text-align:center;">All 80 finalist trials in LE, concatenated. 96×96 @ 30 fps.</figcaption>
</figure>
```

### 6.2 The transfer cliff — 84% LE drops to 67% Genesis

Same checkpoint `044800`, zero-shot in Genesis with no retraining and no domain
randomization, fell to **67%** success — a 17 pp gap caused entirely by
renderer-specific style differences (colour cast, micro-shading, edge
sharpness). This is the gap DICE was built to close.

### 6.3 What closed the gap — DICE v3

We replaced the ResNet18 backbone with a frozen **DICE v3** encoder pretrained on
~21 k paired LE↔Real frames (100 episodes × 212 frames). The encoder is a
5-stage ConvBlock (GroupNorm + SiLU, ~2.4 M params) producing a (B, 128, 6, 6)
L2-normalized grid. Three losses on the grid: dense paired InfoNCE (same-cell
positives across domains), VICReg variance/covariance, and DANN gradient-reverse.
Best checkpoint selected by cross-domain retrieval@1 (not loss). At deployment
the encoder is frozen and only a small adapter MLP (4608 → 256 → 128 per camera)
and the IMLE U-Net are trained on the SO-100 demos.

### 6.4 DICE-IMLE in Genesis sim2sim — 76%

**Figure 6.2 — DICE-IMLE in Genesis, 25 trials each** (success / lift / grasp %).
Best checkpoint `006280` reaches **76%** — within 8 pp of the vanilla LE
training-domain 84%, and well above the 67% zero-shot baseline, without ever
seeing Genesis pixels.

| Checkpoint | success | lift | grasp |
|-----------|---------|------|-------|
| `006280` | **76** | 80 | 84 |
| `009430` | 64 | 68 | 72 |

### 6.5 DICE-IMLE on the real SO-100 — 72%

The same DICE-conditioned policy was deployed on the physical SO-100 follower
(2× RealSense @ 96×96, 30 Hz control loop). 25 trials each at two checkpoint
snapshots.

**Figure 6.3 — Real-robot success vs checkpoint step.** Solid measurements at
step 18 000 (0.60) and 19 500 (0.72) are 25-trial runs; intermediate points are
linearly interpolated, and earlier steps are open-circle lower-bound estimates.

```{raw} html
<figure style="margin:16px auto;max-width:640px;">
  <video controls preload="metadata" style="width:100%;border-radius:8px;background:#000;"
    src="https://luckyrobots.github.io/lerobot-luckyengine-tutorial/videos/sim2real_real_robot.mp4"></video>
  <figcaption style="text-align:center;">Real-robot pick-and-place using DICE-IMLE checkpoint 19 500.</figcaption>
</figure>
```

> **72% success on the real SO-100** — checkpoint trained only on simulator
> recordings. No domain randomization. No real-data fine-tuning. Just LE-recorded
> demos → `lerobot-train` → deployment.

## 7 · Going deeper

- **Inference architecture canon** — gRPC, AgentBatch, agent schemas, the
  lock-step protocol: `LuckyEngine/docs/lerobot-inference.md`.
- **LeRobot library docs** — <https://huggingface.co/docs/lerobot>.
- **Genesis** — <https://github.com/Genesis-Embodied-AI/Genesis>.
- **ACT paper** — Zhao et al. 2023,
  [arXiv:2304.13705](https://arxiv.org/abs/2304.13705).

## 8 · Supplementary

Reference material moved out of the main flow. Skip unless you want the orienting
picture or the install checklist.

### 8.1 Pipeline overview

**Figure 8.1 — The whole pipeline.** Record once in LE, train once with LeRobot,
evaluate the same checkpoint against three lanes:

```text
LE scene  →  Record demos  →  Train ACT  →  Inference  →  ┌─ In-domain (LE)        §3
MuJoCo +     LeRobot 3.0      lerobot-      ~30 Hz loop    ├─ Sim-to-sim (Genesis)  §4
cameras      dataset         train                        └─ Sim-to-real           §5
```

### 8.2 Setup & prerequisites

This guide assumes your LE scene is already built and a robot agent is in it. If
you need to build one first, the walkthrough below covers scene creation inside
the LE editor; otherwise jump to the install table.

```{raw} html
<figure style="margin:16px 0;">
  <video controls preload="metadata" style="width:100%;border-radius:8px;background:#000;"
    src="https://luckyrobots.github.io/lerobot-luckyengine-tutorial/videos/scene_creation.mp4"></video>
  <figcaption>Video 8.1 — Building a scene in LuckyEngine and getting it ready for recording.</figcaption>
</figure>
```

| Requirement | Detail |
|-------------|--------|
| OS | Windows 10/11 for LE; Linux for the Python trainer. |
| Python | 3.10–3.12. `pip install lerobot luckyrobots torch grpcio numpy` (LeRobot ≥ 3.0). For §4 (Genesis sim-to-sim) also `pip install genesis-world`. |
| GPU | Any CUDA card for training. LE renders on the host GPU. |
| LE build | Release x64 from `LuckyEngine.sln`. |
| gRPC port | SDK default `50051`; pass `port=` to `Session(...)` if your LE binds something else. |
