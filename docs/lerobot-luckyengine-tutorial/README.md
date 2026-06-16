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

https://github.com/user-attachments/assets/17a122b4-b880-4422-af7f-497fd37d2cb9

<sub>▶️ [hero_teleop.mp4](videos/hero_teleop.mp4)</sub>

**Scripted in LuckyEngine** — hands-free, repeatable, same dataset format

https://github.com/user-attachments/assets/bdea560b-1175-45c9-b4a0-71a616ea81c8

<sub>▶️ [hero_sim.mp4](videos/hero_sim.mp4)</sub>

**The payoff** — the same checkpoint, autonomous on the real SO-100 (two-camera DICE-IMLE @ 30 Hz)

https://github.com/user-attachments/assets/c83c4fb0-23d2-4ed1-a09b-91e1e6d3adad

<sub>▶️ [hero_sim2real.mp4](videos/hero_sim2real.mp4)</sub>

---

## 1 · Record demos in LE

Scripted C# scene scripts drive the robot through waypoints while the engine
writes a LeRobot 3.0 dataset to disk in parallel.

**End-to-end walkthrough of recording demonstrations in LE**

https://github.com/user-attachments/assets/99eb681d-80f6-44be-814f-c86d0ae9f842

<sub>▶️ [recording_walkthrough.mp4](videos/recording_walkthrough.mp4)</sub>

**SO-100 pick-and-place recorded inside LuckyEngine** — the dataset behind the case study

https://github.com/user-attachments/assets/4f3ba857-fc91-4cce-88cc-907b7a841d56

<sub>▶️ [so100_sim.mp4](videos/so100_sim.mp4)</sub>

---

## 3 · Evaluate in LE (in-domain)

**Trained policy running in LE during in-domain eval** — finalist checkpoint at 96×96 / 30 fps

https://github.com/user-attachments/assets/b45317d8-5bd5-40ce-bd2d-c5550e9de8af

<sub>▶️ [le_finalist_trials.mp4](videos/le_finalist_trials.mp4)</sub>

---

## 4 · Evaluate in Genesis (sim-to-sim)

**Vanilla IMLE checkpoint `044800`, zero-shot in Genesis** — 96×96 @ 30 fps

https://github.com/user-attachments/assets/bd0307ac-e452-449f-b53e-cd7144f9339a

<sub>▶️ [genesis_sim2sim.mp4](videos/genesis_sim2sim.mp4)</sub>

---

## 5 · Evaluate on the real robot

**Real SO-100 running the same checkpoint trained only on simulator demos**

https://github.com/user-attachments/assets/8cb3b6d9-d4b6-4430-993c-7c690854dbcc

<sub>▶️ [sim2real_real_robot.mp4](videos/sim2real_real_robot.mp4)</sub>

---

## 8 · Supplementary — building a scene

**Building a scene in LuckyEngine and getting it ready for recording**

https://github.com/user-attachments/assets/9dad2763-90e3-43be-bcb9-30a781a8407f

<sub>▶️ [scene_creation.mp4](videos/scene_creation.mp4)</sub>

---

For the complete step-by-step guide — training commands, eval loops, the DICE
encoder, latency budgets, and the install table — see
[getting-started-lerobot.md](getting-started-lerobot.md).
