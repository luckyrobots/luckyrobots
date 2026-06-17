# LuckyEngine + LeRobot: Getting Started

Record demonstrations in **LuckyEngine** (LE), train an imitation-learning
policy with **LeRobot**, and deploy the same checkpoint in LE, then Genesis,
then on a real SO-100 — **72% success on the real robot, trained only on
simulator demos** (no domain randomization, no real-data fine-tuning).

- 📖 Full step-by-step guide: [getting-started-lerobot.md](getting-started-lerobot.md)
- 🌐 Rendered tutorial: <https://luckyrobots.github.io/lerobot-luckyengine-tutorial/>
- 📦 Python SDK: [`luckyrobots`](https://github.com/luckyrobots/luckyrobots)

---

## The pitch: sim demos → real robot

Manual leader-arm teleop gives you one human, one demo at a time. Scripting the
same task in LuckyEngine is hands-free, repeatable, and writes the identical
LeRobot dataset format.

**Manual leader-arm teleop** — one human, one demo at a time

<video src="https://github.com/user-attachments/assets/0274d5c0-7600-4299-b734-ba66ad0446b1" controls muted width="100%"></video>

<sub>▶️ [hero_teleop.mp4](https://github.com/user-attachments/assets/0274d5c0-7600-4299-b734-ba66ad0446b1)</sub>

**Scripted in LuckyEngine** — hands-free, repeatable, same dataset format

<video src="https://github.com/user-attachments/assets/dbb5e470-de5a-4b11-b4e5-a0c091bf7315" controls muted width="100%"></video>

<sub>▶️ [hero_sim.mp4](https://github.com/user-attachments/assets/dbb5e470-de5a-4b11-b4e5-a0c091bf7315)</sub>

**The payoff** — the same checkpoint, autonomous on the real SO-100 (two-camera DICE-IMLE @ 30 Hz)

<video src="https://github.com/user-attachments/assets/26c5ff9e-6efd-43bf-92a3-c6d603e6cbfc" controls muted width="100%"></video>

<sub>▶️ [hero_sim2real.mp4](https://github.com/user-attachments/assets/26c5ff9e-6efd-43bf-92a3-c6d603e6cbfc)</sub>

---

## 1 · Record demos in LE

Scripted C# scene scripts drive the robot through waypoints while the engine
writes a LeRobot 3.0 dataset to disk in parallel.

**End-to-end walkthrough of recording demonstrations in LE**

<video src="https://github.com/user-attachments/assets/010ce79e-2a9c-471a-b7bb-7c4bacea058c" controls muted width="100%"></video>

<sub>▶️ [recording_walkthrough.mp4](https://github.com/user-attachments/assets/010ce79e-2a9c-471a-b7bb-7c4bacea058c)</sub>

**SO-100 pick-and-place recorded inside LuckyEngine** — the dataset behind the case study

<video src="https://github.com/user-attachments/assets/8ba270a6-b983-496a-bfaf-87f43e686443" controls muted width="100%"></video>

<sub>▶️ [so100_sim.mp4](https://github.com/user-attachments/assets/8ba270a6-b983-496a-bfaf-87f43e686443)</sub>

---

## 3 · Evaluate in LE (in-domain)

**Trained policy running in LE during in-domain eval** — finalist checkpoint at 96×96 / 30 fps

<video src="https://github.com/user-attachments/assets/e5cdea1b-9028-4357-b2b8-0f327b2ee795" controls muted width="100%"></video>

<sub>▶️ [le_finalist_trials.mp4](https://github.com/user-attachments/assets/e5cdea1b-9028-4357-b2b8-0f327b2ee795)</sub>

---

## 4 · Evaluate in Genesis (sim-to-sim)

**Vanilla IMLE checkpoint `044800`, zero-shot in Genesis** — 96×96 @ 30 fps

<video src="https://github.com/user-attachments/assets/ee06523f-9028-45dd-b07e-6e37f98cbf65" controls muted width="100%"></video>

<sub>▶️ [genesis_sim2sim.mp4](https://github.com/user-attachments/assets/ee06523f-9028-45dd-b07e-6e37f98cbf65)</sub>

---

## 5 · Evaluate on the real robot

**Real SO-100 running the same checkpoint trained only on simulator demos**

<video src="https://github.com/user-attachments/assets/7a348355-34d0-472e-9b7a-52bb1c209f6c" controls muted width="100%"></video>

<sub>▶️ [sim2real_real_robot.mp4](https://github.com/user-attachments/assets/7a348355-34d0-472e-9b7a-52bb1c209f6c)</sub>

---

## 8 · Supplementary — building a scene

**Building a scene in LuckyEngine and getting it ready for recording**

<video src="https://github.com/user-attachments/assets/75a46b2d-2721-419b-879e-2e7d99c07ca7" controls muted width="100%"></video>

<sub>▶️ [scene_creation.mp4](https://github.com/user-attachments/assets/75a46b2d-2721-419b-879e-2e7d99c07ca7)</sub>

---

For the complete step-by-step guide — training commands, eval loops, the DICE
encoder, latency budgets, and the install table — see
[getting-started-lerobot.md](getting-started-lerobot.md).
