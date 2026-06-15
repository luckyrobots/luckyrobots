# LuckyEngine + LeRobot: Getting Started

Record demonstrations in **LuckyEngine** (LE), train an imitation-learning
policy with **LeRobot**, and deploy the same checkpoint in LE, then Genesis,
then on a real SO-100 — **72% success on the real robot, trained only on
simulator demos** (no domain randomization, no real-data fine-tuning).

- 📖 Full step-by-step guide: [getting-started-lerobot.md](getting-started-lerobot.md)
- 🌐 Rendered tutorial: <https://luckyrobots.github.io/lerobot-luckyengine-tutorial/>
- 📦 Python SDK: [`luckyrobots`](https://github.com/luckyrobots/luckyrobots)

This directory is self-contained: the write-up, plus the demo clips under
[`videos/`](videos). The videos embed inline on GitHub below — if a player
doesn't load, use the link beneath it.

---

## The pitch: sim demos → real robot

Manual leader-arm teleop gives you one human, one demo at a time. Scripting the
same task in LuckyEngine is hands-free, repeatable, and writes the identical
LeRobot dataset format.

**Manual leader-arm teleop** — one human, one demo at a time

<video src="videos/hero_teleop.mp4" controls muted width="480"></video>

▶️ [hero_teleop.mp4](videos/hero_teleop.mp4)

**Scripted in LuckyEngine** — hands-free, repeatable, same dataset format

<video src="videos/hero_sim.mp4" controls muted width="480"></video>

▶️ [hero_sim.mp4](videos/hero_sim.mp4)

**The payoff** — the same checkpoint, autonomous on the real SO-100 (two-camera DICE-IMLE @ 30 Hz)

<video src="videos/hero_sim2real.mp4" controls muted width="640"></video>

▶️ [hero_sim2real.mp4](videos/hero_sim2real.mp4)

---

## 1 · Record demos in LE

Scripted C# scene scripts drive the robot through waypoints while the engine
writes a LeRobot 3.0 dataset to disk in parallel.

**End-to-end walkthrough of recording demonstrations in LE**

<video src="videos/recording_walkthrough.mp4" controls muted width="640"></video>

▶️ [recording_walkthrough.mp4](videos/recording_walkthrough.mp4)

**SO-100 pick-and-place recorded inside LuckyEngine** — the dataset behind the case study

<video src="videos/so100_sim.mp4" controls muted width="480"></video>

▶️ [so100_sim.mp4](videos/so100_sim.mp4)

---

## 3 · Evaluate in LE (in-domain)

**Trained policy running in LE during in-domain eval** — finalist checkpoint at 96×96 / 30 fps

<video src="videos/le_finalist_trials.mp4" controls muted width="560"></video>

▶️ [le_finalist_trials.mp4](videos/le_finalist_trials.mp4)

---

## 4 · Evaluate in Genesis (sim-to-sim)

**Vanilla IMLE checkpoint `044800`, zero-shot in Genesis** — 96×96 @ 30 fps

<video src="videos/genesis_sim2sim.mp4" controls muted width="560"></video>

▶️ [genesis_sim2sim.mp4](videos/genesis_sim2sim.mp4)

---

## 5 · Evaluate on the real robot

**Real SO-100 running the same checkpoint trained only on simulator demos**

<video src="videos/sim2real_real_robot.mp4" controls muted width="640"></video>

▶️ [sim2real_real_robot.mp4](videos/sim2real_real_robot.mp4)

---

## 8 · Supplementary — building a scene

**Building a scene in LuckyEngine and getting it ready for recording**

<video src="videos/scene_creation.mp4" controls muted width="640"></video>

▶️ [scene_creation.mp4](videos/scene_creation.mp4)

---

For the complete step-by-step guide — training commands, eval loops, the DICE
encoder, latency budgets, and the install table — see
[getting-started-lerobot.md](getting-started-lerobot.md).
