"""CLI for luckyrobots system identification.

Registered as the ``sysid`` subcommand of the top-level ``luckyrobots`` CLI.
Usage: ``luckyrobots sysid <command>``
"""

from __future__ import annotations

from pathlib import Path

import click


@click.group("sysid")
def sysid():
    """System identification for sim-to-real calibration."""
    pass


@sysid.command()
@click.option("--host", default="127.0.0.1", help="LuckyEngine gRPC host.")
@click.option("--port", default=50051, type=int, help="LuckyEngine gRPC port.")
@click.option("--robot", default="unitreego2", help="Robot name.")
@click.option(
    "--signal",
    type=click.Choice(["chirp", "multisine", "random_steps"]),
    default="chirp",
    help="Excitation signal type.",
)
@click.option("--duration", default=15.0, type=float, help="Collection duration (seconds).")
@click.option("--dt", default=0.02, type=float, help="Timestep (seconds).")
@click.option("--amplitude", default=0.3, type=float, help="Signal amplitude.")
@click.option("--num-joints", default=12, type=int, help="Number of joints.")
@click.option("-o", "--output", default="trajectory.npz", help="Output file path.")
def collect(host, port, robot, signal, duration, dt, amplitude, num_joints, output):
    """Collect trajectory data from LuckyEngine."""
    from .collector import EngineCollector
    from .excitation import chirp as chirp_fn
    from .excitation import multisine as ms_fn
    from .excitation import random_steps as rs_fn

    signal_generators = {
        "chirp": chirp_fn,
        "multisine": ms_fn,
        "random_steps": rs_fn,
    }

    ctrl_seq = signal_generators[signal](
        duration=duration, dt=dt, amplitude=amplitude, num_joints=num_joints,
    )

    click.echo(f"Generating {signal} signal: {ctrl_seq.shape[0]} steps, {num_joints} joints")
    click.echo(f"Connecting to LuckyEngine at {host}:{port}...")

    with EngineCollector(host=host, port=port, robot_name=robot) as collector:
        click.echo("Collecting trajectory data...")
        traj = collector.collect(ctrl_seq, dt=dt)

    path = traj.save(output)
    click.echo(f"Saved {traj.num_steps} steps ({traj.duration:.1f}s) to {path}")


@sysid.command()
@click.argument("data_path", type=click.Path(exists=True))
@click.option("-m", "--model", required=True, type=click.Path(exists=True), help="MuJoCo XML model.")
@click.option("--preset", default=None, help="Parameter preset (e.g. go2:motor).")
@click.option("--max-iter", default=100, type=int, help="Max optimization iterations.")
@click.option("--report-dir", default=None, help="Directory for identification report.")
@click.option("-o", "--output", default="sysid_result.json", help="Output result file.")
def identify(data_path, model, preset, max_iter, report_dir, output):
    """Identify model parameters from trajectory data."""
    from .trajectory import TrajectoryData
    from .sysid import identify as run_identify
    from .parameters import load_preset

    traj = TrajectoryData.load(data_path)
    click.echo(f"Loaded trajectory: {traj.num_steps} steps, {traj.duration:.1f}s")

    if preset is None:
        raise click.UsageError("--preset is required (e.g. go2:motor)")

    robot, group = preset.split(":")
    specs = load_preset(robot, group)
    click.echo(f"Identifying {len(specs)} parameters ({robot}:{group})")

    result = run_identify(
        model_xml=model,
        trajectories=traj,
        param_specs=specs,
        report_dir=report_dir,
        max_iterations=max_iter,
    )

    result.save(output)
    click.echo(f"\nResidual: {result.residual_before:.4f} -> {result.residual_after:.4f}")
    click.echo(f"Results saved to {output}")

    click.echo("\nIdentified parameters:")
    for name, val in result.params.items():
        initial = result.initial_params[name]
        ci = result.confidence[name]
        pct = ((val - initial) / initial * 100) if initial != 0 else float("inf")
        click.echo(
            f"  {name}: {initial:.4f} -> {val:.4f} ({pct:+.1f}%) "
            f"CI=[{ci[0]:.4f}, {ci[1]:.4f}]"
        )


@sysid.command()
@click.argument("result_path", type=click.Path(exists=True))
@click.option("-m", "--model", required=True, type=click.Path(exists=True), help="MuJoCo XML model.")
@click.option("-o", "--output", required=True, help="Output calibrated XML path.")
def apply(result_path, model, output):
    """Apply identified parameters to create a calibrated MuJoCo XML."""
    from .sysid import SysIdResult
    from .calibrate import apply_params

    result = SysIdResult.load(result_path)
    out_path = apply_params(model, result, output)
    click.echo(f"Calibrated model written to {out_path}")
    click.echo(f"Modified {len(result.params)} parameters")


@sysid.command()
@click.option("--robot", default=None, help="Filter by robot name.")
def presets(robot):
    """List available parameter presets."""
    from .parameters import GO2_PRESETS

    all_presets = {"go2": GO2_PRESETS}

    if robot:
        filtered = {robot.lower(): all_presets.get(robot.lower(), {})}
    else:
        filtered = all_presets

    for rname, groups in filtered.items():
        click.echo(f"\n{rname}:")
        for gname, specs in groups.items():
            click.echo(f"  {rname}:{gname} ({len(specs)} parameters)")
            for spec in specs:
                click.echo(
                    f"    {spec.name}: {spec.element}.{spec.mj_name}.{spec.attribute} "
                    f"[{spec.min_value}, {spec.max_value}] (nominal={spec.nominal})"
                )


if __name__ == "__main__":
    sysid()
